#!/bin/bash
#
# AI Analytics Platform - Automated Setup Script
# This script sets up the entire platform with security best practices
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"
ENV_EXAMPLE="$PROJECT_ROOT/.env.example"

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

# ASCII Art Banner
cat << 'EOF'
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║          🤖 AI Analytics Platform - Setup Wizard                 ║
║                                                                  ║
║       Powered by Kimi K2.5 • Supabase • Enterprise Security     ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
EOF

echo ""
log_info "Starting setup process..."
echo ""

# ============================================
# STEP 1: Check Prerequisites
# ============================================
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local missing=()
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        missing+=("docker")
    else
        local docker_version=$(docker --version | grep -oE '[0-9]+\.[0-9]+' | head -1)
        log_success "Docker found (v$docker_version)"
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        missing+=("docker-compose")
    else
        log_success "Docker Compose found"
    fi
    
    # Check ports
    local ports=(3000 8000 5432 6379)
    for port in "${ports[@]}"; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            log_warn "Port $port is already in use"
        fi
    done
    
    if [ ${#missing[@]} -ne 0 ]; then
        log_error "Missing prerequisites: ${missing[*]}"
        log_info "Please install missing tools and try again"
        exit 1
    fi
    
    log_success "All prerequisites met"
}

# ============================================
# STEP 2: Create .env File
# ============================================
setup_environment() {
    log_info "Setting up environment configuration..."
    
    if [ -f "$ENV_FILE" ]; then
        log_warn ".env file already exists"
        read -p "Overwrite existing configuration? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Keeping existing .env file"
            return
        fi
        cp "$ENV_FILE" "$ENV_FILE.backup.$(date +%Y%m%d%H%M%S)"
        log_info "Backup created: .env.backup.*"
    fi
    
    # Create new .env from template
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    
    # Generate secure random keys
    local secret_key=$(openssl rand -hex 32)
    local jwt_secret=$(openssl rand -hex 32)
    local encryption_key=$(openssl rand -hex 16)
    
    # Update generated secrets
    sed -i.bak "s|SECRET_KEY=.*|SECRET_KEY=$secret_key|g" "$ENV_FILE"
    sed -i.bak "s|JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$jwt_secret|g" "$ENV_FILE"
    sed -i.bak "s|ENCRYPTION_KEY=.*|ENCRYPTION_KEY=$encryption_key|g" "$ENV_FILE"
    rm -f "$ENV_FILE.bak"
    
    log_success "Environment file created"
}

# ============================================
# STEP 3: Collect API Keys
# ============================================
collect_api_keys() {
    log_info "Please enter your API keys (input will be hidden for security)"
    echo ""
    
    echo -e "${YELLOW}┌─────────────────────────────────────────────────────────┐${NC}"
    echo -e "${YELLOW}│  Moonshot AI (Kimi K2.5) - Get key at:                  │${NC}"
    echo -e "${YELLOW}│  https://platform.moonshot.cn                          │${NC}"
    echo -e "${YELLOW}└─────────────────────────────────────────────────────────┘${NC}"
    
    read -s -p "Moonshot API Key (sk-proj-...): " moonshot_key
    echo
    
    if [[ ! $moonshot_key =~ ^sk-proj-[a-zA-Z0-9]+$ ]]; then
        log_warn "Key format doesn't match expected pattern, but continuing..."
    fi
    
    echo ""
    echo -e "${YELLOW}┌─────────────────────────────────────────────────────────┐${NC}"
    echo -e "${YELLOW}│  Supabase - Get credentials from:                       │${NC}"
    echo -e "${YELLOW}│  https://supabase.com/dashboard                         │${NC}"
    echo -e "${YELLOW}└─────────────────────────────────────────────────────────┘${NC}"
    
    read -p "Supabase Project URL (https://...supabase.co): " supabase_url
    read -s -p "Supabase Service Role Key (eyJ...): " supabase_service_key
    echo
    read -s -p "Supabase Anon Key (eyJ...): " supabase_anon_key
    echo
    
    echo ""
    echo -e "${YELLOW}┌─────────────────────────────────────────────────────────┐${NC}"
    echo -e "${YELLOW}│  Clerk Authentication - Get keys from:                  │${NC}"
    echo -e "${YELLOW}│  https://dashboard.clerk.com                           │${NC}"
    echo -e "${YELLOW}└─────────────────────────────────────────────────────────┘${NC}"
    
    read -s -p "Clerk Secret Key (sk_test_... or sk_live_...): " clerk_secret
    echo
    read -p "Clerk Publishable Key (pk_test_... or pk_live_...): " clerk_publishable
    
    # Optional: OpenAI fallback
    echo ""
    read -p "OpenAI API Key (optional, for fallback): " -s openai_key
    echo
    
    # Update .env file with provided keys
    sed -i.bak "s|MOONSHOT_API_KEY=.*|MOONSHOT_API_KEY=$moonshot_key|g" "$ENV_FILE"
    sed -i.bak "s|SUPABASE_URL=.*|SUPABASE_URL=$supabase_url|g" "$ENV_FILE"
    sed -i.bak "s|SUPABASE_SERVICE_KEY=.*|SUPABASE_SERVICE_KEY=$supabase_service_key|g" "$ENV_FILE"
    sed -i.bak "s|SUPABASE_ANON_KEY=.*|SUPABASE_ANON_KEY=$supabase_anon_key|g" "$ENV_FILE"
    sed -i.bak "s|CLERK_SECRET_KEY=.*|CLERK_SECRET_KEY=$clerk_secret|g" "$ENV_FILE"
    sed -i.bak "s|CLERK_PUBLISHABLE_KEY=.*|CLERK_PUBLISHABLE_KEY=$clerk_publishable|g" "$ENV_FILE"
    sed -i.bak "s|NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=.*|NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$clerk_publishable|g" "$ENV_FILE"
    
    if [ -n "$openai_key" ]; then
        sed -i.bak "s|OPENAI_API_KEY=.*|OPENAI_API_KEY=$openai_key|g" "$ENV_FILE"
    fi
    
    # Set database URL from Supabase URL
    local project_ref=$(echo "$supabase_url" | sed -E 's|https://([^.]+).*|\1|')
    local db_url="postgresql://postgres.$project_ref@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require"
    sed -i.bak "s|DATABASE_URL=.*|DATABASE_URL=$db_url|g" "$ENV_FILE"
    
    rm -f "$ENV_FILE.bak"
    
    log_success "API keys configured"
}

# ============================================
# STEP 4: Validate Configuration
# ============================================
validate_setup() {
    log_info "Validating configuration..."
    
    # Source the .env file
    set -a
    source "$ENV_FILE"
    set +a
    
    # Validate Moonshot API key
    log_info "Testing Moonshot API connection..."
    if curl -s -f -H "Authorization: Bearer $MOONSHOT_API_KEY" \
         https://api.moonshot.cn/v1/models > /dev/null 2>&1; then
        log_success "Moonshot API connection successful"
    else
        log_warn "Could not verify Moonshot API connection (may be network issue)"
    fi
    
    # Validate Supabase connection
    log_info "Testing Supabase connection..."
    if curl -s -f -H "apikey: $SUPABASE_ANON_KEY" \
         -H "Authorization: Bearer $SUPABASE_ANON_KEY" \
         "$SUPABASE_URL/rest/v1/" > /dev/null 2>&1; then
        log_success "Supabase connection successful"
    else
        log_warn "Could not verify Supabase connection"
    fi
    
    log_success "Configuration validation complete"
}

# ============================================
# STEP 5: Setup Directories
# ============================================
setup_directories() {
    log_info "Creating necessary directories..."
    
    mkdir -p "$PROJECT_ROOT/data/postgres"
    mkdir -p "$PROJECT_ROOT/data/redis"
    mkdir -p "$PROJECT_ROOT/data/logs"
    mkdir -p "$PROJECT_ROOT/data/ssl"
    mkdir -p "$PROJECT_ROOT/data/backups"
    
    # Create .gitignore for data directory
    echo "*" > "$PROJECT_ROOT/data/.gitignore"
    echo "!.gitignore" >> "$PROJECT_ROOT/data/.gitignore"
    
    log_success "Directories created"
}

# ============================================
# STEP 6: SSL Certificates (Local Dev)
# ============================================
setup_ssl() {
    log_info "Setting up SSL certificates for local development..."
    
    if command -v mkcert &> /dev/null; then
        cd "$PROJECT_ROOT/data/ssl"
        mkcert -install
        mkcert localhost 127.0.0.1 ::1
        log_success "SSL certificates generated with mkcert"
    else
        log_warn "mkcert not found, skipping SSL setup"
        log_info "To install mkcert: https://github.com/FiloSottile/mkcert"
    fi
}

# ============================================
# STEP 7: Final Instructions
# ============================================
show_completion() {
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                                  ║${NC}"
    echo -e "${GREEN}║              ✅ Setup Complete!                                  ║${NC}"
    echo -e "${GREEN}║                                                                  ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    log_info "Next steps:"
    echo ""
    echo "  1. Start the platform:"
    echo -e "     ${YELLOW}./scripts/start.sh${NC}"
    echo ""
    echo "  2. Or start manually with Docker:"
    echo -e "     ${YELLOW}docker-compose up -d${NC}"
    echo ""
    echo "  3. Access your platform:"
    echo -e "     • Frontend: ${BLUE}http://localhost:3000${NC}"
    echo -e "     • API:      ${BLUE}http://localhost:8000${NC}"
    echo -e "     • API Docs: ${BLUE}http://localhost:8000/docs${NC}"
    echo ""
    echo "  4. Run health check:"
    echo -e "     ${YELLOW}./scripts/health-check.sh${NC}"
    echo ""
    echo "  5. View logs:"
    echo -e "     ${YELLOW}docker-compose logs -f${NC}"
    echo ""
    log_info "Need help? Check SETUP.md or open an issue on GitHub"
}

# ============================================
# MAIN EXECUTION
# ============================================
main() {
    check_prerequisites
    setup_environment
    collect_api_keys
    validate_setup
    setup_directories
    setup_ssl
    show_completion
}

# Run main function
main "$@"
