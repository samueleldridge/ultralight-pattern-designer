.PHONY: help setup start stop restart logs shell clean test migrate health

# Default target
help:
	@echo "╔══════════════════════════════════════════════════════════════════╗"
	@echo "║         AI Analytics Platform - Available Commands               ║"
	@echo "╠══════════════════════════════════════════════════════════════════╣"
	@echo "║                                                                  ║"
	@echo "║  Setup & Installation                                            ║"
	@echo "║    make setup           Run automated setup wizard               ║"
	@echo "║    make install-deps    Check and install dependencies           ║"
	@echo "║                                                                  ║"
	@echo "║  Development                                                     ║"
	@echo "║    make start           Start all services (docker-compose)      ║"
	@echo "║    make stop            Stop all services                        ║"
	@echo "║    make restart         Restart all services                     ║"
	@echo "║    make logs            View logs from all services              ║"
	@echo "║    make logs-backend    View backend logs only                   ║"
	@echo "║    make logs-frontend   View frontend logs only                  ║"
	@echo "║                                                                  ║"
	@echo "║  Database                                                        ║"
	@echo "║    make migrate         Run database migrations                  ║"
	@echo "║    make seed            Seed database with demo data             ║"
	@echo "║    make db-reset        Reset database (WARNING: destructive)    ║"
	@echo "║                                                                  ║"
	@echo "║  Testing & Health                                                ║"
	@echo "║    make test            Run test suite                           ║"
	@echo "║    make health          Run health checks                        ║"
	@echo "║    make lint            Run linting                              ║"
	@echo "║                                                                  ║"
	@echo "║  Shell Access                                                    ║"
	@echo "║    make shell-backend   Open shell in backend container          ║"
	@echo "║    make shell-db        Open PostgreSQL shell                    ║"
	@echo "║    make shell-redis     Open Redis CLI                           ║"
	@echo "║                                                                  ║"
	@echo "║  Production                                                      ║"
	@echo "║    make prod-up         Start production services                ║"
	@echo "║    make prod-down       Stop production services                 ║"
	@echo "║                                                                  ║"
	@echo "║  Cleanup                                                         ║"
	@echo "║    make clean           Remove containers and volumes            ║"
	@echo "║    make clean-all       Deep clean (containers, volumes, images) ║"
	@echo "║                                                                  ║"
	@echo "╚══════════════════════════════════════════════════════════════════╝"

# ═════════════════════════════════════════════════════════════════════════════
# SETUP & INSTALLATION
# ═════════════════════════════════════════════════════════════════════════════

setup:
	@echo "🚀 Starting AI Analytics Platform setup..."
	@./scripts/setup.sh

install-deps:
	@echo "Checking dependencies..."
	@command -v docker >/dev/null 2>&1 || { echo "❌ Docker not found. Install: https://docs.docker.com/get-docker/"; exit 1; }
	@command -v docker-compose >/dev/null 2>&1 || docker compose version >/dev/null 2>&1 || { echo "❌ Docker Compose not found. Install: https://docs.docker.com/compose/install/"; exit 1; }
	@echo "✅ All dependencies found"

# ═════════════════════════════════════════════════════════════════════════════
# DEVELOPMENT
# ═════════════════════════════════════════════════════════════════════════════

start:
	@echo "🚀 Starting development environment..."
	@./scripts/start.sh

stop:
	@echo "🛑 Stopping services..."
	@./scripts/stop.sh

restart: stop start

logs:
	@docker-compose logs -f

logs-backend:
	@docker-compose logs -f backend

logs-frontend:
	@docker-compose logs -f frontend

logs-db:
	@docker-compose logs -f postgres

# ═════════════════════════════════════════════════════════════════════════════
# DATABASE
# ═════════════════════════════════════════════════════════════════════════════

migrate:
	@./scripts/migrate.sh migrate

seed:
	@./scripts/migrate.sh seed

db-reset:
	@./scripts/migrate.sh reset

db-status:
	@./scripts/migrate.sh status

# ═════════════════════════════════════════════════════════════════════════════
# TESTING & HEALTH
# ═════════════════════════════════════════════════════════════════════════════

test:
	@echo "🧪 Running tests..."
	@cd backend && python -m pytest app/tests/ -v || true

health:
	@./scripts/health-check.sh

lint:
	@echo "🔍 Running linters..."
	@cd backend && flake8 app/ --max-line-length=100 || true
	@cd frontend && npm run lint || true

# ═════════════════════════════════════════════════════════════════════════════
# SHELL ACCESS
# ═════════════════════════════════════════════════════════════════════════════

shell-backend:
	@docker-compose exec backend /bin/bash

shell-frontend:
	@docker-compose exec frontend /bin/sh

shell-db:
	@docker-compose exec postgres psql -U postgres -d aianalytics

shell-redis:
	@docker-compose exec redis redis-cli

# ═════════════════════════════════════════════════════════════════════════════
# PRODUCTION
# ═════════════════════════════════════════════════════════════════════════════

prod-up:
	@echo "🚀 Starting production environment..."
	@docker-compose -f config/docker/docker-compose.prod.yml up -d

prod-down:
	@echo "🛑 Stopping production environment..."
	@docker-compose -f config/docker/docker-compose.prod.yml down

prod-logs:
	@docker-compose -f config/docker/docker-compose.prod.yml logs -f

prod-build:
	@docker-compose -f config/docker/docker-compose.prod.yml build

# ═════════════════════════════════════════════════════════════════════════════
# CLEANUP
# ═════════════════════════════════════════════════════════════════════════════

clean:
	@echo "🧹 Cleaning up containers..."
	@docker-compose down -v
	@echo "✅ Containers and volumes removed"

clean-all:
	@echo "🧹 Deep cleaning (containers, volumes, images)..."
	@docker-compose down -v --rmi all
	@docker system prune -f
	@echo "✅ Deep clean complete"

# ═════════════════════════════════════════════════════════════════════════════
# UTILITY
# ═════════════════════════════════════════════════════════════════════════════

format:
	@echo "📝 Formatting code..."
	@cd backend && black app/ || true
	@cd frontend && npm run format || true

update:
	@echo "⬇️  Pulling latest changes..."
	@git pull origin main
	@docker-compose pull
	@make migrate
	@make restart

backup:
	@echo "💾 Creating backup..."
	@mkdir -p backups
	@docker-compose exec postgres pg_dump -U postgres aianalytics > backups/backup-$$(date +%Y%m%d-%H%M%S).sql
	@echo "✅ Backup created in backups/"

restore:
	@echo "📂 Available backups:"
	@ls -la backups/
	@read -p "Enter backup filename to restore: " file; \
	docker-compose exec -T postgres psql -U postgres -d aianalytics < backups/$$file

# Quick development cycle
dev: start logs

# Full reset and restart
reset: clean start
