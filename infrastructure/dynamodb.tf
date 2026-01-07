# Stocks table - stores valid ticker symbols
resource "aws_dynamodb_table" "stocks" {
  name         = "${var.project_name}-stocks"
  billing_mode = "PAY_PER_REQUEST" # On-demand, stays in free tier for low usage

  hash_key = "ticker"

  attribute {
    name = "ticker"
    type = "S"
  }

  tags = {
    Name = "${var.project_name}-stocks"
  }
}

# Mentions table - stores Reddit post mentions
resource "aws_dynamodb_table" "mentions" {
  name         = "${var.project_name}-mentions"
  billing_mode = "PAY_PER_REQUEST"

  hash_key  = "ticker"
  range_key = "timestamp_post_id" # Format: "2024-01-15T14:30:00Z#abc123"

  attribute {
    name = "ticker"
    type = "S"
  }

  attribute {
    name = "timestamp_post_id"
    type = "S"
  }

  attribute {
    name = "subreddit"
    type = "S"
  }

  # GSI for querying by subreddit
  global_secondary_index {
    name            = "by-subreddit"
    hash_key        = "subreddit"
    range_key       = "timestamp_post_id"
    projection_type = "ALL"
  }

  tags = {
    Name = "${var.project_name}-mentions"
  }
}

# Metadata table - stores last fetch timestamps, etc.
resource "aws_dynamodb_table" "metadata" {
  name         = "${var.project_name}-metadata"
  billing_mode = "PAY_PER_REQUEST"

  hash_key = "key"

  attribute {
    name = "key"
    type = "S"
  }

  tags = {
    Name = "${var.project_name}-metadata"
  }
}

# Trends table - stores pre-aggregated trending data
resource "aws_dynamodb_table" "trends" {
  name         = "${var.project_name}-trends"
  billing_mode = "PAY_PER_REQUEST"

  hash_key  = "period"
  range_key = "ticker"

  attribute {
    name = "period"
    type = "S"
  }

  attribute {
    name = "ticker"
    type = "S"
  }

  attribute {
    name = "mention_count"
    type = "N"
  }

  # GSI for sorting by mention count (get top N tickers)
  global_secondary_index {
    name            = "by-mention-count"
    hash_key        = "period"
    range_key       = "mention_count"
    projection_type = "ALL"
  }

  tags = {
    Name = "${var.project_name}-trends"
  }
}
