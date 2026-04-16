-- =====================================================================
--  Olist E-Commerce Schema  –  runs automatically on first DB start
-- =====================================================================

-- Customers
CREATE TABLE IF NOT EXISTS olist_customers (
    customer_id               VARCHAR(64) PRIMARY KEY,
    customer_unique_id        VARCHAR(64),
    customer_zip_code_prefix  VARCHAR(10),
    customer_city             VARCHAR(100),
    customer_state            VARCHAR(2)
);

-- Orders
CREATE TABLE IF NOT EXISTS olist_orders (
    order_id                       VARCHAR(64) PRIMARY KEY,
    customer_id                    VARCHAR(64) REFERENCES olist_customers(customer_id),
    order_status                   VARCHAR(20),
    order_purchase_timestamp       TIMESTAMP,
    order_approved_at              TIMESTAMP,
    order_delivered_carrier_date   TIMESTAMP,
    order_delivered_customer_date  TIMESTAMP,
    order_estimated_delivery_date  TIMESTAMP
);

-- Products
CREATE TABLE IF NOT EXISTS olist_products (
    product_id                  VARCHAR(64) PRIMARY KEY,
    product_category_name       VARCHAR(100),
    product_name_length         INT,
    product_description_length  INT,
    product_photos_qty          INT,
    product_weight_g            INT,
    product_length_cm           INT,
    product_height_cm           INT,
    product_width_cm            INT
);

-- Sellers
CREATE TABLE IF NOT EXISTS olist_sellers (
    seller_id               VARCHAR(64) PRIMARY KEY,
    seller_zip_code_prefix  VARCHAR(10),
    seller_city             VARCHAR(100),
    seller_state            VARCHAR(2)
);

-- Order Items
CREATE TABLE IF NOT EXISTS olist_order_items (
    order_id            VARCHAR(64) REFERENCES olist_orders(order_id),
    order_item_id       INT,
    product_id          VARCHAR(64) REFERENCES olist_products(product_id),
    seller_id           VARCHAR(64) REFERENCES olist_sellers(seller_id),
    shipping_limit_date TIMESTAMP,
    price               NUMERIC(10,2),
    freight_value       NUMERIC(10,2),
    PRIMARY KEY (order_id, order_item_id)
);

-- Order Payments
CREATE TABLE IF NOT EXISTS olist_order_payments (
    order_id              VARCHAR(64) REFERENCES olist_orders(order_id),
    payment_sequential    INT,
    payment_type          VARCHAR(30),
    payment_installments  INT,
    payment_value         NUMERIC(10,2),
    PRIMARY KEY (order_id, payment_sequential)
);

-- Order Reviews
CREATE TABLE IF NOT EXISTS olist_order_reviews (
    review_id               VARCHAR(64) PRIMARY KEY,
    order_id                VARCHAR(64) REFERENCES olist_orders(order_id),
    review_score            INT,
    review_comment_title    TEXT,
    review_comment_message  TEXT,
    review_creation_date    TIMESTAMP,
    review_answer_timestamp TIMESTAMP
);

-- Geolocation
CREATE TABLE IF NOT EXISTS olist_geolocation (
    geolocation_zip_code_prefix  VARCHAR(10),
    geolocation_lat              NUMERIC(12,8),
    geolocation_lng              NUMERIC(12,8),
    geolocation_city             VARCHAR(100),
    geolocation_state            VARCHAR(2)
);

-- Product Category Translation
CREATE TABLE IF NOT EXISTS product_category_name_translation (
    product_category_name          VARCHAR(100) PRIMARY KEY,
    product_category_name_english  VARCHAR(100)
);

-- ── Indexes for common query patterns ─────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_orders_customer  ON olist_orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status    ON olist_orders(order_status);
CREATE INDEX IF NOT EXISTS idx_orders_purchase  ON olist_orders(order_purchase_timestamp);
CREATE INDEX IF NOT EXISTS idx_items_product    ON olist_order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_items_seller     ON olist_order_items(seller_id);
CREATE INDEX IF NOT EXISTS idx_payments_order   ON olist_order_payments(order_id);
CREATE INDEX IF NOT EXISTS idx_reviews_order    ON olist_order_reviews(order_id);
