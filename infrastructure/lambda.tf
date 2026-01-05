# S3 bucket for Lambda deployment packages
resource "aws_s3_bucket" "lambda_packages" {
  bucket = "${var.project_name}-lambda-packages-${data.aws_caller_identity.current.account_id}"
}

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket_versioning" "lambda_packages" {
  bucket = aws_s3_bucket.lambda_packages.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Placeholder zip for initial deployment (will be replaced by deploy script)
data "archive_file" "placeholder" {
  type        = "zip"
  output_path = "${path.module}/.terraform/placeholder.zip"

  source {
    content  = "# placeholder"
    filename = "handler.py"
  }
}

# Stock Sync Lambda
resource "aws_lambda_function" "stock_sync" {
  function_name = "${var.project_name}-stock-sync"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = 300 # 5 minutes
  memory_size   = 256

  filename         = data.archive_file.placeholder.output_path
  source_code_hash = data.archive_file.placeholder.output_base64sha256

  environment {
    variables = {
      STOCKS_TABLE = aws_dynamodb_table.stocks.name
    }
  }

  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }

  tags = {
    Name = "${var.project_name}-stock-sync"
  }
}

# Reddit Fetch Lambda
resource "aws_lambda_function" "reddit_fetch" {
  function_name = "${var.project_name}-reddit-fetch"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = 60
  memory_size   = 128

  filename         = data.archive_file.placeholder.output_path
  source_code_hash = data.archive_file.placeholder.output_base64sha256

  environment {
    variables = {
      SQS_QUEUE_URL              = aws_sqs_queue.posts.url
      METADATA_TABLE             = aws_dynamodb_table.metadata.name
      REDDIT_CLIENT_ID_PARAM     = var.reddit_client_id_param
      REDDIT_CLIENT_SECRET_PARAM = var.reddit_client_secret_param
      TARGET_SUBREDDITS          = join(",", var.target_subreddits)
    }
  }

  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }

  tags = {
    Name = "${var.project_name}-reddit-fetch"
  }
}

# Mention Processor Lambda
resource "aws_lambda_function" "mention_processor" {
  function_name = "${var.project_name}-mention-processor"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 128

  filename         = data.archive_file.placeholder.output_path
  source_code_hash = data.archive_file.placeholder.output_base64sha256

  environment {
    variables = {
      STOCKS_TABLE   = aws_dynamodb_table.stocks.name
      MENTIONS_TABLE = aws_dynamodb_table.mentions.name
    }
  }

  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }

  tags = {
    Name = "${var.project_name}-mention-processor"
  }
}

# SQS trigger for mention processor
resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = aws_sqs_queue.posts.arn
  function_name    = aws_lambda_function.mention_processor.arn
  batch_size       = 10
}

# API Handler Lambda
resource "aws_lambda_function" "api_handler" {
  function_name = "${var.project_name}-api-handler"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = 10
  memory_size   = 128

  filename         = data.archive_file.placeholder.output_path
  source_code_hash = data.archive_file.placeholder.output_base64sha256

  environment {
    variables = {
      STOCKS_TABLE   = aws_dynamodb_table.stocks.name
      MENTIONS_TABLE = aws_dynamodb_table.mentions.name
    }
  }

  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }

  tags = {
    Name = "${var.project_name}-api-handler"
  }
}

# Permission for API Gateway to invoke Lambda
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}
