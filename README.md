# AI Analytics Platform

> **Natural language to SQL analytics powered by Kimi K2.5**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

Transform your database into intelligent insights. Ask questions in plain English, get beautiful visualizations powered by the advanced reasoning of Kimi K2.5.

![Platform Preview](docs/assets/preview.png)

---

## ✨ Features

🧠 **AI-Powered Analytics**
- Natural language to SQL with Kimi K2.5
- Smart schema understanding
- Automatic visualization suggestions
- Multi-turn reasoning for complex queries

🔐 **Enterprise Security**
- Supabase PostgreSQL with Row Level Security
- Clerk authentication
- Encrypted database credentials
- Audit logging

⚡ **Production Ready**
- Docker containerization
- Redis caching
- Horizontal scaling
- Health monitoring

📊 **Beautiful Visualizations**
- Auto-generated charts
- Interactive dashboards
- Real-time collaboration
- Export to PNG/SVG/CSV

---

## 🚀 Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) 24.0+
- API keys: [Moonshot AI](https://platform.moonshot.cn), [Supabase](https://supabase.com), [Clerk](https://clerk.com)

### One-Command Setup

```bash
git clone <repository>
cd ai-analytics-platform
make setup
```

Then visit http://localhost:3000

**[→ Full Setup Guide](SETUP.md)** | **[→ Quick Start](QUICKSTART.md)**

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Next.js       │────▶│   FastAPI        │────▶│   Kimi K2.5     │
│   Frontend      │◄────│   Backend        │◄────│   (Moonshot)    │
│   (Port 3000)   │     │   (Port 8000)    │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   Supabase       │
                       │   PostgreSQL     │
                       │   + pgvector     │
                       └──────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   Redis Cache    │
                       └──────────────────┘
```

---

## 📁 Project Structure

```
ai-analytics-platform/
├── 📄 SETUP.md              # Complete setup guide
├── 📄 QUICKSTART.md         # Quick start guide
├── 📄 DEPLOYMENT.md         # Deployment options
├── 📁 scripts/              # Automation scripts
│   ├── setup.sh            # One-time setup
│   ├── start.sh            # Start services
│   └── health-check.sh     # Verify deployment
├── 📁 config/               # Configuration files
│   ├── supabase/           # Database schema
│   ├── docker/             # Compose configs
│   └── nginx/              # Reverse proxy
├── 📁 backend/              # FastAPI application
│   ├── app/
│   │   ├── agent/          # AI agent (Kimi K2.5)
│   │   ├── api/            # REST endpoints
│   │   └── llm_provider.py # Unified LLM interface
│   └── Dockerfile
└── 📁 frontend/             # Next.js application
    ├── app/
    └── Dockerfile
```

---

## 🎯 Usage Examples

### Natural Language Queries

```
"What was our revenue last quarter by region?"
"Show me the top 10 customers by lifetime value"
"How has user engagement changed over the past 6 months?"
"Which products have the highest return rate?"
```

### Generated SQL Example

```sql
-- Natural language: "Monthly revenue trend"
SELECT 
    DATE_TRUNC('month', order_date) AS month,
    SUM(total_amount) AS revenue,
    COUNT(*) AS order_count
FROM orders
WHERE order_date >= NOW() - INTERVAL '12 months'
GROUP BY 1
ORDER BY 1;
```

---

## 🛠️ Development

```bash
# Start development environment
make start

# View logs
make logs

# Run tests
make test

# Access database shell
make shell-db
```

### Makefile Commands

| Command | Description |
|---------|-------------|
| `make setup` | Run setup wizard |
| `make start` | Start all services |
| `make stop` | Stop all services |
| `make logs` | View logs |
| `make health` | Run health checks |
| `make migrate` | Run database migrations |
| `make test` | Run test suite |

---

## ☁️ Deployment

### Docker Compose (Production)

```bash
docker-compose -f config/docker/docker-compose.prod.yml up -d
```

### Cloud Platforms

- [Railway](DEPLOYMENT.md#railway) - One-click deploy
- [Render](DEPLOYMENT.md#render) - Platform as a service
- [AWS ECS](DEPLOYMENT.md#aws-ecs) - Container orchestration
- [Google Cloud Run](DEPLOYMENT.md#google-cloud-run) - Serverless containers
- [Fly.io](DEPLOYMENT.md#flyio) - Edge deployment

**[→ Full Deployment Guide](DEPLOYMENT.md)**

---

## 🔒 Security

- **API Keys**: Stored in `.env`, never committed
- **Database**: Row Level Security (RLS) enabled
- **Auth**: JWT-based with Clerk
- **Encryption**: AES-256 for sensitive data
- **CORS**: Configurable origin restrictions

See [SECURITY.md](SECURITY.md) for details.

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📝 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.

---

## 🙏 Acknowledgments

- [Moonshot AI](https://www.moonshot.cn) - Kimi K2.5 LLM
- [Supabase](https://supabase.com) - Backend infrastructure
- [Clerk](https://clerk.com) - Authentication
- [LangChain](https://langchain.com) - AI orchestration
- [FastAPI](https://fastapi.tiangolo.com) - Backend framework
- [Next.js](https://nextjs.org) - Frontend framework

---

## 💬 Support

- 📖 [Documentation](https://docs.ai-analytics.io)
- 🐛 [Issue Tracker](../../issues)
- 💬 [Discussions](../../discussions)

---

<p align="center">
  Built with ❤️ using Kimi K2.5
</p>
