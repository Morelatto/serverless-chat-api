terraform {
  required_version = ">= 1.0"
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

# Simple Lambda function with inline code for now
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
        "dynamodb:Scan"
      ]
      Resource = aws_dynamodb_table.main.arn
    }]
  })
}

# Create a simple ZIP file with Python code
data "archive_file" "lambda_package" {
  type        = "zip"
  output_path = "${path.module}/lambda_function.zip"
  
  source {
    content = <<EOF
import json

def handler(event, context):
    """Simple Lambda handler for testing"""
    
    # Parse the incoming event
    path = event.get('rawPath', '/')
    method = event.get('requestContext', {}).get('http', {}).get('method', 'GET')
    
    # Handle health check
    if path == '/v1/health':
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'status': 'healthy',
                'version': '1.0.0',
                'environment': 'dev'
            })
        }
    
    # Handle chat endpoint
    if path == '/v1/chat' and method == 'POST':
        try:
            body = json.loads(event.get('body', '{}'))
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'id': 'test-123',
                    'userId': body.get('userId', 'unknown'),
                    'prompt': body.get('prompt', ''),
                    'response': 'This is a test response from Lambda',
                    'model': 'lambda-test'
                })
            }
        except Exception as e:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': str(e)})
            }
    
    # Default response
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'message': 'Serverless Chat API',
            'path': path,
            'method': method
        })
    }
EOF
    filename = "lambda_function.py"
  }
}

resource "aws_lambda_function" "api" {
  filename         = data.archive_file.lambda_package.output_path
  function_name    = "${var.project_name}-${var.environment}"
  role             = aws_iam_role.lambda.arn
  handler          = "lambda_function.handler"
  source_code_hash = data.archive_file.lambda_package.output_base64sha256
  runtime          = "python3.11"
  memory_size      = var.lambda_memory_size
  timeout          = var.lambda_timeout

  environment {
    variables = {
      ENVIRONMENT = var.environment
      TABLE_NAME  = aws_dynamodb_table.main.name
    }
  }
}

resource "aws_lambda_function_url" "api" {
  function_name      = aws_lambda_function.api.function_name
  authorization_type = "NONE"

  cors {
    allow_origins = ["*"]
    allow_methods = ["*"]
    allow_headers = ["*"]
  }
}

resource "aws_dynamodb_table" "main" {
  name           = "${var.project_name}-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "id"

  attribute {
    name = "id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${aws_lambda_function.api.function_name}"
  retention_in_days = var.log_retention_days
}