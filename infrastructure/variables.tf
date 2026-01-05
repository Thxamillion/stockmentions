variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "stock-mentions"
}

# Reddit API credentials stored in SSM Parameter Store
variable "reddit_client_id_param" {
  description = "SSM parameter name for Reddit client ID"
  type        = string
  default     = "/stock-mentions/reddit_client_id"
}

variable "reddit_client_secret_param" {
  description = "SSM parameter name for Reddit client secret"
  type        = string
  default     = "/stock-mentions/reddit_client_secret"
}

# Target subreddits for monitoring
variable "target_subreddits" {
  description = "List of subreddits to monitor"
  type        = list(string)
  default = [
    "wallstreetbets",
    "stocks",
    "investing",
    "stockmarket",
    "options"
  ]
}
