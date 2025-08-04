# 🚀 Deploy Pipeline - Production Ready

## Quick Setup

### 1. GitHub Repository Setup
```bash
# Configure secrets
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_ACCESS_KEY_ID_PROD=your_prod_key  # Optional
AWS_SECRET_ACCESS_KEY_PROD=your_prod_secret  # Optional
```

### 2. GitHub Environments
Create environments: `dev`, `staging`, `prod`
- `prod` environment: Require reviewers

### 3. Test Pipeline
```bash
# Test locally first
./scripts/test-pipeline.sh

# Test on GitHub (dry run)
gh workflow run test-deploy.yml --field dry_run=true
```

## Deploy Options

### Auto Deploy (main branch)
```bash
git push origin main  # → deploys to dev
```

### Manual Deploy
```bash
gh workflow run deploy.yml --field environment=staging
gh workflow run deploy.yml --field environment=prod
```

### Local Deploy
```bash
./scripts/deploy.sh dev
```

## Pipeline Structure

### CI (Pull Requests)
- **test**: ruff → mypy → pytest → codecov
- **docker**: build → health check

### Deploy (Production)
- **Matrix strategy**: dev/staging/prod
- **Conditional execution**: based on triggers
- **Health checks**: automatic validation

## Files Overview

```
.github/workflows/
├── ci.yml           # 26 lines - PR validation
├── deploy.yml       # 55 lines - Production deploy
└── test-deploy.yml  # 38 lines - Pipeline testing

scripts/
├── deploy.sh        # Manual deploy
├── test-pipeline.sh # Local testing
└── quick-deploy.sh  # GitHub CLI deploy
```

## Key Features

✅ **Minimal Lines**: ~120 total vs 300+ original
✅ **Production Ready**: Matrix strategy + environments
✅ **Testable**: Local testing + dry run workflow
✅ **Parameterized**: Reusable actions
✅ **Secure**: Environment-based secrets

## Ready to Deploy

1. **Copy to your repo**
2. **Add GitHub secrets**
3. **Create environments**
4. **Test with dry run**
5. **Deploy!**

The pipeline is optimized for real-world usage with minimal configuration.
