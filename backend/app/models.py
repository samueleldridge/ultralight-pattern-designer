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


# Additional models from subagent work
class Tenant(Base):
    """Organization/tenant model"""
    __tablename__ = "tenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    plan = Column(String, default="free")  # free, pro, enterprise
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class User(Base):
    """User account model"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    email = Column(String, unique=True, nullable=False)
    name = Column(String)
    role = Column(String, default="member")  # admin, member, viewer
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    last_login = Column(DateTime(timezone=True))


class QuestionHistory(Base):
    """Stores user query history"""
    __tablename__ = "question_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    question = Column(Text, nullable=False)
    sql_generated = Column(Text)
    results_summary = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    execution_time_ms = Column(Integer)


class UserProfile(Base):
    """User preferences and behavioral patterns"""
    __tablename__ = "user_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    preferences = Column(JSON)
    common_queries = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class DBConnection(Base):
    """Database connection configuration"""
    __tablename__ = "db_connections"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    db_type = Column(String, nullable=False)  # postgresql, mysql, etc.
    host = Column(String)
    port = Column(Integer)
    database = Column(String)
    username = Column(String)
    encrypted_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class Dashboard(Base):
    """Saved dashboards"""
    __tablename__ = "dashboards"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    config = Column(JSON)  # Dashboard layout and widgets
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class DashboardView(Base):
    """Individual views/widgets within a dashboard"""
    __tablename__ = "dashboard_views"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    dashboard_id = Column(UUID(as_uuid=True), ForeignKey("dashboards.id"), nullable=False)
    name = Column(String, nullable=False)
    view_type = Column(String, nullable=False)  # chart, table, metric
    config = Column(JSON)  # View-specific configuration
    query_sql = Column(Text)
    position = Column(JSON)  # x, y, width, height
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class ProactiveInsight(Base):
    """AI-generated insights"""
    __tablename__ = "proactive_insights"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    insight_type = Column(String)  # trend, anomaly, recommendation
    severity = Column(String)  # low, medium, high
    related_query = Column(Text)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


# Alias for backwards compatibility
DatabaseConnection = DBConnection
View = DashboardView
