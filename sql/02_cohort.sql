-- 02_cohort.sql — 回答 Q2：哪個月加入的客人品質好？
-- 輸出 long format：cohort_month × month_offset × 活躍客數 × 營收；
-- pandas 端 pivot 成矩陣、除以第 0 月人數得 retention rate。

WITH firsts AS (
  SELECT customer_unique_id, MIN(purchased_at) AS first_at
  FROM base_orders
  GROUP BY 1
),
cohorted AS (
  SELECT b.customer_unique_id,
         b.gmv,
         date_trunc('month', f.first_at) AS cohort_month,
         datediff('month', date_trunc('month', f.first_at),
                           date_trunc('month', b.purchased_at)) AS month_offset
  FROM base_orders b
  JOIN firsts f USING (customer_unique_id)
)
SELECT cohort_month,
       month_offset,
       COUNT(DISTINCT customer_unique_id) AS active_customers,
       SUM(gmv)                           AS revenue
FROM cohorted
GROUP BY 1, 2
ORDER BY 1, 2;
