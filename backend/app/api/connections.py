from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.database import get_db

router = APIRouter(prefix="/api/connections", tags=["connections"])


@router.get("")
async def list_connections(db: AsyncSession = Depends(get_db)):
    """List database connections"""
    # TODO: Implement
    return []


@router.post("")
async def create_connection(db: AsyncSession = Depends(get_db)):
    """Create a new database connection"""
    # TODO: Implement
    return {"id": "123", "status": "created"}


@router.post("/{connection_id}/test")
async def test_connection(connection_id: str, db: AsyncSession = Depends(get_db)):
    """Test a database connection"""
    # TODO: Implement
    return {"status": "success"}


@router.post("/{connection_id}/sync-schema")
async def sync_schema(connection_id: str, db: AsyncSession = Depends(get_db)):
    """Sync schema from database"""
    # TODO: Implement
    return {"status": "syncing"}
