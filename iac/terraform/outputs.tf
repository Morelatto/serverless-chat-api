output "api_url" {
  value = aws_lambda_function_url.api.function_url
}

output "lambda_name" {
  value = aws_lambda_function.api.function_name
}

output "table_name" {
  value = aws_dynamodb_table.main.name
}

output "estimated_cost" {
  value = "~$5/month for 10k requests"
}
