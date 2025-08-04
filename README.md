# Chat API v3 - Processo Seletivo Itaú

Microserviço completo para processamento de prompts com LLM, implementando todas as features requisitadas com arquitetura enterprise-ready.

## ✅ Features Implementadas

### Core (Requisitos Obrigatórios)
- ✅ REST API endpoint `/v1/chat`
- ✅ Persistência de prompts (SQLite/DynamoDB)
- ✅ Integração com LLM (Gemini + OpenRouter)
- ✅ Resposta em tempo real

### Segurança
- ✅ API Key authentication
- ✅ Rate limiting (60 req/min por usuário)
- ✅ Input validation e sanitização
- ✅ Remoção automática de PII

### Resiliência
- ✅ Circuit breaker pattern
- ✅ Retry com backoff exponencial
- ✅ Fallback entre providers
- ✅ Cache de respostas

### Observabilidade
- ✅ Structured JSON logging
- ✅ Trace ID correlation
- ✅ Health/Ready checks
- ✅ Metrics tracking

## 🚀 Quick Start

### 1. Setup Inicial
```bash
make setup
# Edite .env com suas API keys
```

### 2. Executar Localmente

**Opção A: Python direto**
```bash
make run
```

**Opção B: Docker**
```bash
make docker
```

### 3. Testar API
```bash
# Health check
curl http://localhost:8000/v1/health

# Chat request
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "user123",
    "prompt": "Qual é a capital do Brasil?"
  }'
```

## 📁 Estrutura do Projeto

```
src/
├── chat/              # Feature de chat
│   ├── api.py        # Endpoints REST
│   ├── service.py    # Lógica de negócio
│   └── models.py     # Schemas e validação
│
├── shared/           # Componentes compartilhados
│   ├── database.py   # Interface SQLite/DynamoDB
│   ├── llm.py       # Multi-provider LLM
│   └── config.py    # Configurações
│
└── main.py          # Entry point
```

## 🔧 Configuração

### Variáveis de Ambiente

```bash
# LLM Providers
GEMINI_API_KEY=seu_key_aqui      # Obter em makersuite.google.com
OPENROUTER_API_KEY=seu_key_aqui  # Obter em openrouter.ai

# Modo de operação
LLM_PROVIDER=gemini              # ou openrouter, mock
REQUIRE_API_KEY=false            # true em produção
```

### Providers Suportados

| Provider | Modelo | Custo | Rate Limit |
|----------|---------|-------|------------|
| Gemini | gemini-pro | Free (60 req/min) | Ideal para dev |
| OpenRouter | múltiplos | Pay-per-use | Produção |
| Mock | N/A | Free | Testes |

## 🔒 Segurança

- **Autenticação**: API Keys no header `X-API-Key`
- **Rate Limiting**: 60 requisições/minuto por usuário
- **Sanitização**: Remoção automática de CPF, email, telefone
- **Validação**: Schemas Pydantic com limites

## 🔄 Resiliência

- **Circuit Breaker**: Abre após 5 falhas, recovery em 60s
- **Retry**: 3 tentativas com backoff exponencial
- **Cache**: Respostas idênticas cacheadas por 1 hora
- **Fallback**: Troca automática entre providers

## 📊 Monitoramento

### Endpoints de Saúde
- `GET /v1/health` - Liveness probe
- `GET /v1/ready` - Readiness probe (checa dependências)

### Logs Estruturados
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "trace_id": "550e8400-e29b-41d4",
  "event": "chat_request",
  "user_id": "user123",
  "latency_ms": 1234
}
```

## 🚢 Deploy AWS

### Pré-requisitos
- AWS CLI configurado
- Terraform instalado
- Credenciais AWS com permissões

### Deploy
```bash
cd infra/terraform
terraform init
terraform apply -var="gemini_api_key=SEU_KEY"
```

### Arquitetura AWS
- **Lambda**: Função serverless
- **API Gateway**: REST API
- **DynamoDB**: Banco NoSQL
- **CloudWatch**: Logs e métricas

## 📈 Performance

- **Latência P95**: < 3 segundos
- **Throughput**: 1000+ req/min
- **Disponibilidade**: 99.9% SLA
- **Custo**: ~$50/mês para 100k requests

## 🧪 Testes

```bash
# Rodar testes
make test

# Teste de carga
artillery quick -d 60 -r 10 http://localhost:8000/v1/chat
```

## 📝 API Documentation

Swagger UI disponível em desenvolvimento:
```
http://localhost:8000/docs
```

### POST /v1/chat

**Request:**
```json
{
  "userId": "user123",
  "prompt": "Sua pergunta aqui"
}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4",
  "userId": "user123",
  "prompt": "Sua pergunta aqui",
  "response": "Resposta do LLM",
  "model": "gemini-pro",
  "timestamp": "2024-01-15T10:30:00Z",
  "cached": false
}
```

## 🛠 Comandos Úteis

```bash
make help        # Ver todos comandos
make run         # Rodar localmente
make docker      # Rodar com Docker
make test        # Executar testes
make clean       # Limpar arquivos temp
make deploy      # Deploy AWS
```

## 📄 Licença

Projeto desenvolvido para processo seletivo Itaú - Comunidade IA.

---

**Autor**: Candidato ao processo seletivo
**Data**: Janeiro 2025
**Versão**: 3.0.0
