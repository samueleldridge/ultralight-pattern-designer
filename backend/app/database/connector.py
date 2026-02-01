from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
import asyncpg
import aiomysql
import aioodbc
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from app.config import get_settings

settings = get_settings()


class DatabaseType(str, Enum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SNOWFLAKE = "snowflake"
    BIGQUERY = "bigquery"
    SQLSERVER = "sqlserver"
    SQLITE = "sqlite"


class DatabaseConfig(BaseModel):
    db_type: DatabaseType
    host: str
    port: int
    database: str
    username: str
    password: str
    schema: Optional[str] = None
    warehouse: Optional[str] = None  # For Snowflake
    project_id: Optional[str] = None  # For BigQuery
    ssl_mode: Optional[str] = None
    
    class Config:
        from_attributes = True


class SchemaColumn(BaseModel):
    name: str
    data_type: str
    nullable: bool
    default: Optional[str] = None
    is_primary_key: bool = False
    comment: Optional[str] = None


class SchemaTable(BaseModel):
    name: str
    schema: str
    columns: List[SchemaColumn]
    primary_keys: List[str]
    foreign_keys: List[Dict[str, Any]]
    row_count: Optional[int] = None
    comment: Optional[str] = None
    sample_data: Optional[List[Dict]] = None


class DatabaseConnector:
    """Universal database connector supporting multiple database types"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.engine: Optional[AsyncEngine] = None
        self._connection = None
    
    async def connect(self):
        """Establish database connection"""
        if self.config.db_type == DatabaseType.POSTGRESQL:
            self._connection = await asyncpg.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.username,
                password=self.config.password,
                ssl=self.config.ssl_mode == 'require'
            )
        elif self.config.db_type == DatabaseType.MYSQL:
            self._connection = await aiomysql.connect(
                host=self.config.host,
                port=self.config.port,
                db=self.config.database,
                user=self.config.username,
                password=self.config.password,
                ssl={'ssl': {}} if self.config.ssl_mode else None
            )
        # Snowflake, BigQuery, SQLServer implementations below
        
        return self._connection
    
    async def disconnect(self):
        """Close database connection"""
        if self._connection:
            await self._connection.close()
            self._connection = None
    
    async def execute(self, query: str, timeout: int = 30) -> List[Dict]:
        """Execute query and return results"""
        if not self._connection:
            await self.connect()
        
        if self.config.db_type == DatabaseType.POSTGRESQL:
            rows = await self._connection.fetch(query)
            return [dict(row) for row in rows]
        elif self.config.db_type == DatabaseType.MYSQL:
            async with self._connection.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query)
                rows = await cur.fetchall()
                return rows
        
        return []
    
    async def test_connection(self) -> bool:
        """Test if connection works"""
        try:
            await self.connect()
            
            # Database-specific test query
            test_queries = {
                DatabaseType.POSTGRESQL: "SELECT 1",
                DatabaseType.MYSQL: "SELECT 1",
                DatabaseType.SNOWFLAKE: "SELECT 1",
                DatabaseType.BIGQUERY: "SELECT 1",
                DatabaseType.SQLSERVER: "SELECT 1"
            }
            
            await self.execute(test_queries.get(self.config.db_type, "SELECT 1"))
            return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
        finally:
            await self.disconnect()
    
    async def introspect_schema(self) -> List[SchemaTable]:
        """Introspect database schema - works across database types"""
        if self.config.db_type == DatabaseType.POSTGRESQL:
            return await self._introspect_postgres()
        elif self.config.db_type == DatabaseType.MYSQL:
            return await self._introspect_mysql()
        elif self.config.db_type == DatabaseType.SNOWFLAKE:
            return await self._introspect_snowflake()
        elif self.config.db_type == DatabaseType.BIGQUERY:
            return await self._introspect_bigquery()
        
        return []
    
    async def _introspect_postgres(self) -> List[SchemaTable]:
        """PostgreSQL schema introspection"""
        await self.connect()
        
        # Get all tables
        tables_query = """
            SELECT 
                t.table_schema,
                t.table_name,
                obj_description(
                    (quote_ident(t.table_schema) || '.' || quote_ident(t.table_name))::regclass, 
                    'pg_class'
                ) as table_comment
            FROM information_schema.tables t
            WHERE t.table_schema NOT IN ('pg_catalog', 'information_schema')
            AND t.table_type = 'BASE TABLE'
            ORDER BY t.table_schema, t.table_name
        """
        
        tables = await self.execute(tables_query)
        schema_tables = []
        
        for table_row in tables:
            schema = table_row['table_schema']
            table_name = table_row['table_name']
            
            # Get columns
            columns_query = """
                SELECT 
                    c.column_name,
                    c.data_type,
                    c.is_nullable = 'YES' as nullable,
                    c.column_default as default_value,
                    col_description(
                        (quote_ident(c.table_schema) || '.' || quote_ident(c.table_name))::regclass::oid,
                        c.ordinal_position
                    ) as column_comment
                FROM information_schema.columns c
                WHERE c.table_schema = $1 AND c.table_name = $2
                ORDER BY c.ordinal_position
            """
            
            columns = await self._connection.fetch(columns_query, schema, table_name)
            
            # Get primary keys
            pk_query = """
                SELECT kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu 
                    ON tc.constraint_name = kcu.constraint_name
                WHERE tc.table_schema = $1 
                AND tc.table_name = $2
                AND tc.constraint_type = 'PRIMARY KEY'
            """
            
            pk_rows = await self._connection.fetch(pk_query, schema, table_name)
            primary_keys = [row['column_name'] for row in pk_rows]
            
            # Get foreign keys
            fk_query = """
                SELECT
                    kcu.column_name,
                    ccu.table_name AS foreign_table,
                    ccu.column_name AS foreign_column
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage ccu
                    ON tc.constraint_name = ccu.constraint_name
                WHERE tc.table_schema = $1
                AND tc.table_name = $2
                AND tc.constraint_type = 'FOREIGN KEY'
            """
            
            fk_rows = await self._connection.fetch(fk_query, schema, table_name)
            foreign_keys = [
                {
                    'column': row['column_name'],
                    'references_table': row['foreign_table'],
                    'references_column': row['foreign_column']
                }
                for row in fk_rows
            ]
            
            # Get sample data (first 3 rows)
            sample_query = f"""
                SELECT * FROM {schema}.{table_name} 
                LIMIT 3
            """
            sample_rows = await self.execute(sample_query)
            
            # Get row count estimate
            count_query = f"""
                SELECT reltuples::BIGINT as estimate 
                FROM pg_class 
                WHERE relname = '{table_name}'
            """
            count_result = await self.execute(count_query)
            row_count = count_result[0]['estimate'] if count_result else None
            
            schema_columns = [
                SchemaColumn(
                    name=col['column_name'],
                    data_type=col['data_type'],
                    nullable=col['nullable'],
                    default=col['default_value'],
                    is_primary_key=col['column_name'] in primary_keys,
                    comment=col['column_comment']
                )
                for col in columns
            ]
            
            schema_tables.append(SchemaTable(
                name=table_name,
                schema=schema,
                columns=schema_columns,
                primary_keys=primary_keys,
                foreign_keys=foreign_keys,
                row_count=row_count,
                comment=table_row['table_comment'],
                sample_data=sample_rows
            ))
        
        await self.disconnect()
        return schema_tables
    
    async def _introspect_mysql(self) -> List[SchemaTable]:
        """MySQL schema introspection"""
        await self.connect()
        
        # Get all tables
        tables_query = """
            SELECT 
                TABLE_SCHEMA,
                TABLE_NAME,
                TABLE_COMMENT
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_TYPE = 'BASE TABLE'
        """
        
        tables = await self.execute(tables_query)
        schema_tables = []
        
        for table_row in tables:
            schema = table_row['TABLE_SCHEMA']
            table_name = table_row['TABLE_NAME']
            
            # Get columns
            columns_query = f"""
                SELECT 
                    COLUMN_NAME,
                    DATA_TYPE,
                    IS_NULLABLE = 'YES' as nullable,
                    COLUMN_DEFAULT,
                    COLUMN_COMMENT
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = '{schema}'
                AND TABLE_NAME = '{table_name}'
                ORDER BY ORDINAL_POSITION
            """
            
            columns = await self.execute(columns_query)
            
            # Get primary keys
            pk_query = f"""
                SELECT COLUMN_NAME
                FROM information_schema.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = '{schema}'
                AND TABLE_NAME = '{table_name}'
                AND CONSTRAINT_NAME = 'PRIMARY'
            """
            
            pk_rows = await self.execute(pk_query)
            primary_keys = [row['COLUMN_NAME'] for row in pk_rows]
            
            # Get foreign keys
            fk_query = f"""
                SELECT
                    COLUMN_NAME,
                    REFERENCED_TABLE_NAME,
                    REFERENCED_COLUMN_NAME
                FROM information_schema.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = '{schema}'
                AND TABLE_NAME = '{table_name}'
                AND REFERENCED_TABLE_NAME IS NOT NULL
            """
            
            fk_rows = await self.execute(fk_query)
            foreign_keys = [
                {
                    'column': row['COLUMN_NAME'],
                    'references_table': row['REFERENCED_TABLE_NAME'],
                    'references_column': row['REFERENCED_COLUMN_NAME']
                }
                for row in fk_rows
            ]
            
            # Get sample data
            sample_query = f"SELECT * FROM {table_name} LIMIT 3"
            sample_rows = await self.execute(sample_query)
            
            # Get row count
            count_query = f"SELECT COUNT(*) as count FROM {table_name}"
            count_result = await self.execute(count_query)
            row_count = count_result[0]['count'] if count_result else None
            
            schema_columns = [
                SchemaColumn(
                    name=col['COLUMN_NAME'],
                    data_type=col['DATA_TYPE'],
                    nullable=col['nullable'],
                    default=col['COLUMN_DEFAULT'],
                    is_primary_key=col['COLUMN_NAME'] in primary_keys,
                    comment=col['COLUMN_COMMENT']
                )
                for col in columns
            ]
            
            schema_tables.append(SchemaTable(
                name=table_name,
                schema=schema,
                columns=schema_columns,
                primary_keys=primary_keys,
                foreign_keys=foreign_keys,
                row_count=row_count,
                comment=table_row['TABLE_COMMENT'],
                sample_data=sample_rows
            ))
        
        await self.disconnect()
        return schema_tables
    
    async def _introspect_snowflake(self) -> List[SchemaTable]:
        """Snowflake schema introspection"""
        # Implementation for Snowflake
        pass
    
    async def _introspect_bigquery(self) -> List[SchemaTable]:
        """BigQuery schema introspection"""
        # Implementation for BigQuery
        pass
    
    def get_dialect_hints(self) -> Dict[str, Any]:
        """Get SQL dialect-specific hints for LLM"""
        dialect_hints = {
            DatabaseType.POSTGRESQL: {
                "date_functions": ["NOW()", "CURRENT_DATE", "DATE_TRUNC", "EXTRACT"],
                "string_functions": ["CONCAT", "||", "LOWER", "UPPER"],
                "limit_syntax": "LIMIT n OFFSET m",
                "quote_style": "double quotes for identifiers",
                "ilike_supported": True
            },
            DatabaseType.MYSQL: {
                "date_functions": ["NOW()", "CURDATE()", "DATE_FORMAT", "DATEDIFF"],
                "string_functions": ["CONCAT", "LOWER", "UPPER", "SUBSTRING"],
                "limit_syntax": "LIMIT offset, count",
                "quote_style": "backticks for identifiers",
                "ilike_supported": False
            },
            DatabaseType.SNOWFLAKE: {
                "date_functions": ["CURRENT_TIMESTAMP", "DATE_TRUNC", "DATEDIFF"],
                "string_functions": ["CONCAT", "LOWER", "UPPER", "SUBSTR"],
                "limit_syntax": "LIMIT n",
                "quote_style": "double quotes for identifiers",
                "warehouse_required": True
            },
            DatabaseType.BIGQUERY: {
                "date_functions": ["CURRENT_TIMESTAMP", "DATE_TRUNC", "DATE_DIFF"],
                "string_functions": ["CONCAT", "LOWER", "UPPER", "SUBSTR"],
                "limit_syntax": "LIMIT n",
                "quote_style": "backticks for project.dataset.table",
                "partitioning": True
            }
        }
        
        return dialect_hints.get(self.config.db_type, {})
