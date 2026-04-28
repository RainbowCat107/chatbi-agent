from app.tools.schema_tool import get_schema_text
from app.tools.sql_tool import execute_sql

print("========== SCHEMA ==========")
print(get_schema_text())

print("\n========== SQL RESULT ==========")
sql = """
SELECT s.cat_name, SUM(o.pay_amount) AS total_gmv
FROM dwd_trade_order o
JOIN dim_sku_info s ON o.sku_id = s.sku_id
WHERE o.order_status IN (20, 30)
  AND s.is_on_sale = 1
GROUP BY s.cat_name
ORDER BY total_gmv DESC
LIMIT 5
"""
result = execute_sql(sql)
print(result)
