#!/bin/bash
#
# Test script to validate the AI Analytics Platform setup
# Run this after setup to ensure everything is configured correctly
#

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PASSED=0
FAILED=0

test_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $2"
        ((FAILED++))
    fi
}

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                    AI Analytics Platform Tests                   ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Test 1: Check .env file exists
echo "Testing configuration files..."
if [ -f "$PROJECT_ROOT/.env" ]; then
    test_result 0 ".env file exists"
else
    test_result 1 ".env file exists (run ./scripts/setup.sh)"
fi

# Test 2: Check required env vars
echo ""
echo "Testing environment variables..."
if [ -f "$PROJECT_ROOT/.env" ]; then
    source "$PROJECT_ROOT/.env"
    
    [ -n "$MOONSHOT_API_KEY" ] && test_result 0 "MOONSHOT_API_KEY is set" || test_result 1 "MOONSHOT_API_KEY is set"
    [ -n "$SUPABASE_URL" ] && test_result 0 "SUPABASE_URL is set" || test_result 1 "SUPABASE_URL is set"
    [ -n "$SUPABASE_SERVICE_KEY" ] && test_result 0 "SUPABASE_SERVICE_KEY is set" || test_result 1 "SUPABASE_SERVICE_KEY is set"
    [ -n "$CLERK_SECRET_KEY" ] && test_result 0 "CLERK_SECRET_KEY is set" || test_result 1 "CLERK_SECRET_KEY is set"
fi

# Test 3: Check Docker
echo ""
echo "Testing Docker..."
docker ps > /dev/null 2>&1 && test_result 0 "Docker daemon is running" || test_result 1 "Docker daemon is running"
command -v docker-compose > /dev/null 2>&1 && test_result 0 "Docker Compose is installed" || test_result 1 "Docker Compose is installed"

# Test 4: Check file structure
echo ""
echo "Testing file structure..."
[ -f "$PROJECT_ROOT/backend/app/main.py" ] && test_result 0 "Backend main.py exists" || test_result 1 "Backend main.py exists"
[ -f "$PROJECT_ROOT/frontend/package.json" ] && test_result 0 "Frontend package.json exists" || test_result 1 "Frontend package.json exists"
[ -f "$PROJECT_ROOT/docker-compose.yml" ] && test_result 0 "docker-compose.yml exists" || test_result 1 "docker-compose.yml exists"
[ -f "$PROJECT_ROOT/config/supabase/schema.sql" ] && test_result 0 "Database schema exists" || test_result 1 "Database schema exists"

# Test 5: Test API connectivity (if running)
echo ""
echo "Testing API connectivity..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    test_result 0 "Backend API is responding"
    
    # Test specific endpoints
    curl -s http://localhost:8000/health | grep -q "ok" && test_result 0 "Health endpoint returns ok" || test_result 1 "Health endpoint returns ok"
else
    test_result 1 "Backend API is responding (is it running?)"
fi

# Test 6: Test Moonshot API
echo ""
echo "Testing external APIs..."
if [ -n "${MOONSHOT_API_KEY:-}" ]; then
    if curl -s -H "Authorization: Bearer $MOONSHOT_API_KEY" https://api.moonshot.cn/v1/models > /dev/null 2>&1; then
        test_result 0 "Moonshot API key is valid"
    else
        test_result 1 "Moonshot API key is valid"
    fi
else
    test_result 1 "Moonshot API key is valid (not set)"
fi

# Summary
echo ""
echo "═══════════════════════════════════════════════════════════════════"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
else
    echo -e "${YELLOW}⚠️  $FAILED test(s) failed${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Run ./scripts/setup.sh to configure environment"
    echo "  2. Run make start to start services"
    echo "  3. Check QUICKSTART.md for help"
fi
echo "═══════════════════════════════════════════════════════════════════"
echo "Passed: $PASSED | Failed: $FAILED"
echo ""

exit $FAILED
