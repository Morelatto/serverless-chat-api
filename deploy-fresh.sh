#!/bin/bash

set -e

echo "🚀 Fresh Infrastructure Deployment (Cost-Optimized)"
echo "================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_step() {
    echo -e "\n${YELLOW}$1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check prerequisites
print_step "1. Checking prerequisites..."

if ! command -v terraform &> /dev/null; then
    print_error "Terraform not found. Please install: https://terraform.io/downloads"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    print_error "AWS CLI not found. Please install: https://aws.amazon.com/cli/"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    print_error "Docker not found. Please install: https://docker.com/"
    exit 1
fi

print_success "Prerequisites installed"

# Check AWS credentials
print_step "2. Checking AWS credentials..."

if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured"
    echo "Please run one of:"
    echo "  aws configure                    # Interactive setup"
    echo "  export AWS_ACCESS_KEY_ID=xxx     # Environment variables"
    echo "  export AWS_SECRET_ACCESS_KEY=yyy"
    echo "  export AWS_DEFAULT_REGION=us-east-1"
    exit 1
fi

AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region || echo "us-east-1")
print_success "AWS credentials configured (Account: $AWS_ACCOUNT, Region: $AWS_REGION)"

# Cost estimate
print_step "3. Cost estimate for development environment..."
echo "Expected monthly costs:"
echo "  • Lambda (1M requests, 256MB):    $2.00"
echo "  • DynamoDB (1M operations):       $2.50"
echo "  • ECR + CloudWatch:               $0.60"
echo "  • Redis:                          $0.00 (disabled)"
echo "  • Total:                          ~$5.10/month"
echo ""
echo "Note: First 12 months may be covered by AWS Free Tier"

read -p "Continue with deployment? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled"
    exit 0
fi

# Check for existing infrastructure to remove
print_step "4. Checking for existing infrastructure..."

cd iac/terraform

# Try to find existing state (either local or remote)
EXISTING_RESOURCES=""
if [ -f terraform.tfstate ]; then
    EXISTING_RESOURCES=$(terraform show -json 2>/dev/null | jq -r '.values.root_module.resources[]?.address' 2>/dev/null || echo "")
elif aws s3 ls s3://serverless-chat-api-terraform-state/terraform.tfstate &>/dev/null; then
    echo "Found remote state in S3"
    # Temporarily use remote state to check
    sed -i 's/backend "local"/# backend "local"/' main.tf
    sed -i 's/# backend "s3"/backend "s3"/' main.tf
    terraform init -reconfigure &>/dev/null || true
    EXISTING_RESOURCES=$(terraform show -json 2>/dev/null | jq -r '.values.root_module.resources[]?.address' 2>/dev/null || echo "")
    # Switch back to local
    sed -i 's/backend "s3"/# backend "s3"/' main.tf
    sed -i 's/# backend "local"/backend "local"/' main.tf
fi

if [ ! -z "$EXISTING_RESOURCES" ]; then
    print_step "5. Removing existing infrastructure..."
    echo "Found existing resources:"
    echo "$EXISTING_RESOURCES"

    read -p "Remove existing infrastructure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        terraform destroy -auto-approve -var-file="terraform.tfvars.dev"
        print_success "Old infrastructure removed"
    fi
else
    print_success "No existing infrastructure found"
fi

# Deploy new infrastructure
print_step "6. Deploying fresh infrastructure..."

# Ensure Gemini API key is set
if [ -z "$CHAT_GEMINI_API_KEY" ]; then
    echo "Please set your Gemini API key:"
    echo "  Get one from: https://aistudio.google.com/app/apikey"
    read -p "Enter Gemini API key: " -s GEMINI_KEY
    echo
    export CHAT_GEMINI_API_KEY="$GEMINI_KEY"

    # Update tfvars
    sed -i "s/gemini_api_key     = \"\"/gemini_api_key     = \"$GEMINI_KEY\"/" terraform.tfvars.dev
fi

# Initialize and deploy
terraform init
terraform plan -var-file="terraform.tfvars.dev" -out=deployment.tfplan
terraform apply deployment.tfplan

print_success "Infrastructure deployed successfully"

# Get outputs
ECR_URI=$(terraform output -raw ecr_repository_url)
LAMBDA_URL=$(terraform output -raw lambda_function_url)

print_step "7. Building and deploying container..."

# Build and push container
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URI

cd ../.. # Back to project root

docker build --build-arg TARGET=lambda -t serverless-chat-api .
docker tag serverless-chat-api:latest $ECR_URI:latest
docker push $ECR_URI:latest

# Update Lambda function
FUNCTION_NAME=$(cd iac/terraform && terraform output -raw lambda_function_name)
aws lambda update-function-code --function-name $FUNCTION_NAME --image-uri $ECR_URI:latest

print_success "Container deployed successfully"

print_step "8. Verifying deployment..."

# Wait for Lambda to be ready
sleep 10

# Test health endpoint
if curl -s "$LAMBDA_URL/health" | grep -q "healthy"; then
    print_success "Health check passed"
else
    print_error "Health check failed"
    echo "Lambda URL: $LAMBDA_URL"
    echo "Check logs with: aws logs tail --follow '/aws/lambda/$FUNCTION_NAME'"
    exit 1
fi

# Final summary
print_step "9. Deployment Summary"
echo "🎉 Fresh infrastructure deployed successfully!"
echo ""
echo "Resources created:"
echo "  • Lambda Function URL: $LAMBDA_URL"
echo "  • ECR Repository:       $ECR_URI"
echo "  • DynamoDB Table:       $(cd iac/terraform && terraform output -raw dynamodb_table_name)"
echo ""
echo "Next steps:"
echo "  • Test the API:         curl '$LAMBDA_URL/health'"
echo "  • Monitor costs:        aws ce get-cost-and-usage (after 24h)"
echo "  • Enable monitoring:    Set enable_monitoring=true for production"
echo ""
echo "Estimated monthly cost:  ~$5/month (development configuration)"

print_success "Deployment complete!"
