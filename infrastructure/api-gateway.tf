# HTTP API (v2) - cheaper than REST API
resource "aws_apigatewayv2_api" "main" {
  name          = "${var.project_name}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"] # Restrict in production
    allow_methods = ["GET", "OPTIONS"]
    allow_headers = ["Content-Type"]
    max_age       = 3600
  }

  tags = {
    Name = "${var.project_name}-api"
  }
}

# Default stage
resource "aws_apigatewayv2_stage" "main" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      responseLength = "$context.responseLength"
      errorMessage   = "$context.error.message"
    })
  }
}

# CloudWatch log group for API Gateway
resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${var.project_name}"
  retention_in_days = 7
}

# Lambda integration
resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api_handler.invoke_arn
  payload_format_version = "2.0"
}

# GET /trending
resource "aws_apigatewayv2_route" "trending" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /trending"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# GET /ticker/{symbol}
resource "aws_apigatewayv2_route" "ticker" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /ticker/{symbol}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# GET /subreddit/{name}
resource "aws_apigatewayv2_route" "subreddit" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /subreddit/{name}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}
