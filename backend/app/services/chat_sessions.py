"""
Chat Session Management

Tracks complete chat sessions with full message history.
Enables:
- Previous chat sessions list
- Resume a past session
- View full conversation history
- Multi-turn context for LLM
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from enum import Enum
import json
import hashlib
import uuid

from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, JSON, ForeignKey
from sqlalchemy import select, desc, and_, func
from sqlalchemy.orm import relationship
from app.database import Base, AsyncSessionLocal


class ChatSession(Base):
    """A chat session containing multiple messages"""
    __tablename__ = "chat_sessions"
    
    id = Column(String, primary_key=True)  # UUID
    user_id = Column(String, index=True, nullable=False)
    tenant_id = Column(String, index=True, nullable=False)
    
    # Session metadata
    title = Column(String)  # Auto-generated or user-set
    summary = Column(Text)  # AI-generated summary of the session
    
    # Status
    status = Column(String, default="active")  # active, archived, deleted
    
    # Message counts
    message_count = Column(Integer, default=0)
    user_message_count = Column(Integer, default=0)
    assistant_message_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_message_at = Column(DateTime)
    
    # Context for resuming
    context_summary = Column(Text)  # Key facts from conversation
    entities_discussed = Column(JSON, default=list)  # ["LBG", "revenue"]
    
    # Relationships
    messages = relationship("ChatMessage", back_populates="session", order_by="ChatMessage.created_at")


class ChatMessage(Base):
    """Individual message within a chat session"""
    __tablename__ = "chat_messages"
    
    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("chat_sessions.id"), index=True, nullable=False)
    
    # Message details
    role = Column(String, nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    
    # For assistant messages - execution details
    sql_generated = Column(Text)
    query_results = Column(JSON)  # Full result data
    chart_type = Column(String)
    execution_time_ms = Column(Integer)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    sequence_number = Column(Integer)  # Order within session
    
    # Relationships
    session = relationship("ChatSession", back_populates="messages")


class ChatSessionService:
    """Service for managing chat sessions"""
    
    async def create_session(
        self,
        user_id: str,
        tenant_id: str,
        title: Optional[str] = None
    ) -> ChatSession:
        """Create a new chat session"""
        
        async with AsyncSessionLocal() as session:
            chat_session = ChatSession(
                id=str(uuid.uuid4()),
                user_id=user_id,
                tenant_id=tenant_id,
                title=title or "New Chat",
                status="active"
            )
            
            session.add(chat_session)
            await session.commit()
            
            return chat_session
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        sql_generated: Optional[str] = None,
        query_results: Optional[Dict] = None,
        chart_type: Optional[str] = None,
        execution_time_ms: Optional[int] = None
    ) -> ChatMessage:
        """Add a message to a session"""
        
        async with AsyncSessionLocal() as session:
            # Get current message count for sequence number
            result = await session.execute(
                select(func.count(ChatMessage.id)).where(
                    ChatMessage.session_id == session_id
                )
            )
            sequence = result.scalar() or 0
            
            # Create message
            message = ChatMessage(
                id=str(uuid.uuid4()),
                session_id=session_id,
                role=role,
                content=content,
                sql_generated=sql_generated,
                query_results=query_results,
                chart_type=chart_type,
                execution_time_ms=execution_time_ms,
                sequence_number=sequence
            )
            
            session.add(message)
            
            # Update session
            chat_session = await session.get(ChatSession, session_id)
            if chat_session:
                chat_session.message_count = sequence + 1
                if role == "user":
                    chat_session.user_message_count += 1
                elif role == "assistant":
                    chat_session.assistant_message_count += 1
                chat_session.last_message_at = datetime.utcnow()
                chat_session.updated_at = datetime.utcnow()
                
                # Auto-generate title from first user message
                if sequence == 0 and role == "user" and not chat_session.title:
                    chat_session.title = content[:50] + ("..." if len(content) > 50 else "")
            
            await session.commit()
            
            return message
    
    async def get_session(
        self,
        session_id: str,
        user_id: str,
        tenant_id: str
    ) -> Optional[ChatSession]:
        """Get a specific session with all messages"""
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ChatSession).where(
                    and_(
                        ChatSession.id == session_id,
                        ChatSession.user_id == user_id,
                        ChatSession.tenant_id == tenant_id
                    )
                )
            )
            
            return result.scalar_one_or_none()
    
    async def get_user_sessions(
        self,
        user_id: str,
        tenant_id: str,
        limit: int = 20,
        include_archived: bool = False
    ) -> List[ChatSession]:
        """Get all sessions for a user"""
        
        async with AsyncSessionLocal() as session:
            query = select(ChatSession).where(
                and_(
                    ChatSession.user_id == user_id,
                    ChatSession.tenant_id == tenant_id
                )
            )
            
            if not include_archived:
                query = query.where(ChatSession.status == "active")
            
            query = query.order_by(desc(ChatSession.last_message_at))
            query = query.limit(limit)
            
            result = await session.execute(query)
            return result.scalars().all()
    
    async def get_session_messages(
        self,
        session_id: str,
        user_id: str,
        tenant_id: str,
        limit: int = 100
    ) -> List[ChatMessage]:
        """Get messages for a specific session"""
        
        async with AsyncSessionLocal() as session:
            # Verify ownership
            session_check = await session.execute(
                select(ChatSession).where(
                    and_(
                        ChatSession.id == session_id,
                        ChatSession.user_id == user_id,
                        ChatSession.tenant_id == tenant_id
                    )
                )
            )
            
            if not session_check.scalar_one_or_none():
                return []
            
            # Get messages
            result = await session.execute(
                select(ChatMessage).where(
                    ChatMessage.session_id == session_id
                ).order_by(
                    ChatMessage.sequence_number
                ).limit(limit)
            )
            
            return result.scalars().all()
    
    async def update_session_title(
        self,
        session_id: str,
        user_id: str,
        title: str
    ) -> bool:
        """Update session title"""
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ChatSession).where(
                    and_(
                        ChatSession.id == session_id,
                        ChatSession.user_id == user_id
                    )
                )
            )
            
            chat_session = result.scalar_one_or_none()
            if not chat_session:
                return False
            
            chat_session.title = title
            await session.commit()
            
            return True
    
    async def archive_session(
        self,
        session_id: str,
        user_id: str
    ) -> bool:
        """Archive a session"""
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ChatSession).where(
                    and_(
                        ChatSession.id == session_id,
                        ChatSession.user_id == user_id
                    )
                )
            )
            
            chat_session = result.scalar_one_or_none()
            if not chat_session:
                return False
            
            chat_session.status = "archived"
            await session.commit()
            
            return True
    
    async def delete_session(
        self,
        session_id: str,
        user_id: str
    ) -> bool:
        """Soft delete a session"""
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ChatSession).where(
                    and_(
                        ChatSession.id == session_id,
                        ChatSession.user_id == user_id
                    )
                )
            )
            
            chat_session = result.scalar_one_or_none()
            if not chat_session:
                return False
            
            chat_session.status = "deleted"
            await session.commit()
            
            return True
    
    async def get_context_for_llm(
        self,
        session_id: str,
        user_id: str,
        tenant_id: str,
        max_messages: int = 10
    ) -> List[Dict[str, str]]:
        """Get recent messages formatted for LLM context"""
        
        messages = await self.get_session_messages(session_id, user_id, tenant_id, limit=max_messages)
        
        # Format for LLM
        context = []
        for msg in messages:
            context.append({
                "role": msg.role,
                "content": msg.content
            })
        
        return context


# Singleton instance
_session_service: Optional[ChatSessionService] = None


def get_chat_session_service() -> ChatSessionService:
    """Get or create chat session service"""
    global _session_service
    if _session_service is None:
        _session_service = ChatSessionService()
    return _session_service
