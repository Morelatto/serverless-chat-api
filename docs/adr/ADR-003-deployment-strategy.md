# ADR-003: Estratégia de Deploy e Infraestrutura

**Status:** Aceito
**Data:** 2025-01-04

## Contexto

Deploy deve ser simples, reproduzível e adequado para ambiente corporativo AWS.

## Decisão

Deploy em duas fases: desenvolvimento local com Docker e produção com Terraform/Lambda.

## Estratégia de Deploy

### Desenvolvimento Local
```bash
# Opção 1: Docker
docker-compose up

# Opção 2: Python direto
python -m src.main
```

### Produção AWS
```bash
# Deploy completo
cd infra/terraform
terraform init
terraform apply
```

## Componentes de Infraestrutura

### Compute
- **Local**: FastAPI com Uvicorn
- **Prod**: Lambda com 1GB RAM
- **Timeout**: 30 segundos
- **Concorrência**: 1000 execuções

### API Gateway
- **Protocolo**: REST (não GraphQL)
- **Throttling**: 10k burst, 5k sustained
- **WAF**: Proteção básica habilitada
- **CORS**: Configurado para frontend

### Storage
- **Local**: SQLite file
- **Prod**: DynamoDB on-demand
- **Backup**: Point-in-time recovery
- **Índices**: GSI para interaction_id

### Segurança
- **Secrets**: SSM Parameter Store
- **IAM**: Least privilege
- **KMS**: Encryption at rest
- **VPC**: Não necessário (serverless)

### Monitoramento
- **Logs**: CloudWatch Logs
- **Métricas**: CloudWatch Metrics
- **Alertas**: SNS para email/Slack
- **Dashboard**: Métricas principais

## Estrutura Terraform

```hcl
# main.tf
- Lambda function
- API Gateway
- DynamoDB table

# monitoring.tf
- CloudWatch dashboards
- Alarms
- Log groups

# security.tf
- IAM roles
- KMS keys
- SSM parameters
```

## CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/deploy.yml
steps:
  - Test: pytest
  - Build: zip Lambda
  - Deploy: terraform apply
  - Smoke test: curl health
```

## Custos Estimados

| Componente | Volume | Custo/mês |
|------------|--------|-----------|
| Lambda | 100k requests | $20 |
| DynamoDB | 100k items | $25 |
| API Gateway | 100k calls | $3.50 |
| CloudWatch | Logs + Metrics | $5 |
| **Total** | | **~$55** |

## Rollback Strategy

1. **Blue/Green**: Lambda alias com weighted routing
2. **Canary**: 10% tráfego para nova versão
3. **Instant Rollback**: Terraform previous state

## Disaster Recovery

- **RTO**: 15 minutos
- **RPO**: 1 hora
- **Backup**: DynamoDB continuous
- **Multi-região**: Preparado, não ativo
