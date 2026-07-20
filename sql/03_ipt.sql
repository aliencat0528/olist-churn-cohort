-- 03_ipt.sql — 回答 Q1：客人多久回來一次？（churn 定義的依據）
-- inter-purchase time：同一客戶相鄰兩單的間隔天數。
-- 同日重複下單（間隔 0 天）不計入回購節奏，數量另行記錄於 DATA_NOTES。

WITH seq AS (
  SELECT customer_unique_id,
         purchased_at,
         LAG(purchased_at) OVER (
           PARTITION BY customer_unique_id ORDER BY purchased_at
         ) AS prev_at
  FROM base_orders
)
SELECT datediff('day', prev_at, purchased_at) AS ipt_days
FROM seq
WHERE prev_at IS NOT NULL
  AND datediff('day', prev_at, purchased_at) > 0;
