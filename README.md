# API de Chat Serverless

[![CI](https://github.com/Morelatto/AWSDeployTest/actions/workflows/ci.yml/badge.svg)](https://github.com/Morelatto/AWSDeployTest/actions/workflows/ci.yml)
[![Deploy](https://github.com/Morelatto/AWSDeployTest/actions/workflows/deploy.yml/badge.svg)](https://github.com/Morelatto/AWSDeployTest/actions/workflows/deploy.yml)
[![MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

API serverless multi-LLM otimizada para AWS Lambda com fallback automático, circuit breakers e 95%+ cobertura de testes.

## Início Rápido

```bash
# Setup
git clone https://github.com/Morelatto/AWSDeployTest.git
cd AWSDeployTest && make dev
cp .env.example .env  # Configure suas API keys

# Executar
python -m src.main     # Local
make docker-env        # Docker

# Testar
curl localhost:8000/v1/health
curl -X POST localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"userId": "user123", "prompt": "Olá!"}'
```

## Configuração

### Essencial
- `GEMINI_API_KEY` - **Obrigatório**
- `OPENROUTER_API_KEY` - Opcional (fallback)
- `LLM_PROVIDER` - `gemini` | `openrouter` | `mock`

### Avançado
- `DATABASE_PATH` - SQLite local (default: `chat_history.db`)
- `DYNAMODB_TABLE` - Produção (default: `chat-interactions`)
- `REQUIRE_API_KEY` + `API_KEYS` - Autenticação
- `RATE_LIMIT_PER_MINUTE` - Default: 60

## API

**Documentação interativa disponível em `/docs` (Swagger) e `/redoc`**

### `POST /v1/chat`
```json
// Request
{"userId": "string", "prompt": "string"}

// Response
{
  "id": "uuid",
  "userId": "string",
  "prompt": "string",
  "response": "string",
  "model": "string",
  "timestamp": "ISO-8601"
}
```

### `GET /v1/health`
Retorna status, versão e timestamp.

## Deploy

```bash
make deploy ENV=dev    # AWS Lambda
cd iac/terraform && terraform apply    # Terraform
```

Push para `main` dispara deploy automático via GitHub Actions.

## Performance
- Latência: < 200ms p50, < 500ms p99
- Taxa: 10.000+ req/s
- SLA: 99.9%
- Custo: < R$250/milhão req

## Desenvolvimento

```bash
pytest tests/              # Todos os testes
pytest tests/ --cov=src    # Com cobertura
make lint                  # Verificação de código
```

## 🤝 Contribuindo

1. Faça um fork do repositório
2. Crie sua branch de feature (`git checkout -b feature/recurso-incrivel`)
3. Faça commit das suas mudanças (`git commit -m 'Adiciona recurso incrível'`)
4. Faça push para a branch (`git push origin feature/recurso-incrivel`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.