# Stock sync schedule - every 3 days at 6 AM UTC
resource "aws_cloudwatch_event_rule" "stock_sync" {
  name                = "${var.project_name}-stock-sync"
  description         = "Trigger stock sync Lambda every 3 days"
  schedule_expression = "rate(3 days)"

  tags = {
    Name = "${var.project_name}-stock-sync"
  }
}

resource "aws_cloudwatch_event_target" "stock_sync" {
  rule      = aws_cloudwatch_event_rule.stock_sync.name
  target_id = "stock-sync-lambda"
  arn       = aws_lambda_function.stock_sync.arn
}

resource "aws_lambda_permission" "stock_sync_eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.stock_sync.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.stock_sync.arn
}

# Reddit fetch schedule - every hour
resource "aws_cloudwatch_event_rule" "reddit_fetch" {
  name                = "${var.project_name}-reddit-fetch"
  description         = "Trigger Reddit fetch Lambda every hour"
  schedule_expression = "rate(1 hour)"

  tags = {
    Name = "${var.project_name}-reddit-fetch"
  }
}

resource "aws_cloudwatch_event_target" "reddit_fetch" {
  rule      = aws_cloudwatch_event_rule.reddit_fetch.name
  target_id = "reddit-fetch-lambda"
  arn       = aws_lambda_function.reddit_fetch.arn
}

resource "aws_lambda_permission" "reddit_fetch_eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.reddit_fetch.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.reddit_fetch.arn
}
