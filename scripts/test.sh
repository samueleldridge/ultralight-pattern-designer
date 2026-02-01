#!/bin/bash
# Test runner script for AI Analytics Platform
# Usage: ./scripts/test.sh [options]
#
# Options:
#   unit        Run unit tests only (fast, no external deps)
#   integration Run integration tests (requires database)
#   coverage    Run all tests with coverage report
#   ci          Run CI test suite
#   watch       Run tests in watch mode
#   help        Show this help message

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
BACKEND_DIR="$PROJECT_ROOT/backend"

# Default values
TEST_TYPE="all"
COVERAGE=false
VERBOSE=false
MARKERS=""

echo -e "${BLUE}AI Analytics Platform - Test Runner${NC}"
echo "========================================"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        unit)
            TEST_TYPE="unit"
            MARKERS="-m unit"
            shift
            ;;
        integration)
            TEST_TYPE="integration"
            MARKERS="-m integration"
            shift
            ;;
        coverage)
            COVERAGE=true
            shift
            ;;
        ci)
            TEST_TYPE="ci"
            MARKERS="-m 'not slow'"
            COVERAGE=true
            shift
            ;;
        api)
            TEST_TYPE="api"
            MARKERS="-m api"
            shift
            ;;
        agent)
            TEST_TYPE="agent"
            MARKERS="-m agent"
            shift
            ;;
        db)
            TEST_TYPE="db"
            MARKERS="-m db"
            shift
            ;;
        watch)
            TEST_TYPE="watch"
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        help|--help|-h)
            echo ""
            echo "Usage: ./scripts/test.sh [command] [options]"
            echo ""
            echo "Commands:"
            echo "  unit         Run unit tests only (fast, mocked)"
            echo "  integration  Run integration tests (requires services)"
            echo "  api          Run API endpoint tests"
            echo "  agent        Run agent workflow tests"
            echo "  db           Run database tests"
            echo "  coverage     Run all tests with coverage report"
            echo "  ci           Run CI test suite (excludes slow tests)"
            echo "  watch        Run tests in watch mode"
            echo ""
            echo "Options:"
            echo "  -v, --verbose  Enable verbose output"
            echo "  -h, --help     Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./scripts/test.sh unit           # Run unit tests"
            echo "  ./scripts/test.sh integration    # Run integration tests"
            echo "  ./scripts/test.sh coverage       # Run with coverage"
            echo "  ./scripts/test.sh ci             # Run CI suite"
            echo "  ./scripts/test.sh -v             # Run all tests verbosely"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Run './scripts/test.sh help' for usage information"
            exit 1
            ;;
    esac
done

# Check if we're in the right directory
if [ ! -f "$BACKEND_DIR/pytest.ini" ]; then
    echo -e "${RED}Error: Could not find backend/pytest.ini${NC}"
    echo "Make sure you're running this script from the project root."
    exit 1
fi

# Change to backend directory
cd "$BACKEND_DIR"

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo -e "${BLUE}Activating virtual environment...${NC}"
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo -e "${BLUE}Activating virtual environment...${NC}"
    source .venv/bin/activate
fi

# Install test dependencies if needed
echo -e "${BLUE}Checking test dependencies...${NC}"
pip install -q pytest pytest-asyncio pytest-cov httpx anyio 2>/dev/null || true

# Set environment variables for testing
export PYTHONPATH="${BACKEND_DIR}:${PYTHONPATH}"
export TESTING=true
export ENVIRONMENT=test

# Set test database URL if not already set
if [ -z "$TEST_DATABASE_URL" ]; then
    export TEST_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/aianalytics_test"
    echo -e "${YELLOW}Using default test database URL: $TEST_DATABASE_URL${NC}"
    echo -e "${YELLOW}Set TEST_DATABASE_URL environment variable to override${NC}"
fi

# Build pytest command
PYTEST_ARGS=""

# Add markers
if [ -n "$MARKERS" ]; then
    PYTEST_ARGS="$PYTEST_ARGS $MARKERS"
fi

# Add coverage if requested
if [ "$COVERAGE" = true ]; then
    PYTEST_ARGS="$PYTEST_ARGS --cov=app --cov-report=term-missing --cov-report=html:htmlcov"
fi

# Add verbosity
if [ "$VERBOSE" = true ]; then
    PYTEST_ARGS="$PYTEST_ARGS -v -s"
fi

# Handle watch mode
if [ "$TEST_TYPE" = "watch" ]; then
    echo -e "${BLUE}Running tests in watch mode...${NC}"
    echo -e "${YELLOW}Install pytest-watch with: pip install pytest-watch${NC}"
    
    if command -v ptw &> /dev/null; then
        ptw tests/ -- $PYTEST_ARGS
    else
        echo -e "${RED}pytest-watch not installed. Install with: pip install pytest-watch${NC}"
        exit 1
    fi
    exit 0
fi

# Check database connection for integration tests
if [ "$TEST_TYPE" = "integration" ] || [ "$TEST_TYPE" = "ci" ] || [ "$TEST_TYPE" = "db" ]; then
    echo -e "${BLUE}Checking database connection...${NC}"
    
    # Try to connect to the database
    python3 -c "
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check_db():
    try:
        engine = create_async_engine('$TEST_DATABASE_URL', echo=False)
        async with engine.connect() as conn:
            result = await conn.execute(text('SELECT 1'))
            print('Database connection successful')
            return True
    except Exception as e:
        print(f'Database connection failed: {e}')
        return False

success = asyncio.run(check_db())
sys.exit(0 if success else 1)
" || {
        echo -e "${RED}Failed to connect to test database.${NC}"
        echo -e "${YELLOW}Make sure PostgreSQL is running and accessible.${NC}"
        echo -e "${YELLOW}You may need to create the test database:${NC}"
        echo -e "${YELLOW}  createdb aianalytics_test${NC}"
        exit 1
    }
fi

# Run tests
echo ""
echo -e "${BLUE}Running tests...${NC}"
echo "========================================"

if [ "$TEST_TYPE" = "unit" ]; then
    echo -e "${GREEN}Running unit tests (fast, no external deps)...${NC}"
elif [ "$TEST_TYPE" = "integration" ]; then
    echo -e "${GREEN}Running integration tests...${NC}"
elif [ "$TEST_TYPE" = "api" ]; then
    echo -e "${GREEN}Running API tests...${NC}"
elif [ "$TEST_TYPE" = "agent" ]; then
    echo -e "${GREEN}Running agent tests...${NC}"
elif [ "$TEST_TYPE" = "db" ]; then
    echo -e "${GREEN}Running database tests...${NC}"
elif [ "$TEST_TYPE" = "ci" ]; then
    echo -e "${GREEN}Running CI test suite...${NC}"
else
    echo -e "${GREEN}Running all tests...${NC}"
fi

# Run pytest
python -m pytest tests/ $PYTEST_ARGS

# Capture exit code
EXIT_CODE=$?

echo ""
echo "========================================"

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    
    if [ "$COVERAGE" = true ]; then
        echo ""
        echo -e "${BLUE}Coverage report generated in htmlcov/index.html${NC}"
        echo -e "${BLUE}Open with: open htmlcov/index.html${NC}"
    fi
else
    echo -e "${RED}Tests failed with exit code $EXIT_CODE${NC}"
fi

exit $EXIT_CODE
