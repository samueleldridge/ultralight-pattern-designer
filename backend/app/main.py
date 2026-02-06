import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import init_db
from app.api import query, dashboards, connections, intelligence, history, user_memory, subscriptions, chat_sessions
from app.api.suggestions_enhanced import router as suggestions_router
from app.middleware import (
    RateLimitMiddleware,
    QueryLimitsMiddleware,
    AuthMiddleware,
    TenantMiddleware,
)
from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    
    # Start background worker
    from app.async_jobs import start_background_worker, get_job_queue, QueryJobHandler, ExportJobHandler
    from app.cache import get_enhanced_cache
    from app.export import ExportManager
    
    # Register job handlers
    queue = get_job_queue()
    cache = get_enhanced_cache()
    export_manager = ExportManager()
    
    # Register handlers (these would need actual implementations)
    # queue.register_handler("query", QueryJobHandler(executor, cache))
    # queue.register_handler("export", ExportJobHandler(export_manager, storage))
    
    await start_background_worker(max_concurrent=5)
    
    yield
    
    # Shutdown
    from app.async_jobs import stop_background_worker
    await stop_background_worker()


app = FastAPI(
    title="AI Analytics Platform",
    description="AI-native BI with agentic workflows and edge case handling",
    version="0.3.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
app.add_middleware(
    RateLimitMiddleware,
    default_requests_per_minute=60,
    route_limits={
        "/api/query/stream": {"rpm": 30, "rph": 500},
        "/api/export": {"rpm": 5, "rph": 50},
    }
)

# Query limits
app.add_middleware(
    QueryLimitsMiddleware,
    check_paths=["/api/query"]
)

# Auth
app.add_middleware(
    AuthMiddleware,
    exempt_routes=["/health", "/docs", "/openapi.json", "/api/public"]
)

# Tenant isolation
app.add_middleware(TenantMiddleware)

# Include routers
app.include_router(query.router)
app.include_router(dashboards.router)
app.include_router(suggestions_router)
app.include_router(connections.router)
app.include_router(intelligence.router)
app.include_router(history.router)
app.include_router(user_memory.router)
app.include_router(subscriptions.router)
app.include_router(chat_sessions.router)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from app.async_jobs import get_job_queue
    from app.cache import get_enhanced_cache
    
    queue_status = get_job_queue().get_queue_status()
    
    return {
        "status": "healthy",
        "version": "0.3.0",
        "queue": queue_status
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    from app.monitoring import get_monitor, MetricsExporter
    
    monitor = get_monitor()
    exporter = MetricsExporter(monitor)
    
    return exporter.to_prometheus_format()


@app.get("/")
async def root():
    return {
        "message": "AI Analytics Platform API",
        "version": "0.3.0",
        "features": [
            "enhanced_nlp",
            "intent_classification",
            "entity_extraction",
            "context_management",
            "query_suggestions",
            "few_shot_prompting",
            "query_timeouts",
            "rate_limiting",
            "query_caching",
            "audit_logging",
            "background_jobs",
            "data_export"
        ],
        "docs": "/docs"
    }
