import re


def build_nl2sql_prompt(question: str, schema_text: str) -> str:
    return f"""
你是一个专业的数据分析 SQL 助手。
请基于给定的数据库 Schema，将用户问题转换为 SQLite 可执行的 SQL。

要求：
1. 只能输出一条 SQL，不要输出解释。
2. SQL 必须是 SQLite 语法。
3. 只允许使用 schema 中存在的表和字段。
4. 如需聚合，请正确使用 GROUP BY。
5. 默认只读查询，不能包含 INSERT/UPDATE/DELETE/DROP 等语句。

数据库 Schema:
{schema_text}

用户问题:
{question}

请直接输出 SQL:
""".strip()


def mock_generate_sql(question: str, schema_text: str) -> str:
    q = question.lower()

    # 故意增加一个带有错误的 SQL 场景
    if "测试报错修复" in question:
        return """
SELECT category_name, SUM(sales_amount) AS total_sales
FROM orders
GROUP BY category_name
ORDER BY total_sales DESC
LIMIT 5
""".strip()

    # 其他正常场景
    if "销量最高" in question and ("品类" in question or "类别" in question):
        return """
SELECT p.category, SUM(o.sales_amount) AS total_sales
FROM orders o
JOIN products p ON o.product_id = p.product_id
GROUP BY p.category
ORDER BY total_sales DESC
LIMIT 5
""".strip()

    if "华东" in question and ("趋势" in question or "近三个月" in question):
        return """
SELECT substr(o.order_date, 1, 7) AS month, SUM(o.sales_amount) AS total_sales
FROM orders o
JOIN regions r ON o.region_id = r.region_id
WHERE r.region_name = '华东'
  AND o.order_date >= '2024-10-01'
  AND o.order_date < '2025-01-01'
GROUP BY substr(o.order_date, 1, 7)
ORDER BY month
""".strip()

    return """
SELECT p.category, SUM(o.sales_amount) AS total_sales
FROM orders o
JOIN products p ON o.product_id = p.product_id
GROUP BY p.category
ORDER BY total_sales DESC
LIMIT 10
""".strip()

def mock_fix_sql(question: str, schema_text: str, bad_sql: str, error_message: str) -> str:
    # 如果遇到 no such column 或 category_name 错误
    if "no such column" in error_message.lower() or "category_name" in bad_sql.lower():
        return """
SELECT p.category, SUM(o.sales_amount) AS total_sales
FROM orders o
JOIN products p ON o.product_id = p.product_id
GROUP BY p.category
ORDER BY total_sales DESC
LIMIT 5
""".strip()

    return bad_sql


def extract_sql(text: str) -> str:
    text = text.strip()

    code_block_match = re.search(r"```sql\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if code_block_match:
        return code_block_match.group(1).strip()

    code_block_match = re.search(r"```\s*(.*?)```", text, re.DOTALL)
    if code_block_match:
        return code_block_match.group(1).strip()

    return text