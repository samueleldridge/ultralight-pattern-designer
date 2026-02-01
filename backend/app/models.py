from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Text, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
from datetime import datetime

# Document RAG models
class Document(Base):
    """Uploaded documents for RAG"""
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    content_type = Column(String(50))  # pdf, txt, md, etc.
    chunk_count = Column(Integer, default=0)
    file_size = Column(Integer)  # bytes
    meta_data = Column(JSON)  # Renamed from 'metadata' (reserved in SQLAlchemy)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class DocumentChunk(Base):
    """Individual chunks of documents for vector search"""
    __tablename__ = "document_chunks"
    
    id = Column(String, primary_key=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    embedding = Column(Text)  # Store as text for SQLite compatibility
    meta_data = Column(JSON)  # Renamed from 'metadata'
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
