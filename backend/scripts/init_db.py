#!/usr/bin/env python3
"""
Database Initialization Script

Supports both SQLite (development) and PostgreSQL (production).
Creates tables, indexes, and extensions needed for the AI Analytics Platform.

Usage:
    python scripts/init_db.py [--env dev|prod] [--demo]
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings, Settings
from app.models import Base

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """Handles database initialization for different environments."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.engine = None
        
    def get_database_url(self, env: str) -> str:
        """Get appropriate database URL based on environment."""
        if env == "dev":
            # Use SQLite for development
            db_path = Path(__file__).parent.parent / "data" / "analytics.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite+aiosqlite:///{db_path}"
        else:
            # Use configured PostgreSQL URL for production
            return self.settings.database_url
    
    def create_engine(self, database_url: str):
        """Create async database engine with appropriate settings."""
        is_sqlite = "sqlite" in database_url
        
        engine_kwargs = {
            "echo": self.settings.debug,
            "future": True,
        }
        
        if not is_sqlite:
            # PostgreSQL connection pooling settings
            engine_kwargs.update({
                "pool_size": self.settings.db_pool_size,
                "max_overflow": self.settings.db_max_overflow,
                "pool_pre_ping": True,
                "pool_recycle": 3600,  # Recycle connections after 1 hour
            })
        
        self.engine = create_async_engine(database_url, **engine_kwargs)
        return self.engine
    
    async def create_extensions(self):
        """Create PostgreSQL extensions."""
        if "sqlite" in str(self.engine.url):
            logger.info("Skipping extensions for SQLite")
            return
            
        async with self.engine.begin() as conn:
            logger.info("Creating PostgreSQL extensions...")
            
            # pgvector for embeddings
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            
            # btree_gist for exclusion constraints with btree
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
            
            # pg_trgm for trigram similarity (fuzzy search)
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            
            # unaccent for case-insensitive search
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent"))
            
            logger.info("Extensions created successfully")
    
    async def create_tables(self):
        """Create all database tables."""
        async with self.engine.begin() as conn:
            logger.info("Creating database tables...")
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Tables created successfully")
    
    async def create_analytics_tables(self):
        """Create tables for analytics demo data (orders, customers, products)."""
        is_sqlite = "sqlite" in str(self.engine.url)
        
        async with self.engine.begin() as conn:
            logger.info("Creating analytics tables...")
            
            # Customers table
            customers_sql = """
            CREATE TABLE IF NOT EXISTS customers (
                customer_id VARCHAR(20) PRIMARY KEY,
                first_name VARCHAR(50) NOT NULL,
                last_name VARCHAR(50) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                phone VARCHAR(20),
                region VARCHAR(10) NOT NULL,
                country VARCHAR(5) NOT NULL,
                state VARCHAR(50),
                city VARCHAR(50),
                postal_code VARCHAR(20),
                segment VARCHAR(20) NOT NULL,
                ltv_factor DECIMAL(3,2),
                churn_risk DECIMAL(3,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                CONSTRAINT chk_segment CHECK (segment IN ('vip', 'enterprise', 'mid_market', 'smb')),
                CONSTRAINT chk_region CHECK (region IN ('US', 'UK', 'EU', 'APAC')),
                CONSTRAINT chk_email CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$') 
                    OR email LIKE '%@%'
            )
            """ if not is_sqlite else """
            CREATE TABLE IF NOT EXISTS customers (
                customer_id VARCHAR(20) PRIMARY KEY,
                first_name VARCHAR(50) NOT NULL,
                last_name VARCHAR(50) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                phone VARCHAR(20),
                region VARCHAR(10) NOT NULL,
                country VARCHAR(5) NOT NULL,
                state VARCHAR(50),
                city VARCHAR(50),
                postal_code VARCHAR(20),
                segment VARCHAR(20) NOT NULL,
                ltv_factor DECIMAL(3,2),
                churn_risk DECIMAL(3,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                CONSTRAINT chk_segment CHECK (segment IN ('vip', 'enterprise', 'mid_market', 'smb'))
            )
            """
            await conn.execute(text(customers_sql))
            
            # Products table
            products_sql = """
            CREATE TABLE IF NOT EXISTS products (
                product_id VARCHAR(20) PRIMARY KEY,
                sku VARCHAR(20) UNIQUE NOT NULL,
                name VARCHAR(200) NOT NULL,
                category VARCHAR(50) NOT NULL,
                description TEXT,
                base_price DECIMAL(10,2) NOT NULL,
                cost DECIMAL(10,2),
                margin DECIMAL(4,2),
                stock_quantity INTEGER,
                is_active BOOLEAN DEFAULT TRUE,
                created_at DATE DEFAULT CURRENT_DATE,
                CONSTRAINT chk_price CHECK (base_price >= 0),
                CONSTRAINT chk_cost CHECK (cost IS NULL OR cost >= 0)
            )
            """
            await conn.execute(text(products_sql))
            
            # Orders table
            orders_sql = """
            CREATE TABLE IF NOT EXISTS orders (
                order_id VARCHAR(20) PRIMARY KEY,
                customer_id VARCHAR(20) NOT NULL,
                order_date TIMESTAMP NOT NULL,
                status VARCHAR(20) NOT NULL,
                payment_method VARCHAR(30),
                shipping_method VARCHAR(20),
                subtotal DECIMAL(10,2),
                shipping_cost DECIMAL(10,2),
                tax DECIMAL(10,2),
                discount DECIMAL(10,2),
                total DECIMAL(10,2),
                currency VARCHAR(5) DEFAULT 'USD',
                shipped_date TIMESTAMP,
                delivered_date TIMESTAMP,
                region VARCHAR(10),
                customer_segment VARCHAR(20),
                CONSTRAINT fk_orders_customer 
                    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
                CONSTRAINT chk_status CHECK (status IN ('pending', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded')),
                CONSTRAINT chk_total CHECK (total IS NULL OR total >= 0)
            )
            """
            await conn.execute(text(orders_sql))
            
            # Order items table
            order_items_sql = """
            CREATE TABLE IF NOT EXISTS order_items (
                order_item_id VARCHAR(20) PRIMARY KEY,
                order_id VARCHAR(20) NOT NULL,
                product_id VARCHAR(20) NOT NULL,
                sku VARCHAR(20),
                quantity INTEGER NOT NULL,
                unit_price DECIMAL(10,2),
                total_price DECIMAL(10,2),
                cost DECIMAL(10,2),
                CONSTRAINT fk_items_order 
                    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
                CONSTRAINT fk_items_product 
                    FOREIGN KEY (product_id) REFERENCES products(product_id),
                CONSTRAINT chk_quantity CHECK (quantity > 0),
                CONSTRAINT chk_unit_price CHECK (unit_price IS NULL OR unit_price >= 0)
            )
            """
            await conn.execute(text(order_items_sql))
            
            # Audit log table for data changes
            audit_sql = """
            CREATE TABLE IF NOT EXISTS audit_log (
                id SERIAL PRIMARY KEY,
                table_name VARCHAR(50) NOT NULL,
                record_id VARCHAR(50) NOT NULL,
                action VARCHAR(10) NOT NULL,
                old_data JSONB,
                new_data JSONB,
                changed_by VARCHAR(100),
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address INET,
                CONSTRAINT chk_action CHECK (action IN ('INSERT', 'UPDATE', 'DELETE'))
            )
            """ if not is_sqlite else """
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name VARCHAR(50) NOT NULL,
                record_id VARCHAR(50) NOT NULL,
                action VARCHAR(10) NOT NULL,
                old_data TEXT,
                new_data TEXT,
                changed_by VARCHAR(100),
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address VARCHAR(45),
                CONSTRAINT chk_action CHECK (action IN ('INSERT', 'UPDATE', 'DELETE'))
            )
            """
            await conn.execute(text(audit_sql))
            
            logger.info("Analytics tables created successfully")
    
    async def create_indexes(self):
        """Create performance indexes for analytical queries."""
        from app.db.indexes import get_index_definitions
        
        is_sqlite = "sqlite" in str(self.engine.url)
        indexes = get_index_definitions(is_sqlite=is_sqlite)
        
        async with self.engine.begin() as conn:
            logger.info("Creating performance indexes...")
            
            for index_name, index_sql in indexes.items():
                try:
                    await conn.execute(text(index_sql))
                    logger.info(f"  ✓ Created index: {index_name}")
                except Exception as e:
                    logger.warning(f"  ⚠ Index {index_name} may already exist: {e}")
            
            logger.info("Indexes created successfully")
    
    async def create_materialized_views(self):
        """Create materialized views for common aggregations (PostgreSQL only)."""
        if "sqlite" in str(self.engine.url):
            logger.info("Skipping materialized views for SQLite")
            return
            
        async with self.engine.begin() as conn:
            logger.info("Creating materialized views...")
            
            views = {
                "mv_daily_sales": """
                    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_daily_sales AS
                    SELECT 
                        DATE(order_date) as date,
                        region,
                        customer_segment as segment,
                        COUNT(*) as order_count,
                        SUM(total) as total_revenue,
                        AVG(total) as avg_order_value,
                        SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled_count
                    FROM orders
                    GROUP BY DATE(order_date), region, customer_segment
                    ORDER BY date DESC
                """,
                "mv_monthly_revenue": """
                    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_monthly_revenue AS
                    SELECT 
                        DATE_TRUNC('month', order_date) as month,
                        region,
                        COUNT(*) as order_count,
                        SUM(total) as revenue,
                        COUNT(DISTINCT customer_id) as unique_customers
                    FROM orders
                    WHERE status NOT IN ('cancelled', 'refunded')
                    GROUP BY DATE_TRUNC('month', order_date), region
                    ORDER BY month DESC
                """,
                "mv_customer_ltv": """
                    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_customer_ltv AS
                    SELECT 
                        c.customer_id,
                        c.segment,
                        c.region,
                        COUNT(o.order_id) as total_orders,
                        SUM(o.total) as lifetime_value,
                        AVG(o.total) as avg_order_value,
                        MAX(o.order_date) as last_order_date,
                        MIN(o.order_date) as first_order_date
                    FROM customers c
                    LEFT JOIN orders o ON c.customer_id = o.customer_id
                    WHERE o.status NOT IN ('cancelled', 'refunded')
                    GROUP BY c.customer_id, c.segment, c.region
                """,
                "mv_product_performance": """
                    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_product_performance AS
                    SELECT 
                        p.product_id,
                        p.name,
                        p.category,
                        COUNT(DISTINCT oi.order_id) as times_ordered,
                        SUM(oi.quantity) as units_sold,
                        SUM(oi.total_price) as total_revenue,
                        AVG(oi.unit_price) as avg_selling_price,
                        SUM(oi.cost * oi.quantity) as total_cost,
                        SUM(oi.total_price - (oi.cost * oi.quantity)) as total_profit
                    FROM products p
                    LEFT JOIN order_items oi ON p.product_id = oi.product_id
                    LEFT JOIN orders o ON oi.order_id = o.order_id
                    WHERE o.status NOT IN ('cancelled', 'refunded')
                    GROUP BY p.product_id, p.name, p.category
                """,
                "mv_category_summary": """
                    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_category_summary AS
                    SELECT 
                        p.category,
                        COUNT(DISTINCT p.product_id) as product_count,
                        SUM(oi.quantity) as units_sold,
                        SUM(oi.total_price) as revenue,
                        AVG(oi.total_price / NULLIF(oi.quantity, 0)) as avg_price
                    FROM products p
                    LEFT JOIN order_items oi ON p.product_id = oi.product_id
                    LEFT JOIN orders o ON oi.order_id = o.order_id
                    WHERE o.status NOT IN ('cancelled', 'refunded')
                    GROUP BY p.category
                """
            }
            
            for view_name, view_sql in views.items():
                try:
                    await conn.execute(text(view_sql))
                    # Create index on materialized view
                    await conn.execute(text(f"""
                        CREATE INDEX IF NOT EXISTS idx_{view_name}_date 
                        ON {view_name}(date)
                    """))
                    logger.info(f"  ✓ Created view: {view_name}")
                except Exception as e:
                    logger.error(f"  ✗ Failed to create view {view_name}: {e}")
    
    async def create_triggers(self):
        """Create audit triggers for data changes."""
        if "sqlite" in str(self.engine.url):
            logger.info("Skipping triggers for SQLite (manual audit logging required)")
            return
            
        async with self.engine.begin() as conn:
            logger.info("Creating audit triggers...")
            
            # Create audit trigger function
            trigger_func = """
            CREATE OR REPLACE FUNCTION audit_trigger_func()
            RETURNS TRIGGER AS $$
            BEGIN
                IF (TG_OP = 'DELETE') THEN
                    INSERT INTO audit_log (table_name, record_id, action, old_data, changed_at)
                    VALUES (TG_TABLE_NAME, OLD.customer_id, 'DELETE', row_to_json(OLD), NOW());
                    RETURN OLD;
                ELSIF (TG_OP = 'UPDATE') THEN
                    INSERT INTO audit_log (table_name, record_id, action, old_data, new_data, changed_at)
                    VALUES (TG_TABLE_NAME, NEW.customer_id, 'UPDATE', row_to_json(OLD), row_to_json(NEW), NOW());
                    RETURN NEW;
                ELSIF (TG_OP = 'INSERT') THEN
                    INSERT INTO audit_log (table_name, record_id, action, new_data, changed_at)
                    VALUES (TG_TABLE_NAME, NEW.customer_id, 'INSERT', row_to_json(NEW), NOW());
                    RETURN NEW;
                END IF;
                RETURN NULL;
            END;
            $$ LANGUAGE plpgsql;
            """
            await conn.execute(text(trigger_func))
            
            # Apply triggers to tables
            tables = ['customers', 'orders', 'products', 'order_items']
            for table in tables:
                trigger_sql = f"""
                DROP TRIGGER IF EXISTS audit_{table}_trigger ON {table};
                CREATE TRIGGER audit_{table}_trigger
                AFTER INSERT OR UPDATE OR DELETE ON {table}
                FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();
                """
                await conn.execute(text(trigger_sql))
                logger.info(f"  ✓ Created audit trigger for: {table}")
    
    async def initialize(self, env: str, load_demo: bool = False):
        """Run full initialization sequence."""
        database_url = self.get_database_url(env)
        logger.info(f"Initializing database for environment: {env}")
        logger.info(f"Database URL: {database_url.replace(self.settings.database_url.split('@')[0].split(':')[-1] if '@' in self.settings.database_url else '', '***')}")
        
        self.create_engine(database_url)
        
        try:
            # Step 1: Extensions (PostgreSQL only)
            await self.create_extensions()
            
            # Step 2: Core tables from models
            await self.create_tables()
            
            # Step 3: Analytics tables
            await self.create_analytics_tables()
            
            # Step 4: Indexes
            await self.create_indexes()
            
            # Step 5: Materialized views (PostgreSQL only)
            await self.create_materialized_views()
            
            # Step 6: Triggers (PostgreSQL only)
            await self.create_triggers()
            
            logger.info("✓ Database initialization completed successfully!")
            
            # Step 7: Load demo data if requested
            if load_demo:
                logger.info("Loading demo data...")
                from scripts.load_demo_data import DemoDataLoader
                loader = DemoDataLoader(self.engine)
                await loader.load_all()
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
        finally:
            await self.engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="Initialize AI Analytics Platform database")
    parser.add_argument(
        "--env", 
        choices=["dev", "prod"], 
        default="dev",
        help="Environment to initialize (dev=SQLite, prod=PostgreSQL)"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Load demo data after initialization"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate all tables (WARNING: DESTRUCTIVE)"
    )
    
    args = parser.parse_args()
    
    settings = get_settings()
    initializer = DatabaseInitializer(settings)
    
    try:
        asyncio.run(initializer.initialize(args.env, args.demo))
    except KeyboardInterrupt:
        logger.info("Initialization cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
