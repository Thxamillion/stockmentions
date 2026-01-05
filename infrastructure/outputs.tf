output "api_endpoint" {
  description = "API Gateway endpoint URL"
  value       = aws_apigatewayv2_stage.main.invoke_url
}

output "stocks_table_name" {
  description = "DynamoDB stocks table name"
  value       = aws_dynamodb_table.stocks.name
}

output "mentions_table_name" {
  description = "DynamoDB mentions table name"
  value       = aws_dynamodb_table.mentions.name
}

output "frontend_bucket" {
  description = "S3 bucket for frontend hosting"
  value       = aws_s3_bucket.frontend.id
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = aws_cloudfront_distribution.frontend.id
}

output "cloudfront_domain" {
  description = "CloudFront domain name"
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "sqs_queue_url" {
  description = "SQS queue URL for Reddit posts"
  value       = aws_sqs_queue.posts.url
}
