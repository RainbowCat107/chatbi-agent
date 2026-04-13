from app.tools.schema_tool import get_schema_text
from app.tools.sql_tool import execute_sql

print("========== SCHEMA ==========")
print(get_schema_text())

print("\n========== SQL RESULT ==========")
sql = """
SELECT p.category, SUM(o.sales_amount) AS total_sales
FROM orders o
JOIN products p ON o.product_id = p.product_id
GROUP BY p.category
ORDER BY total_sales DESC
LIMIT 5
"""
result = execute_sql(sql)
print(result)
