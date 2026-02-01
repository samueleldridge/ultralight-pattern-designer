#!/bin/bash
#
# Health Check Script
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

check_service() {
    local name=$1
    local url=$2
    
    if curl -s -f "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✅${NC} $name"
        return 0
    else
        echo -e "${RED}❌${NC} $name"
        return 1
    fi
}

echo "🏥 Health Check"
echo "==============="
echo ""

check_service "Backend API" "http://localhost:8000/health"
check_service "Frontend" "http://localhost:3000" || true
check_service "API Docs" "http://localhost:8000/docs" || true

echo ""
echo "🔍 Checking environment..."

if [ -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${GREEN}✅${NC} .env file exists"
else
    echo -e "${RED}❌${NC} .env file missing"
fi

echo ""
echo "Done!"
