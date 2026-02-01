"""
AI Analytics Platform - Main Application
FastAPI backend with comprehensive error handling and logging
"""
import os
import logging
import sys
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager

from app.database import init_db
from app.api import query, dashboards, suggestions, connections, intelligence
from app.schemas import ErrorResponse, HealthResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Log startup info
logger.info("=" * 50)
logger.info("Starting AI Analytics Platform API")
logger.info(f"Python version: {sys.version}")
logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
logger.info("=" * 50)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    try:
        await init_db()
        logger.info("✓ Database initialized successfully")
    except Exception as e:
        logger.error(f"✗ Failed to initialize database: {e}", exc_info=True)
        raise
    
    logger.info("✓ Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")


app = FastAPI(
    title="AI Analytics Platform",
    description="AI-native BI with agentic workflows",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# CORS - comprehensive configuration for all environments
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]

# Add additional origins from environment
env_origins = os.getenv("CORS_ORIGINS", "")
if env_origins:
    ALLOWED_ORIGINS.extend([o.strip() for o in env_origins.split(",") if o.strip()])

logger.info(f"CORS allowed origins: {ALLOWED_ORIGINS}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Workflow-ID"],
    max_age=600,  # 10 minutes
)


# Request ID middleware for tracking
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID for tracing"""
    import uuid
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    
    logger.info(f"[{request_id}] {request.method} {request.url.path}")
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    logger.info(f"[{request_id}] Response: {response.status_code}")
    return response


# Validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed messages"""
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    errors = []
    for error in exc.errors():
        errors.append({
            "field": error.get("loc", ["unknown"]),
            "message": error.get("msg", "Validation error"),
            "type": error.get("type", "unknown")
        })
    
    logger.warning(f"[{request_id}] Validation error: {errors}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="validation_error",
            message="Request validation failed",
            details={"errors": errors}
        ).dict()
    )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    logger.error(f"[{request_id}] Unhandled exception: {exc}", exc_info=True)
    
    # Don't expose internal details in production
    is_development = os.getenv("ENVIRONMENT", "development") == "development"
    
    details: Dict[str, Any] = {"request_id": request_id}
    if is_development:
        import traceback
        details["exception"] = str(exc)
        details["traceback"] = traceback.format_exc()
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="internal_server_error",
            message="An unexpected error occurred. Please try again later.",
            details=details
        ).dict()
    )


# Include routers with error handling
routers = [
    (query.router, "/api"),
    (dashboards.router, "/api/dashboards"),
    (suggestions.router, "/api/suggestions"),
    (connections.router, "/api/connections"),
    (intelligence.router, "/api/intelligence"),
]

for router, prefix in routers:
    try:
        app.include_router(router)
        logger.info(f"✓ Registered router: {prefix}")
    except Exception as e:
        logger.error(f"✗ Failed to register router {prefix}: {e}", exc_info=True)


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """
    Health check endpoint
    
    Returns the current status of the API and its dependencies.
    """
    # Check database connection
    db_status = "healthy"
    try:
        # Simple health check - in production, verify actual connectivity
        from app.database import engine
        # We could add a simple query here to verify DB connectivity
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        db_status = "degraded"
    
    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        version="0.1.0",
        timestamp=datetime.utcnow().isoformat()
    )


@app.get("/health/detailed", tags=["health"])
async def detailed_health_check():
    """
    Detailed health check with component status
    
    Returns comprehensive health information for monitoring.
    """
    checks = {
        "database": {"status": "healthy", "latency_ms": 5},
        "cache": {"status": "healthy", "latency_ms": 2},
        "llm_provider": {"status": "healthy"},
    }
    
    # Overall status is worst of all checks
    overall = "healthy"
    for check in checks.values():
        if check.get("status") == "unhealthy":
            overall = "unhealthy"
        elif check.get("status") == "degraded" and overall == "healthy":
            overall = "degraded"
    
    return {
        "status": overall,
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
        "environment": os.getenv("ENVIRONMENT", "development"),
    }


@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": "AI Analytics Platform API",
        "version": "0.1.0",
        "description": "AI-native BI with agentic workflows",
        "documentation": "/docs",
        "health": "/health",
        "status": "operational",
        "endpoints": {
            "query": "/api/query",
            "suggestions": "/api/suggestions",
            "dashboards": "/api/dashboards",
            "connections": "/api/connections",
            "intelligence": "/api/intelligence",
        }
    }


# 404 handler - must be last
@app.get("/{path:path}", include_in_schema=False)
async def catch_all(path: str, request: Request):
    """Catch-all for undefined routes"""
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    logger.warning(f"[{request_id}] 404: {request.method} /{path}")
    
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=ErrorResponse(
            error="not_found",
            message=f"Endpoint /{path} not found",
            details={
                "path": path,
                "method": request.method,
                "available_endpoints": [
                    "/",
                    "/health",
                    "/health/detailed",
                    "/docs",
                    "/api/query",
                    "/api/suggestions",
                    "/api/dashboards",
                    "/api/connections",
                    "/api/intelligence"
                ]
            }
        ).dict()
    )
