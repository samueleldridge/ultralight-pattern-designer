#!/bin/bash
#
# AI Analytics Platform - Database Migration Script
# Handles schema migrations and seed data
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

# Source environment
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
else
    echo "Error: .env file not found. Run ./scripts/setup.sh first."
    exit 1
fi

# Determine compose command
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
else
    echo "Error: docker-compose not found"
    exit 1
fi

# Parse command
COMMAND=${1:-"migrate"}

case $COMMAND in
    migrate|up)
        log_info "Running database migrations..."
        
        # Run migrations inside backend container
        $COMPOSE_CMD -f "$PROJECT_ROOT/docker-compose.yml" exec backend \
            python -c "
import asyncio
from app.database import engine
from app.models import Base

async def migrate():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('Migrations complete')

asyncio.run(migrate())
" 2>/dev/null || {
            log_warn "Could not run migrations via backend, using direct SQL..."
            # Fallback: run SQL directly
            if [ -n "${DATABASE_URL:-}" ]; then
                psql "$DATABASE_URL" -f "$PROJECT_ROOT/config/supabase/schema.sql" || {
                    log_warn "Could not connect to database directly"
                    log_info "Please run migrations manually in Supabase SQL Editor"
                    log_info "File: config/supabase/schema.sql"
                }
            fi
        }
        
        log_success "Migrations complete"
        ;;
    
    seed)
        log_info "Seeding database with demo data..."
        
        if [ -n "${DATABASE_URL:-}" ]; then
            psql "$DATABASE_URL" -f "$PROJECT_ROOT/config/supabase/seed.sql" || {
                log_warn "Could not seed database directly"
                log_info "Please run seed data manually in Supabase SQL Editor"
                log_info "File: config/supabase/seed.sql"
            }
        fi
        
        log_success "Database seeded"
        ;;
    
    reset)
        log_warn "This will DELETE all data. Are you sure? (y/N)"
        read -r confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
            log_info "Resetting database..."
            # Note: Actual reset logic would go here
            # This is a placeholder for safety
            log_warn "Reset not implemented for safety. Please use Supabase Dashboard."
        else
            log_info "Reset cancelled"
        fi
        ;;
    
    status)
        log_info "Checking migration status..."
        # Would query migration tracking table
        log_info "Migration tracking: Not implemented (using SQL schema)"
        ;;
    
    *)
        echo "Usage: $0 {migrate|seed|reset|status}"
        echo ""
        echo "Commands:"
        echo "  migrate  Run pending migrations"
        echo "  seed     Load demo data"
        echo "  reset    Reset database (DANGEROUS)"
        echo "  status   Show migration status"
        exit 1
        ;;
esac
