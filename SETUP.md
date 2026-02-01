# AI Analytics Platform - Production Deployment Guide

> Complete turnkey deployment with **Kimi K2.5** integration, Supabase backend, and enterprise security.

---

## 🚀 Quick Start (One Command)

```bash
# 1. Clone/enter the directory
cd ai-analytics-platform

# 2. Run the automated setup
./scripts/setup.sh

# 3. Paste your API keys when prompted
# 4. Start the platform
./scripts/start.sh
```

**That's it!** The platform will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## 📋 Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Docker | 24.0+ | Container runtime |
| Docker Compose | 2.20+ | Multi-container orchestration |
| Git | 2.30+ | Version control |
| Bash | 4.0+ | Setup scripts |

**Optional (for local development without Docker):**
- Node.js 20+
- Python 3.11+
- PostgreSQL 15+ (with pgvector)

---

## 🔐 Required API Keys

You'll need these API keys during setup:

### Required (Core Functionality)

| Service | Purpose | Get Key At |
|---------|---------|------------|
| **Moonshot AI** | Kimi K2.5 model inference | [platform.moonshot.cn](https://platform.moonshot.cn) |
| **Supabase** | Database + Auth + Realtime | [supabase.com](https://supabase.com) |
| **Clerk** | Authentication | [clerk.com](https://clerk.com) |

### Optional (Enhanced Features)

| Service | Purpose | Get Key At |
|---------|---------|------------|
| OpenAI | Alternative LLM provider | [platform.openai.com](https://platform.openai.com) |
| Langfuse | Observability & tracing | [langfuse.com](https://langfuse.com) |
| PostHog | Analytics | [posthog.com](https://posthog.com) |

---

## 📁 Project Structure

```
ai-analytics-platform/
├── 📄 SETUP.md                 # This guide
├── 📁 scripts/                 # Automation scripts
│   ├── setup.sh               # One-time setup
│   ├── start.sh               # Start all services
│   ├── stop.sh                # Stop all services
│   ├── migrate.sh             # Database migrations
│   └── health-check.sh        # Verify deployment
├── 📁 config/                  # Configuration templates
│   ├── supabase/
│   │   ├── schema.sql         # Database schema
│   │   ├── migrations/        # Versioned migrations
│   │   └── seed.sql           # Demo data
│   ├── docker/
│   │   ├── docker-compose.prod.yml
│   │   ├── docker-compose.dev.yml
│   │   └── Dockerfile.backend
│   └── nginx/
│       └── nginx.conf         # Reverse proxy config
├── 📁 backend/                 # FastAPI application
│   ├── app/
│   │   ├── config.py          # Settings management
│   │   ├── agent/             # AI agent components
│   │   │   └── nodes/
│   │   │       └── generate.py  # Kimi K2.5 integration
│   │   └── ...
│   └── requirements.txt
├── 📁 frontend/                # Next.js application
│   ├── app/
│   └── package.json
├── 📁 .env.example            # Environment template
└── 📄 .env                    # Your secrets (git-ignored)
```

---

## 🔧 Detailed Setup Instructions

### Step 1: Get Your API Keys

#### Moonshot AI (Kimi K2.5)

1. Visit [platform.moonshot.cn](https://platform.moonshot.cn)
2. Sign up / Log in
3. Navigate to **API Keys** section
4. Create a new key: `sk-proj-xxxxx`
5. Copy the key (you won't see it again!)

#### Supabase

1. Visit [supabase.com](https://supabase.com)
2. Create a new project
3. Go to **Project Settings** → **Database**
4. Copy the connection string (PostgreSQL)
5. Go to **Project Settings** → **API**
6. Copy:
   - Project URL: `https://xxxxx.supabase.co`
   - anon/public key
   - service_role/secret key

#### Clerk

1. Visit [clerk.com](https://clerk.com)
2. Create a new application
3. Copy from **API Keys**:
   - Publishable key: `pk_test_xxxxx` or `pk_live_xxxxx`
   - Secret key: `sk_test_xxxxx` or `sk_live_xxxxx`

---

### Step 2: Run Automated Setup

```bash
./scripts/setup.sh
```

This script will:
1. ✅ Check prerequisites (Docker, ports)
2. ✅ Create `.env` from template
3. ✅ Prompt for API keys securely
4. ✅ Validate key format
5. ✅ Test database connectivity
6. ✅ Run database migrations
7. ✅ Generate secrets for security
8. ✅ Create SSL certificates (local dev)

---

### Step 3: Start the Platform

```bash
./scripts/start.sh
```

Or manually with Docker:

```bash
# Production mode
docker-compose -f config/docker/docker-compose.prod.yml up -d

# Development mode (with hot reload)
docker-compose -f config/docker/docker-compose.dev.yml up
```

---

### Step 4: Verify Deployment

```bash
./scripts/health-check.sh
```

Expected output:
```
✅ PostgreSQL      - Connected (Supabase)
✅ Redis           - Connected
✅ Backend API     - Running (v1.0.0)
✅ Frontend        - Running (Next.js 14)
✅ Kimi K2.5       - API responsive
✅ Authentication  - Clerk configured
```

---

## 🗄️ Database Setup (Supabase)

### Option A: Automatic (Recommended)

The setup script will automatically apply migrations to your Supabase project.

### Option B: Manual SQL Execution

1. Go to Supabase Dashboard → SQL Editor
2. Copy contents of `config/supabase/schema.sql`
3. Run the SQL
4. Run `config/supabase/seed.sql` for demo data

### Option C: Supabase CLI

```bash
# Install Supabase CLI
npm install -g supabase

# Link to your project
supabase link --project-ref your-project-ref

# Push migrations
supabase db push
```

---

## 🔒 Security Best Practices

### API Key Security

✅ **DO:**
- Store keys in `.env` (never commit to git)
- Use different keys for dev/staging/prod
- Rotate keys every 90 days
- Use least-privilege access
- Enable key usage monitoring

❌ **DON'T:**
- Hardcode keys in source code
- Share keys in chat/email
- Use production keys in development
- Log API keys

### Database Security

✅ **DO:**
- Use connection pooling (PgBouncer)
- Enable Row Level Security (RLS)
- Use SSL/TLS for connections
- Rotate database passwords
- Enable query logging

### Network Security

The production Docker Compose includes:
- Internal network isolation
- Reverse proxy with rate limiting
- Fail2ban for intrusion prevention
- Automatic HTTPS with Let's Encrypt

---

## 🔧 Configuration Reference

### Environment Variables

```bash
# ============================================
# CORE: Moonshot AI (Kimi K2.5) - REQUIRED
# ============================================
MOONSHOT_API_KEY=sk-proj-xxxxx
MOONSHOT_BASE_URL=https://api.moonshot.cn/v1
MOONSHOT_MODEL=kimi-k2-5
MOONSHOT_MAX_TOKENS=16384
MOONSHOT_TEMPERATURE=0.1

# ============================================
# CORE: Supabase - REQUIRED
# ============================================
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJxxxxx  # service_role key
SUPABASE_ANON_KEY=eyJxxxxx     # anon/public key
DATABASE_URL=postgresql://postgres.xxxxx@aws-0-xxxxx.pooler.supabase.com:6543/postgres?sslmode=require

# ============================================
# CORE: Clerk Authentication - REQUIRED
# ============================================
CLERK_SECRET_KEY=sk_test_xxxxx
CLERK_PUBLISHABLE_KEY=pk_test_xxxxx
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxxxx

# ============================================
# OPTIONAL: Alternative LLM (OpenAI fallback)
# ============================================
OPENAI_API_KEY=sk-xxxxx
OPENAI_MODEL=gpt-4-0125-preview
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# ============================================
# OPTIONAL: Observability
# ============================================
LANGFUSE_PUBLIC_KEY=pk-xxxxx
LANGFUSE_SECRET_KEY=sk-xxxxx
LANGFUSE_HOST=https://cloud.langfuse.com
POSTHOG_API_KEY=phc_xxxxx

# ============================================
# INFRASTRUCTURE
# ============================================
REDIS_URL=redis://localhost:6379
SECRET_KEY=auto-generated-in-setup
DEBUG=false
LOG_LEVEL=INFO
```

---

## 🐛 Troubleshooting

### Common Issues

#### "Connection refused" to Supabase

```bash
# Check if using correct connection string
# Supabase requires connection pooling port 6543, NOT 5432
# Verify sslmode=require is included
```

#### Kimi K2.5 API errors

```bash
# Verify your API key is valid
curl https://api.moonshot.cn/v1/models \
  -H "Authorization: Bearer $MOONSHOT_API_KEY"

# Check rate limits in Moonshot dashboard
```

#### Clerk authentication not working

```bash
# Ensure NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY is set
# Check that your domain is in Clerk's allowed list
# Verify JWT template is configured
```

### Getting Help

1. Check logs: `docker-compose logs -f backend`
2. Run diagnostics: `./scripts/health-check.sh --verbose`
3. Review: [GitHub Issues](https://github.com/your-org/ai-analytics-platform/issues)

---

## 📊 Production Deployment

### Cloud Deployment Options

#### AWS ECS

```bash
# Use the production compose file
docker-compose -f config/docker/docker-compose.prod.yml config > ecs-compose.yml

# Deploy with ECS CLI
ecs-cli compose up
```

#### Google Cloud Run

```bash
# Build and push
gcloud builds submit --config cloudbuild.yaml

# Deploy
gcloud run deploy ai-analytics-platform --image gcr.io/PROJECT/ai-analytics
```

#### Railway / Render / Fly.io

The `railway.toml`, `render.yaml`, and `fly.toml` configs are included for one-click deployment.

---

## 🔄 Updates & Maintenance

### Update to Latest Version

```bash
# Pull latest code
git pull origin main

# Run migrations
./scripts/migrate.sh

# Restart services
./scripts/stop.sh && ./scripts/start.sh
```

### Backup Database

```bash
# Automated daily backups are configured in Supabase
# Manual backup:
pg_dump $DATABASE_URL > backup-$(date +%Y%m%d).sql
```

---

## 📈 Monitoring & Observability

### Health Endpoints

- API Health: `GET /health`
- Ready Check: `GET /ready`
- Metrics: `GET /metrics` (Prometheus format)

### Logging

Logs are structured JSON and can be sent to:
- Datadog
- Splunk
- ELK Stack
- CloudWatch

Configure in `config/logging.yaml`

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `./scripts/test.sh`
5. Submit a pull request

---

## 📄 License

MIT License - see LICENSE file for details.

---

## 🙏 Acknowledgments

- [Moonshot AI](https://www.moonshot.cn) for Kimi K2.5
- [Supabase](https://supabase.com) for backend infrastructure
- [Clerk](https://clerk.com) for authentication
- [LangChain](https://langchain.com) for AI orchestration

---

**Need help?** Open an issue or contact support@yourcompany.com
