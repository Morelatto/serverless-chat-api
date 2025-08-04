terraform {
  required_version = ">= 1.0"
  
  backend "s3" {
    bucket         = "serverless-chat-api-terraform-state"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
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

# Create Lambda deployment package directly from source
data "archive_file" "lambda_package" {
  type        = "zip"
  source_dir  = "${path.module}/../../src"
  output_path = "${path.module}/lambda_function.zip"
  
  excludes = [
    "__pycache__",
    "*.pyc",
    ".pytest_cache",
    "*.egg-info",
    ".env",
    "tests",
  ]
}

# Create a Lambda layer for dependencies
# In CI/CD, the layer directory is created by the workflow
# Locally, it can be created using build_layer.sh
resource "null_resource" "lambda_layer" {
  count = fileexists("${path.module}/layer/python") ? 0 : 1
  
  triggers = {
    pyproject = fileexists("${path.module}/../../pyproject.toml") ? filemd5("${path.module}/../../pyproject.toml") : "default"
  }

  provisioner "local-exec" {
    command = <<-EOT
      rm -rf ${path.module}/layer
      mkdir -p ${path.module}/layer/python
      
      # Install core Lambda dependencies
      pip install \
        fastapi==0.104.1 \
        mangum==0.17.0 \
        pydantic==2.5.0 \
        pydantic-settings==2.1.0 \
        google-generativeai==0.7.2 \
        openai==1.3.0 \
        tenacity==8.2.3 \
        boto3==1.34.0 \
        python-dotenv==1.0.0 \
        httpx==0.25.2 \
        -t ${path.module}/layer/python \
        --platform manylinux2014_x86_64 \
        --only-binary=:all: \
        --upgrade
    EOT
  }
}

data "archive_file" "lambda_layer" {
  type        = "zip"
  source_dir  = "${path.module}/layer"
  output_path = "${path.module}/lambda_layer.zip"
  
  depends_on = [null_resource.lambda_layer]
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
        "dynamodb:DeleteItem"
      ]
      Resource = [
        aws_dynamodb_table.main.arn,
        "${aws_dynamodb_table.main.arn}/index/*"
      ]
    }]
  })
}

# Lambda layer for dependencies
resource "aws_lambda_layer_version" "dependencies" {
  filename            = data.archive_file.lambda_layer.output_path
  layer_name          = "${var.project_name}-deps-${var.environment}"
  source_code_hash    = data.archive_file.lambda_layer.output_base64sha256
  compatible_runtimes = ["python3.11"]
  
  description = "Dependencies for ${var.project_name}"
}

# Lambda function using the existing Mangum handler in main.py
resource "aws_lambda_function" "api" {
  filename         = data.archive_file.lambda_package.output_path
  function_name    = "${var.project_name}-${var.environment}"
  role             = aws_iam_role.lambda.arn
  handler          = "main.handler"  # Uses the existing handler in src/main.py
  source_code_hash = data.archive_file.lambda_package.output_base64sha256
  runtime          = "python3.11"
  memory_size      = var.lambda_memory_size
  timeout          = var.lambda_timeout
  
  layers = [aws_lambda_layer_version.dependencies.arn]

  environment {
    variables = {
      # Application settings
      ENVIRONMENT      = var.environment
      AWS_LAMBDA_FUNCTION_NAME = "true"  # This tells the app it's running in Lambda
      
      # Database configuration  
      DATABASE_TYPE    = "dynamodb"
      TABLE_NAME       = aws_dynamodb_table.main.name
      
      # LLM configuration
      LLM_PROVIDER     = var.llm_provider
      GEMINI_API_KEY   = var.gemini_api_key
      OPENROUTER_API_KEY = var.openrouter_api_key
      
      # Security
      REQUIRE_API_KEY  = var.require_api_key ? "true" : "false"
      API_KEY          = var.api_key
      
      # Logging
      LOG_LEVEL        = var.log_level
    }
  }
}

# Lambda Function URL
resource "aws_lambda_function_url" "api" {
  function_name      = aws_lambda_function.api.function_name
  authorization_type = "NONE"

  cors {
    allow_origins = var.cors_origins
    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers = ["*"]
    max_age       = 3600
  }
}

# DynamoDB table for session storage
resource "aws_dynamodb_table" "main" {
  name           = "${var.project_name}-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "id"

  attribute {
    name = "id"
    type = "S"
  }
  
  # Optional: Add user_id as a global secondary index for querying by user
  attribute {
    name = "user_id"
    type = "S"
  }
  
  global_secondary_index {
    name            = "user_id_index"
    hash_key        = "user_id"
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
  
  kms_key_id = var.kms_key_id  # Optional: encrypt logs with KMS
}

# Optional: CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  count = var.enable_monitoring ? 1 : 0
  
  alarm_name          = "${var.project_name}-${var.environment}-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors lambda errors"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.api.function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  count = var.enable_monitoring ? 1 : 0
  
  alarm_name          = "${var.project_name}-${var.environment}-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors lambda throttles"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.api.function_name
  }
}