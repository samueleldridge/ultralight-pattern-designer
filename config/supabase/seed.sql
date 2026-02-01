-- ═════════════════════════════════════════════════════════════════════════════
-- AI ANALYTICS PLATFORM - SEED DATA
-- ═════════════════════════════════════════════════════════════════════════════
-- This script populates the database with demo data for testing
-- Run after schema.sql: psql $DATABASE_URL -f config/supabase/seed.sql
-- ═════════════════════════════════════════════════════════════════════════════

-- =============================================================================
-- DEMO ORGANIZATION & USERS
-- =============================================================================

-- Insert demo organization
INSERT INTO public.organizations (id, name, slug, settings)
VALUES (
    '11111111-1111-1111-1111-111111111111',
    'Acme Corporation',
    'acme-corp',
    '{"industry": "Technology", "size": "50-200"}'::jsonb
) ON CONFLICT DO NOTHING;

-- Insert demo users (in real usage, these come from Clerk webhooks)
INSERT INTO public.users (id, clerk_id, email, full_name, preferences)
VALUES 
    (
        '21111111-1111-1111-1111-111111111111',
        'user_demo_admin_001',
        'admin@acme.com',
        'Admin User',
        '{"theme": "dark", "default_connection": "31111111-1111-1111-1111-111111111111"}'::jsonb
    ),
    (
        '21111111-1111-1111-1111-111111111112',
        'user_demo_analyst_001',
        'analyst@acme.com',
        'Data Analyst',
        '{"theme": "light"}'::jsonb
    )
ON CONFLICT DO NOTHING;

-- Link users to organization
INSERT INTO public.organization_members (organization_id, user_id, role)
VALUES 
    ('11111111-1111-1111-1111-111111111111', '21111111-1111-1111-1111-111111111111', 'admin'),
    ('11111111-1111-1111-1111-111111111111', '21111111-1111-1111-1111-111111111112', 'member')
ON CONFLICT DO NOTHING;

-- =============================================================================
-- DEMO DATABASE CONNECTION
-- =============================================================================

INSERT INTO public.database_connections (
    id, organization_id, name, description, 
    host, port, database, username, encrypted_password,
    db_type, is_active, created_by
)
VALUES (
    '31111111-1111-1111-1111-111111111111',
    '11111111-1111-1111-1111-111111111111',
    'Production Analytics DB',
    'Main PostgreSQL database for analytics queries',
    'db.acme-analytics.internal',
    5432,
    'analytics_production',
    'analytics_readonly',
    'encrypted:your-encrypted-password-here',
    'postgresql',
    true,
    '21111111-1111-1111-1111-111111111111'
) ON CONFLICT DO NOTHING;

-- =============================================================================
-- DEMO SCHEMA DISCOVERY (E-commerce Dataset)
-- =============================================================================

-- Insert demo tables
INSERT INTO public.discovered_tables (
    id, connection_id, schema_name, table_name, description,
    semantic_name, semantic_description, tags, row_count
)
VALUES 
    (
        '41111111-1111-1111-1111-111111111111',
        '31111111-1111-1111-1111-111111111111',
        'public',
        'orders',
        'Customer orders and transactions',
        'Orders',
        'Contains all customer purchase transactions with order details, amounts, and status',
        ARRAY['sales', 'transactions', 'revenue'],
        125000
    ),
    (
        '41111111-1111-1111-1111-111111111112',
        '31111111-1111-1111-1111-111111111111',
        'public',
        'customers',
        'Customer profiles and contact information',
        'Customers',
        'Master customer database with demographics and contact details',
        ARRAY['users', 'profiles', 'crm'],
        45000
    ),
    (
        '41111111-1111-1111-1111-111111111113',
        '31111111-1111-1111-1111-111111111111',
        'public',
        'products',
        'Product catalog and inventory',
        'Products',
        'Product information including pricing, categories, and inventory levels',
        ARRAY['catalog', 'inventory', 'items'],
        5000
    ),
    (
        '41111111-1111-1111-1111-111111111114',
        '31111111-1111-1111-1111-111111111111',
        'public',
        'order_items',
        'Line items for each order',
        'Order Items',
        'Individual products within each order with quantities and prices',
        ARRAY['line_items', 'details'],
        350000
    ),
    (
        '41111111-1111-1111-1111-111111111115',
        '31111111-1111-1111-1111-111111111111',
        'public',
        'events',
        'User activity events',
        'Events',
        'User interactions and system events for analytics',
        ARRAY['activity', 'tracking', 'logs'],
        2500000
    )
ON CONFLICT DO NOTHING;

-- Insert demo columns for orders table
INSERT INTO public.discovered_columns (
    table_id, column_name, data_type, is_nullable,
    semantic_name, semantic_description, is_primary_key
)
SELECT 
    '41111111-1111-1111-1111-111111111111',
    cols.column_name,
    cols.data_type,
    cols.is_nullable,
    cols.semantic_name,
    cols.semantic_description,
    cols.is_primary_key
FROM (VALUES
    ('id', 'uuid', false, 'Order ID', 'Unique order identifier', true),
    ('customer_id', 'uuid', false, 'Customer', 'Reference to customer who placed order', false),
    ('order_date', 'timestamp', false, 'Order Date', 'When the order was placed', false),
    ('total_amount', 'decimal', false, 'Total Amount', 'Total order value in USD', false),
    ('status', 'varchar', false, 'Status', 'Order status: pending, processing, shipped, delivered, cancelled', false),
    ('shipping_address', 'jsonb', true, 'Shipping Address', 'Delivery address in JSON format', false),
    ('created_at', 'timestamp', false, 'Created At', 'Record creation timestamp', false)
) AS cols(column_name, data_type, is_nullable, semantic_name, semantic_description, is_primary_key)
ON CONFLICT DO NOTHING;

-- Insert demo columns for customers table
INSERT INTO public.discovered_columns (
    table_id, column_name, data_type, is_nullable,
    semantic_name, semantic_description, is_primary_key
)
SELECT 
    '41111111-1111-1111-1111-111111111112',
    cols.column_name,
    cols.data_type,
    cols.is_nullable,
    cols.semantic_name,
    cols.semantic_description,
    cols.is_primary_key
FROM (VALUES
    ('id', 'uuid', false, 'Customer ID', 'Unique customer identifier', true),
    ('email', 'varchar', false, 'Email', 'Customer email address', false),
    ('full_name', 'varchar', false, 'Full Name', 'Customer display name', false),
    ('signup_date', 'date', false, 'Signup Date', 'When customer registered', false),
    ('country', 'varchar', true, 'Country', 'Customer location', false),
    ('ltv', 'decimal', true, 'Lifetime Value', 'Total revenue from customer', false)
) AS cols(column_name, data_type, is_nullable, semantic_name, semantic_description, is_primary_key)
ON CONFLICT DO NOTHING;

-- =============================================================================
-- DEMO SEMANTIC DEFINITIONS
-- =============================================================================

INSERT INTO public.semantic_definitions (
    organization_id, term, definition, category,
    related_tables, related_columns, sql_expression, examples
)
VALUES 
    (
        '11111111-1111-1111-1111-111111111111',
        'Revenue',
        'Total monetary value of completed transactions',
        'metric',
        ARRAY['orders', 'order_items'],
        ARRAY['orders.total_amount', 'order_items.price'],
        'SUM(orders.total_amount) WHERE orders.status = ''delivered''',
        '{"monthly_revenue": "SELECT DATE_TRUNC(''month'', order_date), SUM(total_amount) FROM orders GROUP BY 1"}'::jsonb
    ),
    (
        '11111111-1111-1111-1111-111111111111',
        'Active Customer',
        'A customer who has placed an order in the last 90 days',
        'dimension',
        ARRAY['customers', 'orders'],
        ARRAY['customers.id', 'orders.customer_id', 'orders.order_date'],
        NULL,
        '{"recent_customers": "SELECT * FROM customers WHERE id IN (SELECT customer_id FROM orders WHERE order_date > NOW() - INTERVAL ''90 days'')"}'::jsonb
    ),
    (
        '11111111-1111-1111-1111-111111111111',
        'Average Order Value',
        'Average monetary value per order',
        'metric',
        ARRAY['orders'],
        ARRAY['orders.total_amount'],
        'AVG(orders.total_amount)',
        '{"aov_by_month": "SELECT DATE_TRUNC(''month'', order_date), AVG(total_amount) FROM orders GROUP BY 1"}'::jsonb
    ),
    (
        '11111111-1111-1111-1111-111111111111',
        'Churned Customer',
        'A customer who hasn\'t purchased in 180+ days',
        'dimension',
        ARRAY['customers', 'orders'],
        ARRAY['customers.id', 'orders.order_date'],
        NULL,
        '{"churned_count": "SELECT COUNT(*) FROM customers WHERE id NOT IN (SELECT customer_id FROM orders WHERE order_date > NOW() - INTERVAL ''180 days'')"}'::jsonb
    ),
    (
        '11111111-1111-1111-1111-111111111111',
        'Conversion Rate',
        'Percentage of events that result in a purchase',
        'metric',
        ARRAY['events', 'orders'],
        ARRAY['events.user_id', 'events.event_type', 'orders.customer_id'],
        '(COUNT(DISTINCT orders.customer_id) / COUNT(DISTINCT events.user_id)) * 100',
        NULL
    )
ON CONFLICT DO NOTHING;

-- =============================================================================
-- DEMO SAVED QUERIES
-- =============================================================================

INSERT INTO public.saved_queries (
    id, organization_id, user_id, name, description,
    natural_language, generated_sql, visualization_type, visualization_config
)
VALUES 
    (
        '51111111-1111-1111-1111-111111111111',
        '11111111-1111-1111-1111-111111111111',
        '21111111-1111-1111-1111-111111111111',
        'Monthly Revenue Trend',
        'Revenue over time by month',
        'Show me monthly revenue trend for the last 12 months',
        'SELECT DATE_TRUNC(''month'', order_date) as month, SUM(total_amount) as revenue FROM orders WHERE order_date >= NOW() - INTERVAL ''12 months'' GROUP BY 1 ORDER BY 1',
        'line',
        '{"x": "month", "y": "revenue", "title": "Monthly Revenue"}'::jsonb
    ),
    (
        '51111111-1111-1111-1111-111111111112',
        '11111111-1111-1111-1111-111111111111',
        '21111111-1111-1111-1111-111111111111',
        'Top Customers by Revenue',
        'Highest value customers',
        'Who are our top 10 customers by total spend?',
        'SELECT c.full_name, c.email, SUM(o.total_amount) as total_spent FROM customers c JOIN orders o ON c.id = o.customer_id GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 10',
        'table',
        '{}'::jsonb
    ),
    (
        '51111111-1111-1111-1111-111111111113',
        '11111111-1111-1111-1111-111111111111',
        '21111111-1111-1111-1111-111111111112',
        'Orders by Status',
        'Order count breakdown by status',
        'How many orders do we have in each status?',
        'SELECT status, COUNT(*) as order_count FROM orders GROUP BY 1 ORDER BY 2 DESC',
        'pie',
        '{"category": "status", "value": "order_count"}'::jsonb
    )
ON CONFLICT DO NOTHING;

-- =============================================================================
-- DEMO DASHBOARD
-- =============================================================================

INSERT INTO public.dashboards (
    id, organization_id, created_by, name, description, layout
)
VALUES (
    '61111111-1111-1111-1111-111111111111',
    '11111111-1111-1111-1111-111111111111',
    '21111111-1111-1111-1111-111111111111',
    'Executive Summary',
    'Key metrics for leadership team',
    '{"refresh_interval": 300, "theme": "light"}'::jsonb
) ON CONFLICT DO NOTHING;

-- Dashboard widgets
INSERT INTO public.dashboard_widgets (
    dashboard_id, widget_type, title, position, saved_query_id, custom_config
)
VALUES 
    (
        '61111111-1111-1111-1111-111111111111',
        'chart',
        'Monthly Revenue',
        '{"x": 0, "y": 0, "w": 6, "h": 4}'::jsonb,
        '51111111-1111-1111-1111-111111111111',
        '{}'::jsonb
    ),
    (
        '61111111-1111-1111-1111-111111111111',
        'chart',
        'Orders by Status',
        '{"x": 6, "y": 0, "w": 6, "h": 4}'::jsonb,
        '51111111-1111-1111-1111-111111111113',
        '{}'::jsonb
    ),
    (
        '61111111-1111-1111-1111-111111111111',
        'table',
        'Top Customers',
        '{"x": 0, "y": 4, "w": 12, "h": 4}'::jsonb,
        '51111111-1111-1111-1111-111111111112',
        '{"page_size": 10}'::jsonb
    )
ON CONFLICT DO NOTHING;

-- =============================================================================
-- DEMO PROACTIVE INSIGHTS
-- =============================================================================

INSERT INTO public.proactive_insights (
    organization_id, insight_type, title, description,
    affected_connection_id, affected_tables, severity
)
VALUES 
    (
        '11111111-1111-1111-1111-111111111111',
        'trend',
        'Revenue up 15% this month',
        'Your monthly revenue has increased by 15% compared to last month, driven primarily by increased order volume from returning customers.',
        '31111111-1111-1111-1111-111111111111',
        ARRAY['orders', 'customers'],
        'info'
    ),
    (
        '11111111-1111-1111-1111-111111111111',
        'anomaly',
        'Unusual spike in failed orders',
        'We detected 3x more failed orders than usual in the last 24 hours. This may indicate a payment processing issue.',
        '31111111-1111-1111-1111-111111111111',
        ARRAY['orders'],
        'warning'
    ),
    (
        '11111111-1111-1111-1111-111111111111',
        'recommendation',
        'Top customers at risk of churning',
        '5 of your top 20 customers by LTV haven\'t made a purchase in 60+ days. Consider a re-engagement campaign.',
        '31111111-1111-1111-1111-111111111111',
        ARRAY['customers', 'orders'],
        'critical'
    )
ON CONFLICT DO NOTHING;

-- =============================================================================
-- SEED COMPLETE
-- =============================================================================

SELECT 'Demo data seeded successfully!' as status;
