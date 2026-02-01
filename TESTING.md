# Testing Guide

## Quick Start

### 1. Install Dependencies

```bash
cd ai-analytics-platform/backend
pip install -r requirements.txt
```

### 2. Set Up Test Database

```bash
# Create test database
createdb aianalytics_test

# Or use Docker
docker run -d \
  --name aianalytics-test-db \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=aianalytics_test \
  -p 5432:5432 \
  postgres:15
```

### 3. Run Tests

```bash
# Run all tests
./scripts/test.sh

# Run specific test categories
./scripts/test.sh unit
./scripts/test.sh integration
./scripts/test.sh api
./scripts/test.sh agent
./scripts/test.sh db

# Run with coverage
./scripts/test.sh coverage

# Run CI suite
./scripts/test.sh ci
```

## Test Structure

```
backend/tests/
├── conftest.py          # Fixtures and configuration
├── test_api.py          # API endpoint tests (17 tests)
├── test_agent.py        # Agent workflow tests (32 tests)
├── test_database.py     # Database tests (28 tests)
├── test_core.py         # Core utility tests (10 tests)
└── README.md            # Detailed testing documentation
```

## Test Coverage

### API Tests (`test_api.py`)
- Health check endpoints
- Query workflow endpoints
- Dashboard CRUD operations
- Suggestions endpoints
- Connection management
- Error handling
- CORS middleware

### Agent Tests (`test_agent.py`)
- Intent classification node
- Context fetching node
- SQL generation nodes (v1 & v2)
- SQL validation node
- SQL execution node
- Result analysis node
- Error analysis node
- Utility nodes
- State management
- Workflow routing

### Database Tests (`test_database.py`)
- SQL validation and safety
- SQL dialect handling
- Database configuration
- Query execution
- Connection handling
- Demo data queries
- SQL injection prevention
- Performance tests

### Core Tests (`test_core.py`)
- Utility functions
- SQL dialect operations
- Database configuration
- Agent state management
- SQL evaluation framework
- Context management

## Configuration

### pytest.ini

```ini
[pytest]
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*
testpaths = tests
asyncio_mode = auto
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests
    api: API endpoint tests
    agent: Agent workflow tests
    db: Database tests
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `TEST_DATABASE_URL` | PostgreSQL connection for tests |
| `ENVIRONMENT` | Set to `test` for testing |
| `TESTING` | Set to `true` to enable test mode |

## Mocking

All external services are automatically mocked:

- **LLM Provider**: `mock_llm_provider` fixture
- **Redis**: `mock_redis` fixture
- **Database**: Test database with transaction rollback

Example:

```python
@pytest.mark.asyncio
async def test_with_mocked_llm(self, sample_agent_state, mock_llm_provider):
    mock_llm_provider.generate_json.return_value = {
        "sql": "SELECT * FROM orders",
        "explanation": "Test"
    }
    
    result = await generate_sql_node(sample_agent_state)
    assert "SELECT" in result["sql"]
```

## Fixtures

### Agent State Fixtures

- `sample_agent_state` - Basic agent state
- `sample_agent_state_complex` - Complex investigation state
- `sample_query_request` - Query request data
- `sample_execution_result` - Mock execution results

### Database Fixtures

- `db_session` - Database session with transaction rollback
- `demo_database` - Database with demo tables and data

### Mock Fixtures

- `mock_llm_provider` - Mocked LLM provider
- `mock_redis` - Mocked Redis client
- `mock_settings` - Test settings

## CI/CD

Tests run automatically on GitHub Actions:

1. **Unit Tests**: Fast tests with mocks
2. **Integration Tests**: Tests with PostgreSQL/Redis
3. **Coverage Report**: Coverage analysis
4. **Lint & Type Check**: Code quality

See `.github/workflows/test.yml` for details.

## Writing New Tests

### API Test Example

```python
@pytest.mark.api
class TestNewEndpoint:
    def test_success(self, client):
        response = client.get("/api/new")
        assert response.status_code == 200
```

### Agent Test Example

```python
@pytest.mark.agent
class TestNewNode:
    @pytest.mark.asyncio
    async def test_behavior(self, sample_agent_state):
        result = await new_node(sample_agent_state)
        assert result["step_status"] == "complete"
```

### Database Test Example

```python
@pytest.mark.db
class TestNewQuery:
    @pytest.mark.asyncio
    async def test_execution(self, demo_database):
        result = await demo_database.execute(text("SELECT 1"))
        assert result.scalar() == 1
```

## Troubleshooting

### Import Errors

```bash
export PYTHONPATH="${PWD}:${PYTHONPATH}"
```

### Database Connection

```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Create test database
createdb aianalytics_test
```

### Missing Dependencies

```bash
pip install -r requirements.txt
```
