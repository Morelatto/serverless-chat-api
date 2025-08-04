variable "project_name" {
  default = "processo-itau"
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
