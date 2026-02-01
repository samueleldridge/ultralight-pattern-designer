# 🚀 AI Analytics Platform - Quick Start Guide

> Get up and running in **under 5 minutes** with Kimi K2.5-powered analytics.

---

## ⚡ TL;DR - One Command Setup

```bash
git clone <repository>
cd ai-analytics-platform
make setup
```

That's it! Then visit http://localhost:3000

---

## 📋 Before You Start

### Required API Keys (Free Tiers Available)

| Service | Purpose | Sign Up |
|---------|---------|---------|
| **Moonshot AI** | Kimi K2.5 LLM | [platform.moonshot.cn](https://platform.moonshot.cn) |
| **Supabase** | Database & Auth | [supabase.com](https://supabase.com) |
| **Clerk** | User Authentication | [clerk.com](https://clerk.com) |

### System Requirements

- **Docker** 24.0+ ([Install](https://docs.docker.com/get-docker/))
- **Docker Compose** 2.20+ (included with Docker Desktop)
- **4GB RAM** minimum (8GB recommended)
- **Ports**: 3000, 8000 available

---

## 🎯 Step-by-Step Setup

### Step 1: Clone & Enter Directory

```bash
git clone <your-repo-url>
cd ai-analytics-platform
```

### Step 2: Run Setup Wizard

```bash
make setup
```

This interactive script will:
1. ✅ Check your system requirements
2. ✅ Create a secure `.env` file
3. ✅ Prompt for API keys (hidden input for security)
4. ✅ Validate your credentials
5. ✅ Set up SSL certificates (local dev)
6. ✅ Initialize the database

### Step 3: Start the Platform

```bash
make start
```

Or use the script directly:
```bash
./scripts/start.sh
```

### Step 4: Access Your Analytics Platform

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:3000 | Main application UI |
| **API Docs** | http://localhost:8000/docs | Interactive API documentation |
| **Health** | http://localhost:8000/health | System status |

---

## 🎮 First Time Usage

### 1. Sign Up / Sign In

Click "Sign In" in the top right. The app uses Clerk for authentication - you can use:
- Email/password
- Google OAuth
- GitHub OAuth

### 2. Connect Your Database

1. Go to **Settings** → **Connections**
2. Click **"Add Connection"**
3. Enter your database details:
   - Host: `your-db-host.com`
   - Port: `5432` (or your port)
   - Database: `analytics`
   - Username: `readonly_user`
   - Password: `••••••••`
4. Click **"Test Connection"** then **"Save"**

### 3. Ask Your First Question

In the main search bar, try:

```
"Show me monthly revenue for the last 6 months"
```

Kimi K2.5 will:
1. 🔍 Analyze your database schema
2. 💡 Understand your question
3. 📝 Generate optimized SQL
4. 📊 Create a beautiful visualization

---

## 🛠️ Common Commands

```bash
# Start everything
make start

# Stop everything
make stop

# View logs
make logs

# Check health
make health

# Run migrations
make migrate

# Reset database
make db-reset

# Shell into backend
make shell-backend

# Access database
make shell-db
```

---

## 🔧 Configuration

### Environment Variables

Your `.env` file contains all configuration:

```bash
# Core AI (Kimi K2.5)
MOONSHOT_API_KEY=sk-proj-xxxxx
MOONSHOT_MODEL=kimi-k2-5

# Database (Supabase)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJxxxxx
DATABASE_URL=postgresql://...

# Auth (Clerk)
CLERK_SECRET_KEY=sk_test_xxxxx
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxxxx
```

Edit `.env` directly or re-run `make setup`.

---

## 🐳 Deployment Options

### Option A: Local Docker (Development)

```bash
# Uses local PostgreSQL + Redis
make start
```

### Option B: Production with Supabase

```bash
# Uses Supabase for database
# Set DATABASE_URL to your Supabase connection string
docker-compose -f config/docker/docker-compose.prod.yml up -d
```

### Option C: Cloud Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for:
- AWS ECS
- Google Cloud Run
- Railway
- Render
- Fly.io

---

## 🚨 Troubleshooting

### "Port already in use"

```bash
# Check what's using port 3000
lsof -i :3000

# Stop it or change ports in .env
FRONTEND_PORT=3001
```

### "Database connection failed"

```bash
# Test connection manually
./scripts/health-check.sh --verbose

# Check .env DATABASE_URL format
# Should be: postgresql+asyncpg://user:pass@host:6543/db?sslmode=require
```

### "Moonshot API error"

```bash
# Test your API key
curl https://api.moonshot.cn/v1/models \
  -H "Authorization: Bearer $MOONSHOT_API_KEY"

# Check key starts with "sk-proj-"
```

### Docker issues

```bash
# Reset everything
make clean-all
make setup

# Or manually:
docker-compose down -v
docker system prune -f
```

---

## 📚 Next Steps

- 📖 **[Full Documentation](SETUP.md)** - Complete setup guide
- 🏗️ **[Architecture](backend/ARCHITECTURE.md)** - System design
- 🔌 **[API Reference](http://localhost:8000/docs)** - Interactive docs
- 🤝 **[Contributing](CONTRIBUTING.md)** - How to contribute

---

## 💡 Pro Tips

1. **Use `make` shortcuts** - They're faster than typing full commands
2. **Check logs often** - `make logs-backend` shows errors in real-time
3. **Seed data** - Run `make seed` to get demo data instantly
4. **Health checks** - Run `make health` before reporting issues
5. **Back up** - Use `make backup` before major changes

---

## 🆘 Getting Help

1. Run diagnostics: `./scripts/health-check.sh --verbose`
2. Check logs: `make logs`
3. Review [SETUP.md](SETUP.md) for detailed instructions
4. Open an issue on GitHub with diagnostics output

---

**Happy Analyzing! 🎉**
