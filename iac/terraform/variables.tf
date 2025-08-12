variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "serverless-chat-api"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

# Lambda Configuration
variable "lambda_memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 512
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 30
}

# LLM Configuration
variable "llm_provider" {
  description = "LLM provider to use (gemini, openrouter)"
  type        = string
  default     = "gemini"
}

variable "gemini_api_key" {
  description = "Google Gemini API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "openrouter_api_key" {
  description = "OpenRouter API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "openrouter_model_name" {
  description = "OpenRouter model name (without openrouter/ prefix)"
  type        = string
  default     = "auto"
}

# Security
variable "require_api_key" {
  description = "Whether to require API key authentication"
  type        = bool
  default     = true
}

variable "api_key" {
  description = "API key for authentication (generated if not provided)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "jwt_secret_key" {
  description = "JWT secret key for token signing (generated if not provided)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "cors_origins" {
  description = "CORS allowed origins"
  type        = list(string)
  default     = ["*"]
}

# Logging and Monitoring
variable "log_level" {
  description = "Application log level"
  type        = string
  default     = "INFO"
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}

variable "enable_monitoring" {
  description = "Enable CloudWatch alarms for Lambda function"
  type        = bool
  default     = false
}

variable "enable_cache" {
  description = "Enable ElastiCache Serverless for response caching"
  type        = bool
  default     = false  # Start without cache to save costs
}

# Database Configuration
variable "enable_point_in_time_recovery" {
  description = "Enable point-in-time recovery for DynamoDB"
  type        = bool
  default     = false
}

# Encryption
variable "kms_key_id" {
  description = "KMS key ID for CloudWatch logs encryption (optional)"
  type        = string
  default     = null
}
