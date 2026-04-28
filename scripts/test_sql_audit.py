from app.tools.sql_audit import audit_sql


cases = [
    (
        "valid_gmv",
        "请按品类统计GMV",
        """
        SELECT s.cat_name, SUM(o.pay_amount) AS total_gmv
        FROM dwd_trade_order o
        JOIN dim_sku_info s ON o.sku_id = s.sku_id
        WHERE o.order_status IN (20, 30)
          AND s.is_on_sale = 1
        GROUP BY s.cat_name
        """,
    ),
    (
        "missing_order_status",
        "请按品类统计GMV",
        """
        SELECT s.cat_name, SUM(o.pay_amount) AS total_gmv
        FROM dwd_trade_order o
        JOIN dim_sku_info s ON o.sku_id = s.sku_id
        WHERE s.is_on_sale = 1
        GROUP BY s.cat_name
        """,
    ),
]

for name, question, sql in cases:
    print("=" * 80)
    print(name)
    print(audit_sql(sql, question))
