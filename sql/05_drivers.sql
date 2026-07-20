-- 05_drivers.sql — 回答 Q4：客人為什麼不回來？
-- 一列 = 一位客戶的「首購體驗」＋ 是否在 {horizon} 天內回購。
-- 右側截斷處理：首購日晚於（窗口終點 − {horizon} 天）的客戶排除，
-- 否則「還沒來得及回購」會被誤判成「沒回購」。
-- 首購當日多筆訂單時取 gmv 最大的一筆代表首購體驗。

WITH firsts AS (
  SELECT customer_unique_id, MIN(purchased_at) AS first_at
  FROM base_orders
  GROUP BY 1
  HAVING MIN(purchased_at) <= CAST('{end}' AS TIMESTAMP) - INTERVAL {horizon} DAY
),
first_orders AS (
  SELECT b.*, f.first_at,
         ROW_NUMBER() OVER (
           PARTITION BY b.customer_unique_id ORDER BY b.gmv DESC
         ) AS rn
  FROM base_orders b
  JOIN firsts f
    ON b.customer_unique_id = f.customer_unique_id
   AND b.purchased_at = f.first_at
),
rep AS (
  SELECT f.customer_unique_id,
         MAX(CASE WHEN b2.purchased_at >  f.first_at
                   AND b2.purchased_at <= f.first_at + INTERVAL {horizon} DAY
                  THEN 1 ELSE 0 END) AS repurchased
  FROM firsts f
  LEFT JOIN base_orders b2 USING (customer_unique_id)
  GROUP BY 1
)
SELECT fo.customer_unique_id,
       fo.customer_state,
       fo.gmv,
       fo.freight_ratio,
       fo.review_score,
       CASE WHEN fo.delivered_at IS NULL THEN NULL
            WHEN fo.delivered_at > fo.estimated_at THEN 1 ELSE 0 END AS late_delivery,
       r.repurchased
FROM first_orders fo
JOIN rep r USING (customer_unique_id)
WHERE fo.rn = 1;
