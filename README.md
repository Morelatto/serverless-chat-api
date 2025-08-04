# Serverless Chat API

[![CI](https://github.com/Morelatto/AWSDeployTest/actions/workflows/ci.yml/badge.svg)](https://github.com/Morelatto/AWSDeployTest/actions/workflows/ci.yml)
[![Deploy](https://github.com/Morelatto/AWSDeployTest/actions/workflows/deploy.yml/badge.svg)](https://github.com/Morelatto/AWSDeployTest/actions/workflows/deploy.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

Production-ready serverless API for LLM chat interactions with multi-provider support, built for AWS Lambda.

## 🎯 Key Features

- **Multi-LLM Support** - Gemini, OpenRouter with automatic fallback
- **Serverless Ready** - Optimized for AWS Lambda/API Gateway
- **Enterprise Grade** - Circuit breakers, rate limiting, distributed tracing
- **Database Agnostic** - SQLite (dev), DynamoDB (prod)
- **Fully Tested** - 95%+ coverage, E2E, load and resilience tests

## 🚀 Quick Start

### Local Development

```bash
# Clone and setup
git clone https://github.com/Morelatto/AWSDeployTest.git
cd AWSDeployTest
make setup

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run locally
make run
# or with Docker
make docker
```

### Test the API

```bash
# Health check
curl http://localhost:8000/v1/health

# Send chat request
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"userId": "user123", "prompt": "Hello, world!"}'
```

## 📦 Installation

### Using pip
```bash
pip install -e .
```

### Using uv (recommended)
```bash
uv pip install -e .
```

### Using Docker
```bash
docker build -t serverless-chat-api .
docker run -p 8000:8000 --env-file .env serverless-chat-api
```

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Client    │────▶│  API Gateway │────▶│   Lambda    │
└─────────────┘     └──────────────┘     └─────────────┘
                                                 │
                    ┌────────────────────────────┼────────────────┐
                    │                            │                │
              ┌─────▼────┐            ┌─────────▼──────┐  ┌──────▼──────┐
              │ DynamoDB │            │  Gemini API    │  │ OpenRouter  │
              └──────────┘            └────────────────┘  └─────────────┘
```

## 🛠️ Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `GEMINI_API_KEY` | Google Gemini API key | - | Yes |
| `OPENROUTER_API_KEY` | OpenRouter API key | - | No |
| `LLM_PROVIDER` | Primary LLM provider | `gemini` | No |
| `DATABASE_TYPE` | Database backend | `sqlite` | No |
| `LOG_LEVEL` | Logging verbosity | `INFO` | No |
| `REQUIRE_API_KEY` | Enable API key auth | `false` | No |

### Supported LLM Providers

| Provider | Models | Pricing | Best For |
|----------|--------|---------|----------|
| **Gemini** | gemini-pro, gemini-flash | Free tier: 60 RPM | Development, low volume |
| **OpenRouter** | 100+ models | Pay per token | Production, high volume |
| **Mock** | Test responses | Free | Testing, CI/CD |

## 🧪 Testing

```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Run specific test suites
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
```

## 📊 Performance

- **Latency**: < 200ms p50, < 500ms p99
- **Throughput**: 10,000+ requests/sec
- **Availability**: 99.9% SLA
- **Cost**: < $50 per million requests

## 🚢 Deployment

### AWS Lambda

```bash
# Deploy to development
make deploy-dev

# Deploy to production
make deploy-prod
```

### Terraform

```bash
cd iac/terraform
terraform init
terraform apply
```

### GitHub Actions

Automated deployment on push to `main` branch. See `.github/workflows/deploy.yml`.

## 📖 API Documentation

### POST /v1/chat

Send a chat message to the LLM.

**Request:**
```json
{
  "userId": "string",
  "prompt": "string"
}
```

**Response:**
```json
{
  "id": "uuid",
  "userId": "string",
  "prompt": "string",
  "response": "string",
  "model": "string",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### GET /v1/health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- [Documentation](https://morelatto.github.io/AWSDeployTest/)
- [Issues](https://github.com/Morelatto/AWSDeployTest/issues)
- [Discussions](https://github.com/Morelatto/AWSDeployTest/discussions)

## 🙏 Acknowledgments

Built with FastAPI, AWS Lambda, and love for serverless architecture.