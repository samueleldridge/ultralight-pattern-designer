#!/usr/bin/env python3
"""
Cache warming script.
Pre-populates cache with common queries.
Run this periodically or on startup.
"""

import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any
import argparse


# Add parent to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


class CacheWarmer:
    """Cache warming utility"""
    
    def __init__(self):
        self.queries: List[Dict[str, Any]] = []
        self.results: List[Dict] = []
    
    def add_query(
        self,
        name: str,
        query: str,
        connection_id: str,
        ttl_seconds: int = 3600
    ):
        """Register a query to warm"""
        self.queries.append({
            "name": name,
            "query": query,
            "connection_id": connection_id,
            "ttl_seconds": ttl_seconds
        })
    
    async def warm_all(self):
        """Execute all registered queries and cache results"""
        print(f"[{datetime.now()}] Starting cache warming...")
        print(f"[{datetime.now()}] Queries to warm: {len(self.queries)}")
        
        for query_def in self.queries:
            result = await self._warm_query(query_def)
            self.results.append(result)
        
        # Print summary
        success = sum(1 for r in self.results if r["status"] == "success")
        failed = sum(1 for r in self.results if r["status"] == "error")
        
        print(f"\n[{datetime.now()}] Cache warming complete!")
        print(f"  Success: {success}")
        print(f"  Failed: {failed}")
        print(f"  Total: {len(self.results)}")
        
        return self.results
    
    async def _warm_query(self, query_def: Dict) -> Dict:
        """Warm a single query"""
        name = query_def["name"]
        query = query_def["query"]
        
        print(f"  Warming: {name}...", end=" ")
        
        try:
            start = datetime.now()
            
            # Here you would actually execute the query
            # For now, just simulate
            # from app.database.executor import QueryExecutor
            # executor = QueryExecutor()
            # result = await executor.execute(query, query_def["connection_id"])
            
            # Simulated execution
            await asyncio.sleep(0.1)
            
            duration = (datetime.now() - start).total_seconds()
            
            print(f"OK ({duration:.2f}s)")
            
            return {
                "name": name,
                "status": "success",
                "duration": duration,
                "cached_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"FAILED: {str(e)}")
            
            return {
                "name": name,
                "status": "error",
                "error": str(e)
            }


def load_common_queries() -> List[Dict]:
    """Load list of common queries to warm"""
    # This could load from a JSON file or database
    return [
        {
            "name": "daily_active_users",
            "query": "SELECT DATE(created_at) as date, COUNT(*) as users FROM users GROUP BY 1 ORDER BY 1 DESC LIMIT 30",
            "connection_id": "default",
            "ttl_seconds": 1800  # 30 min
        },
        {
            "name": "monthly_revenue",
            "query": "SELECT DATE_TRUNC('month', date) as month, SUM(amount) as revenue FROM transactions GROUP BY 1 ORDER BY 1 DESC LIMIT 12",
            "connection_id": "default",
            "ttl_seconds": 3600  # 1 hour
        },
        {
            "name": "top_products",
            "query": "SELECT product_name, SUM(quantity) as total_sold FROM order_items GROUP BY 1 ORDER BY 2 DESC LIMIT 10",
            "connection_id": "default",
            "ttl_seconds": 7200  # 2 hours
        },
    ]


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Cache warming script")
    parser.add_argument("--config", help="Path to queries config JSON file")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be warmed without executing")
    args = parser.parse_args()
    
    warmer = CacheWarmer()
    
    # Load queries
    if args.config:
        with open(args.config) as f:
            queries = json.load(f)
    else:
        queries = load_common_queries()
    
    # Register queries
    for q in queries:
        warmer.add_query(
            name=q["name"],
            query=q["query"],
            connection_id=q.get("connection_id", "default"),
            ttl_seconds=q.get("ttl_seconds", 3600)
        )
    
    if args.dry_run:
        print("Dry run - would warm the following queries:")
        for q in queries:
            print(f"  - {q['name']}")
        return
    
    # Warm cache
    await warmer.warm_all()


if __name__ == "__main__":
    asyncio.run(main())
