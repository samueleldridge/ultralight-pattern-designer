"""
Database Index Definitions

Optimized indexes for analytical queries including:
- B-tree indexes for range queries and sorting
- Composite indexes for common filter combinations  
- Partial indexes for frequently filtered subsets
- Full-text search indexes for product names
"""

from typing import Dict


def get_index_definitions(is_sqlite: bool = False) -> Dict[str, str]:
    """
    Get database index definitions optimized for analytical queries.
    
    Args:
        is_sqlite: If True, return SQLite-compatible index definitions
        
    Returns:
        Dictionary mapping index names to CREATE INDEX SQL statements
    """
    indexes = {}
    
    # =========================================================================
    # ORDERS TABLE INDEXES
    # =========================================================================
    
    # Primary query filters
    indexes['idx_orders_date'] = """
        CREATE INDEX IF NOT EXISTS idx_orders_date 
        ON orders(order_date DESC)
    """
    
    indexes['idx_orders_customer_id'] = """
        CREATE INDEX IF NOT EXISTS idx_orders_customer_id 
        ON orders(customer_id)
    """
    
    indexes['idx_orders_status'] = """
        CREATE INDEX IF NOT EXISTS idx_orders_status 
        ON orders(status)
    """
    
    # Composite indexes for common query patterns
    indexes['idx_orders_date_status'] = """
        CREATE INDEX IF NOT EXISTS idx_orders_date_status 
        ON orders(order_date DESC, status)
    """
    
    indexes['idx_orders_customer_date'] = """
        CREATE INDEX IF NOT EXISTS idx_orders_customer_date 
        ON orders(customer_id, order_date DESC)
    """
    
    indexes['idx_orders_region_date'] = """
        CREATE INDEX IF NOT EXISTS idx_orders_region_date 
        ON orders(region, order_date DESC)
    """
    
    indexes['idx_orders_segment_date'] = """
        CREATE INDEX IF NOT EXISTS idx_orders_segment_date 
        ON orders(customer_segment, order_date DESC)
    """
    
    # Covering index for common analytical queries
    indexes['idx_orders_analytics_covering'] = """
        CREATE INDEX IF NOT EXISTS idx_orders_analytics_covering 
        ON orders(order_date, region, customer_segment, status, total, customer_id)
    """
    
    # Partial indexes for frequently filtered statuses
    if not is_sqlite:
        indexes['idx_orders_active'] = """
            CREATE INDEX IF NOT EXISTS idx_orders_active 
            ON orders(order_date DESC, customer_id, total)
            WHERE status NOT IN ('cancelled', 'refunded')
        """
        
        indexes['idx_orders_pending'] = """
            CREATE INDEX IF NOT EXISTS idx_orders_pending 
            ON orders(order_date, customer_id)
            WHERE status = 'pending'
        """
    
    # =========================================================================
    # CUSTOMERS TABLE INDEXES
    # =========================================================================
    
    indexes['idx_customers_segment'] = """
        CREATE INDEX IF NOT EXISTS idx_customers_segment 
        ON customers(segment)
    """
    
    indexes['idx_customers_region'] = """
        CREATE INDEX IF NOT EXISTS idx_customers_region 
        ON customers(region)
    """
    
    # Composite for segment + region queries
    indexes['idx_customers_segment_region'] = """
        CREATE INDEX IF NOT EXISTS idx_customers_segment_region 
        ON customers(segment, region)
    """
    
    # Email lookup (common for authentication/identification)
    indexes['idx_customers_email'] = """
        CREATE INDEX IF NOT EXISTS idx_customers_email 
        ON customers(email)
    """
    
    # Churn risk analysis
    indexes['idx_customers_churn'] = """
        CREATE INDEX IF NOT EXISTS idx_customers_churn 
        ON customers(churn_risk DESC, segment)
        WHERE churn_risk IS NOT NULL
    """
    
    # =========================================================================
    # PRODUCTS TABLE INDEXES
    # =========================================================================
    
    indexes['idx_products_category'] = """
        CREATE INDEX IF NOT EXISTS idx_products_category 
        ON products(category)
    """
    
    indexes['idx_products_active'] = """
        CREATE INDEX IF NOT EXISTS idx_products_active 
        ON products(category, base_price)
        WHERE is_active = TRUE
    """
    
    # Full-text search on product names (PostgreSQL)
    if not is_sqlite:
        indexes['idx_products_name_trgm'] = """
            CREATE INDEX IF NOT EXISTS idx_products_name_trgm 
            ON products USING gin (name gin_trgm_ops)
        """
        
        indexes['idx_products_name_search'] = """
            CREATE INDEX IF NOT EXISTS idx_products_name_search 
            ON products USING gin(to_tsvector('english', name))
        """
        
        indexes['idx_products_description_search'] = """
            CREATE INDEX IF NOT EXISTS idx_products_description_search 
            ON products USING gin(to_tsvector('english', COALESCE(description, '')))
        """
    else:
        # SQLite FTS
        indexes['idx_products_name_fts'] = """
            CREATE VIRTUAL TABLE IF NOT EXISTS products_fts USING fts5(
                name, description,
                content='products',
                content_rowid='rowid'
            )
        """
    
    # SKU lookup (frequently used in joins)
    indexes['idx_products_sku'] = """
        CREATE INDEX IF NOT EXISTS idx_products_sku 
        ON products(sku)
    """
    
    # Price range queries
    indexes['idx_products_price'] = """
        CREATE INDEX IF NOT EXISTS idx_products_price 
        ON products(base_price)
    """
    
    # =========================================================================
    # ORDER_ITEMS TABLE INDEXES
    # =========================================================================
    
    indexes['idx_order_items_order'] = """
        CREATE INDEX IF NOT EXISTS idx_order_items_order 
        ON order_items(order_id)
    """
    
    indexes['idx_order_items_product'] = """
        CREATE INDEX IF NOT EXISTS idx_order_items_product 
        ON order_items(product_id)
    """
    
    # Composite for order-product lookups
    indexes['idx_order_items_order_product'] = """
        CREATE INDEX IF NOT EXISTS idx_order_items_order_product 
        ON order_items(order_id, product_id)
    """
    
    # For product performance analytics
    indexes['idx_order_items_product_price'] = """
        CREATE INDEX IF NOT EXISTS idx_order_items_product_price 
        ON order_items(product_id, unit_price, quantity)
    """
    
    # =========================================================================
    # DOCUMENTS (RAG) INDEXES
    # =========================================================================
    
    # Tenant isolation index
    indexes['idx_documents_tenant'] = """
        CREATE INDEX IF NOT EXISTS idx_documents_tenant 
        ON documents(tenant_id, created_at DESC)
    """
    
    # Content type filtering
    indexes['idx_documents_content_type'] = """
        CREATE INDEX IF NOT EXISTS idx_documents_content_type 
        ON documents(content_type, tenant_id)
    """
    
    # =========================================================================
    # AUDIT LOG INDEXES
    # =========================================================================
    
    indexes['idx_audit_table_record'] = """
        CREATE INDEX IF NOT EXISTS idx_audit_table_record 
        ON audit_log(table_name, record_id, changed_at DESC)
    """
    
    indexes['idx_audit_changed_at'] = """
        CREATE INDEX IF NOT EXISTS idx_audit_changed_at 
        ON audit_log(changed_at DESC)
    """
    
    return indexes


def get_sqlite_fts_setup() -> list:
    """Get SQLite FTS5 trigger definitions for maintaining search indexes."""
    return [
        """
        CREATE TRIGGER IF NOT EXISTS products_fts_insert 
        AFTER INSERT ON products
        BEGIN
            INSERT INTO products_fts(rowid, name, description)
            VALUES (NEW.rowid, NEW.name, NEW.description);
        END
        """,
        """
        CREATE TRIGGER IF NOT EXISTS products_fts_update 
        AFTER UPDATE ON products
        BEGIN
            INSERT INTO products_fts(products_fts, rowid, name, description)
            VALUES ('delete', OLD.rowid, OLD.name, OLD.description);
            INSERT INTO products_fts(rowid, name, description)
            VALUES (NEW.rowid, NEW.name, NEW.description);
        END
        """,
        """
        CREATE TRIGGER IF NOT EXISTS products_fts_delete 
        AFTER DELETE ON products
        BEGIN
            INSERT INTO products_fts(products_fts, rowid, name, description)
            VALUES ('delete', OLD.rowid, OLD.name, OLD.description);
        END
        """
    ]


def get_index_recommendations() -> Dict[str, list]:
    """
    Get index recommendations for common query patterns.
    
    Returns:
        Dictionary mapping query patterns to recommended indexes
    """
    return {
        "date_range_queries": [
            "idx_orders_date",
            "idx_orders_date_status"
        ],
        "customer_analysis": [
            "idx_orders_customer_id",
            "idx_orders_customer_date",
            "idx_customers_segment",
            "idx_customers_region"
        ],
        "revenue_analytics": [
            "idx_orders_date",
            "idx_orders_region_date",
            "idx_orders_segment_date",
            "idx_orders_analytics_covering"
        ],
        "product_search": [
            "idx_products_name_trgm",  # PostgreSQL
            "idx_products_name_search",  # PostgreSQL
            "idx_products_name_fts"  # SQLite
        ],
        "order_status_filtering": [
            "idx_orders_status",
            "idx_orders_active"
        ],
        "geographic_analysis": [
            "idx_customers_region",
            "idx_customers_segment_region",
            "idx_orders_region_date"
        ]
    }


def get_maintenance_sql(is_sqlite: bool = False) -> list:
    """Get SQL statements for index maintenance."""
    if is_sqlite:
        return [
            "ANALYZE customers",
            "ANALYZE products", 
            "ANALYZE orders",
            "ANALYZE order_items",
            "REINDEX"
        ]
    else:
        return [
            "ANALYZE customers",
            "ANALYZE products",
            "ANALYZE orders", 
            "ANALYZE order_items",
            "REINDEX TABLE customers",
            "REINDEX TABLE products",
            "REINDEX TABLE orders",
            "REINDEX TABLE order_items"
        ]
