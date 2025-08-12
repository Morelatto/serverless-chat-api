# 🚀 Deployment Diagrams

Deployment options and scaling strategies.

## Diagrams

### 1. Deployment Options
**File**: `03_deployment_options.png`

Three deployment targets from same codebase:
- **Development**: Local with SQLite and dict cache ($0/mo)
- **Staging**: Docker with PostgreSQL and Redis ($50/mo)
- **Production**: AWS Lambda with DynamoDB and ElastiCache ($0.20/1M requests)

**Key Insight**: Same code adapts to different environments via configuration.

### 2. Scaling Strategy
**File**: `10_scaling_strategy.png`

Progressive scaling approach:
- **Local**: 1 user, 10 req/s
- **Docker**: 100 users, 1000 req/s with load balancing
- **Lambda**: ∞ users, 10K+ req/s with auto-scaling

**Key Insight**: Serverless provides infinite scaling without infrastructure management.

## Visual Conventions
- **Environment colors**: Yellow (dev), Blue (staging), Pink (production)
- **Instance count** shows scaling capability
- **Metrics** provide performance benchmarks
