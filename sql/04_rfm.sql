-- 04_rfm.sql — 回答 Q3：誰快要流失、誰已經流失？
-- Olist 上 Frequency 幾乎全為 1（見規劃書轉折二），故分層以 R×M 為主，F 保留供描述。
-- r_quartile：1 = 最近才買；m_quartile：1 = 金額最高。快照日 = 窗口內最後一筆訂單日。

WITH snapshot AS (
  SELECT MAX(purchased_at) AS snap_at FROM base_orders
),
cust AS (
  SELECT customer_unique_id,
         MAX(purchased_at) AS last_at,
         COUNT(*)          AS frequency,
         SUM(gmv)          AS monetary
  FROM base_orders
  GROUP BY 1
)
SELECT c.customer_unique_id,
       datediff('day', c.last_at, s.snap_at) AS recency_days,
       c.frequency,
       c.monetary,
       NTILE(4) OVER (ORDER BY datediff('day', c.last_at, s.snap_at) ASC)  AS r_quartile,
       NTILE(4) OVER (ORDER BY c.monetary DESC)                            AS m_quartile
FROM cust c, snapshot s;
