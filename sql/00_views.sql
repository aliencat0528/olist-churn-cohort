-- 00_views.sql — 建立基礎 view（所有下游查詢的單一入口）
-- 口徑：只留 delivered、分析窗口 {start} ~ {end}（左閉右開）、
--       訂單金額 = SUM(items.price + freight_value)。
-- geolocation 表刻意不建 view：本專案州別分析用 customers.customer_state 即可。

CREATE OR REPLACE VIEW raw_orders    AS SELECT * FROM read_csv_auto('{data_dir}/olist_orders_dataset.csv');
CREATE OR REPLACE VIEW raw_customers AS SELECT * FROM read_csv_auto('{data_dir}/olist_customers_dataset.csv');
CREATE OR REPLACE VIEW raw_items     AS SELECT * FROM read_csv_auto('{data_dir}/olist_order_items_dataset.csv');
CREATE OR REPLACE VIEW raw_payments  AS SELECT * FROM read_csv_auto('{data_dir}/olist_order_payments_dataset.csv');
CREATE OR REPLACE VIEW raw_reviews   AS SELECT * FROM read_csv_auto('{data_dir}/olist_order_reviews_dataset.csv');
CREATE OR REPLACE VIEW raw_products  AS SELECT * FROM read_csv_auto('{data_dir}/olist_products_dataset.csv');
CREATE OR REPLACE VIEW raw_category_translation AS
  SELECT * FROM read_csv_auto('{data_dir}/product_category_name_translation.csv');

-- 一單多列 → 先聚合成單筆訂單金額，join 才不會重複計算（陷阱 #4）
CREATE OR REPLACE VIEW order_gmv AS
SELECT order_id,
       SUM(price + freight_value) AS gmv,
       COUNT(*)                   AS n_items,
       SUM(freight_value) / NULLIF(SUM(price + freight_value), 0) AS freight_ratio
FROM raw_items
GROUP BY order_id;

-- 每單取最新一筆評論（陷阱 #7）
CREATE OR REPLACE VIEW order_review AS
SELECT order_id, review_score
FROM (
  SELECT order_id, review_score,
         ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY review_creation_date DESC) AS rn
  FROM raw_reviews
)
WHERE rn = 1;

-- 主分析表：一列 = 一張已送達訂單，帶真實客戶 id（陷阱 #1）
CREATE OR REPLACE VIEW base_orders AS
SELECT o.order_id,
       c.customer_unique_id,
       c.customer_state,
       CAST(o.order_purchase_timestamp        AS TIMESTAMP) AS purchased_at,
       CAST(o.order_delivered_customer_date   AS TIMESTAMP) AS delivered_at,
       CAST(o.order_estimated_delivery_date   AS TIMESTAMP) AS estimated_at,
       g.gmv, g.n_items, g.freight_ratio,
       r.review_score
FROM raw_orders o
JOIN raw_customers c USING (customer_id)
JOIN order_gmv     g USING (order_id)
LEFT JOIN order_review r USING (order_id)
WHERE o.order_status = 'delivered'
  AND o.order_purchase_timestamp >= '{start}'
  AND o.order_purchase_timestamp <  '{end}';
