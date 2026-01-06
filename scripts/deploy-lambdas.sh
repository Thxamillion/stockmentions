#!/bin/bash
set -e

# Configuration
LAMBDAS_DIR="$(dirname "$0")/../lambdas"
REGION="${AWS_REGION:-us-east-1}"
PROJECT_NAME="stock-mentions"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Stock Mentions Lambda Deployment ===${NC}"

# Check for AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI not found. Please install it first.${NC}"
    exit 1
fi

# Check for pip3 or pip
if command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
elif command -v pip &> /dev/null; then
    PIP_CMD="pip"
else
    echo -e "${RED}Error: pip not found. Please install Python and pip.${NC}"
    exit 1
fi

# Function to deploy a Lambda
deploy_lambda() {
    local lambda_name=$1
    local lambda_dir="${LAMBDAS_DIR}/${lambda_name}"
    local function_name="${PROJECT_NAME}-${lambda_name}"
    local package_dir="${lambda_dir}/package"
    local zip_file="${lambda_dir}/deployment.zip"

    echo -e "\n${YELLOW}Deploying ${function_name}...${NC}"

    # Clean up previous package
    rm -rf "${package_dir}" "${zip_file}"
    mkdir -p "${package_dir}"

    # Install dependencies
    if [ -f "${lambda_dir}/requirements.txt" ]; then
        echo "Installing dependencies..."
        $PIP_CMD install -r "${lambda_dir}/requirements.txt" -t "${package_dir}" --quiet --upgrade

        # Remove unnecessary files to reduce package size
        find "${package_dir}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find "${package_dir}" -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
        find "${package_dir}" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
        rm -rf "${package_dir}/boto3" "${package_dir}/botocore" 2>/dev/null || true
    fi

    # Copy handler
    cp "${lambda_dir}/handler.py" "${package_dir}/"

    # Create zip
    echo "Creating deployment package..."
    cd "${package_dir}"
    zip -r "${zip_file}" . --quiet
    cd - > /dev/null

    # Get zip size
    local zip_size=$(du -h "${zip_file}" | cut -f1)
    echo "Package size: ${zip_size}"

    # Update Lambda function
    echo "Uploading to AWS Lambda..."
    aws lambda update-function-code \
        --function-name "${function_name}" \
        --zip-file "fileb://${zip_file}" \
        --region "${REGION}" \
        --output text \
        --query 'FunctionArn'

    echo -e "${GREEN}✓ ${function_name} deployed successfully${NC}"

    # Clean up
    rm -rf "${package_dir}"
}

# Deploy all lambdas
LAMBDAS=("stock-sync" "reddit-fetch" "mention-processor" "api-handler")

for lambda in "${LAMBDAS[@]}"; do
    if [ -d "${LAMBDAS_DIR}/${lambda}" ]; then
        deploy_lambda "${lambda}"
    else
        echo -e "${RED}Warning: Lambda directory not found: ${lambda}${NC}"
    fi
done

echo -e "\n${GREEN}=== Deployment Complete ===${NC}"
echo ""
echo "Next steps:"
echo "1. Set up Reddit API credentials in SSM Parameter Store:"
echo "   aws ssm put-parameter --name '/stock-mentions/reddit_client_id' --value 'YOUR_CLIENT_ID' --type SecureString"
echo "   aws ssm put-parameter --name '/stock-mentions/reddit_client_secret' --value 'YOUR_SECRET' --type SecureString"
echo ""
echo "2. Manually trigger stock-sync to populate tickers:"
echo "   aws lambda invoke --function-name stock-mentions-stock-sync output.json"
echo ""
echo "3. Check CloudWatch logs for any errors"
