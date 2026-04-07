import sqlparse
import pandas as pd
from app.core.database import get_connection

ALLOWED_START_TOKENS = {"SELECT", "WITH"}
FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
    "TRUNCATE", "CREATE", "REPLACE", "ATTACH", "DETACH",
    "PRAGMA"
}

def is_safe_sql(sql: str):
    if not sql or not sql.strip():
        return False, "SQL 不能为空"

    formatted = sqlparse.format(sql, strip_comments=True).strip()
    upper_sql = formatted.upper()

    first_token = upper_sql.split()[0] if upper_sql.split() else ""
    if first_token not in ALLOWED_START_TOKENS:
        return False, f"仅允许 SELECT / WITH 查询，当前起始语句为: {first_token}"

    for keyword in FORBIDDEN_KEYWORDS:
        if keyword in upper_sql:
            return False, f"检测到非法关键字: {keyword}"

    if ";" in formatted[:-1]:
        return False, "仅允许单条 SQL 语句"

    return True, "ok"

def execute_sql(sql: str, limit: int = 200):
    safe, msg = is_safe_sql(sql)
    if not safe:
        return {
            "success": False,
            "error": msg,
            "sql": sql,
            "rows": [],
            "columns": [],
            "row_count": 0,
        }

    try:
        conn = get_connection()
        df = pd.read_sql_query(sql, conn)
        conn.close()

        if len(df) > limit:
            df = df.head(limit)

        return {
            "success": True,
            "error": None,
            "sql": sql,
            "columns": df.columns.tolist(),
            "rows": df.to_dict(orient="records"),
            "row_count": len(df),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "sql": sql,
            "rows": [],
            "columns": [],
            "row_count": 0,
        }
