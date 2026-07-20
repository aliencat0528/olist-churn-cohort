-- 01_validation.sql — 資料驗證（Phase 1，先於任何分析）
-- 每個 SELECT 一項檢查；run_pipeline.py 逐項執行並比對期望值。
-- 各檢查以「@check:」標記行分隔，標記後為檢查名稱。

-- @check: orders_rowcount（期望 99441）
SELECT COUNT(*) AS n FROM raw_orders;

-- @check: order_id_unique（期望 0 重複）
SELECT COUNT(*) - COUNT(DISTINCT order_id) AS dup FROM raw_orders;

-- @check: customer_id_vs_unique_id（陷阱 #1 的量化證據）
SELECT COUNT(DISTINCT customer_id)        AS n_customer_id,
       COUNT(DISTINCT customer_unique_id) AS n_unique_id
FROM raw_customers;

-- @check: status_distribution（delivered 應約 97%）
SELECT order_status, COUNT(*) AS n,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct
FROM raw_orders GROUP BY 1 ORDER BY n DESC;

-- @check: date_bounds（確認 2016 稀疏、2018-09 之後不完整 → 窗口截斷依據）
SELECT date_trunc('month', CAST(order_purchase_timestamp AS TIMESTAMP)) AS month,
       COUNT(*) AS n
FROM raw_orders GROUP BY 1 ORDER BY 1;

-- @check: payment_reconciliation（items+freight vs payments 總額差，門檻見 params；差異來自分期利息與無 items 的取消單）
WITH i AS (SELECT SUM(price + freight_value) AS items_total FROM raw_items),
     p AS (SELECT SUM(payment_value) AS pay_total FROM raw_payments)
SELECT items_total, pay_total,
       ROUND(100.0 * ABS(items_total - pay_total) / pay_total, 3) AS diff_pct
FROM i, p;

-- @check: base_orders_rowcount（窗口內 delivered 訂單數，pipeline 記錄用）
SELECT COUNT(*) AS n, COUNT(DISTINCT customer_unique_id) AS n_customers FROM base_orders;

-- @check: repeat_rate（回購客占比，預期 ~3%，轉折二的證據）
WITH freq AS (
  SELECT customer_unique_id, COUNT(*) AS n_orders
  FROM base_orders GROUP BY 1
)
SELECT COUNT(*) FILTER (WHERE n_orders >= 2)              AS repeat_customers,
       COUNT(*)                                            AS total_customers,
       ROUND(100.0 * COUNT(*) FILTER (WHERE n_orders >= 2) / COUNT(*), 2) AS repeat_pct
FROM freq;

-- @check: delivered_missing_timestamp（delivered 但缺送達時間的訂單數，應極少）
SELECT COUNT(*) AS n FROM raw_orders
WHERE order_status = 'delivered' AND order_delivered_customer_date IS NULL;
