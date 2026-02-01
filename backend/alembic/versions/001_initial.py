"""
Initial migration: Create core analytics tables.

This migration creates the base tables for the AI Analytics Platform:
- customers
- products  
- orders
- order_items
- audit_log

Revision ID: 001_initial
Revises: 
Create Date: 2025-02-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create customers table
    op.create_table(
        'customers',
        sa.Column('customer_id', sa.String(20), primary_key=True),
        sa.Column('first_name', sa.String(50), nullable=False),
        sa.Column('last_name', sa.String(50), nullable=False),
        sa.Column('email', sa.String(100), nullable=False, unique=True),
        sa.Column('phone', sa.String(20)),
        sa.Column('region', sa.String(10), nullable=False),
        sa.Column('country', sa.String(5), nullable=False),
        sa.Column('state', sa.String(50)),
        sa.Column('city', sa.String(50)),
        sa.Column('postal_code', sa.String(20)),
        sa.Column('segment', sa.String(20), nullable=False),
        sa.Column('ltv_factor', sa.Numeric(3, 2)),
        sa.Column('churn_risk', sa.Numeric(3, 2)),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('last_login', sa.DateTime()),
        sa.CheckConstraint("segment IN ('vip', 'enterprise', 'mid_market', 'smb')"),
        sa.CheckConstraint("region IN ('US', 'UK', 'EU', 'APAC')"),
        sa.CheckConstraint("churn_risk IS NULL OR (churn_risk >= 0 AND churn_risk <= 1)"),
        sa.CheckConstraint("ltv_factor IS NULL OR (ltv_factor >= 0 AND ltv_factor <= 10)"),
    )
    
    # Create products table
    op.create_table(
        'products',
        sa.Column('product_id', sa.String(20), primary_key=True),
        sa.Column('sku', sa.String(20), nullable=False, unique=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('base_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('cost', sa.Numeric(10, 2)),
        sa.Column('margin', sa.Numeric(4, 2)),
        sa.Column('stock_quantity', sa.Integer()),
        sa.Column('is_active', sa.Boolean(), server_default=sa.true()),
        sa.Column('created_at', sa.Date(), server_default=sa.func.current_date()),
        sa.CheckConstraint("base_price >= 0"),
        sa.CheckConstraint("cost IS NULL OR cost >= 0"),
        sa.CheckConstraint("stock_quantity IS NULL OR stock_quantity >= 0"),
    )
    
    # Create orders table
    op.create_table(
        'orders',
        sa.Column('order_id', sa.String(20), primary_key=True),
        sa.Column('customer_id', sa.String(20), sa.ForeignKey('customers.customer_id'), nullable=False),
        sa.Column('order_date', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('payment_method', sa.String(30)),
        sa.Column('shipping_method', sa.String(20)),
        sa.Column('subtotal', sa.Numeric(10, 2)),
        sa.Column('shipping_cost', sa.Numeric(10, 2)),
        sa.Column('tax', sa.Numeric(10, 2)),
        sa.Column('discount', sa.Numeric(10, 2)),
        sa.Column('total', sa.Numeric(10, 2)),
        sa.Column('currency', sa.String(5), server_default='USD'),
        sa.Column('shipped_date', sa.DateTime()),
        sa.Column('delivered_date', sa.DateTime()),
        sa.Column('region', sa.String(10)),
        sa.Column('customer_segment', sa.String(20)),
        sa.CheckConstraint("status IN ('pending', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded')"),
        sa.CheckConstraint("total IS NULL OR total >= 0"),
    )
    
    # Create order_items table
    op.create_table(
        'order_items',
        sa.Column('order_item_id', sa.String(20), primary_key=True),
        sa.Column('order_id', sa.String(20), sa.ForeignKey('orders.order_id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_id', sa.String(20), sa.ForeignKey('products.product_id'), nullable=False),
        sa.Column('sku', sa.String(20)),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit_price', sa.Numeric(10, 2)),
        sa.Column('total_price', sa.Numeric(10, 2)),
        sa.Column('cost', sa.Numeric(10, 2)),
        sa.CheckConstraint("quantity > 0"),
        sa.CheckConstraint("unit_price IS NULL OR unit_price >= 0"),
    )
    
    # Create audit_log table
    op.create_table(
        'audit_log',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('table_name', sa.String(50), nullable=False),
        sa.Column('record_id', sa.String(50), nullable=False),
        sa.Column('action', sa.String(10), nullable=False),
        sa.Column('old_data', postgresql.JSONB() if op.get_bind().dialect.name == 'postgresql' else sa.Text()),
        sa.Column('new_data', postgresql.JSONB() if op.get_bind().dialect.name == 'postgresql' else sa.Text()),
        sa.Column('changed_by', sa.String(100)),
        sa.Column('changed_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('ip_address', sa.String(45)),
        sa.CheckConstraint("action IN ('INSERT', 'UPDATE', 'DELETE')"),
    )
    
    # Create indexes for performance
    op.create_index('idx_orders_date', 'orders', ['order_date'])
    op.create_index('idx_orders_customer_id', 'orders', ['customer_id'])
    op.create_index('idx_orders_status', 'orders', ['status'])
    op.create_index('idx_orders_date_status', 'orders', ['order_date', 'status'])
    op.create_index('idx_orders_region_date', 'orders', ['region', 'order_date'])
    
    op.create_index('idx_customers_segment', 'customers', ['segment'])
    op.create_index('idx_customers_region', 'customers', ['region'])
    op.create_index('idx_customers_segment_region', 'customers', ['segment', 'region'])
    
    op.create_index('idx_products_category', 'products', ['category'])
    op.create_index('idx_products_sku', 'products', ['sku'])
    
    op.create_index('idx_order_items_order', 'order_items', ['order_id'])
    op.create_index('idx_order_items_product', 'order_items', ['product_id'])
    
    op.create_index('idx_audit_table_record', 'audit_log', ['table_name', 'record_id'])
    op.create_index('idx_audit_changed_at', 'audit_log', ['changed_at'])


def downgrade() -> None:
    op.drop_index('idx_audit_changed_at')
    op.drop_index('idx_audit_table_record')
    op.drop_index('idx_order_items_product')
    op.drop_index('idx_order_items_order')
    op.drop_index('idx_products_sku')
    op.drop_index('idx_products_category')
    op.drop_index('idx_customers_segment_region')
    op.drop_index('idx_customers_region')
    op.drop_index('idx_customers_segment')
    op.drop_index('idx_orders_region_date')
    op.drop_index('idx_orders_date_status')
    op.drop_index('idx_orders_status')
    op.drop_index('idx_orders_customer_id')
    op.drop_index('idx_orders_date')
    
    op.drop_table('audit_log')
    op.drop_table('order_items')
    op.drop_table('orders')
    op.drop_table('products')
    op.drop_table('customers')
