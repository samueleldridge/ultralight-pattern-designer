#!/usr/bin/env python3
"""
Demo Data Loader

Loads the rich demo dataset (11,000+ orders, 550 customers, 220 products)
into the database. Supports both SQLite and PostgreSQL.

Usage:
    python scripts/load_demo_data.py [--source sql|csv] [--batch-size 1000]
"""

import asyncio
import argparse
import csv
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DemoDataLoader:
    """Loads demo data from SQL or CSV sources."""
    
    def __init__(self, engine: AsyncEngine, batch_size: int = 1000):
        self.engine = engine
        self.batch_size = batch_size
        self.data_dir = Path(__file__).parent.parent.parent / "backend"
        self.is_sqlite = "sqlite" in str(engine.url)
        self.stats = {
            "customers": 0,
            "products": 0,
            "orders": 0,
            "order_items": 0
        }
    
    def get_sql_file_path(self) -> Path:
        """Get path to demo data SQL file."""
        # Try multiple locations
        paths = [
            self.data_dir / "demo-data-rich.sql",
            Path(__file__).parent.parent.parent.parent / "backend" / "demo-data-rich.sql",
            Path("/Users/sam-bot/.openclaw/workspace/backend/demo-data-rich.sql"),
        ]
        for path in paths:
            if path.exists():
                return path
        raise FileNotFoundError("Could not find demo-data-rich.sql")
    
    def get_csv_paths(self) -> Dict[str, Path]:
        """Get paths to CSV files."""
        base_paths = [
            self.data_dir,
            Path(__file__).parent.parent.parent.parent / "backend",
            Path("/Users/sam-bot/.openclaw/workspace/backend"),
        ]
        
        files = {}
        for base in base_paths:
            if base.exists():
                for name in ["customers", "products", "orders", "order_items"]:
                    path = base / f"demo_{name}.csv"
                    if path.exists() and name not in files:
                        files[name] = path
        
        if len(files) != 4:
            raise FileNotFoundError(f"Missing CSV files. Found: {list(files.keys())}")
        return files
    
    async def clear_existing_data(self):
        """Clear existing demo data from tables."""
        logger.info("Clearing existing demo data...")
        async with self.engine.begin() as conn:
            # Disable foreign key checks for SQLite
            if self.is_sqlite:
                await conn.execute(text("PRAGMA foreign_keys = OFF"))
            
            await conn.execute(text("DELETE FROM order_items"))
            await conn.execute(text("DELETE FROM orders"))
            await conn.execute(text("DELETE FROM products"))
            await conn.execute(text("DELETE FROM customers"))
            
            if self.is_sqlite:
                await conn.execute(text("PRAGMA foreign_keys = ON"))
        
        logger.info("Existing data cleared")
    
    async def load_from_sql(self):
        """Load data from SQL dump file."""
        sql_path = self.get_sql_file_path()
        logger.info(f"Loading data from SQL file: {sql_path}")
        
        # Read SQL file
        with open(sql_path, 'r') as f:
            sql_content = f.read()
        
        # Split into statements and filter out CREATE/DROP
        statements = []
        current_statement = []
        
        for line in sql_content.split('\n'):
            line = line.strip()
            
            # Skip comments and DDL
            if not line or line.startswith('--') or line.startswith('/*'):
                continue
            if line.upper().startswith(('CREATE', 'DROP', 'ALTER')):
                continue
            
            current_statement.append(line)
            
            if line.endswith(';'):
                stmt = ' '.join(current_statement)
                if stmt.upper().startswith('INSERT'):
                    statements.append(stmt)
                current_statement = []
        
        # Execute in batches
        async with self.engine.begin() as conn:
            total = len(statements)
            for i in range(0, total, self.batch_size):
                batch = statements[i:i + self.batch_size]
                for stmt in batch:
                    try:
                        await conn.execute(text(stmt))
                    except Exception as e:
                        logger.warning(f"Failed to execute statement: {e}")
                
                if (i // self.batch_size + 1) % 10 == 0:
                    logger.info(f"  Progress: {min(i + self.batch_size, total)}/{total} statements")
        
        logger.info("SQL data loaded successfully")
    
    def parse_value(self, value: str, column: str) -> Any:
        """Parse CSV value to appropriate type."""
        if value is None or value == '':
            return None
        
        # Date/datetime columns
        if 'date' in column.lower() or 'at' in column.lower():
            if ' ' in value:  # datetime
                try:
                    return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    return None
            else:  # date
                try:
                    return datetime.strptime(value, '%Y-%m-%d').date()
                except ValueError:
                    return None
        
        # Numeric columns
        if column in ['ltv_factor', 'churn_risk', 'base_price', 'cost', 'margin',
                      'subtotal', 'shipping_cost', 'tax', 'discount', 'total',
                      'unit_price', 'total_price']:
            try:
                return float(value)
            except ValueError:
                return None
        
        # Integer columns
        if column in ['stock_quantity', 'quantity', 'chunk_count', 'file_size']:
            try:
                return int(value)
            except ValueError:
                return None
        
        # Boolean
        if column in ['is_active']:
            return value.lower() in ['true', '1', 'yes', 't']
        
        return value
    
    async def load_table_from_csv(self, table_name: str, csv_path: Path):
        """Load a single table from CSV."""
        logger.info(f"Loading {table_name} from {csv_path}")
        
        # Read CSV
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        if not rows:
            logger.warning(f"No data found in {csv_path}")
            return
        
        # Get columns from first row
        columns = list(rows[0].keys())
        placeholders = ', '.join([f':{col}' for col in columns])
        sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        
        # Insert in batches
        total = len(rows)
        async with self.engine.begin() as conn:
            for i in range(0, total, self.batch_size):
                batch = rows[i:i + self.batch_size]
                
                for row in batch:
                    # Parse values
                    parsed = {
                        col: self.parse_value(row.get(col), col)
                        for col in columns
                    }
                    await conn.execute(text(sql), parsed)
                
                if (i // self.batch_size + 1) % 5 == 0 or i + self.batch_size >= total:
                    logger.info(f"  {table_name}: {min(i + len(batch), total)}/{total}")
        
        self.stats[table_name] = total
        logger.info(f"✓ Loaded {total} rows into {table_name}")
    
    async def load_from_csv(self):
        """Load data from CSV files."""
        csv_paths = self.get_csv_paths()
        
        # Load in order: customers, products, orders, order_items
        await self.load_table_from_csv("customers", csv_paths["customers"])
        await self.load_table_from_csv("products", csv_paths["products"])
        await self.load_table_from_csv("orders", csv_paths["orders"])
        await self.load_table_from_csv("order_items", csv_paths["order_items"])
    
    async def verify_data(self):
        """Verify loaded data counts."""
        logger.info("Verifying loaded data...")
        
        async with self.engine.connect() as conn:
            tables = ['customers', 'products', 'orders', 'order_items']
            
            for table in tables:
                result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                logger.info(f"  {table}: {count} rows")
                self.stats[table] = count
        
        total_orders = self.stats.get('orders', 0)
        if total_orders >= 10000:
            logger.info(f"✓ Successfully loaded rich demo dataset ({total_orders:,} orders)")
        else:
            logger.warning(f"⚠ Expected ~11,000 orders, found {total_orders}")
    
    async def refresh_materialized_views(self):
        """Refresh materialized views after data load."""
        if self.is_sqlite:
            return
            
        logger.info("Refreshing materialized views...")
        
        views = [
            'mv_daily_sales',
            'mv_monthly_revenue', 
            'mv_customer_ltv',
            'mv_product_performance',
            'mv_category_summary'
        ]
        
        async with self.engine.begin() as conn:
            for view in views:
                try:
                    await conn.execute(text(f"REFRESH MATERIALIZED VIEW {view}"))
                    logger.info(f"  ✓ Refreshed {view}")
                except Exception as e:
                    logger.warning(f"  ⚠ Could not refresh {view}: {e}")
    
    async def analyze_tables(self):
        """Run ANALYZE for query optimization (PostgreSQL only)."""
        if self.is_sqlite:
            return
            
        logger.info("Running ANALYZE for query optimization...")
        
        async with self.engine.begin() as conn:
            await conn.execute(text("ANALYZE customers"))
            await conn.execute(text("ANALYZE products"))
            await conn.execute(text("ANALYZE orders"))
            await conn.execute(text("ANALYZE order_items"))
        
        logger.info("✓ Analysis complete")
    
    async def load_all(self, source: str = "auto", clear: bool = True):
        """Run full data loading sequence."""
        start_time = datetime.now()
        
        if clear:
            await self.clear_existing_data()
        
        # Determine source
        if source == "auto":
            try:
                self.get_sql_file_path()
                source = "sql"
            except FileNotFoundError:
                source = "csv"
        
        # Load data
        if source == "sql":
            await self.load_from_sql()
        else:
            await self.load_from_csv()
        
        # Post-load tasks
        await self.verify_data()
        await self.refresh_materialized_views()
        await self.analyze_tables()
        
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"✓ Demo data loading completed in {elapsed:.1f}s")
        
        return self.stats


def main():
    parser = argparse.ArgumentParser(description="Load demo data into AI Analytics Platform")
    parser.add_argument(
        "--source",
        choices=["sql", "csv", "auto"],
        default="auto",
        help="Data source format"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for inserts"
    )
    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="Keep existing data (don't clear)"
    )
    
    args = parser.parse_args()
    
    # Import here to avoid circular dependency
    from app.config import get_settings
    from scripts.init_db import DatabaseInitializer
    
    settings = get_settings()
    initializer = DatabaseInitializer(settings)
    
    # Use dev database by default
    database_url = initializer.get_database_url("dev")
    initializer.create_engine(database_url)
    
    try:
        loader = DemoDataLoader(initializer.engine, batch_size=args.batch_size)
        asyncio.run(loader.load_all(source=args.source, clear=not args.keep_existing))
    except KeyboardInterrupt:
        logger.info("Loading cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Loading failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        asyncio.run(initializer.engine.dispose())


if __name__ == "__main__":
    main()
