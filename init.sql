-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Tenants (SaaS multi-tenant)
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Database connections (customer DBs)
CREATE TABLE IF NOT EXISTS db_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    name TEXT NOT NULL,
    connection_string_encrypted TEXT NOT NULL,
    db_type VARCHAR(20) DEFAULT 'postgresql',
    schema_cache JSONB,
    last_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Dashboards
CREATE TABLE IF NOT EXISTS dashboards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    user_id UUID REFERENCES users(id),
    name TEXT NOT NULL,
    description TEXT,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Views (saved visualizations)
CREATE TABLE IF NOT EXISTS views (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    user_id UUID REFERENCES users(id),
    dashboard_id UUID REFERENCES dashboards(id),
    title TEXT NOT NULL,
    query_text TEXT NOT NULL,
    generated_sql TEXT,
    viz_config JSONB,
    refresh_schedule VARCHAR(20) DEFAULT 'manual',
    last_refreshed_at TIMESTAMPTZ,
    cached_data JSONB,
    position_x INT DEFAULT 0,
    position_y INT DEFAULT 0,
    width INT DEFAULT 6,
    height INT DEFAULT 4,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Question history (with vector search)
CREATE TABLE IF NOT EXISTS question_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    user_id UUID REFERENCES users(id),
    question_text TEXT NOT NULL,
    question_embedding VECTOR(1536),
    intent_category VARCHAR(50),
    topics TEXT[],
    entities TEXT[],
    generated_sql TEXT,
    result_summary JSONB,
    chart_type VARCHAR(20),
    user_action VARCHAR(20) DEFAULT 'viewed',
    session_duration_seconds INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User profiles
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    user_id UUID REFERENCES users(id) UNIQUE,
    top_topics JSONB DEFAULT '[]',
    preferred_metrics JSONB DEFAULT '[]',
    preferred_chart_types JSONB DEFAULT '[]',
    active_hours INT[] DEFAULT '{}',
    active_days INT[] DEFAULT '{}',
    total_questions INT DEFAULT 0,
    saved_views INT DEFAULT 0,
    inferred_role VARCHAR(50),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Proactive insights
CREATE TABLE IF NOT EXISTS proactive_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    user_id UUID REFERENCES users(id),
    insight_type VARCHAR(50),
    title TEXT NOT NULL,
    description TEXT,
    relevant_metric VARCHAR(100),
    metric_value DECIMAL,
    change_percent DECIMAL,
    suggested_question TEXT,
    generated_sql TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    delivered_at TIMESTAMPTZ,
    viewed_at TIMESTAMPTZ,
    user_feedback VARCHAR(20),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_question_embedding ON question_history 
    USING ivfflat (question_embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_question_history_user ON question_history(tenant_id, user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_proactive_insights_user ON proactive_insights(user_id, status);
CREATE INDEX IF NOT EXISTS idx_views_dashboard ON views(dashboard_id);
