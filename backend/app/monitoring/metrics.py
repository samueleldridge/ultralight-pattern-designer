"""
Monitoring and observability module.
Tracks query performance, LLM costs, errors, and slow queries.
"""

import time
import asyncio
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import json


@dataclass
class QueryMetrics:
    """Metrics for a single query execution"""
    query_hash: str
    sql_preview: str
    start_time: float
    end_time: Optional[float] = None
    row_count: Optional[int] = None
    error: Optional[str] = None
    cache_hit: bool = False
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    connection_id: Optional[str] = None
    
    @property
    def duration_ms(self) -> Optional[float]:
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return None
    
    @property
    def success(self) -> bool:
        return self.error is None


@dataclass
class LLMMetrics:
    """Metrics for LLM API calls"""
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None
    endpoint: str = ""  # Which endpoint/feature used the LLM
    
    # Pricing per 1K tokens (approximate, update as needed)
    PRICING = {
        "kimi-k2-5": {"input": 0.005, "output": 0.015},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    }
    
    def calculate_cost(self) -> float:
        """Calculate cost based on token usage"""
        pricing = self.PRICING.get(self.model, {"input": 0.01, "output": 0.03})
        
        input_cost = (self.prompt_tokens / 1000) * pricing["input"]
        output_cost = (self.completion_tokens / 1000) * pricing["output"]
        
        self.cost_usd = input_cost + output_cost
        return self.cost_usd


@dataclass
class ErrorMetrics:
    """Metrics for error tracking"""
    error_type: str
    message: str
    stack_trace: Optional[str] = None
    count: int = 1
    first_seen: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    endpoint: Optional[str] = None
    is_system_error: bool = True


class PerformanceMonitor:
    """
    Monitor query and system performance.
    """
    
    # Thresholds for slow queries (in ms)
    SLOW_QUERY_THRESHOLD = 5000  # 5 seconds
    VERY_SLOW_QUERY_THRESHOLD = 30000  # 30 seconds
    
    def __init__(self):
        self._query_metrics: List[QueryMetrics] = []
        self._llm_metrics: List[LLMMetrics] = []
        self._error_metrics: Dict[str, ErrorMetrics] = {}
        self._active_queries: Dict[str, QueryMetrics] = {}
        self._handlers: List[Callable] = []
        self._running = False
        
        # Aggregated stats
        self._query_stats = defaultdict(lambda: {
            "count": 0,
            "total_duration": 0,
            "errors": 0,
            "cache_hits": 0
        })
    
    def add_handler(self, handler: Callable):
        """Add metrics handler"""
        self._handlers.append(handler)
    
    def start_query(
        self,
        query_hash: str,
        sql: str,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        connection_id: Optional[str] = None
    ) -> str:
        """Start tracking a query"""
        metric_id = f"{query_hash}_{time.time()}"
        
        self._active_queries[metric_id] = QueryMetrics(
            query_hash=query_hash,
            sql_preview=sql[:200] if len(sql) > 200 else sql,
            start_time=time.time(),
            user_id=user_id,
            tenant_id=tenant_id,
            connection_id=connection_id
        )
        
        return metric_id
    
    def end_query(
        self,
        metric_id: str,
        row_count: Optional[int] = None,
        error: Optional[str] = None,
        cache_hit: bool = False
    ):
        """End tracking a query"""
        if metric_id not in self._active_queries:
            return
        
        metric = self._active_queries.pop(metric_id)
        metric.end_time = time.time()
        metric.row_count = row_count
        metric.error = error
        metric.cache_hit = cache_hit
        
        self._query_metrics.append(metric)
        
        # Update aggregated stats
        stats = self._query_stats[metric.query_hash]
        stats["count"] += 1
        if metric.duration_ms:
            stats["total_duration"] += metric.duration_ms
        if error:
            stats["errors"] += 1
        if cache_hit:
            stats["cache_hits"] += 1
        
        # Check for slow query
        if metric.duration_ms and metric.duration_ms > self.SLOW_QUERY_THRESHOLD:
            self._handle_slow_query(metric)
        
        # Notify handlers
        for handler in self._handlers:
            try:
                handler("query", metric)
            except Exception:
                pass
    
    def record_llm_call(self, metrics: LLMMetrics):
        """Record LLM API call metrics"""
        metrics.calculate_cost()
        self._llm_metrics.append(metrics)
        
        # Notify handlers
        for handler in self._handlers:
            try:
                handler("llm", metrics)
            except Exception:
                pass
    
    def record_error(
        self,
        error_type: str,
        message: str,
        stack_trace: Optional[str] = None,
        user_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        is_system_error: bool = True
    ):
        """Record an error"""
        key = f"{error_type}:{message[:100]}"
        
        if key in self._error_metrics:
            existing = self._error_metrics[key]
            existing.count += 1
            existing.last_seen = datetime.utcnow()
        else:
            self._error_metrics[key] = ErrorMetrics(
                error_type=error_type,
                message=message,
                stack_trace=stack_trace,
                user_id=user_id,
                endpoint=endpoint,
                is_system_error=is_system_error
            )
        
        # Notify handlers
        for handler in self._handlers:
            try:
                handler("error", self._error_metrics[key])
            except Exception:
                pass
    
    def _handle_slow_query(self, metric: QueryMetrics):
        """Handle slow query detection"""
        # This could send alerts, log to special log, etc.
        pass
    
    def get_slow_queries(
        self,
        threshold_ms: Optional[float] = None,
        limit: int = 10
    ) -> List[QueryMetrics]:
        """Get slowest queries"""
        threshold = threshold_ms or self.SLOW_QUERY_THRESHOLD
        
        slow = [
            m for m in self._query_metrics
            if m.duration_ms and m.duration_ms >= threshold
        ]
        
        return sorted(slow, key=lambda x: x.duration_ms or 0, reverse=True)[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics"""
        if not self._query_metrics:
            return {}
        
        total_queries = len(self._query_metrics)
        total_errors = sum(1 for m in self._query_metrics if not m.success)
        cache_hits = sum(1 for m in self._query_metrics if m.cache_hit)
        
        durations = [m.duration_ms for m in self._query_metrics if m.duration_ms]
        
        return {
            "total_queries": total_queries,
            "total_errors": total_errors,
            "error_rate": total_errors / total_queries if total_queries > 0 else 0,
            "cache_hit_rate": cache_hits / total_queries if total_queries > 0 else 0,
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
            "max_duration_ms": max(durations) if durations else 0,
            "slow_queries": len(self.get_slow_queries()),
            "llm_calls": len(self._llm_metrics),
            "llm_cost_usd": sum(m.cost_usd for m in self._llm_metrics),
        }
    
    def get_llm_stats(self) -> Dict[str, Any]:
        """Get LLM usage statistics"""
        if not self._llm_metrics:
            return {}
        
        by_model = defaultdict(lambda: {
            "calls": 0,
            "tokens": 0,
            "cost": 0.0
        })
        
        for metric in self._llm_metrics:
            model_stats = by_model[metric.model]
            model_stats["calls"] += 1
            model_stats["tokens"] += metric.total_tokens
            model_stats["cost"] += metric.cost_usd
        
        return {
            "total_calls": len(self._llm_metrics),
            "total_tokens": sum(m.total_tokens for m in self._llm_metrics),
            "total_cost_usd": sum(m.cost_usd for m in self._llm_metrics),
            "by_model": dict(by_model),
            "errors": sum(1 for m in self._llm_metrics if not m.success)
        }
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        if not self._error_metrics:
            return {}
        
        total_errors = sum(e.count for e in self._error_metrics.values())
        system_errors = sum(
            e.count for e in self._error_metrics.values() if e.is_system_error
        )
        user_errors = total_errors - system_errors
        
        return {
            "unique_errors": len(self._error_metrics),
            "total_occurrences": total_errors,
            "system_errors": system_errors,
            "user_errors": user_errors,
            "top_errors": sorted(
                [
                    {
                        "type": e.error_type,
                        "message": e.message[:100],
                        "count": e.count
                    }
                    for e in self._error_metrics.values()
                ],
                key=lambda x: x["count"],
                reverse=True
            )[:10]
        }
    
    def reset(self):
        """Reset all metrics"""
        self._query_metrics.clear()
        self._llm_metrics.clear()
        self._error_metrics.clear()
        self._query_stats.clear()


class MetricsExporter:
    """Export metrics to various destinations"""
    
    def __init__(self, monitor: PerformanceMonitor):
        self.monitor = monitor
    
    def to_prometheus_format(self) -> str:
        """Export metrics in Prometheus format"""
        stats = self.monitor.get_stats()
        lines = []
        
        # Query metrics
        lines.append(f"# HELP aip_queries_total Total number of queries")
        lines.append(f"# TYPE aip_queries_total counter")
        lines.append(f'aip_queries_total {stats.get("total_queries", 0)}')
        
        lines.append(f"# HELP aip_query_errors_total Total query errors")
        lines.append(f"# TYPE aip_query_errors_total counter")
        lines.append(f'aip_query_errors_total {stats.get("total_errors", 0)}')
        
        lines.append(f"# HELP aip_query_duration_ms Average query duration")
        lines.append(f"# TYPE aip_query_duration_ms gauge")
        lines.append(f'aip_query_duration_ms {stats.get("avg_duration_ms", 0)}')
        
        # LLM metrics
        llm_stats = self.monitor.get_llm_stats()
        lines.append(f"# HELP aip_llm_cost_usd Total LLM cost")
        lines.append(f"# TYPE aip_llm_cost_usd counter")
        lines.append(f'aip_llm_cost_usd {llm_stats.get("total_cost_usd", 0)}')
        
        return "\n".join(lines)
    
    def to_json(self) -> Dict[str, Any]:
        """Export all metrics as JSON"""
        return {
            "queries": self.monitor.get_stats(),
            "llm": self.monitor.get_llm_stats(),
            "errors": self.monitor.get_error_stats(),
            "timestamp": datetime.utcnow().isoformat()
        }


# Global monitor instance
_monitor_instance: Optional[PerformanceMonitor] = None


def get_monitor() -> PerformanceMonitor:
    """Get global performance monitor"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = PerformanceMonitor()
    return _monitor_instance


def track_query(
    sql: str,
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    connection_id: Optional[str] = None
):
    """Context manager to track query execution"""
    import hashlib
    
    monitor = get_monitor()
    query_hash = hashlib.sha256(sql.encode()).hexdigest()[:16]
    metric_id = monitor.start_query(query_hash, sql, user_id, tenant_id, connection_id)
    
    class QueryTracker:
        def __enter__(self):
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            error = str(exc_val) if exc_val else None
            monitor.end_query(metric_id, error=error)
        
        def set_row_count(self, count: int):
            """Set the row count for the query"""
            pass  # Will be handled in end_query
    
    return QueryTracker()


def track_llm_call(
    provider: str,
    model: str,
    endpoint: str = ""
) -> LLMMetrics:
    """Create LLM metrics tracker"""
    metrics = LLMMetrics(
        provider=provider,
        model=model,
        endpoint=endpoint
    )
    return metrics
