#!/bin/bash
set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
S3_BUCKET="stock-mentions-frontend-386667539733"
CLOUDFRONT_ID="E21CWGQMJS52ZZ"
REGION="us-east-1"
CLOUDFRONT_URL="https://d1ars4pboly1fj.cloudfront.net"

echo -e "${BLUE}🏗️  Building production bundle...${NC}"
npm run build

echo -e "${BLUE}📤 Uploading to S3 (${S3_BUCKET})...${NC}"
aws s3 sync dist/ s3://${S3_BUCKET} \
  --delete \
  --region ${REGION}

echo -e "${BLUE}🔄 Invalidating CloudFront cache...${NC}"
INVALIDATION_ID=$(aws cloudfront create-invalidation \
  --distribution-id ${CLOUDFRONT_ID} \
  --paths "/*" \
  --region ${REGION} \
  --query 'Invalidation.Id' \
  --output text)

echo -e "${YELLOW}⏳ Invalidation created: ${INVALIDATION_ID}${NC}"
echo -e "${YELLOW}   Cache will be cleared in 1-2 minutes${NC}"

echo ""
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo -e "${GREEN}🌍 Live at: ${CLOUDFRONT_URL}${NC}"
echo ""
echo "Tip: Check cache invalidation status with:"
echo "  aws cloudfront get-invalidation --distribution-id ${CLOUDFRONT_ID} --id ${INVALIDATION_ID}"
