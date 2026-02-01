"""
Cron job scheduling for proactive intelligence.
Run these as background workers.
"""

import asyncio
from datetime import datetime
from app.intelligence.proactive import (
    run_pattern_detection,
    run_insight_generation,
    run_anomaly_detection
)


async def schedule_jobs():
    """Schedule and run background intelligence jobs"""
    
    while True:
        now = datetime.utcnow()
        
        # Pattern detection: Run daily at 2 AM
        if now.hour == 2 and now.minute == 0:
            print(f"[{now}] Running pattern detection...")
            await run_pattern_detection()
        
        # Insight generation: Run every 4 hours
        if now.hour % 4 == 0 and now.minute == 0:
            print(f"[{now}] Running insight generation...")
            await run_insight_generation()
        
        # Anomaly detection: Run every hour
        if now.minute == 0:
            print(f"[{now}] Running anomaly detection...")
            await run_anomaly_detection()
        
        # Sleep for 1 minute
        await asyncio.sleep(60)


if __name__ == "__main__":
    print("Starting proactive intelligence scheduler...")
    asyncio.run(schedule_jobs())
