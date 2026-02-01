# Testing Infrastructure

This directory contains the comprehensive testing suite for the AI Analytics Platform backend.

## Overview

- **Framework**: pytest with pytest-asyncio for async support
- **Coverage**: pytest-cov for coverage reporting
- **Mocking**: unittest.mock for external services
- **Fixtures**: Comprehensive fixtures in `conftest.py`

## Test Organization

```
backend/tests/
├── conftest.py        # Shared fixtures and configuration
├── test_api.py        # API endpoint tests
├── test_agent.py      # Agent workflow tests
└── test_database.py   # Database and SQL tests
```

### Test Categories

| Marker | Description | Speed |
|--------|-------------|-------|
| `unit` | Unit tests with mocked dependencies | ⚡ Fast |
| `integration` | Integration tests with real services | 🐢 Slow |
| `api` | API endpoint tests | ⚡ Fast |
| `agent` | Agent workflow tests | ⚡ Fast |
| `db` | Database tests | 🐢 Slow |
| `slow` | Slow tests (LLM calls, heavy compute) | 🐢 Slow |
| `e2e` | End-to-end tests | 🐢 Slow |

## Running Tests

### Quick Start

```bash
# Run all tests
./scripts/test.sh

# Run unit tests only (fast)
./scripts/test.sh unit

# Run integration tests (requires database)
./scripts/test.sh integration

# Run with coverage
./scripts/test.sh coverage

# Run CI suite (excludes slow tests)
./scripts/test.sh ci
```

### Using pytest directly

```bash
cd backend

# Run all tests
pytest

# Run specific test file
pytest tests/test_api.py

# Run specific test
pytest tests/test_api.py::TestQueryEndpoints::test_start_query_success

# Run with markers
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests only
pytest -m "not slow"     # Exclude slow tests

# Run with coverage
pytest --cov=app --cov-report=html

# Run in watch mode (requires pytest-watch)
ptw tests/ -- -v
```

## Test Database Setup

### Option 1: Local PostgreSQL

```bash
# Create test database
createdb aianalytics_test

# Set environment variable
export TEST_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/aianalytics_test"

# Run tests
./scripts/test.sh integration
```

### Option 2: Docker

```bash
# Start PostgreSQL in Docker
docker run -d \
  --name aianalytics-test-db \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=aianalytics_test \
  -p 5432:5432 \
  postgres:15

# Run tests
./scripts/test.sh integration

# Stop container
docker stop aianalytics-test-db
docker rm aianalytics-test-db
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TEST_DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/aianalytics_test` | Test database connection |
| `ENVIRONMENT` | `test` | Environment setting |
| `TESTING` | `true` | Testing mode flag |

## Mocking External Services

All external services are automatically mocked in tests:

- **LLM Provider**: Mocked via `mock_llm_provider` fixture
- **Redis**: Mocked via `mock_redis` fixture
- **Database**: Uses test database with transaction rollback

Example of using mocks:

```python
@pytest.mark.asyncio
async def test_with_mocked_llm(self, sample_agent_state, mock_llm_provider):
    # Configure mock response
    mock_llm_provider.generate_json.return_value = {
        "sql": "SELECT * FROM orders",
        "explanation": "Test"
    }
    
    # Run your test
    result = await generate_sql_node(sample_agent_state)
    assert result["sql"] == "SELECT * FROM orders"
```

## Writing Tests

### API Tests

```python
@pytest.mark.api
class TestNewEndpoint:
    def test_endpoint_success(self, client):
        response = client.get("/api/new-endpoint")
        assert response.status_code == 200
        assert "expected_key" in response.json()
```

### Agent Tests

```python
@pytest.mark.agent
class TestNewNode:
    @pytest.mark.asyncio
    async def test_node_behavior(self, sample_agent_state):
        result = await new_node(sample_agent_state)
        assert result["current_step"] == "new_node"
        assert result["step_status"] == "complete"
```

### Database Tests

```python
@pytest.mark.db
class TestNewQuery:
    @pytest.mark.asyncio
    async def test_query_execution(self, demo_database):
        result = await demo_database.execute(text("SELECT 1"))
        assert result.scalar() == 1
```

## Coverage

Coverage reports are generated in multiple formats:

- **Terminal**: Coverage summary in console
- **HTML**: `backend/htmlcov/index.html` (open in browser)
- **XML**: `backend/coverage.xml` (for CI integration)

To view HTML coverage report:

```bash
# After running tests with coverage
open backend/htmlcov/index.html
```

## CI/CD

Tests run automatically on:
- Push to `main` or `develop`
- Pull requests to `main` or `develop`

See `.github/workflows/test.yml` for CI configuration.

### CI Jobs

1. **Unit Tests**: Fast tests with mocked dependencies
2. **Integration Tests**: Tests with PostgreSQL and Redis services
3. **Coverage Report**: Coverage analysis and upload to Codecov
4. **Lint & Type Check**: Code quality checks

## Troubleshooting

### Database Connection Failed

```
Database connection failed: could not connect to server
```

**Solution**: Start PostgreSQL and create the test database:
```bash
# macOS
brew services start postgresql
createdb aianalytics_test

# Linux
sudo service postgresql start
sudo -u postgres createdb aianalytics_test
```

### Module Import Errors

```
ModuleNotFoundError: No module named 'app'
```

**Solution**: Install dependencies and ensure PYTHONPATH is set:
```bash
cd backend
pip install -r requirements.txt
export PYTHONPATH="${PWD}:${PYTHONPATH}"
```

### Async Tests Not Running

```
pytest.PytestCollectionWarning: async def functions are not natively supported
```

**Solution**: Install pytest-asyncio:
```bash
pip install pytest-asyncio
```

## Best Practices

1. **Use markers**: Tag tests with appropriate markers (`@pytest.mark.unit`, `@pytest.mark.integration`)
2. **Mock external services**: Don't make real API calls in unit tests
3. **Use fixtures**: Leverage fixtures from `conftest.py` for common setup
4. **Clean up**: Tests should clean up after themselves (use transaction rollback)
5. **Fast tests**: Keep unit tests fast by mocking slow operations
6. **Descriptive names**: Use descriptive test names that explain what's being tested

## Contributing

When adding new tests:

1. Follow existing test structure and naming conventions
2. Add appropriate markers
3. Use existing fixtures where possible
4. Update this README if adding new test categories
