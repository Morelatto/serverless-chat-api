terraform {
  required_version = ">= 1.5"

  backend "s3" {
    bucket         = "serverless-chat-api-terraform-state"
    key            = "serverless/terraform.tfstate"  # Changed key to avoid state conflicts
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
      ManagedBy   = "Terraform"
    }
  }
}

# ElastiCache Serverless for Redis caching (pay per use, no idle costs!)
resource "aws_elasticache_serverless_cache" "redis" {
  count = var.enable_cache ? 1 : 0

  name        = "${var.project_name}-cache-${var.environment}"
  engine      = "redis"
  description = "Serverless Redis cache for chat responses"

  # Security
  security_group_ids = [aws_security_group.cache[0].id]
  subnet_ids         = data.aws_subnets.default.ids

  # Optional: Set cache usage limits to control costs
  cache_usage_limits {
    data_storage {
      maximum = 1  # GB
      unit    = "GB"
    }
    ecpu_per_second {
      maximum = 5000  # ElastiCache Processing Units
    }
  }

  tags = {
    Name = "${var.project_name}-cache"
  }
}

# Security group for ElastiCache (if enabled)
resource "aws_security_group" "cache" {
  count = var.enable_cache ? 1 : 0

  name        = "${var.project_name}-cache-${var.environment}"
  description = "Security group for ElastiCache Serverless"

  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.default.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Get default VPC data
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# DynamoDB table for chat history storage
resource "aws_dynamodb_table" "main" {
  name         = "${var.project_name}-chat-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"  # No idle costs!
  hash_key     = "user_id"
  range_key    = "timestamp"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  attribute {
    name = "message_id"
    type = "S"
  }

  global_secondary_index {
    name            = "message_id_index"
    hash_key        = "message_id"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Name = "${var.project_name}-chat-history"
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

# ECR lifecycle policy to keep only last 5 images
resource "aws_ecr_lifecycle_policy" "lambda" {
  repository = aws_ecr_repository.lambda.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 5 images"
      selection = {
        tagStatus     = "any"
        countType     = "imageCountMoreThan"
        countNumber   = 5
      }
      action = {
        type = "expire"
      }
    }]
  })
}

# CloudWatch log group for Lambda
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.kms_key_id
}

# IAM role for Lambda
resource "aws_iam_role" "lambda" {
  name = "${var.project_name}-lambda-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# Attach basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Policy for DynamoDB access
resource "aws_iam_role_policy" "lambda_dynamodb" {
  name = "${var.project_name}-lambda-dynamodb-${var.environment}"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem"
        ]
        Resource = [
          aws_dynamodb_table.main.arn,
          "${aws_dynamodb_table.main.arn}/index/*"
        ]
      }
    ]
  })
}

# Lambda function
resource "aws_lambda_function" "api" {
  function_name = "${var.project_name}-${var.environment}"
  role          = aws_iam_role.lambda.arn

  # Container image configuration
  package_type = "Image"
  image_uri    = "${aws_ecr_repository.lambda.repository_url}:latest"

  # Performance configuration
  memory_size = var.lambda_memory_size
  timeout     = var.lambda_timeout

  # Environment variables
  environment {
    variables = {
      # Application settings
      CHAT_ENVIRONMENT = var.environment
      CHAT_LOG_LEVEL   = var.log_level

      # Database
      CHAT_DATABASE_URL = "dynamodb://${aws_dynamodb_table.main.name}"
      # AWS_REGION is automatically set by Lambda environment

      # Cache (if enabled)
      CHAT_REDIS_URL = var.enable_cache ? "redis://${aws_elasticache_serverless_cache.redis[0].endpoint[0].address}" : ""

      # LLM Configuration
      CHAT_LLM_PROVIDER      = var.llm_provider
      CHAT_GEMINI_API_KEY    = var.gemini_api_key
      CHAT_OPENROUTER_API_KEY = var.openrouter_api_key
      CHAT_OPENROUTER_MODEL  = var.openrouter_model_name

      # Security
      CHAT_SECRET_KEY = var.jwt_secret_key != "" ? var.jwt_secret_key : random_password.jwt_secret[0].result
      CHAT_REQUIRE_API_KEY = tostring(var.require_api_key)
      CHAT_API_KEY = var.api_key != "" ? var.api_key : random_password.api_key[0].result

      # CORS
      CHAT_CORS_ORIGINS = join(",", var.cors_origins)
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_logs,
    aws_cloudwatch_log_group.lambda,
  ]
}

# Lambda Function URL for HTTP access
resource "aws_lambda_function_url" "api" {
  function_name      = aws_lambda_function.api.function_name
  authorization_type = "NONE"  # We handle auth in the app

  cors {
    allow_origins     = var.cors_origins
    allow_methods     = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers     = ["*"]
    expose_headers    = ["*"]
    max_age           = 3600
    allow_credentials = true
  }
}

# Generate random JWT secret if not provided
resource "random_password" "jwt_secret" {
  count   = var.jwt_secret_key == "" ? 1 : 0
  length  = 64
  special = true
}

# Generate random API key if not provided
resource "random_password" "api_key" {
  count   = var.api_key == "" ? 1 : 0
  length  = 32
  special = false  # Easier to copy/paste
}

# CloudWatch alarms (optional, for monitoring)
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  count = var.enable_monitoring ? 1 : 0

  alarm_name          = "${var.project_name}-${var.environment}-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "This metric monitors lambda errors"

  dimensions = {
    FunctionName = aws_lambda_function.api.function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  count = var.enable_monitoring ? 1 : 0

  alarm_name          = "${var.project_name}-${var.environment}-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors lambda throttles"

  dimensions = {
    FunctionName = aws_lambda_function.api.function_name
  }
}

# Outputs
output "lambda_function_url" {
  description = "URL of the Lambda function"
  value       = aws_lambda_function_url.api.function_url
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB table"
  value       = aws_dynamodb_table.main.name
}

output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = aws_ecr_repository.lambda.repository_url
}

output "api_key" {
  description = "API key for authentication (if generated)"
  value       = var.api_key != "" ? var.api_key : try(random_password.api_key[0].result, "not-generated")
  sensitive   = true
}
