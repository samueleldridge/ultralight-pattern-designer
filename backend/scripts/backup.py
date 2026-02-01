#!/usr/bin/env python3
"""
Database Backup and Export Utilities

Provides:
- SQLite backup with compression
- Data export to CSV, JSON, and Parquet formats
- Scheduled backup support
- Point-in-time recovery helpers
"""

import argparse
import asyncio
import gzip
import json
import logging
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

import aiofiles

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

from app.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseBackupManager:
    """Manages database backups for SQLite and PostgreSQL."""
    
    def __init__(self, backup_dir: Optional[Path] = None):
        self.backup_dir = backup_dir or Path(__file__).parent.parent / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.settings = get_settings()
    
    def get_sqlite_db_path(self) -> Path:
        """Get the path to the SQLite database file."""
        # Try to extract path from database URL
        db_url = self.settings.database_url
        if "sqlite" in db_url:
            # Extract path from sqlite:///path or sqlite+aiosqlite:///path
            path = db_url.replace("sqlite+aiosqlite://", "").replace("sqlite://", "")
            path = path.lstrip("/")
            if not path.startswith("/"):
                # Relative path
                return Path(__file__).parent.parent / path
            return Path(path)
        
        # Default location
        return Path(__file__).parent.parent / "data" / "analytics.db"
    
    async def backup_sqlite(
        self,
        compress: bool = True,
        backup_name: Optional[str] = None
    ) -> Path:
        """Create a SQLite database backup."""
        db_path = self.get_sqlite_db_path()
        
        if not db_path.exists():
            raise FileNotFoundError(f"Database not found at {db_path}")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = backup_name or f"analytics_backup_{timestamp}"
        
        if compress:
            backup_path = self.backup_dir / f"{backup_name}.db.gz"
            logger.info(f"Creating compressed SQLite backup: {backup_path}")
            
            # Use SQLite's backup API for consistency
            async with aiofiles.open(backup_path, 'wb') as f_out:
                with gzip.GzipFile(fileobj=f_out, mode='wb') as gz:
                    # Connect to source and backup databases
                    source_conn = sqlite3.connect(str(db_path))
                    
                    # Write to a temporary file first
                    temp_path = self.backup_dir / f"{backup_name}.db"
                    backup_conn = sqlite3.connect(str(temp_path))
                    source_conn.backup(backup_conn)
                    backup_conn.close()
                    source_conn.close()
                    
                    # Compress the backup
                    with open(temp_path, 'rb') as f_in:
                        shutil.copyfileobj(f_in, gz)
                    
                    # Clean up temp file
                    temp_path.unlink()
        else:
            backup_path = self.backup_dir / f"{backup_name}.db"
            logger.info(f"Creating SQLite backup: {backup_path}")
            
            source_conn = sqlite3.connect(str(db_path))
            backup_conn = sqlite3.connect(str(backup_path))
            source_conn.backup(backup_conn)
            backup_conn.close()
            source_conn.close()
        
        # Verify backup
        if backup_path.exists():
            size = backup_path.stat().st_size
            logger.info(f"✓ Backup created: {backup_path} ({size:,} bytes)")
            return backup_path
        else:
            raise RuntimeError("Backup file was not created")
    
    async def backup_postgresql(
        self,
        backup_name: Optional[str] = None,
        format_type: str = "custom"  # custom, plain, directory, tar
    ) -> Path:
        """Create a PostgreSQL database backup using pg_dump."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = backup_name or f"analytics_backup_{timestamp}"
        
        # Parse database URL
        db_url = self.settings.database_url
        # postgresql+asyncpg://user:pass@host:port/dbname
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
        
        backup_path = self.backup_dir / f"{backup_name}.dump"
        
        # Build pg_dump command
        cmd = [
            "pg_dump",
            "--format", format_type,
            "--file", str(backup_path),
            "--verbose",
            db_url
        ]
        
        logger.info(f"Creating PostgreSQL backup: {backup_path}")
        
        # Run pg_dump
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise RuntimeError(f"pg_dump failed: {error_msg}")
        
        logger.info(f"✓ PostgreSQL backup created: {backup_path}")
        return backup_path
    
    async def backup(self, **kwargs) -> Path:
        """Create backup based on database type."""
        if "sqlite" in self.settings.database_url:
            return await self.backup_sqlite(**kwargs)
        else:
            return await self.backup_postgresql(**kwargs)
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups."""
        backups = []
        
        for file_path in self.backup_dir.iterdir():
            if file_path.suffix in ['.db', '.gz', '.dump', '.sql']:
                stat = file_path.stat()
                backups.append({
                    "name": file_path.name,
                    "path": str(file_path),
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_ctime),
                    "type": file_path.suffix
                })
        
        return sorted(backups, key=lambda x: x["created"], reverse=True)
    
    async def restore_sqlite(self, backup_path: Path, target_path: Optional[Path] = None):
        """Restore SQLite database from backup."""
        target_path = target_path or self.get_sqlite_db_path()
        
        logger.info(f"Restoring SQLite database from {backup_path}")
        
        # Handle compressed backups
        if backup_path.suffix == '.gz':
            temp_path = self.backup_dir / "restore_temp.db"
            
            async with aiofiles.open(backup_path, 'rb') as f_in:
                with gzip.GzipFile(fileobj=f_in, mode='rb') as gz:
                    async with aiofiles.open(temp_path, 'wb') as f_out:
                        while chunk := gz.read(8192):
                            await f_out.write(chunk)
            
            backup_path = temp_path
        
        # Restore using SQLite backup API
        source_conn = sqlite3.connect(str(backup_path))
        target_conn = sqlite3.connect(str(target_path))
        source_conn.backup(target_conn)
        target_conn.close()
        source_conn.close()
        
        # Clean up temp file if created
        if backup_path.name == "restore_temp.db":
            backup_path.unlink()
        
        logger.info(f"✓ Database restored to {target_path}")
    
    async def cleanup_old_backups(self, keep_days: int = 7):
        """Remove backups older than specified days."""
        cutoff = datetime.now() - timedelta(days=keep_days)
        removed = 0
        
        for file_path in self.backup_dir.iterdir():
            if file_path.suffix in ['.db', '.gz', '.dump', '.sql']:
                created = datetime.fromtimestamp(file_path.stat().st_ctime)
                if created < cutoff:
                    file_path.unlink()
                    removed += 1
                    logger.info(f"Removed old backup: {file_path.name}")
        
        logger.info(f"Cleanup complete: {removed} backups removed")
        return removed


class DataExporter:
    """Export database data to various formats."""
    
    def __init__(self, engine: Optional[AsyncEngine] = None):
        self.settings = get_settings()
        self.engine = engine
        self.export_dir = Path(__file__).parent.parent / "exports"
        self.export_dir.mkdir(parents=True, exist_ok=True)
    
    async def get_engine(self) -> AsyncEngine:
        """Get or create database engine."""
        if self.engine is None:
            self.engine = create_async_engine(
                self.settings.database_url,
                echo=False,
                future=True
            )
        return self.engine
    
    async def export_table_to_csv(
        self,
        table: str,
        output_path: Optional[Path] = None,
        where_clause: Optional[str] = None
    ) -> Path:
        """Export a table to CSV format."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_path or self.export_dir / f"{table}_{timestamp}.csv"
        
        engine = await self.get_engine()
        
        async with engine.connect() as conn:
            # Get column names
            result = await conn.execute(text(f"SELECT * FROM {table} LIMIT 0"))
            columns = result.keys()
            
            # Build query
            query = f"SELECT * FROM {table}"
            if where_clause:
                query += f" WHERE {where_clause}"
            
            result = await conn.execute(text(query))
            rows = result.fetchall()
        
        # Write CSV
        import csv
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(rows)
        
        logger.info(f"✓ Exported {len(rows)} rows to {output_path}")
        return output_path
    
    async def export_table_to_json(
        self,
        table: str,
        output_path: Optional[Path] = None,
        where_clause: Optional[str] = None
    ) -> Path:
        """Export a table to JSON format."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_path or self.export_dir / f"{table}_{timestamp}.json"
        
        engine = await self.get_engine()
        
        async with engine.connect() as conn:
            query = f"SELECT * FROM {table}"
            if where_clause:
                query += f" WHERE {where_clause}"
            
            result = await conn.execute(text(query))
            rows = result.mappings().all()
            
            # Convert to list of dicts
            data = [dict(row) for row in rows]
            
            # Convert datetime objects to strings
            for row in data:
                for key, value in row.items():
                    if isinstance(value, datetime):
                        row[key] = value.isoformat()
        
        # Write JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"✓ Exported {len(data)} rows to {output_path}")
        return output_path
    
    async def export_all_tables(self, format_type: str = "csv") -> List[Path]:
        """Export all analytics tables."""
        tables = ["customers", "products", "orders", "order_items"]
        exported = []
        
        for table in tables:
            if format_type == "csv":
                path = await self.export_table_to_csv(table)
            else:
                path = await self.export_table_to_json(table)
            exported.append(path)
        
        return exported
    
    async def export_analytics_summary(self) -> Path:
        """Export a summary of key analytics metrics."""
        engine = await self.get_engine()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.export_dir / f"analytics_summary_{timestamp}.json"
        
        summary = {
            "generated_at": datetime.now().isoformat(),
            "tables": {}
        }
        
        async with engine.connect() as conn:
            # Table counts
            for table in ["customers", "products", "orders", "order_items"]:
                result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                summary["tables"][table] = {"count": count}
            
            # Revenue summary
            result = await conn.execute(text("""
                SELECT 
                    COUNT(*) as total_orders,
                    SUM(total) as total_revenue,
                    AVG(total) as avg_order_value,
                    MIN(order_date) as first_order,
                    MAX(order_date) as last_order
                FROM orders
                WHERE status NOT IN ('cancelled', 'refunded')
            """))
            row = result.fetchone()
            summary["revenue"] = {
                "total_orders": row.total_orders,
                "total_revenue": float(row.total_revenue) if row.total_revenue else 0,
                "avg_order_value": float(row.avg_order_value) if row.avg_order_value else 0,
                "date_range": {
                    "first": row.first_order.isoformat() if row.first_order else None,
                    "last": row.last_order.isoformat() if row.last_order else None
                }
            }
            
            # Segment breakdown
            result = await conn.execute(text("""
                SELECT segment, COUNT(*) as count
                FROM customers
                GROUP BY segment
            """))
            summary["customers_by_segment"] = {
                row.segment: row.count for row in result.fetchall()
            }
            
            # Category breakdown
            result = await conn.execute(text("""
                SELECT category, COUNT(*) as count
                FROM products
                GROUP BY category
            """))
            summary["products_by_category"] = {
                row.category: row.count for row in result.fetchall()
            }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"✓ Analytics summary exported to {output_path}")
        return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Database backup and export utilities"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Create database backup")
    backup_parser.add_argument(
        "--name",
        help="Custom backup name"
    )
    backup_parser.add_argument(
        "--no-compress",
        action="store_true",
        help="Don't compress SQLite backup"
    )
    
    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore database from backup")
    restore_parser.add_argument(
        "backup_file",
        help="Path to backup file"
    )
    
    # List command
    subparsers.add_parser("list", help="List available backups")
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Remove old backups")
    cleanup_parser.add_argument(
        "--keep-days",
        type=int,
        default=7,
        help="Keep backups from last N days"
    )
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export data")
    export_parser.add_argument(
        "--table",
        help="Specific table to export (default: all)"
    )
    export_parser.add_argument(
        "--format",
        choices=["csv", "json"],
        default="csv",
        help="Export format"
    )
    export_parser.add_argument(
        "--summary",
        action="store_true",
        help="Export analytics summary"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == "backup":
            manager = DatabaseBackupManager()
            asyncio.run(manager.backup(
                backup_name=args.name,
                compress=not args.no_compress
            ))
        
        elif args.command == "restore":
            manager = DatabaseBackupManager()
            backup_path = Path(args.backup_file)
            asyncio.run(manager.restore_sqlite(backup_path))
        
        elif args.command == "list":
            manager = DatabaseBackupManager()
            backups = manager.list_backups()
            print(f"{'Name':<40} {'Size':>12} {'Created':<20}")
            print("-" * 72)
            for b in backups:
                size_mb = b["size"] / (1024 * 1024)
                created = b["created"].strftime("%Y-%m-%d %H:%M:%S")
                print(f"{b['name']:<40} {size_mb:>10.1f}MB {created:<20}")
        
        elif args.command == "cleanup":
            manager = DatabaseBackupManager()
            removed = asyncio.run(manager.cleanup_old_backups(args.keep_days))
            print(f"Removed {removed} old backups")
        
        elif args.command == "export":
            exporter = DataExporter()
            
            if args.summary:
                asyncio.run(exporter.export_analytics_summary())
            elif args.table:
                if args.format == "csv":
                    asyncio.run(exporter.export_table_to_csv(args.table))
                else:
                    asyncio.run(exporter.export_table_to_json(args.table))
            else:
                asyncio.run(exporter.export_all_tables(args.format))
    
    except Exception as e:
        logger.error(f"Command failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
