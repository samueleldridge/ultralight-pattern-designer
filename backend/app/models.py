from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Text, Float, Boolean, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
from datetime import datetime
import uuid

# Document RAG models
class Document(Base):
    """Uploaded documents for RAG"""
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    content_type = Column(String(50))  # pdf, txt, md, etc.
    chunk_count = Column(Integer, default=0)
    file_size = Column(Integer)  # bytes
    meta_data = Column(JSON)  # Renamed from 'metadata' (reserved in SQLAlchemy)
    uploaded_by = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class DocumentChunk(Base):
    """Individual chunks of documents for vector search"""
    __tablename__ = "document_chunks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    embedding = Column(Text)  # Store as text for SQLite compatibility
    meta_data = Column(JSON)  # Renamed from 'metadata'
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class Tenant(Base):
    """Tenant/Organization model"""
    __tablename__ = "tenants"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    plan = Column(String, default="free")  # free, pro, enterprise
    settings = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False)
    name = Column(String)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    role = Column(String, default="member")  # admin, member, viewer
    preferences = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    last_active_at = Column(DateTime(timezone=True))


class QuestionHistory(Base):
    """History of questions asked by users"""
    __tablename__ = "question_history"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Question details
    question_text = Column(Text, nullable=False)
    question_embedding = Column(Text)  # Store as text for SQLite compatibility
    
    # Classification
    intent_category = Column(String)  # simple, complex, investigate, clarify
    topics = Column(JSON, default=list)  # List of topics
    entities = Column(JSON, default=list)  # List of entities found
    
    # Generated SQL and results
    generated_sql = Column(Text)
    result_summary = Column(JSON)  # Summary of results
    chart_type = Column(String)  # line, bar, table, pie, metric
    
    # User interaction
    user_action = Column(String, default="viewed")  # viewed, saved, shared, exported
    is_favorite = Column(Boolean, default=False)
    
    # Metadata
    execution_time_ms = Column(Integer)
    row_count = Column(Integer)
    error_message = Column(Text)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class UserProfile(Base):
    """User preferences and behavioral patterns"""
    __tablename__ = "user_profiles"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    
    # Preferences
    top_topics = Column(JSON, default=list)  # ["revenue", "sales"]
    preferred_metrics = Column(JSON, default=list)  # ["total_revenue", "active_users"]
    preferred_chart_types = Column(JSON, default=list)  # ["line", "bar"]
    preferred_time_ranges = Column(JSON, default=list)  # ["last_30_days", "this_month"]
    
    # Behavioral patterns
    active_hours = Column(JSON)  # {"peak": [9, 10, 14], "timezone": "UTC"}
    query_patterns = Column(JSON)  # {"avg_complexity": 0.7, "favorite_tables": ["orders"]}
    
    # Inferred attributes
    inferred_role = Column(String)  # "analyst", "executive", "manager"
    inferred_expertise = Column(String)  # "beginner", "intermediate", "expert"
    
    # Engagement
    total_queries = Column(Integer, default=0)
    last_query_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class DatabaseConnection(Base):
    """Database connection configurations"""
    __tablename__ = "database_connections"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    
    # Connection details
    connection_type = Column(String, default="postgresql")  # postgresql, mysql, etc.
    host = Column(String, nullable=False)
    port = Column(Integer, nullable=False)
    database = Column(String, nullable=False)
    username = Column(String, nullable=False)
    password_encrypted = Column(Text)  # Encrypted password
    
    # SSL and options
    ssl_mode = Column(String, default="prefer")
    connection_options = Column(JSON, default={})
    
    # Status
    status = Column(String, default="pending")  # pending, connected, error
    last_tested_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    
    # Schema cache
    schema_cache = Column(JSON)
    schema_cached_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class Dashboard(Base):
    """Saved dashboards"""
    __tablename__ = "dashboards"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    
    name = Column(String, nullable=False)
    description = Column(Text)
    is_default = Column(Boolean, default=False)
    is_shared = Column(Boolean, default=False)
    
    layout_config = Column(JSON, default={})
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class DashboardView(Base):
    """Individual views/widgets within a dashboard"""
    __tablename__ = "dashboard_views"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    dashboard_id = Column(String, ForeignKey("dashboards.id"), nullable=False)
    
    title = Column(String, nullable=False)
    query_text = Column(Text, nullable=False)
    
    # Position and size
    position_x = Column(Integer, default=0)
    position_y = Column(Integer, default=0)
    width = Column(Integer, default=6)
    height = Column(Integer, default=4)
    
    # Visualization
    chart_type = Column(String, default="line")
    viz_config = Column(JSON, default={})
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class ProactiveInsight(Base):
    """AI-generated proactive insights for users"""
    __tablename__ = "proactive_insights"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Insight details
    insight_type = Column(String, nullable=False)  # anomaly, trend, pattern, correlation, reminder, suggestion
    priority = Column(String, default="medium")  # high, medium, low
    title = Column(String, nullable=False)
    description = Column(Text)
    
    # Suggested action
    suggested_query = Column(Text)
    action_type = Column(String)  # run_query, view_dashboard, explore
    
    # Data context
    data_context = Column(JSON)  # Supporting data for the insight
    related_metrics = Column(JSON, default=list)
    
    # Delivery status
    status = Column(String, default="pending")  # pending, delivered, dismissed, acted_upon
    delivered_at = Column(DateTime(timezone=True))
    dismissed_at = Column(DateTime(timezone=True))
    
    # User feedback
    was_helpful = Column(Boolean)
    feedback_text = Column(Text)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True))  # When this insight becomes irrelevant


# Alias for DatabaseConnection used in intelligence module
DBConnection = DatabaseConnection

# Alias for DashboardView used in intelligence module
View = DashboardView