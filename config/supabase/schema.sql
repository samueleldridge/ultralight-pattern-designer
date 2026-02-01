-- ═════════════════════════════════════════════════════════════════════════════
-- AI ANALYTICS PLATFORM - SUPABASE DATABASE SCHEMA
-- ═════════════════════════════════════════════════════════════════════════════
-- Run this in Supabase SQL Editor to set up your database
-- Or use: psql $DATABASE_URL -f config/supabase/schema.sql
-- ═════════════════════════════════════════════════════════════════════════════

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search

-- =============================================================================
-- CORE TABLES
-- =============================================================================

-- Users table (extends Clerk auth)
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clerk_id TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    avatar_url TEXT,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Organizations/Teams
CREATE TABLE IF NOT EXISTS public.organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Organization memberships
CREATE TABLE IF NOT EXISTS public.organization_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'member', -- admin, member, viewer
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(organization_id, user_id)
);

-- =============================================================================
-- DATABASE CONNECTIONS
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.database_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    
    -- Connection details (encrypted at application level)
    host TEXT NOT NULL,
    port INTEGER DEFAULT 5432,
    database TEXT NOT NULL,
    username TEXT NOT NULL,
    -- Password is stored encrypted, not here
    encrypted_password TEXT NOT NULL,
    
    -- SSL/TLS settings
    ssl_mode TEXT DEFAULT 'require',
    
    -- Connection pool settings
    pool_size INTEGER DEFAULT 10,
    max_overflow INTEGER DEFAULT 20,
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    last_connected_at TIMESTAMPTZ,
    connection_error TEXT,
    
    -- Metadata
    db_type TEXT DEFAULT 'postgresql', -- postgresql, mysql, snowflake, bigquery
    db_version TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES public.users(id)
);

-- =============================================================================
-- SCHEMA DISCOVERY & METADATA
-- =============================================================================

-- Tables discovered from connected databases
CREATE TABLE IF NOT EXISTS public.discovered_tables (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    connection_id UUID NOT NULL REFERENCES public.database_connections(id) ON DELETE CASCADE,
    schema_name TEXT NOT NULL DEFAULT 'public',
    table_name TEXT NOT NULL,
    description TEXT,
    row_count BIGINT,
    size_bytes BIGINT,
    
    -- AI-generated metadata
    semantic_name TEXT,
    semantic_description TEXT,
    tags TEXT[],
    
    -- Usage tracking
    query_count INTEGER DEFAULT 0,
    last_queried_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(connection_id, schema_name, table_name)
);

-- Columns discovered from tables
CREATE TABLE IF NOT EXISTS public.discovered_columns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_id UUID NOT NULL REFERENCES public.discovered_tables(id) ON DELETE CASCADE,
    column_name TEXT NOT NULL,
    data_type TEXT NOT NULL,
    is_nullable BOOLEAN DEFAULT true,
    default_value TEXT,
    
    -- Statistics
    distinct_count BIGINT,
    null_count BIGINT,
    sample_values JSONB,
    
    -- AI-generated metadata
    semantic_name TEXT,
    semantic_description TEXT,
    is_primary_key BOOLEAN DEFAULT false,
    is_foreign_key BOOLEAN DEFAULT false,
    foreign_key_table TEXT,
    foreign_key_column TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(table_id, column_name)
);

-- Semantic definitions (business glossary)
CREATE TABLE IF NOT EXISTS public.semantic_definitions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    
    term TEXT NOT NULL,
    definition TEXT NOT NULL,
    category TEXT, -- metric, dimension, filter, etc.
    
    -- Related database objects
    related_tables TEXT[],
    related_columns TEXT[],
    sql_expression TEXT, -- Optional SQL expression
    
    -- Metadata
    synonyms TEXT[],
    examples JSONB,
    
    created_by UUID REFERENCES public.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(organization_id, term)
);

-- =============================================================================
-- QUERY SYSTEM
-- =============================================================================

-- Natural language queries
CREATE TABLE IF NOT EXISTS public.queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.users(id),
    
    -- Query content
    natural_language TEXT NOT NULL,
    generated_sql TEXT,
    
    -- Execution results
    status TEXT DEFAULT 'pending', -- pending, generating, executing, completed, error
    error_message TEXT,
    
    -- Performance metrics
    generation_time_ms INTEGER,
    execution_time_ms INTEGER,
    total_time_ms INTEGER,
    
    -- Results (truncated for storage)
    result_summary JSONB,
    row_count INTEGER,
    
    -- Caching
    cache_hit BOOLEAN DEFAULT false,
    cache_key TEXT,
    
    -- AI metadata
    model_used TEXT,
    tokens_used INTEGER,
    cost_estimate DECIMAL(10,6),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Query execution history
CREATE TABLE IF NOT EXISTS public.query_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_id UUID NOT NULL REFERENCES public.queries(id) ON DELETE CASCADE,
    
    execution_timestamp TIMESTAMPTZ DEFAULT NOW(),
    duration_ms INTEGER,
    rows_returned INTEGER,
    was_cached BOOLEAN DEFAULT false,
    error_occurred BOOLEAN DEFAULT false,
    error_message TEXT
);

-- Query feedback for few-shot learning
CREATE TABLE IF NOT EXISTS public.query_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_id UUID NOT NULL REFERENCES public.queries(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.users(id),
    
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    feedback_text TEXT,
    corrected_sql TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Saved queries (favorites)
CREATE TABLE IF NOT EXISTS public.saved_queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.users(id),
    
    name TEXT NOT NULL,
    description TEXT,
    natural_language TEXT NOT NULL,
    generated_sql TEXT,
    
    -- Visualization preferences
    visualization_type TEXT DEFAULT 'table', -- table, line, bar, pie, metric
    visualization_config JSONB DEFAULT '{}',
    
    -- Sharing
    is_shared BOOLEAN DEFAULT false,
    share_token TEXT UNIQUE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- DASHBOARDS
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.dashboards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    created_by UUID NOT NULL REFERENCES public.users(id),
    
    name TEXT NOT NULL,
    description TEXT,
    
    -- Layout configuration
    layout JSONB DEFAULT '{}',
    
    -- Sharing
    is_public BOOLEAN DEFAULT false,
    share_token TEXT UNIQUE,
    
    -- Activity
    view_count INTEGER DEFAULT 0,
    last_viewed_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Dashboard widgets
CREATE TABLE IF NOT EXISTS public.dashboard_widgets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dashboard_id UUID NOT NULL REFERENCES public.dashboards(id) ON DELETE CASCADE,
    
    widget_type TEXT NOT NULL, -- chart, table, metric, text
    title TEXT NOT NULL,
    position JSONB NOT NULL, -- {x, y, w, h}
    
    -- Data source
    saved_query_id UUID REFERENCES public.saved_queries(id),
    custom_config JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- AI AGENT & INSIGHTS
-- =============================================================================

-- Proactive insights
CREATE TABLE IF NOT EXISTS public.proactive_insights (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    
    insight_type TEXT NOT NULL, -- anomaly, trend, recommendation
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    
    -- Data context
    affected_connection_id UUID REFERENCES public.database_connections(id),
    affected_tables TEXT[],
    
    -- Severity
    severity TEXT DEFAULT 'info', -- info, warning, critical
    
    -- Status
    is_read BOOLEAN DEFAULT false,
    dismissed_at TIMESTAMPTZ,
    dismissed_by UUID REFERENCES public.users(id),
    
    -- Query for details
    related_query_id UUID REFERENCES public.queries(id),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent conversations
CREATE TABLE IF NOT EXISTS public.agent_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.users(id),
    
    title TEXT,
    
    -- Context
    connection_id UUID REFERENCES public.database_connections(id),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent messages
CREATE TABLE IF NOT EXISTS public.agent_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES public.agent_conversations(id) ON DELETE CASCADE,
    
    role TEXT NOT NULL, -- user, assistant, system
    content TEXT NOT NULL,
    
    -- For assistant messages
    sql_generated TEXT,
    results JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- RAG / DOCUMENT SYSTEM
-- =============================================================================

-- Document uploads
CREATE TABLE IF NOT EXISTS public.documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    uploaded_by UUID NOT NULL REFERENCES public.users(id),
    
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size_bytes BIGINT,
    storage_path TEXT NOT NULL,
    
    -- Processing status
    status TEXT DEFAULT 'pending', -- pending, processing, completed, error
    processing_error TEXT,
    
    -- Extracted content
    extracted_text TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Document chunks for RAG
CREATE TABLE IF NOT EXISTS public.document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    
    -- Vector embedding for semantic search
    embedding VECTOR(1536), -- Adjust dimension based on your embedding model
    
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(document_id, chunk_index)
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- Users & Organizations
CREATE INDEX idx_users_clerk_id ON public.users(clerk_id);
CREATE INDEX idx_users_email ON public.users(email);
CREATE INDEX idx_org_members_org ON public.organization_members(organization_id);
CREATE INDEX idx_org_members_user ON public.organization_members(user_id);

-- Database Connections
CREATE INDEX idx_connections_org ON public.database_connections(organization_id);
CREATE INDEX idx_connections_active ON public.database_connections(is_active);

-- Schema Discovery
CREATE INDEX idx_discovered_tables_connection ON public.discovered_tables(connection_id);
CREATE INDEX idx_discovered_tables_name ON public.discovered_tables(table_name);
CREATE INDEX idx_discovered_columns_table ON public.discovered_columns(table_id);
CREATE INDEX idx_semantic_defs_org ON public.semantic_definitions(organization_id);

-- Queries
CREATE INDEX idx_queries_org ON public.queries(organization_id);
CREATE INDEX idx_queries_user ON public.queries(user_id);
CREATE INDEX idx_queries_status ON public.queries(status);
CREATE INDEX idx_queries_created ON public.queries(created_at DESC);
CREATE INDEX idx_saved_queries_org ON public.saved_queries(organization_id);

-- Dashboards
CREATE INDEX idx_dashboards_org ON public.dashboards(organization_id);

-- Insights & Conversations
CREATE INDEX idx_insights_org ON public.proactive_insights(organization_id);
CREATE INDEX idx_insights_unread ON public.proactive_insights(organization_id, is_read) WHERE is_read = false;
CREATE INDEX idx_conversations_org ON public.agent_conversations(organization_id);
CREATE INDEX idx_conversations_user ON public.agent_conversations(user_id);

-- RAG
CREATE INDEX idx_documents_org ON public.documents(organization_id);
CREATE INDEX idx_document_chunks_doc ON public.document_chunks(document_id);
CREATE INDEX idx_document_chunks_embedding ON public.document_chunks USING ivfflat (embedding vector_cosine_ops);

-- =============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- =============================================================================

-- Enable RLS on all tables
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.organization_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.database_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.discovered_tables ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.discovered_columns ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.semantic_definitions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.queries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.saved_queries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dashboards ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dashboard_widgets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.proactive_insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_chunks ENABLE ROW LEVEL SECURITY;

-- Organizations: Users can view organizations they belong to
CREATE POLICY org_select_policy ON public.organizations
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.organization_members 
            WHERE organization_id = organizations.id 
            AND user_id = auth.uid()
        )
    );

-- Database Connections: Members can view connections in their org
CREATE POLICY connections_select_policy ON public.database_connections
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.organization_members 
            WHERE organization_id = database_connections.organization_id 
            AND user_id = auth.uid()
        )
    );

-- Queries: Users can view queries in their org
CREATE POLICY queries_select_policy ON public.queries
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.organization_members 
            WHERE organization_id = queries.organization_id 
            AND user_id = auth.uid()
        )
    );

-- Dashboards: Users can view dashboards in their org
CREATE POLICY dashboards_select_policy ON public.dashboards
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.organization_members 
            WHERE organization_id = dashboards.organization_id 
            AND user_id = auth.uid()
        )
    );

-- =============================================================================
-- FUNCTIONS & TRIGGERS
-- =============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply auto-update to all tables with updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON public.organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_connections_updated_at BEFORE UPDATE ON public.database_connections
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_discovered_tables_updated_at BEFORE UPDATE ON public.discovered_tables
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_discovered_columns_updated_at BEFORE UPDATE ON public.discovered_columns
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_queries_updated_at BEFORE UPDATE ON public.queries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_saved_queries_updated_at BEFORE UPDATE ON public.saved_queries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_dashboards_updated_at BEFORE UPDATE ON public.dashboards
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Semantic search function for document chunks
CREATE OR REPLACE FUNCTION match_document_chunks(
    query_embedding VECTOR(1536),
    match_threshold FLOAT,
    match_count INT,
    p_organization_id UUID
)
RETURNS TABLE (
    id UUID,
    document_id UUID,
    content TEXT,
    similarity FLOAT
)
LANGUAGE SQL STABLE
AS $$
    SELECT 
        dc.id,
        dc.document_id,
        dc.content,
        1 - (dc.embedding <=> query_embedding) AS similarity
    FROM public.document_chunks dc
    JOIN public.documents d ON dc.document_id = d.id
    WHERE d.organization_id = p_organization_id
    AND 1 - (dc.embedding <=> query_embedding) > match_threshold
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
$$;

-- =============================================================================
-- SCHEMA COMPLETE
-- =============================================================================

-- Verify extensions are enabled
SELECT 'Extensions enabled' as status;
SELECT extname FROM pg_extension WHERE extname IN ('uuid-ossp', 'pgvector', 'pg_trgm');
