-- Synthetic dataset for AI Analytics Platform MVP
-- E-commerce style data: orders, customers, products

-- Create demo schema
CREATE SCHEMA IF NOT EXISTS demo;

-- Customers table
CREATE TABLE IF NOT EXISTS demo.customers (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    country VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    segment VARCHAR(50) DEFAULT 'standard'
);

-- Products table
CREATE TABLE IF NOT EXISTS demo.products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    price DECIMAL(10,2) NOT NULL,
    cost DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Orders table
CREATE TABLE IF NOT EXISTS demo.orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES demo.customers(id),
    total_amount DECIMAL(10,2) NOT NULL,
    discount_amount DECIMAL(10,2) DEFAULT 0,
    status VARCHAR(50) DEFAULT 'completed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Order items table
CREATE TABLE IF NOT EXISTS demo.order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES demo.orders(id),
    product_id INTEGER REFERENCES demo.products(id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL
);

-- Insert sample customers
INSERT INTO demo.customers (email, name, country, created_at, segment) VALUES
('john@example.com', 'John Smith', 'USA', '2023-01-15', 'premium'),
('sarah@example.com', 'Sarah Johnson', 'UK', '2023-02-20', 'standard'),
('mike@example.com', 'Mike Chen', 'Canada', '2023-03-10', 'standard'),
('emma@example.com', 'Emma Wilson', 'Australia', '2023-04-05', 'premium'),
('david@example.com', 'David Brown', 'USA', '2023-05-12', 'standard'),
('lisa@example.com', 'Lisa Garcia', 'UK', '2023-06-18', 'premium'),
('james@example.com', 'James Taylor', 'Canada', '2023-07-22', 'standard'),
('anna@example.com', 'Anna Martinez', 'USA', '2023-08-30', 'premium'),
('robert@example.com', 'Robert Lee', 'Australia', '2023-09-14', 'standard'),
('jennifer@example.com', 'Jennifer White', 'UK', '2023-10-01', 'premium');

-- Insert sample products
INSERT INTO demo.products (name, category, price, cost, created_at) VALUES
('Laptop Pro', 'Electronics', 1299.99, 800.00, '2023-01-01'),
('Wireless Mouse', 'Electronics', 29.99, 12.00, '2023-01-01'),
('USB-C Hub', 'Electronics', 79.99, 35.00, '2023-01-15'),
('Monitor 4K', 'Electronics', 449.99, 280.00, '2023-02-01'),
('Keyboard Mechanical', 'Electronics', 149.99, 70.00, '2023-02-15'),
('Webcam HD', 'Electronics', 89.99, 40.00, '2023-03-01'),
('Desk Chair', 'Furniture', 299.99, 150.00, '2023-01-10'),
('Standing Desk', 'Furniture', 599.99, 350.00, '2023-02-20'),
('Notebook Pack', 'Office Supplies', 14.99, 5.00, '2023-01-05'),
('Pen Set', 'Office Supplies', 24.99, 8.00, '2023-03-10');

-- Insert sample orders (last 6 months with realistic patterns)
INSERT INTO demo.orders (customer_id, total_amount, discount_amount, status, created_at) VALUES
-- January (lower sales)
(1, 1329.98, 0, 'completed', '2024-01-05'),
(2, 29.99, 0, 'completed', '2024-01-08'),
(3, 529.98, 20.00, 'completed', '2024-01-12'),
(4, 149.99, 0, 'completed', '2024-01-15'),
(5, 89.99, 0, 'completed', '2024-01-20'),

-- February (growth)
(6, 1379.98, 50.00, 'completed', '2024-02-03'),
(7, 79.99, 0, 'completed', '2024-02-08'),
(8, 599.99, 0, 'completed', '2024-02-14'),
(9, 44.98, 0, 'completed', '2024-02-18'),
(10, 1299.99, 100.00, 'completed', '2024-02-22'),
(1, 29.99, 0, 'completed', '2024-02-25'),
(2, 449.99, 0, 'completed', '2024-02-28'),

-- March (strong month)
(3, 1429.97, 0, 'completed', '2024-03-05'),
(4, 89.99, 0, 'completed', '2024-03-08'),
(5, 329.98, 15.00, 'completed', '2024-03-12'),
(6, 599.99, 0, 'completed', '2024-03-15'),
(7, 24.99, 0, 'completed', '2024-03-18'),
(8, 1379.98, 0, 'completed', '2024-03-22'),
(9, 79.99, 0, 'completed', '2024-03-25'),
(10, 149.99, 0, 'completed', '2024-03-28'),

-- April (slight dip)
(1, 59.98, 0, 'completed', '2024-04-02'),
(2, 299.99, 0, 'completed', '2024-04-05'),
(3, 1329.98, 0, 'completed', '2024-04-08'),
(4, 14.99, 0, 'completed', '2024-04-12'),
(5, 449.99, 25.00, 'completed', '2024-04-15'),
(6, 89.99, 0, 'completed', '2024-04-18'),
(7, 599.99, 0, 'completed', '2024-04-22'),

-- May (recovery)
(8, 1429.97, 50.00, 'completed', '2024-05-03'),
(9, 29.99, 0, 'completed', '2024-05-07'),
(10, 329.98, 0, 'completed', '2024-05-10'),
(1, 89.99, 0, 'completed', '2024-05-14'),
(2, 1379.98, 0, 'completed', '2024-05-18'),
(3, 79.99, 0, 'completed', '2024-05-22'),
(4, 149.99, 10.00, 'completed', '2024-05-25'),
(5, 599.99, 0, 'completed', '2024-05-28'),

-- June (strong end of quarter)
(6, 1329.98, 0, 'completed', '2024-06-03'),
(7, 44.98, 0, 'completed', '2024-06-06'),
(8, 529.98, 0, 'completed', '2024-06-10'),
(9, 299.99, 0, 'completed', '2024-06-14'),
(10, 1429.97, 75.00, 'completed', '2024-06-18'),
(1, 79.99, 0, 'completed', '2024-06-22'),
(2, 149.99, 0, 'completed', '2024-06-25'),
(3, 599.99, 0, 'completed', '2024-06-28');

-- Insert order items
INSERT INTO demo.order_items (order_id, product_id, quantity, unit_price) VALUES
-- Order 1: Laptop + Mouse
(1, 1, 1, 1299.99),
(1, 2, 1, 29.99),

-- Order 2: Mouse
(2, 2, 1, 29.99),

-- Order 3: Monitor + Hub
(3, 4, 1, 449.99),
(3, 3, 1, 79.99),

-- Order 4: Keyboard
(4, 5, 1, 149.99),

-- Order 5: Webcam
(5, 6, 1, 89.99),

-- Order 6: Laptop + Mouse + Hub
(6, 1, 1, 1299.99),
(6, 2, 1, 29.99),
(6, 3, 1, 79.99),

-- Order 7: Hub
(7, 3, 1, 79.99),

-- Order 8: Desk
(8, 8, 1, 599.99),

-- Order 9: Notebook + Pen
(9, 9, 1, 14.99),
(9, 10, 1, 24.99),

-- Order 10: Laptop
(10, 1, 1, 1299.99),

-- Order 11: Mouse
(11, 2, 1, 29.99),

-- Order 12: Monitor
(12, 4, 1, 449.99),

-- Order 13: Laptop + Mouse + Keyboard
(13, 1, 1, 1299.99),
(13, 2, 1, 29.99),
(13, 5, 1, 149.99),

-- Order 14: Webcam
(14, 6, 1, 89.99),

-- Order 15: Chair + Mouse
(15, 7, 1, 299.99),
(15, 2, 1, 29.99),

-- Order 16: Desk
(16, 8, 1, 599.99),

-- Order 17: Notebook
(17, 9, 1, 14.99),

-- Order 18: Laptop + Mouse + Hub
(18, 1, 1, 1299.99),
(18, 2, 1, 29.99),
(18, 3, 1, 79.99),

-- Order 19: Hub
(19, 3, 1, 79.99),

-- Order 20: Keyboard
(20, 5, 1, 149.99),

-- Order 21: Monitor
(21, 4, 1, 449.99),

-- Order 22: Webcam
(22, 6, 1, 89.99),

-- Order 23: Desk
(23, 8, 1, 599.99),

-- Order 24: Laptop + Mouse + Keyboard
(24, 1, 1, 1299.99),
(24, 2, 1, 29.99),
(24, 5, 1, 149.99),

-- Order 25: Mouse + Notebook
(25, 2, 1, 29.99),
(25, 9, 1, 14.99),

-- Order 26: Monitor + Hub
(26, 4, 1, 449.99),
(26, 3, 1, 79.99),

-- Order 27: Chair
(27, 7, 1, 299.99),

-- Order 28: Laptop + Mouse + Hub + Keyboard
(28, 1, 1, 1299.99),
(28, 2, 1, 29.99),
(28, 3, 1, 79.99),
(28, 5, 1, 149.99),

-- Order 29: Hub
(29, 3, 1, 79.99),

-- Order 30: Keyboard
(30, 5, 1, 149.99),

-- Order 31: Mouse
(31, 2, 1, 29.99),

-- Order 32: Laptop + Hub
(32, 1, 1, 1299.99),
(32, 3, 1, 79.99),

-- Order 33: Monitor + Mouse
(33, 4, 1, 449.99),
(33, 2, 1, 29.99),

-- Order 34: Webcam + Notebook
(34, 6, 1, 89.99),
(34, 9, 1, 14.99),

-- Order 35: Desk + Chair
(35, 8, 1, 599.99),
(35, 7, 1, 299.99),

-- Order 36: Laptop + Mouse
(36, 1, 1, 1299.99),
(36, 2, 1, 29.99),

-- Order 37: Hub
(37, 3, 1, 79.99),

-- Order 38: Keyboard + Pen
(38, 5, 1, 149.99),
(38, 10, 1, 24.99);

-- Create helpful views for the AI
CREATE OR REPLACE VIEW demo.revenue_by_month AS
SELECT 
    DATE_TRUNC('month', created_at) as month,
    SUM(total_amount - discount_amount) as revenue,
    COUNT(*) as order_count,
    AVG(total_amount - discount_amount) as avg_order_value
FROM demo.orders
WHERE status = 'completed'
GROUP BY DATE_TRUNC('month', created_at)
ORDER BY month;

CREATE OR REPLACE VIEW demo.top_products AS
SELECT 
    p.name,
    p.category,
    SUM(oi.quantity) as total_sold,
    SUM(oi.quantity * oi.unit_price) as total_revenue
FROM demo.products p
JOIN demo.order_items oi ON p.id = oi.product_id
JOIN demo.orders o ON oi.order_id = o.id
WHERE o.status = 'completed'
GROUP BY p.id, p.name, p.category
ORDER BY total_revenue DESC;

CREATE OR REPLACE VIEW demo.customer_summary AS
SELECT 
    c.id,
    c.name,
    c.country,
    c.segment,
    COUNT(DISTINCT o.id) as total_orders,
    SUM(o.total_amount - o.discount_amount) as total_spent,
    MAX(o.created_at) as last_order_date
FROM demo.customers c
LEFT JOIN demo.orders o ON c.id = o.customer_id AND o.status = 'completed'
GROUP BY c.id, c.name, c.country, c.segment;
