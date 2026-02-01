from typing import Dict, List, Optional, Any
import json
from datetime import datetime, timedelta
from app.cache import get_redis
from app.database.connector import DatabaseConfig, DatabaseConnector


class QueryCache:
    """Intelligent query result caching"""
    
    def __init__(self):
        self.redis = None
    
    async def _get_redis(self):
        if not self.redis:
            self.redis = await get_redis()
        return self.redis
    
    def _generate_cache_key(self, query: str, connection_id: str) -> str:
        """Generate deterministic cache key"""
        import hashlib
        key_data = f"{connection_id}:{query.strip().lower()}"
        return f"query_cache:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    def _is_cacheable(self, query: str) -> bool:
        """Determine if query should be cached"""
        # Don't cache queries with NOW(), CURRENT_DATE, etc.
        non_cacheable_functions = [
            'NOW()', 'CURRENT_DATE', 'CURRENT_TIMESTAMP',
            'RAND()', 'RANDOM()', 'UUID()', 'NEWID()'
        ]
        
        query_upper = query.upper()
        for func in non_cacheable_functions:
            if func in query_upper:
                return False
        
        return True
    
    async def get(self, query: str, connection_id: str) -> Optional[Dict]:
        """Get cached result if available"""
        if not self._is_cacheable(query):
            return None
        
        redis = await self._get_redis()
        cache_key = self._generate_cache_key(query, connection_id)
        
        cached = await redis.get(cache_key)
        if cached:
            data = json.loads(cached)
            data['from_cache'] = True
            return data
        
        return None
    
    async def set(
        self, 
        query: str, 
        connection_id: str, 
        result: Dict,
        ttl_minutes: int = 60
    ):
        """Cache query result"""
        if not self._is_cacheable(query):
            return
        
        redis = await self._get_redis()
        cache_key = self._generate_cache_key(query, connection_id)
        
        cache_data = {
            'result': result,
            'cached_at': datetime.utcnow().isoformat(),
            'query': query[:200]  # Store truncated query for debugging
        }
        
        await redis.setex(
            cache_key,
            timedelta(minutes=ttl_minutes),
            json.dumps(cache_data)
        )
    
    async def invalidate(self, connection_id: str):
        """Invalidate all cached queries for a connection"""
        redis = await self._get_redis()
        # This would require pattern scanning in production
        # For now, we'll use a simpler invalidation strategy
        pass


class QueryExecutor:
    """Execute queries with caching, timeouts, and monitoring"""
    
    def __init__(self):
        self.cache = QueryCache()
        self.active_queries = {}
    
    async def execute(
        self,
        query: str,
        config: DatabaseConfig,
        use_cache: bool = True,
        timeout_seconds: int = 30
    ) -> Dict[str, Any]:
        """Execute query with full lifecycle management"""
        
        connection_id = f"{config.host}:{config.database}"
        
        # 1. Check cache
        if use_cache:
            cached = await self.cache.get(query, connection_id)
            if cached:
                return {
                    'success': True,
                    'data': cached['result'],
                    'from_cache': True,
                    'row_count': len(cached['result'].get('rows', []))
                }
        
        # 2. Create connector
        connector = DatabaseConnector(config)
        
        # 3. Validate query
        from app.database.dialect import SQLValidator, SQLDialect
        validator = SQLValidator(SQLDialect(config.db_type))
        validation = validator.validate(query)
        
        if not validation['valid']:
            return {
                'success': False,
                'error': 'Validation failed',
                'details': validation['errors']
            }
        
        # 4. Sanitize
        try:
            sanitized_query = validator.sanitize_for_execution(query)
        except ValueError as e:
            return {
                'success': False,
                'error': str(e)
            }
        
        # 5. Execute with timeout handling
        try:
            import asyncio
            
            # Execute with timeout
            rows = await asyncio.wait_for(
                connector.execute(sanitized_query),
                timeout=timeout_seconds
            )
            
            result = {
                'rows': rows,
                'row_count': len(rows),
                'columns': list(rows[0].keys()) if rows else []
            }
            
            # 6. Cache result
            await self.cache.set(query, connection_id, result)
            
            return {
                'success': True,
                'data': result,
                'from_cache': False,
                'warnings': validation.get('warnings', [])
            }
            
        except asyncio.TimeoutError:
            return {
                'success': False,
                'error': f'Query timed out after {timeout_seconds} seconds',
                'suggestion': 'Try adding LIMIT or more specific filters'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'query': query[:200]
            }
        finally:
            await connector.disconnect()
    
    async def explain_query(
        self,
        query: str,
        config: DatabaseConfig
    ) -> Dict[str, Any]:
        """Get query execution plan"""
        connector = DatabaseConnector(config)
        
        try:
            await connector.connect()
            
            # Get execution plan
            if config.db_type == 'postgresql':
                explain_query = f"EXPLAIN (FORMAT JSON) {query}"
                result = await connector.execute(explain_query)
                return {
                    'success': True,
                    'plan': result[0] if result else None
                }
            elif config.db_type == 'mysql':
                explain_query = f"EXPLAIN FORMAT=JSON {query}"
                result = await connector.execute(explain_query)
                return {
                    'success': True,
                    'plan': result[0] if result else None
                }
            else:
                return {
                    'success': False,
                    'error': 'EXPLAIN not supported for this database type'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            await connector.disconnect()
