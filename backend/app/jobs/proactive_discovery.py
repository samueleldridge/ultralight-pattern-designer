"""
Proactive Intelligence Discovery Job

Weekly/Monthly cron job that:
1. Analyzes user interaction patterns
2. Consolidates user memory profiles
3. Discovers new insights based on user interests
4. Generates and stores proactive suggestions

Schedule: Weekly (Sundays at 9 AM) or Monthly (1st of month)
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict

from app.database import AsyncSessionLocal
from app.intelligence.user_memory import (
    UserMemoryService,
    ProactiveIntelligenceService,
    create_user_memory_tables
)
from app.models import User
from sqlalchemy import select, distinct

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("proactive_intelligence")


class ProactiveDiscoveryJob:
    """Scheduled job for proactive insight discovery"""
    
    def __init__(self):
        self.memory_service = UserMemoryService()
        # Initialize with placeholder - would need real connectors
        self.proactive_service = None  # Lazy init
    
    async def run(self, mode: str = "weekly"):
        """
        Run proactive discovery for all users
        
        Args:
            mode: 'weekly' or 'monthly' - affects lookback period and analysis depth
        """
        logger.info(f"🚀 Starting proactive discovery job ({mode} mode)")
        start_time = datetime.utcnow()
        
        # Ensure tables exist
        await create_user_memory_tables()
        
        # Get all active users
        users = await self._get_active_users()
        logger.info(f"📊 Processing {len(users)} users")
        
        stats = {
            "users_processed": 0,
            "interactions_analyzed": 0,
            "memories_consolidated": 0,
            "suggestions_generated": 0,
            "errors": 0
        }
        
        for user in users:
            try:
                result = await self._process_user(user, mode)
                stats["users_processed"] += 1
                stats["suggestions_generated"] += result.get("suggestions", 0)
                
            except Exception as e:
                logger.error(f"❌ Error processing user {user['user_id']}: {e}")
                stats["errors"] += 1
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        logger.info(f"✅ Proactive discovery complete in {duration:.1f}s")
        logger.info(f"📈 Stats: {stats}")
        
        return stats
    
    async def _get_active_users(self) -> List[Dict]:
        """Get list of users with recent activity"""
        async with AsyncSessionLocal() as session:
            # Get users with interactions in last 30 days
            from app.intelligence.user_memory import UserInteraction
            
            cutoff = datetime.utcnow() - timedelta(days=30)
            
            result = await session.execute(
                select(
                    distinct(UserInteraction.user_id),
                    UserInteraction.tenant_id
                ).where(
                    UserInteraction.created_at >= cutoff
                )
            )
            
            return [
                {"user_id": row[0], "tenant_id": row[1]}
                for row in result.fetchall()
            ]
    
    async def _process_user(self, user: Dict, mode: str) -> Dict:
        """Process a single user"""
        user_id = user["user_id"]
        tenant_id = user["tenant_id"]
        
        logger.info(f"👤 Processing user {user_id}")
        
        # 1. Consolidate memory
        lookback_days = 7 if mode == "weekly" else 30
        profile = await self.memory_service.consolidate_memory(
            user_id=user_id,
            tenant_id=tenant_id,
            lookback_days=lookback_days
        )
        
        logger.info(f"  📝 Memory updated: {len(profile.interests)} interests")
        
        # 2. Discover insights (only if proactive service initialized)
        if self.proactive_service:
            suggestions = await self.proactive_service.discover_insights(
                user_id=user_id,
                tenant_id=tenant_id
            )
            
            logger.info(f"  💡 Generated {len(suggestions)} suggestions")
            
            return {"suggestions": len(suggestions)}
        
        return {"suggestions": 0}


async def run_weekly_discovery():
    """Entry point for weekly cron job"""
    job = ProactiveDiscoveryJob()
    return await job.run(mode="weekly")


async def run_monthly_discovery():
    """Entry point for monthly cron job"""
    job = ProactiveDiscoveryJob()
    return await job.run(mode="monthly")


# For direct execution
if __name__ == "__main__":
    import sys
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "weekly"
    
    if mode not in ["weekly", "monthly"]:
        print(f"Usage: python {sys.argv[0]} [weekly|monthly]")
        sys.exit(1)
    
    result = asyncio.run(run_weekly_discovery() if mode == "weekly" else run_monthly_discovery())
    print(f"Result: {result}")
