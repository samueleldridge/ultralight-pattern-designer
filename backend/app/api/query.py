import json
import asyncio
import uuid
from datetime import datetime
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.cache import get_redis
from app.agent.state import AgentState
from app.agent.workflow import workflow_app
from app.agent.messages import (
    get_user_friendly_message, 
    get_step_icon, 
    calculate_progress,
    get_step_category
)
from app.schemas import QueryRequest, QueryResponse, StreamEvent

router = APIRouter(prefix="/api", tags=["query"])


@router.post("/query")
async def start_query(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db)
) -> QueryResponse:
    """Start a new query workflow"""
    
    workflow_id = str(uuid.uuid4())
    
    # Initialize state
    initial_state = AgentState(
        query=request.query,
        tenant_id=request.tenant_id,
        user_id=request.user_id,
        connection_id=request.connection_id,
        workflow_id=workflow_id,
        started_at=datetime.utcnow().isoformat(),
        investigation_history=[],
        retry_count=0,
        sql_valid=True,
        needs_clarification=False,
        investigation_complete=False
    )
    
    # Store initial state in Redis for streaming
    redis = await get_redis()
    await redis.setex(
        f"workflow:{workflow_id}",
        3600,  # 1 hour expiry
        json.dumps(initial_state, default=str)
    )
    
    return QueryResponse(
        workflow_id=workflow_id,
        status="started",
        message="Query started. Connect to stream endpoint."
    )


async def event_generator(workflow_id: str):
    """Generate SSE events for workflow"""
    from app.cache import redis_client
    
    redis = redis_client
    
    # Get initial state
    state_data = await redis.get(f"workflow:{workflow_id}")
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
            
            # Store updated state
            await redis.setex(
                f"workflow:{workflow_id}",
                3600,
                json.dumps(state, default=str)
            )
        
        # Send completion event
        yield f"data: {json.dumps({'step': 'end', 'status': 'complete', 'message': 'Workflow complete'})}\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'step': 'error', 'status': 'error', 'message': str(e)})}\n\n"
    
    finally:
        # Clean up
        await redis.delete(f"workflow:{workflow_id}")


@router.get("/stream/{workflow_id}")
async def stream_workflow(workflow_id: str):
    """Stream workflow events via SSE"""
    return StreamingResponse(
        event_generator(workflow_id),
        media_type="text/event-stream"
    )


@router.get("/workflow/{workflow_id}/result")
async def get_workflow_result(
    workflow_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get final workflow result"""
    
    # TODO: Store and retrieve from database
    return {"workflow_id": workflow_id, "status": "not_implemented"}
