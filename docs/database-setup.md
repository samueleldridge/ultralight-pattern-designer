# Database Setup & Optimization Guide

Complete guide for setting up and optimizing the AI Analytics Platform database infrastructure.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Database Initialization](#database-initialization)
- [Query Optimization](#query-optimization)
- [Connection Pooling](#connection-pooling)
- [Data Validation](#data-validation)
- [Backup & Recovery](#backup--recovery)
- [Migrations](#migrations)
- [Production Deployment](#production-deployment)

## Overview

The database layer supports both **SQLite** (development) and **PostgreSQL** (production) with:

- **Dual database support**: SQLite for development, PostgreSQL for production
- **Optimized indexes**: B-tree, composite, partial, and full-text search indexes
- **Materialized views**: Pre-computed aggregations for fast analytics
- **Connection pooling**: Separate pools for OLTP and analytical workloads
- **Automatic retries**: Exponential backoff for transient failures
- **Audit logging**: Complete change tracking for compliance
- **Backup utilities**: Automated backups with compression

## Quick Start

### 1. Development (SQLite)

```bash
cd backend

# Initialize SQLite database with demo data
python scripts/init_db.py --env dev --demo

# Verify setup
python scripts/backup.py list
```

### 2. Production (PostgreSQL)

```bash
# Set environment variables
export DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/aianalytics"

# Initialize PostgreSQL database
python scripts/init_db.py --env prod --demo

# Run migrations
alembic upgrade head
```

## Database Initialization

### Script: `scripts/init_db.py`

The initialization script handles:
- Database engine creation with appropriate settings
- PostgreSQL extensions (pgvector, pg_trgm, unaccent)
- Table creation (core + analytics tables)
- Index creation
- Materialized views (PostgreSQL)
- Audit triggers (PostgreSQL)

```bash
# Initialize development database
python scripts/init_db.py --env dev

# Initialize with demo data
python scripts/init_db.py --env dev --demo

# Initialize production database
python scripts/init_db.py --env prod
```

### Tables Created

| Table | Description |
|-------|-------------|
| `customers` | Customer profiles with segmentation |
| `products` | Product catalog with pricing |
| `orders` | Order headers with status tracking |
| `order_items` | Line items for each order |
| `audit_log` | Change tracking for compliance |
| `documents` | RAG document storage |
| `document_chunks` | Chunked document content with embeddings |

### Demo Data Loading

```bash
# Load from SQL dump (fastest)
python scripts/load_demo_data.py --source sql

# Load from CSV files
python scripts/load_demo_data.py --source csv

# Custom batch size for large datasets
python scripts/load_demo_data.py --batch-size 500
```

The demo dataset includes:
- **11,000+ orders** across 2 years (2023-2025)
- **550 customers** across 4 segments
- **220 products** across multiple categories
- Seasonal patterns and growth trends

## Query Optimization

### Index Strategy

Indexes are defined in `app/db/indexes.py` and automatically created during initialization.

#### Core Indexes

| Index | Table | Columns | Purpose |
|-------|-------|---------|---------|
| `idx_orders_date` | orders | `order_date DESC` | Time-series queries |
| `idx_orders_customer_id` | orders | `customer_id` | Customer lookups |
| `idx_orders_status` | orders | `status` | Status filtering |
| `idx_customers_segment` | customers | `segment` | Segment analysis |
| `idx_customers_region` | customers | `region` | Geographic queries |
| `idx_products_category` | products | `category` | Category filtering |

#### Composite Indexes

```sql
-- Multi-column for common filter combinations
idx_orders_region_date ON orders(region, order_date DESC)
idx_orders_segment_date ON orders(customer_segment, order_date DESC)
idx_customers_segment_region ON customers(segment, region)
```

#### Covering Index

```sql
-- Includes all commonly queried columns to avoid table lookups
idx_orders_analytics_covering ON orders(
    order_date, region, customer_segment, 
    status, total, customer_id
)
```

#### Partial Indexes (PostgreSQL)

```sql
-- Only index active orders for faster analytics
idx_orders_active ON orders(order_date DESC, customer_id, total)
WHERE status NOT IN ('cancelled', 'refunded')
```

#### Full-Text Search

PostgreSQL:
```sql
-- Trigram index for fuzzy search
CREATE INDEX idx_products_name_trgm ON products 
USING gin (name gin_trgm_ops);

-- Full-text search index
CREATE INDEX idx_products_name_search ON products 
USING gin(to_tsvector('english', name));
```

SQLite:
```sql
-- FTS5 virtual table
CREATE VIRTUAL TABLE products_fts USING fts5(
    name, description, content='products', content_rowid='rowid'
);
```

### Materialized Views

Pre-computed aggregations for instant analytics:

| View | Purpose | Refresh |
|------|---------|---------|
| `mv_daily_sales` | Daily revenue by region/segment | After data load |
| `mv_monthly_revenue` | Monthly trends | After data load |
| `mv_customer_ltv` | Customer lifetime value | Weekly |
| `mv_product_performance` | Product sales metrics | Daily |
| `mv_category_summary` | Category aggregations | Daily |

```python
# Refresh materialized views
REFRESH MATERIALIZED VIEW mv_daily_sales;
```

### Query Performance Tips

1. **Use covering indexes** for analytical queries:
```python
# Good - uses covering index
SELECT order_date, region, total FROM orders 
WHERE order_date > '2024-01-01';

# Slower - requires table lookup
SELECT * FROM orders WHERE order_date > '2024-01-01';
```

2. **Leverage materialized views** for aggregations:
```python
# Fast - uses pre-computed view
SELECT * FROM mv_daily_sales WHERE date > '2024-01-01';

# Slower - computes aggregation on-the-fly
SELECT DATE(order_date), SUM(total) FROM orders 
WHERE order_date > '2024-01-01' GROUP BY DATE(order_date);
```

3. **Use partial indexes** for filtered queries:
```python
# Automatically uses idx_orders_active
SELECT * FROM orders 
WHERE status NOT IN ('cancelled', 'refunded') 
AND order_date > '2024-01-01';
```

## Connection Pooling

### Configuration

Connection pooling is configured in `app/db/connection.py`:

```python
from app.db.connection import ConnectionPoolConfig

# Production OLTP pool
oltp_config = ConnectionPoolConfig(
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600,
    pool_pre_ping=True
)

# Analytics pool (longer timeouts)
analytics_config = ConnectionPoolConfig.for_analytics()
```

### Pool Settings

| Setting | OLTP | Analytics | Description |
|---------|------|-----------|-------------|
| `pool_size` | 10 | 5 | Base connections |
| `max_overflow` | 20 | 10 | Extra connections under load |
| `pool_timeout` | 30s | 60s | Wait time for connection |
| `pool_recycle` | 3600s | 1800s | Connection lifetime |

### Retry Logic

Automatic retry with exponential backoff:

```python
from app.db.connection import with_retry, RetryConfig

@with_retry(RetryConfig(max_retries=3, base_delay=1.0))
async def critical_database_operation():
    # Will retry on connection failures
    pass
```

### Usage Examples

```python
from app.db.connection import (
    DatabaseManager, get_db_session, get_analytics_session,
    execute_analytics_query
)

# Standard OLTP operations
async with get_db_session() as session:
    result = await session.execute(select(Customer))

# Long-running analytics queries
async with get_analytics_session() as session:
    result = await session.execute(complex_aggregation)

# One-shot analytics with timeout
result = await execute_analytics_query(
    "SELECT * FROM large_table",
    timeout=120
)
```

### Health Monitoring

```python
manager = await DatabaseManager.get_instance()
health = await manager.health_check()

print(health)
# {
#     "primary": True,
#     "analytics": True,
#     "metrics": {
#         "primary": {
#             "connection_attempts": 150,
#             "connection_failures": 2,
#             "query_count": 1200,
#             "avg_query_time_ms": 45.2
#         }
#     }
# }
```

## Data Validation

### Validation Rules

Validation is defined in `app/db/validation.py`:

```python
from app.db.validation import DataValidator

# Validate before insert
errors = DataValidator.validate_insert("customers", {
    "customer_id": "CUST_001",
    "email": "user@example.com",
    "segment": "vip"
})

if errors:
    print(f"Validation failed: {errors}")
```

### Constraints

Database-level constraints ensure data integrity:

```sql
-- Check constraints
CONSTRAINT chk_segment CHECK (segment IN ('vip', 'enterprise', 'mid_market', 'smb'))
CONSTRAINT chk_price CHECK (base_price >= 0)
CONSTRAINT chk_quantity CHECK (quantity > 0)

-- Foreign keys
CONSTRAINT fk_orders_customer 
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
```

### Audit Logging

All changes are automatically logged:

```python
from app.db.validation import AuditLogger, ValidationContext

async with ValidationContext(session, "customers", "CUST_001", user="admin") as ctx:
    # Validate
    errors = ctx.validate_insert(data)
    
    # Insert
    await session.execute(insert(Customer).values(data))
    
    # Log
    await ctx.log_insert(data)
```

### Querying Audit History

```python
audit_logger = AuditLogger(session)

# Get history for a record
history = await audit_logger.get_audit_history(
    table_name="customers",
    record_id="CUST_001"
)

# Get all changes in time range
recent_changes = await audit_logger.get_audit_history(
    since=datetime.now() - timedelta(days=7)
)
```

## Backup & Recovery

### Automated Backups

```bash
# SQLite backup (compressed)
python scripts/backup.py backup --name daily_backup

# PostgreSQL backup
python scripts/backup.py backup --name prod_backup

# List backups
python scripts/backup.py list

# Cleanup old backups (keep 7 days)
python scripts/backup.py cleanup --keep-days 7
```

### Restore

```bash
# Restore SQLite from backup
python scripts/backup.py restore backups/analytics_backup_20250201_120000.db.gz
```

### Data Export

```bash
# Export all tables to CSV
python scripts/backup.py export --format csv

# Export specific table
python scripts/backup.py export --table orders --format json

# Export analytics summary
python scripts/backup.py export --summary
```

### Programmatic Usage

```python
from scripts.backup import DatabaseBackupManager, DataExporter

# Backup
manager = DatabaseBackupManager()
backup_path = await manager.backup(compress=True)

# Export
exporter = DataExporter()
await exporter.export_analytics_summary()
```

## Migrations

### Using Alembic

```bash
# Create new migration
alembic revision --autogenerate -m "Add new column"

# Apply migrations
alembic upgrade head

# Rollback one revision
alembic downgrade -1

# View current version
alembic current

# View history
alembic history
```

### Migration Structure

```python
# alembic/versions/xxx_add_feature.py
def upgrade():
    op.add_column('customers', sa.Column('new_field', sa.String(50)))
    op.create_index('idx_customers_new', 'customers', ['new_field'])

def downgrade():
    op.drop_index('idx_customers_new')
    op.drop_column('customers', 'new_field')
```

### Best Practices

1. **Always test migrations** on a copy of production data
2. **Make migrations reversible** - provide both upgrade and downgrade
3. **Add indexes in separate migrations** - avoid locking during peak hours
4. **Use batch mode for SQLite** - enables ALTER TABLE support

## Production Deployment

### Environment Variables

```bash
# Required
DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/aianalytics"

# Pool configuration
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30

# Optional - separate analytics pool
ANALYTICS_DATABASE_URL="postgresql+asyncpg://user:pass@replica:5432/aianalytics"
```

### PostgreSQL Extensions

Required extensions (auto-created by init script):

```sql
CREATE EXTENSION IF NOT EXISTS vector;        -- Embeddings
CREATE EXTENSION IF NOT EXISTS btree_gist;    -- Exclusion constraints
CREATE EXTENSION IF NOT EXISTS pg_trgm;       -- Fuzzy search
CREATE EXTENSION IF NOT EXISTS unaccent;      -- Case-insensitive search
```

### Monitoring

Key metrics to monitor:

| Metric | Alert Threshold | Description |
|--------|----------------|-------------|
| Connection pool usage | > 80% | Scale pool or add replicas |
| Query duration p99 | > 5s | Optimize slow queries |
| Connection failures | > 1/min | Network/DB issues |
| Replication lag | > 10s | Read replica lag |

### Maintenance Schedule

```bash
# Daily - Refresh materialized views
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_sales;

# Weekly - Update statistics
ANALYZE customers;
ANALYZE orders;
ANALYZE order_items;

# Monthly - Reindex
REINDEX TABLE orders;
REINDEX TABLE order_items;
```

### Troubleshooting

#### Slow Queries

```sql
-- Find slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan < 50;
```

#### Connection Issues

```python
# Check pool status
from app.db.connection import DatabaseManager

manager = await DatabaseManager.get_instance()
metrics = manager.primary_pool.get_metrics()
print(f"Pool: {metrics['pool_status']}")
print(f"Failures: {metrics['connection_failures']}")
```

---

## Support

For issues or questions:
1. Check the logs: `logs/database.log`
2. Run health check: `python scripts/backup.py health`
3. Review metrics: `python -c "from app.db.connection import DatabaseManager; ..."`
