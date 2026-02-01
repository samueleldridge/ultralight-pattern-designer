# Deployment Guide

> Deploy AI Analytics Platform to production environments.

---

## ☁️ One-Click Deployments

### Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/your-template)

1. Click the button above
2. Add your environment variables:
   - `MOONSHOT_API_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_KEY`
   - `CLERK_SECRET_KEY`
3. Deploy!

### Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

Use the included `render.yaml`:

```yaml
services:
  - type: web
    name: ai-analytics-backend
    runtime: docker
    dockerfilePath: ./backend/Dockerfile
    envVars:
      - key: MOONSHOT_API_KEY
        sync: false
      - key: SUPABASE_URL
        sync: false
```

### Fly.io

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Launch
fly launch

# Set secrets
fly secrets set MOONSHOT_API_KEY=sk-proj-xxx
fly secrets set SUPABASE_URL=https://xxx.supabase.co
fly secrets set SUPABASE_SERVICE_KEY=xxx
fly secrets set CLERK_SECRET_KEY=sk_test_xxx

# Deploy
fly deploy
```

---

## 🏢 AWS ECS Deployment

### Prerequisites

- AWS CLI configured
- ECS CLI installed
- Docker Hub or ECR access

### Step 1: Build & Push Images

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin YOUR_ECR_URL

# Build images
docker-compose -f config/docker/docker-compose.prod.yml build

# Tag and push
docker tag ai-analytics-backend:latest YOUR_ECR_URL/backend:latest
docker tag ai-analytics-frontend:latest YOUR_ECR_URL/frontend:latest
docker push YOUR_ECR_URL/backend:latest
docker push YOUR_ECR_URL/frontend:latest
```

### Step 2: Create ECS Task Definition

```json
{
  "family": "ai-analytics",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "YOUR_ECR_URL/backend:latest",
      "portMappings": [{"containerPort": 8000}],
      "environment": [
        {"name": "MOONSHOT_API_KEY", "value": "xxx"},
        {"name": "SUPABASE_URL", "value": "xxx"}
      ],
      "secrets": [
        {"name": "DATABASE_URL", "valueFrom": "arn:aws:secretsmanager:..."}
      ]
    }
  ]
}
```

### Step 3: Deploy

```bash
aws ecs register-task-definition --cli-input-json file://task-definition.json
aws ecs create-service --cluster ai-analytics --service-name api --task-definition ai-analytics
```

---

## 🔷 Google Cloud Run

### Using Cloud Build

```bash
# Submit build
gcloud builds submit --config cloudbuild.yaml

# Deploy backend
gcloud run deploy ai-analytics-backend \
  --image gcr.io/PROJECT/backend:latest \
  --platform managed \
  --region us-central1 \
  --set-env-vars MOONSHOT_API_KEY=xxx,SUPABASE_URL=xxx

# Deploy frontend
gcloud run deploy ai-analytics-frontend \
  --image gcr.io/PROJECT/frontend:latest \
  --platform managed \
  --region us-central1
```

### cloudbuild.yaml

```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/backend:latest', './backend']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/frontend:latest', './frontend']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/backend:latest']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/frontend:latest']
```

---

## 🏗️ Kubernetes Deployment

### Using Helm

```bash
# Add repo
helm repo add ai-analytics https://charts.ai-analytics.io

# Install
helm install ai-analytics ai-analytics/ai-analytics \
  --set moonshot.apiKey=xxx \
  --set supabase.url=xxx \
  --set supabase.serviceKey=xxx
```

### Manual kubectl

```bash
# Create namespace
kubectl create namespace ai-analytics

# Create secrets
kubectl create secret generic app-secrets \
  --from-literal=moonshot-api-key=xxx \
  --from-literal=database-url=xxx \
  -n ai-analytics

# Apply manifests
kubectl apply -f k8s/ -n ai-analytics
```

See `k8s/` directory for example manifests.

---

## 🔐 Security Checklist

Before deploying to production:

- [ ] Change all default secrets (SECRET_KEY, JWT_SECRET_KEY)
- [ ] Enable HTTPS/TLS
- [ ] Configure CORS origins explicitly
- [ ] Set up rate limiting
- [ ] Enable Row Level Security in Supabase
- [ ] Configure backup schedules
- [ ] Set up monitoring (Sentry, DataDog, etc.)
- [ ] Enable audit logging
- [ ] Rotate API keys (90-day policy)
- [ ] Review Clerk JWT settings

---

## 📊 Monitoring Setup

### Sentry Integration

```bash
# Add SENTRY_DSN to your environment
SENTRY_DSN=https://xxx@sentry.io/xxx
```

### Langfuse (LLM Observability)

```bash
# Add to .env
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_SECRET_KEY=sk-lf-xxx
LANGFUSE_HOST=https://cloud.langfuse.com
```

### Prometheus & Grafana

```bash
# Start with monitoring profile
docker-compose -f config/docker/docker-compose.prod.yml --profile monitoring up -d

# Access Grafana at http://localhost:3001
# Default credentials: admin/admin
```

---

## 🔄 CI/CD Pipelines

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build images
        run: docker-compose -f config/docker/docker-compose.prod.yml build
      
      - name: Push to registry
        run: |
          echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
          docker-compose -f config/docker/docker-compose.prod.yml push
      
      - name: Deploy to production
        run: |
          # Your deployment commands here
```

### GitLab CI

```yaml
# .gitlab-ci.yml
stages:
  - build
  - deploy

build:
  stage: build
  script:
    - docker build -t $CI_REGISTRY_IMAGE/backend:$CI_COMMIT_SHA ./backend
    - docker push $CI_REGISTRY_IMAGE/backend:$CI_COMMIT_SHA

deploy:
  stage: deploy
  script:
    - kubectl set image deployment/backend backend=$CI_REGISTRY_IMAGE/backend:$CI_COMMIT_SHA
```

---

## 💰 Cost Optimization

### Database

- Use Supabase free tier for development
- Enable connection pooling (PgBouncer)
- Set up automatic backups

### LLM Costs

- Kimi K2.5 pricing: Check [Moonshot platform](https://platform.moonshot.cn)
- Implement query caching (enabled by default)
- Use smaller models for simple tasks

### Compute

- Use spot instances for workers
- Scale to zero with serverless platforms
- Enable horizontal pod autoscaling in K8s

---

## 🆘 Troubleshooting Production Issues

### High Memory Usage

```bash
# Check memory usage
docker stats

# Reduce worker processes in .env
WORKERS=2
```

### Database Connection Pool Exhausted

```bash
# Increase pool size
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
```

### Slow Queries

1. Enable query logging in Supabase
2. Check slow query log
3. Add indexes on frequently queried columns

### LLM Rate Limiting

```bash
# Implement retry logic with exponential backoff
# Use multiple API keys for load balancing
```

---

## 📚 Additional Resources

- [Docker Production Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Supabase Security Guide](https://supabase.com/docs/guides/security)
- [Clerk Production Checklist](https://clerk.com/docs/deployments/overview)
