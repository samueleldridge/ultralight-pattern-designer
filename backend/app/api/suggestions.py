from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.database import get_db
from app.schemas import SuggestionResponse

router = APIRouter(prefix="/api/suggestions", tags=["suggestions"])


@router.get("", response_model=List[SuggestionResponse])
async def get_suggestions(db: AsyncSession = Depends(get_db)):
    """Get personalized suggestions for the user"""
    # TODO: Implement with actual user profile
    return [
        {
            "type": "pattern",
            "text": "You usually check revenue on Mondays. Here's this week:",
            "action": "run",
            "query": "What was revenue this week?"
        },
        {
            "type": "popular",
            "text": "Your team often asks: Top products by sales",
            "action": "suggest",
            "query": "What are the top 10 products by sales?"
        }
    ]


@router.get("/history/search")
async def search_history(q: str, db: AsyncSession = Depends(get_db)):
    """Search question history"""
    # TODO: Implement semantic search
    return []
