from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.database import get_db
from app.schemas import DashboardCreate, DashboardResponse, ViewCreate, ViewResponse

router = APIRouter(prefix="/api/dashboards", tags=["dashboards"])


@router.get("", response_model=List[DashboardResponse])
async def list_dashboards(db: AsyncSession = Depends(get_db)):
    """List all dashboards for current user"""
    # TODO: Implement
    return []


@router.post("", response_model=DashboardResponse)
async def create_dashboard(
    dashboard: DashboardCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new dashboard"""
    from datetime import datetime
    # TODO: Implement
    return {
        "id": "123", 
        "name": dashboard.name, 
        "description": dashboard.description,
        "config": dashboard.config,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }


@router.get("/{dashboard_id}/views", response_model=List[ViewResponse])
async def list_views(dashboard_id: str, db: AsyncSession = Depends(get_db)):
    """List all views in a dashboard"""
    # TODO: Implement
    return []


@router.post("/views", response_model=ViewResponse)
async def create_view(
    view: ViewCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new view"""
    # TODO: Implement
    return {
        "id": "123",
        "title": view.title,
        "query_text": view.query_text,
        "position_x": view.position_x,
        "position_y": view.position_y,
        "width": view.width,
        "height": view.height,
        "chart_type": view.chart_type or "table",
        "config": view.config
    }
