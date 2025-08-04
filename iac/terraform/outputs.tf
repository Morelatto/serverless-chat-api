output "lambda_function_url" {
  description = "URL of the Lambda function"
  value       = aws_lambda_function_url.api.function_url
}

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.api.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.api.arn
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB table"
  value       = aws_dynamodb_table.main.name
}

output "dynamodb_table_arn" {
  description = "ARN of the DynamoDB table"
  value       = aws_dynamodb_table.main.arn
}

output "api_endpoints" {
  description = "Available API endpoints"
  value = {
    base   = aws_lambda_function_url.api.function_url
    health = "${aws_lambda_function_url.api.function_url}v1/health"
    chat   = "${aws_lambda_function_url.api.function_url}v1/chat"
    docs   = var.environment == "dev" ? "${aws_lambda_function_url.api.function_url}docs" : "Disabled in ${var.environment}"
  }
}

output "api_key" {
  description = "API key for authentication (if generated)"
  value       = var.api_key != "" ? var.api_key : "Auto-generated - check Lambda environment variables"
  sensitive   = true
}

output "deployment_info" {
  description = "Deployment information"
  value = {
    environment    = var.environment
    region         = var.aws_region
    llm_provider   = var.llm_provider
    memory_size    = var.lambda_memory_size
    timeout        = var.lambda_timeout
    log_retention  = var.log_retention_days
    monitoring     = var.enable_monitoring ? "Enabled" : "Disabled"
  }
}