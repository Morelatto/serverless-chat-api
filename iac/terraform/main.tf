terraform {
  required_version = ">= 1.0"

  backend "s3" {
    bucket         = "serverless-chat-api-terraform-state"
    key            = "container/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
    }
  }
}

# ECR repository for Lambda container
resource "aws_ecr_repository" "lambda" {
  name                 = "${var.project_name}-${var.environment}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  force_delete = true
}

# IAM role for Lambda
resource "aws_iam_role" "lambda" {
  name = "${var.project_name}-lambda-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_dynamodb" {
  name = "${var.project_name}-lambda-policy"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:DescribeTable"
      ]
      Resource = [
        aws_dynamodb_table.main.arn,
        "${aws_dynamodb_table.main.arn}/index/*"
      ]
    }]
  })
}

# Lambda function using container image
resource "aws_lambda_function" "api" {
  function_name = "${var.project_name}-${var.environment}"
  role          = aws_iam_role.lambda.arn

  # Container image configuration
  package_type = "Image"
  image_uri    = "${aws_ecr_repository.lambda.repository_url}:latest"

  memory_size = var.lambda_memory_size
  timeout     = var.lambda_timeout

  environment {
    variables = {
      # Use CHAT_ prefix to match our application
      CHAT_HOST = "0.0.0.0"
      CHAT_PORT = "8000"
      CHAT_LOG_LEVEL = var.log_level

      # Database configuration - DynamoDB URL format
      CHAT_DATABASE_URL = "dynamodb://${aws_dynamodb_table.main.name}?region=${var.aws_region}"

      # LLM configuration
      CHAT_LLM_PROVIDER = var.llm_provider
      CHAT_GEMINI_API_KEY = var.gemini_api_key
      CHAT_OPENROUTER_API_KEY = var.openrouter_api_key
      CHAT_MODEL_NAME = var.openrouter_model_name

      # Rate limiting
      CHAT_RATE_LIMIT = "60/minute"
      CHAT_CACHE_TTL = "3600"

      # Environment
      ENVIRONMENT = var.environment
    }
  }

  depends_on = [
    aws_ecr_repository.lambda
  ]
}

# Lambda Function URL
resource "aws_lambda_function_url" "api" {
  function_name      = aws_lambda_function.api.function_name
  authorization_type = "NONE"

  cors {
    allow_origins = var.cors_origins
    allow_methods = ["*"]
    allow_headers = ["*"]
    max_age       = 3600
  }
}

# DynamoDB table for session storage and caching
resource "aws_dynamodb_table" "main" {
  name           = "${var.project_name}-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "pk"
  range_key      = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  global_secondary_index {
    name            = "user-index"
    hash_key        = "user_id"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}"
    Environment = var.environment
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${aws_lambda_function.api.function_name}"
  retention_in_days = var.log_retention_days

  kms_key_id = var.kms_key_id
}

# Outputs
output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.lambda.repository_url
}

output "lambda_function_url" {
  description = "Lambda Function URL"
  value       = aws_lambda_function_url.api.function_url
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.api.function_name
}

output "dynamodb_table_name" {
  description = "DynamoDB table name"
  value       = aws_dynamodb_table.main.name
}

output "deployment_commands" {
  description = "Commands to deploy the container"
  value = <<-EOT
    # Build and push Docker image:
    aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${aws_ecr_repository.lambda.repository_url}
    docker build --build-arg TARGET=lambda -t ${var.project_name} ../..
    docker tag ${var.project_name}:latest ${aws_ecr_repository.lambda.repository_url}:latest
    docker push ${aws_ecr_repository.lambda.repository_url}:latest

    # Update Lambda function:
    aws lambda update-function-code --function-name ${aws_lambda_function.api.function_name} --image-uri ${aws_ecr_repository.lambda.repository_url}:latest
  EOT
}
