from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

# Optional imports - handle gracefully if not installed
try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    logger.warning("asyncpg not installed - PostgreSQL support disabled")

try:
    import aiomysql
    AIOMYSQL_AVAILABLE = True
except ImportError:
    AIOMYSQL_AVAILABLE = False
    logger.warning("aiomysql not installed - MySQL support disabled")

try:
    import aioodbc
    AIOODBC_AVAILABLE = True
except ImportError:
    AIOODBC_AVAILABLE = False
    logger.warning("aioodbc not installed - ODBC support disabled")


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
    ssl_cert: Optional[str] = None
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = 22
    ssh_username: Optional[str] = None
    ssh_key_path: Optional[str] = None
    
    class Config:
        from_attributes = True
    
    @property
    def connection_string(self) -> str:
        """Generate SQLAlchemy connection string"""
        if self.db_type == DatabaseType.POSTGRESQL:
            return f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        elif self.db_type == DatabaseType.MYSQL:
            return f"mysql+aiomysql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        elif self.db_type == DatabaseType.SQLITE:
            return f"sqlite+aiosqlite:///{self.database}"
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")


class SchemaColumn(BaseModel):
    name: str
    data_type: str


class DatabaseConnector:
    """
    Unified database connector supporting multiple database types.
    """
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._engine: Optional[AsyncEngine] = None
        self._connection = None
    
    async def connect(self):
        """Establish database connection"""
        if self.config.db_type == DatabaseType.POSTGRESQL:
            if not ASYNCPG_AVAILABLE:
                raise RuntimeError("asyncpg not installed - PostgreSQL support unavailable")
            self._connection = await asyncpg.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.username,
                password=self.config.password
            )
        elif self.config.db_type == DatabaseType.MYSQL:
            if not AIOMYSQL_AVAILABLE:
                raise RuntimeError("aiomysql not installed - MySQL support unavailable")
            self._connection = await aiomysql.create_pool(
                host=self.config.host,
                port=self.config.port,
                db=self.config.database,
                user=self.config.username,
                password=self.config.password
            )
        elif self.config.db_type == DatabaseType.SQLITE:
            # SQLite uses SQLAlchemy
            pass
        else:
            raise ValueError(f"Unsupported database type: {self.config.db_type}")
    
    async def get_schema(self) -> Dict[str, List[SchemaColumn]]:
        """Get database schema"""
        if not self._connection:
            await self.connect()
        
        schema = {}
        
        if self.config.db_type == DatabaseType.POSTGRESQL:
            query = """
                SELECT table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position
            """
            rows = await self._connection.fetch(query)
            for row in rows:
                if row['table_name'] not in schema:
                    schema[row['table_name']] = []
                schema[row['table_name']].append(
                    SchemaColumn(name=row['column_name'], data_type=row['data_type'])
                )
        
        return schema
    
    async def execute_query(self, sql: str, params: Optional[List] = None) -> List[Dict]:
        """Execute query and return results"""
        if not self._connection:
            await self.connect()
        
        if self.config.db_type == DatabaseType.POSTGRESQL:
            rows = await self._connection.fetch(sql, *(params or []))
            return [dict(row) for row in rows]
        
        return []
    
    async def close(self):
        """Close connection"""
        if self._connection:
            if self.config.db_type == DatabaseType.POSTGRESQL:
                await self._connection.close()
            elif self.config.db_type == DatabaseType.MYSQL:
                self._connection.close()
            self._connection = None


def get_sqlalchemy_engine(config: DatabaseConfig) -> AsyncEngine:
    """Get SQLAlchemy async engine for the database"""
    if config.db_type == DatabaseType.POSTGRESQL:
        url = f"postgresql+asyncpg://{config.username}:{config.password}@{config.host}:{config.port}/{config.database}"
    elif config.db_type == DatabaseType.MYSQL:
        url = f"mysql+aiomysql://{config.username}:{config.password}@{config.host}:{config.port}/{config.database}"
    elif config.db_type == DatabaseType.SQLITE:
        url = f"sqlite+aiosqlite:///{config.database}"
    else:
        raise ValueError(f"Unsupported database type for SQLAlchemy: {config.db_type}")
    
    return create_async_engine(url, echo=False, future=True)
