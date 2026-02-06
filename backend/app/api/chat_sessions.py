"""
Chat Sessions API

Endpoints:
- POST /api/chat/sessions - Create new session
- GET /api/chat/sessions - List user sessions
- GET /api/chat/sessions/:id - Get session with messages
- GET /api/chat/sessions/:id/messages - Get session messages
- POST /api/chat/sessions/:id/messages - Add message
- PUT /api/chat/sessions/:id/title - Update title
- POST /api/chat/sessions/:id/archive - Archive session
- DELETE /api/chat/sessions/:id - Delete session
- GET /api/chat/sessions/:id/context - Get LLM context
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime

from app.services.chat_sessions import get_chat_session_service, ChatSession, ChatMessage
from app.middleware import get_current_user

router = APIRouter(prefix="/api/chat", tags=["chat_sessions"])


# Request/Response Models
class CreateSessionRequest(BaseModel):
    title: Optional[str] = None


class CreateMessageRequest(BaseModel):
    role: str  # user, assistant
    content: str
    sql_generated: Optional[str] = None
    query_results: Optional[dict] = None
    chart_type: Optional[str] = None
    execution_time_ms: Optional[int] = None


class UpdateTitleRequest(BaseModel):
    title: str


class SessionResponse(BaseModel):
    id: str
    title: str
    summary: Optional[str]
    status: str
    message_count: int
    created_at: datetime
    updated_at: datetime
    last_message_at: Optional[datetime]


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    sql_generated: Optional[str]
    chart_type: Optional[str]
    execution_time_ms: Optional[int]
    created_at: datetime
    sequence_number: int


class SessionDetailResponse(BaseModel):
    id: str
    title: str
    summary: Optional[str]
    status: str
    message_count: int
    entities_discussed: List[str]
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse]


# Services
_session_service = None


def get_session_service():
    global _session_service
    if _session_service is None:
        _session_service = get_chat_session_service()
    return _session_service


@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    request: CreateSessionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new chat session"""
    service = get_session_service()
    
    session = await service.create_session(
        user_id=current_user["id"],
        tenant_id=current_user["tenant_id"],
        title=request.title
    )
    
    return SessionResponse(
        id=session.id,
        title=session.title,
        summary=session.summary,
        status=session.status,
        message_count=session.message_count,
        created_at=session.created_at,
        updated_at=session.updated_at,
        last_message_at=session.last_message_at
    )


@router.get("/sessions", response_model=List[SessionResponse])
async def list_sessions(
    limit: int = 20,
    include_archived: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """Get all chat sessions for the current user"""
    service = get_session_service()
    
    sessions = await service.get_user_sessions(
        user_id=current_user["id"],
        tenant_id=current_user["tenant_id"],
        limit=limit,
        include_archived=include_archived
    )
    
    return [
        SessionResponse(
            id=s.id,
            title=s.title,
            summary=s.summary,
            status=s.status,
            message_count=s.message_count,
            created_at=s.created_at,
            updated_at=s.updated_at,
            last_message_at=s.last_message_at
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific session with all messages"""
    service = get_session_service()
    
    session = await service.get_session(
        session_id=session_id,
        user_id=current_user["id"],
        tenant_id=current_user["tenant_id"]
    )
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get messages
    messages = await service.get_session_messages(
        session_id=session_id,
        user_id=current_user["id"],
        tenant_id=current_user["tenant_id"]
    )
    
    return SessionDetailResponse(
        id=session.id,
        title=session.title,
        summary=session.summary,
        status=session.status,
        message_count=session.message_count,
        entities_discussed=session.entities_discussed or [],
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=[
            MessageResponse(
                id=m.id,
                role=m.role,
                content=m.content,
                sql_generated=m.sql_generated,
                chart_type=m.chart_type,
                execution_time_ms=m.execution_time_ms,
                created_at=m.created_at,
                sequence_number=m.sequence_number
            )
            for m in messages
        ]
    )


@router.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
async def get_session_messages(
    session_id: str,
    limit: int = 100,
    current_user: dict = Depends(get_current_user)
):
    """Get messages for a specific session"""
    service = get_session_service()
    
    messages = await service.get_session_messages(
        session_id=session_id,
        user_id=current_user["id"],
        tenant_id=current_user["tenant_id"],
        limit=limit
    )
    
    return [
        MessageResponse(
            id=m.id,
            role=m.role,
            content=m.content,
            sql_generated=m.sql_generated,
            chart_type=m.chart_type,
            execution_time_ms=m.execution_time_ms,
            created_at=m.created_at,
            sequence_number=m.sequence_number
        )
        for m in messages
    ]


@router.post("/sessions/{session_id}/messages", response_model=MessageResponse)
async def add_message(
    session_id: str,
    request: CreateMessageRequest,
    current_user: dict = Depends(get_current_user)
):
    """Add a message to a session"""
    service = get_session_service()
    
    # Verify session ownership
    session = await service.get_session(
        session_id=session_id,
        user_id=current_user["id"],
        tenant_id=current_user["tenant_id"]
    )
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.status != "active":
        raise HTTPException(status_code=400, detail="Session is not active")
    
    message = await service.add_message(
        session_id=session_id,
        role=request.role,
        content=request.content,
        sql_generated=request.sql_generated,
        query_results=request.query_results,
        chart_type=request.chart_type,
        execution_time_ms=request.execution_time_ms
    )
    
    return MessageResponse(
        id=message.id,
        role=message.role,
        content=message.content,
        sql_generated=message.sql_generated,
        chart_type=message.chart_type,
        execution_time_ms=message.execution_time_ms,
        created_at=message.created_at,
        sequence_number=message.sequence_number
    )


@router.put("/sessions/{session_id}/title")
async def update_session_title(
    session_id: str,
    request: UpdateTitleRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update session title"""
    service = get_session_service()
    
    success = await service.update_session_title(
        session_id=session_id,
        user_id=current_user["id"],
        title=request.title
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"status": "updated", "title": request.title}


@router.post("/sessions/{session_id}/archive")
async def archive_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Archive a session"""
    service = get_session_service()
    
    success = await service.archive_session(
        session_id=session_id,
        user_id=current_user["id"]
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"status": "archived", "session_id": session_id}


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete (soft delete) a session"""
    service = get_session_service()
    
    success = await service.delete_session(
        session_id=session_id,
        user_id=current_user["id"]
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"status": "deleted", "session_id": session_id}


@router.get("/sessions/{session_id}/context")
async def get_session_context(
    session_id: str,
    max_messages: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Get recent messages formatted for LLM context"""
    service = get_session_service()
    
    context = await service.get_context_for_llm(
        session_id=session_id,
        user_id=current_user["id"],
        tenant_id=current_user["tenant_id"],
        max_messages=max_messages
    )
    
    return {
        "session_id": session_id,
        "context": context,
        "message_count": len(context)
    }


@router.post("/sessions/{session_id}/continue")
async def continue_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Resume an archived session"""
    from app.database import AsyncSessionLocal
    from sqlalchemy import select, and_
    from app.services.chat_sessions import ChatSession
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ChatSession).where(
                and_(
                    ChatSession.id == session_id,
                    ChatSession.user_id == current_user["id"]
                )
            )
        )
        
        chat_session = result.scalar_one_or_none()
        if not chat_session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        chat_session.status = "active"
        chat_session.updated_at = datetime.utcnow()
        await session.commit()
        
        return {"status": "active", "session_id": session_id}
