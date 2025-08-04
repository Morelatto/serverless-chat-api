variable "project_name" {
  default = "serverless-chat-api"
}

variable "environment" {
  default = "dev"
}

variable "aws_region" {
  default = "us-east-1"
}

variable "lambda_memory_size" {
  default = 512
}

variable "lambda_timeout" {
  default = 30
}

variable "log_retention_days" {
  default = 7
}

variable "check_existing_resources" {
  default = false
  description = "Check for existing resources before creating"
}
