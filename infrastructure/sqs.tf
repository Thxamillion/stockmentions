# SQS queue for Reddit posts - DISABLED (EC2 worker writes directly to DynamoDB)
# resource "aws_sqs_queue" "posts" {
#   name                       = "${var.project_name}-posts"
#   message_retention_seconds  = 86400  # 1 day
#   visibility_timeout_seconds = 60     # Must be >= Lambda timeout
#   receive_wait_time_seconds  = 10     # Long polling
#
#   # Dead letter queue for failed messages
#   redrive_policy = jsonencode({
#     deadLetterTargetArn = aws_sqs_queue.posts_dlq.arn
#     maxReceiveCount     = 3
#   })
#
#   tags = {
#     Name = "${var.project_name}-posts"
#   }
# }
#
# # Dead letter queue for failed processing
# resource "aws_sqs_queue" "posts_dlq" {
#   name                      = "${var.project_name}-posts-dlq"
#   message_retention_seconds = 1209600 # 14 days
#
#   tags = {
#     Name = "${var.project_name}-posts-dlq"
#   }
# }
