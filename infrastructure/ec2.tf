# EC2 Worker Infrastructure
# Fully automated - runs worker.py as a systemd service

# ============================================================================
# Variables
# ============================================================================

variable "enable_ec2_worker" {
  description = "Enable EC2 worker instance"
  type        = bool
  default     = true
}

variable "ec2_instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t2.micro"
}

variable "worker_daemon_sleep_seconds" {
  description = "Sleep interval between worker cycles (seconds)"
  type        = number
  default     = 600  # 10 minutes
}

variable "ec2_key_name" {
  description = "EC2 key pair name for SSH access"
  type        = string
  default     = "stockmentions-worker"
}

# ============================================================================
# Data Sources
# ============================================================================

data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

data "aws_vpc" "default" {
  default = true
}

# ============================================================================
# Upload worker.py to S3
# ============================================================================

resource "aws_s3_object" "worker_script" {
  bucket = aws_s3_bucket.lambda_packages.id
  key    = "worker.py"
  source = "${path.module}/../worker/worker.py"
  etag   = filemd5("${path.module}/../worker/worker.py")
}

# ============================================================================
# IAM Role for EC2 Worker
# ============================================================================

resource "aws_iam_role" "ec2_worker" {
  name = "${var.project_name}-ec2-worker-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

# SSM Session Manager access
resource "aws_iam_role_policy_attachment" "ec2_ssm_managed" {
  role       = aws_iam_role.ec2_worker.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "ec2_worker" {
  name = "${var.project_name}-ec2-worker-profile"
  role = aws_iam_role.ec2_worker.name
}

# DynamoDB access
resource "aws_iam_role_policy" "ec2_dynamodb" {
  name = "${var.project_name}-ec2-dynamodb"
  role = aws_iam_role.ec2_worker.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:BatchWriteItem"
        ]
        Resource = [
          aws_dynamodb_table.stocks.arn,
          aws_dynamodb_table.mentions.arn,
          "${aws_dynamodb_table.mentions.arn}/index/*",
          aws_dynamodb_table.metadata.arn
        ]
      }
    ]
  })
}

# SSM Parameter Store access (for Reddit credentials)
resource "aws_iam_role_policy" "ec2_ssm" {
  name = "${var.project_name}-ec2-ssm"
  role = aws_iam_role.ec2_worker.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = [
          "arn:aws:ssm:${var.aws_region}:*:parameter${var.reddit_client_id_param}",
          "arn:aws:ssm:${var.aws_region}:*:parameter${var.reddit_client_secret_param}"
        ]
      }
    ]
  })
}

# S3 access (to download worker.py)
resource "aws_iam_role_policy" "ec2_s3" {
  name = "${var.project_name}-ec2-s3"
  role = aws_iam_role.ec2_worker.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = [
          "${aws_s3_bucket.lambda_packages.arn}/worker.py"
        ]
      }
    ]
  })
}

# ============================================================================
# Security Group
# ============================================================================

resource "aws_security_group" "worker" {
  count = var.enable_ec2_worker ? 1 : 0

  name        = "${var.project_name}-worker-sg"
  description = "Security group for stock mentions worker"
  vpc_id      = data.aws_vpc.default.id

  # Outbound internet access (required for Reddit API and DynamoDB)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # SSH access for debugging
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["75.228.171.174/32"]
  }

  tags = {
    Name = "${var.project_name}-worker-sg"
  }
}

# ============================================================================
# EC2 Instance
# ============================================================================

resource "aws_instance" "worker" {
  count = var.enable_ec2_worker ? 1 : 0

  ami                    = data.aws_ami.amazon_linux_2023.id
  instance_type          = var.ec2_instance_type
  iam_instance_profile   = aws_iam_instance_profile.ec2_worker.name
  vpc_security_group_ids = [aws_security_group.worker[0].id]
  key_name               = var.ec2_key_name

  tags = {
    Name = "${var.project_name}-worker"
  }

  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    aws_region                = var.aws_region
    stocks_table              = aws_dynamodb_table.stocks.name
    mentions_table            = aws_dynamodb_table.mentions.name
    metadata_table            = aws_dynamodb_table.metadata.name
    ssm_client_id_param       = var.reddit_client_id_param
    ssm_client_secret_param   = var.reddit_client_secret_param
    target_subreddits         = join(",", var.target_subreddits)
    daemon_sleep_seconds      = var.worker_daemon_sleep_seconds
    s3_bucket                 = aws_s3_bucket.lambda_packages.id
  }))

  depends_on = [aws_s3_object.worker_script]

  # Ensure instance is replaced when user_data changes
  user_data_replace_on_change = true
}

# ============================================================================
# Outputs
# ============================================================================

output "ec2_worker_instance_id" {
  value       = var.enable_ec2_worker ? aws_instance.worker[0].id : null
  description = "EC2 worker instance ID"
}

output "ec2_worker_public_ip" {
  value       = var.enable_ec2_worker ? aws_instance.worker[0].public_ip : null
  description = "EC2 worker public IP (if applicable)"
}

output "ec2_worker_instance_profile" {
  value       = aws_iam_instance_profile.ec2_worker.name
  description = "IAM instance profile name for EC2 worker"
}
