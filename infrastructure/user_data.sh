#!/bin/bash
# EC2 User Data Script - Downloads worker from S3
set -ex
exec > >(tee /var/log/user-data.log) 2>&1

# Install dependencies
dnf update -y
dnf install -y python3.11 python3.11-pip aws-cli

# Create app directory
mkdir -p /opt/stock-mentions
cd /opt/stock-mentions

# Download worker from S3
aws s3 cp s3://${s3_bucket}/worker.py /opt/stock-mentions/worker.py
chmod +x /opt/stock-mentions/worker.py

# Install Python dependencies
python3.11 -m pip install boto3 praw

# Create environment file
cat > /etc/stock-mentions.env << 'EOF'
AWS_REGION=${aws_region}
STOCKS_TABLE=${stocks_table}
MENTIONS_TABLE=${mentions_table}
METADATA_TABLE=${metadata_table}
SSM_CLIENT_ID_PARAM=${ssm_client_id_param}
SSM_CLIENT_SECRET_PARAM=${ssm_client_secret_param}
TARGET_SUBREDDITS=${target_subreddits}
DAEMON_SLEEP_SECONDS=${daemon_sleep_seconds}
POSTS_PER_SUBREDDIT=100
SUBREDDIT_DELAY_SECONDS=5
POST_DELAY_SECONDS=0.5
EOF

# Create systemd service
cat > /etc/systemd/system/stock-mentions-worker.service << 'EOF'
[Unit]
Description=Stock Mentions Reddit Worker
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile=/etc/stock-mentions.env
ExecStart=/usr/bin/python3.11 /opt/stock-mentions/worker.py --daemon
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
systemctl daemon-reload
systemctl enable stock-mentions-worker
systemctl start stock-mentions-worker

echo "Setup complete"
