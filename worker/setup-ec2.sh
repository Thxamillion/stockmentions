#!/bin/bash
# EC2 Setup Script for Stock Mentions Worker
# Run this on a fresh Amazon Linux 2 or Ubuntu EC2 instance

set -e

echo "=== Stock Mentions EC2 Worker Setup ==="

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "Cannot detect OS"
    exit 1
fi

echo "Detected OS: $OS"

# Install Python and dependencies
if [ "$OS" = "amzn" ] || [ "$OS" = "rhel" ] || [ "$OS" = "centos" ]; then
    echo "Installing Python on Amazon Linux / RHEL..."
    sudo yum update -y
    sudo yum install -y python3 python3-pip git
elif [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
    echo "Installing Python on Ubuntu / Debian..."
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip python3-venv git
else
    echo "Unsupported OS: $OS"
    exit 1
fi

# Create app directory
APP_DIR="/home/ec2-user/stockmentions"
if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
    APP_DIR="/home/ubuntu/stockmentions"
fi

echo "App directory: $APP_DIR"

# Clone or copy files (assuming files are already in place)
if [ ! -d "$APP_DIR/worker" ]; then
    echo "Creating worker directory..."
    mkdir -p "$APP_DIR/worker"
fi

# Create virtual environment
echo "Creating Python virtual environment..."
cd "$APP_DIR/worker"
python3 -m venv venv
source venv/bin/activate

# Install requirements
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo ""
echo "1. Ensure EC2 instance has an IAM role with DynamoDB and SSM permissions"
echo "   Required permissions:"
echo "   - dynamodb:GetItem, PutItem, Query, Scan, BatchWriteItem on stock-mentions-* tables"
echo "   - ssm:GetParameter, GetParameters on /stock-mentions/* parameters"
echo ""
echo "2. Test the worker:"
echo "   cd $APP_DIR/worker"
echo "   source venv/bin/activate"
echo "   python worker.py --verbose"
echo ""
echo "3. For daemon mode (systemd):"
echo "   sudo cp stock-mentions-worker.service /etc/systemd/system/"
echo "   # Edit the service file to update paths if needed"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable stock-mentions-worker"
echo "   sudo systemctl start stock-mentions-worker"
echo "   sudo systemctl status stock-mentions-worker"
echo "   sudo journalctl -u stock-mentions-worker -f"
echo ""
echo "4. For cron mode (every 10 minutes):"
echo "   crontab -e"
echo "   # Add: */10 * * * * cd $APP_DIR/worker && ./venv/bin/python worker.py >> /var/log/stock-mentions.log 2>&1"
echo ""
