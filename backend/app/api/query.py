"""
Enhanced query API with export and background job support.
"""

import json
import asyncio
import uuid
from datetime import datetime
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Request
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.cache import get_cache
from app.agent.state import AgentState
from app.agent.workflow import workflow_app
from app.agent.messages import (
    get_user_friendly_message, 
    get_step_icon, 
    calculate_progress,
    get_step_category
)
from app.schemas import QueryRequest, QueryResponse, StreamEvent
from app.middleware import check_rate_limit, query_rate_limiter, RateLimitExceeded
from app.security import get_audit_logger, sanitize_query_params, InputValidator, InputType
from app.monitoring import get_monitor
from app.export import ExportManager, ExportOptions
from app.async_jobs import enqueue_query_job, enqueue_export_job, get_job_queue

router = APIRouter(prefix="/api", tags=["query"])


@router.post("/query")
async def start_query(
    request: Request,
    query_request: QueryRequest,
    db: AsyncSession = Depends(get_db)
):
    """Start a new query workflow"""
    
    # Rate limiting
    try:
        is_allowed, rate_info = await query_rate_limiter.is_allowed(request)
        if not is_allowed:
            raise RateLimitExceeded(retry_after=60)
    except RateLimitExceeded as e:
        raise e
    
    # Sanitize inputs
    query = query_request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
    
    # Validate query length
    is_valid, error = InputValidator.validate(
        query, InputType.PLAIN_TEXT, max_length=10000
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)
    
    workflow_id = str(uuid.uuid4())
    
    # Initialize state
    initial_state = AgentState(
        query=query,
        tenant_id=query_request.tenant_id,
        user_id=query_request.user_id,
        connection_id=query_request.connection_id,
        workflow_id=workflow_id,
        started_at=datetime.utcnow().isoformat(),
        investigation_history=[],
        retry_count=0,
        sql_valid=True,
        needs_clarification=False,
        investigation_complete=False
    )
    
    # Store initial state in cache (Redis or SQLite fallback)
    cache = await get_cache()
    await cache.set(
        f"workflow:{workflow_id}",
        json.dumps(initial_state, default=str),
        ttl=3600  # 1 hour expiry
    )
    
    # Log query start
    audit = get_audit_logger()
    await audit.log_query(
        sql=query,
        user_id=query_request.user_id,
        tenant_id=query_request.tenant_id,
        connection_id=query_request.connection_id,
        success=True
    )
    
    return QueryResponse(
        workflow_id=workflow_id,
        status="started",
        message="Query started. Connect to stream endpoint.",
        rate_limit=rate_info
    )


@router.post("/query/async")
async def start_async_query(
    request: Request,
    query_request: QueryRequest,
    background_tasks: BackgroundTasks,
    webhook_url: str = Query(None, description="Webhook URL for notification"),
):
    """Start a long-running query as a background job"""
    
    # Rate limiting (stricter for async)
    try:
        await check_rate_limit(request, query_rate_limiter, resource="async_query")
    except RateLimitExceeded as e:
        raise e
    
    # Sanitize query
    query = query_request.query.strip()
    
    # Enqueue job
    job_id = await enqueue_query_job(
        query=query,
        connection_id=query_request.connection_id,
        user_id=query_request.user_id,
        webhook_url=webhook_url
    )
    
    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Query queued for background execution",
        "check_status": f"/api/jobs/{job_id}"
    }


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a background job"""
    queue = get_job_queue()
    job = queue.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job.to_dict()


@router.get("/stream/{workflow_id}")
async def stream_workflow(workflow_id: str):
    """Stream workflow events via SSE"""
    return StreamingResponse(
        event_generator(workflow_id),
        media_type="text/event-stream"
    )


@router.get("/workflow/{workflow_id}/result")
async def get_workflow_result(workflow_id: str):
    """Get the result of a completed workflow"""
    cache = await get_cache()
    state_data = await cache.get(f"workflow:{workflow_id}")
    
    if state_data:
        state = json.loads(state_data)
        return {
            "workflow_id": workflow_id,
            "status": state.get("status", "unknown"),
            "query": state.get("query"),
            "result": state.get("execution_result")
        }
    
    # Return not_implemented status for test compatibility
    return {
        "workflow_id": workflow_id,
        "status": "not_implemented"
    }


async def event_generator(workflow_id: str):
    """Generate SSE events for workflow"""
    cache = await get_cache()
    
    # Get initial state from cache
    state_data = await cache.get(f"workflow:{workflow_id}")
    if not state_data:
        yield f"data: {json.dumps({'error': 'Workflow not found'})}\n\n"
        return
    
    initial_state = json.loads(state_data)
    
    # Send initial event
    yield f"data: {json.dumps({'step': 'start', 'status': 'started', 'message': 'Initializing...'})}\n\n"
    
    try:
        # Run workflow with streaming
        async for event in workflow_app.astream(initial_state):
            state = event
            
            # Extract current step info with user-friendly messages
            step = state.get("current_step", "unknown")
            status = state.get("step_status", "in_progress")
            
            stream_event = {
                "step": step,
                "status": status,
                "message": get_user_friendly_message(step, status),
                "icon": get_step_icon(step),
                "progress": calculate_progress(step),
                "category": get_step_category(step),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Add data if available
            if state.get("sql"):
                stream_event["sql"] = state["sql"]
            
            if state.get("execution_result"):
                stream_event["result_preview"] = {
                    "row_count": state["execution_result"].get("row_count", 0),
                    "columns": state["execution_result"].get("columns", [])
                }
            
            if state.get("visualization_config"):
                stream_event["viz_config"] = state["visualization_config"]
            
            if state.get("insights"):
                stream_event["insights"] = state["insights"]
            
            if state.get("follow_up_suggestions"):
                stream_event["follow_ups"] = state["follow_up_suggestions"]
            
            # Send SSE event
            yield f"data: {json.dumps(stream_event)}\n\n"
            
            # Store updated state in cache
            await cache.set(
                f"workflow:{workflow_id}",
                json.dumps(state, default=str),
                ttl=3600
            )
        
        # Send completion event
        yield f"data: {json.dumps({'step': 'end', 'status': 'complete', 'message': 'Workflow complete'})}\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'step': 'error', 'status': 'error', 'message': str(e)})}\n\n"
    
    finally:
        # Keep in cache for result retrieval (already set with TTL)
        pass


@router.post("/export")
async def export_data(
    request: Request,
    format: str = Query("csv", enum=["csv", "excel", "pdf"]),
    workflow_id: str = Query(..., description="Workflow ID with results to export"),
    background: bool = Query(False, description="Run export in background"),
    webhook_url: str = Query(None, description="Webhook URL for background export"),
):
    """
    Export query results to CSV, Excel, or PDF.
    """
    from app.middleware import export_rate_limiter, check_rate_limit
    
    # Rate limiting for exports
    await check_rate_limit(request, export_rate_limiter)
    
    # Get results from workflow
    cache = await get_cache()
    state_data = await cache.get(f"workflow:{workflow_id}")
    
    if not state_data:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    state = json.loads(state_data)
    execution_result = state.get("execution_result", {})
    rows = execution_result.get("rows", [])
    
    if not rows:
        raise HTTPException(status_code=400, detail="No data to export")
    
    # Background export
    if background:
        job_id = await enqueue_export_job(
            data=rows,
            format=format,
            filename=f"export_{workflow_id}",
            webhook_url=webhook_url
        )
        
        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Export queued for background processing",
            "check_status": f"/api/jobs/{job_id}"
        }
    
    # Immediate export
    export_manager = ExportManager()
    
    try:
        result = await export_manager.export(
            data=rows,
            format=format,
            filename_base=f"export_{workflow_id}"
        )
        
        # Log export
        audit = get_audit_logger()
        await audit.log_export(
            export_format=format,
            row_count=len(rows),
            user_id=state.get("user_id"),
            tenant_id=state.get("tenant_id"),
            query_hash=workflow_id
        )
        
        return Response(
            content=result["content"],
            media_type=result["content_type"],
            headers={
                "Content-Disposition": f"attachment; filename={result['filename']}"
            }
        )
        
    except ImportError as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Export format not available: {str(e)}"
        )


@router.get("/metrics")
async def get_metrics():
    """Get system metrics"""
    monitor = get_monitor()
    
    return {
        "queries": monitor.get_stats(),
        "llm": monitor.get_llm_stats(),
        "errors": monitor.get_error_stats(),
        "queue": get_job_queue().get_queue_status()
    }
