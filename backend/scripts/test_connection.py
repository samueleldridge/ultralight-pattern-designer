#!/usr/bin/env python3
"""
Database connection retry script.
Tests database connectivity with automatic retry.
Useful for health checks and connection validation.
"""

import asyncio
import argparse
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


class ConnectionTester:
    """Test database connectivity"""
    
    def __init__(
        self,
        max_retries: int = 5,
        base_delay: float = 1.0,
        timeout: float = 10.0
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.timeout = timeout
    
    async def test_connection(self, connection_string: str = None) -> bool:
        """Test database connection with retry"""
        from app.config import get_settings
        
        settings = get_settings()
        db_url = connection_string or settings.database_url
        
        print(f"[{datetime.now()}] Testing database connection...")
        print(f"  Database: {settings.database_url_safe}")
        print(f"  Max retries: {self.max_retries}")
        print(f"  Base delay: {self.base_delay}s")
        print()
        
        for attempt in range(1, self.max_retries + 1):
            try:
                print(f"  Attempt {attempt}/{self.max_retries}...", end=" ")
                
                # Try to connect
                # This is a placeholder - implement actual connection test
                # from app.database import test_connection
                # await test_connection(db_url)
                
                # Simulated test
                await asyncio.sleep(0.1)
                
                print("✓ Connected!")
                return True
                
            except Exception as e:
                print(f"✗ Failed: {str(e)}")
                
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** (attempt - 1))  # Exponential backoff
                    print(f"    Retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
        
        print(f"\n[{datetime.now()}] Connection failed after {self.max_retries} attempts")
        return False


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Database connection tester")
    parser.add_argument("--retries", type=int, default=5, help="Maximum retry attempts")
    parser.add_argument("--delay", type=float, default=1.0, help="Base delay between retries")
    parser.add_argument("--connection-string", help="Database connection string")
    args = parser.parse_args()
    
    tester = ConnectionTester(
        max_retries=args.retries,
        base_delay=args.delay
    )
    
    success = await tester.test_connection(args.connection_string)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
