import re
from typing import Optional

import sqlparse

from app.tools.schema_tool import get_schema


ALLOWED_START_TOKENS = {"SELECT", "WITH"}
FORBIDDEN_KEYWORDS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "REPLACE",
    "ATTACH",
    "DETACH",
    "PRAGMA",
}
TABLE_REF_PATTERN = re.compile(
    r"\b(?:FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:AS\s+)?([A-Za-z_][A-Za-z0-9_]*)?",
    re.IGNORECASE,
)
QUALIFIED_COLUMN_PATTERN = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\b")
CTE_PATTERN = re.compile(r"\bWITH\s+([A-Za-z_][A-Za-z0-9_]*)\s+AS\s*\(", re.IGNORECASE)
JOIN_STOP_WORDS = {
    "ON",
    "WHERE",
    "JOIN",
    "LEFT",
    "RIGHT",
    "INNER",
    "OUTER",
    "FULL",
    "CROSS",
    "GROUP",
    "ORDER",
    "LIMIT",
    "UNION",
}
REGION_NAME_VALUES = ["华东", "华南", "华北", "西南"]


def _format_sql(sql: str) -> str:
    return sqlparse.format(sql or "", strip_comments=True).strip()


def _is_refusal_sql(sql: str) -> bool:
    upper_sql = _format_sql(sql).upper()
    return upper_sql.startswith("SELECT") and " AS MESSAGE" in upper_sql and ("无法" in sql or "缺乏" in sql)


def _extract_cte_names(sql: str) -> set[str]:
    return {match.group(1) for match in CTE_PATTERN.finditer(sql)}


def _extract_table_refs(sql: str) -> tuple[list[str], dict[str, str]]:
    tables = []
    alias_map = {}

    for match in TABLE_REF_PATTERN.finditer(sql):
        table = match.group(1)
        alias = match.group(2)
        tables.append(table)

        alias_map[table] = table
        if alias and alias.upper() not in JOIN_STOP_WORDS:
            alias_map[alias] = table

    return tables, alias_map


def _schema_column_map(schema: dict) -> dict[str, set[str]]:
    return {
        table: {column["name"] for column in info.get("columns", [])}
        for table, info in schema.items()
    }


def _has_valid_order_filter(sql: str) -> bool:
    upper_sql = _format_sql(sql).upper()
    status = r"(?:[A-Z_][A-Z0-9_]*\.)?ORDER_STATUS"
    in_20_30 = rf"{status}\s+IN\s*\(\s*(20\s*,\s*30|30\s*,\s*20)\s*\)"
    or_20_30 = rf"{status}\s*=\s*20\s+OR\s+{status}\s*=\s*30"
    return bool(re.search(in_20_30, upper_sql) or re.search(or_20_30, upper_sql))


def _has_refund_filter(sql: str) -> bool:
    upper_sql = _format_sql(sql).upper()
    return bool(re.search(r"(?:[A-Z_][A-Z0-9_]*\.)?ORDER_STATUS\s*=\s*40", upper_sql))


def _has_binary_filter(sql: str, column: str, value: int) -> bool:
    upper_sql = _format_sql(sql).upper()
    pattern = rf"(?:[A-Z_][A-Z0-9_]*\.)?{column.upper()}\s*=\s*{value}"
    return bool(re.search(pattern, upper_sql))


def _question_contains_any(question: str, keywords: list[str]) -> bool:
    return any(keyword in question for keyword in keywords)


def _region_value_errors(sql: str, question: str) -> list[str]:
    errors = []
    for value in REGION_NAME_VALUES:
        if value not in question:
            continue

        has_region_filter = re.search(
            rf"\b(?:[A-Za-z_][A-Za-z0-9_]*\.)?region_name\s*=\s*['\"]{re.escape(value)}['\"]",
            sql,
            re.IGNORECASE,
        ) or re.search(
            rf"\b(?:[A-Za-z_][A-Za-z0-9_]*\.)?region_name\s+IN\s*\([^)]*['\"]{re.escape(value)}['\"][^)]*\)",
            sql,
            re.IGNORECASE,
        )
        has_wrong_filter = re.search(
            rf"\b(?:[A-Za-z_][A-Za-z0-9_]*\.)?(?:province_name|city_name)\s*=\s*['\"]{re.escape(value)}['\"]",
            sql,
            re.IGNORECASE,
        )

        if has_wrong_filter or not has_region_filter:
            errors.append(
                f"{value} 是大区名称，地区过滤必须使用 dim_region_info.region_name = '{value}'，"
                f"不能使用 province_name/city_name = '{value}'"
            )

    return errors


def audit_sql(sql: str, question: str = "", schema: Optional[dict] = None, strict_business: bool = True) -> dict:
    if schema is None:
        schema = get_schema()

    errors = []
    warnings = []
    checks = {}
    formatted = _format_sql(sql)
    upper_sql = formatted.upper()

    if not formatted:
        errors.append("SQL 不能为空")
        return {"success": False, "errors": errors, "warnings": warnings, "checks": checks}

    statements = [stmt for stmt in sqlparse.split(formatted) if stmt.strip()]
    checks["single_statement"] = len(statements) == 1
    if len(statements) != 1:
        errors.append("仅允许单条 SQL 语句")

    first_token = upper_sql.split()[0] if upper_sql.split() else ""
    checks["readonly_start"] = first_token in ALLOWED_START_TOKENS
    if first_token not in ALLOWED_START_TOKENS:
        errors.append(f"仅允许 SELECT / WITH 查询，当前起始语句为: {first_token}")

    forbidden_hits = sorted(
        keyword for keyword in FORBIDDEN_KEYWORDS if re.search(rf"\b{keyword}\b", upper_sql)
    )
    checks["forbidden_keywords"] = forbidden_hits
    if forbidden_hits:
        errors.append("检测到非法关键字: " + ", ".join(forbidden_hits))

    cte_names = _extract_cte_names(formatted)
    table_refs, alias_map = _extract_table_refs(formatted)
    schema_columns = _schema_column_map(schema)
    schema_tables = set(schema_columns)
    unknown_tables = sorted({table for table in table_refs if table not in schema_tables and table not in cte_names})
    checks["table_refs"] = table_refs
    checks["unknown_tables"] = unknown_tables
    if unknown_tables:
        errors.append("SQL 使用了不存在的表: " + ", ".join(unknown_tables))

    unknown_columns = []
    for alias, column in QUALIFIED_COLUMN_PATTERN.findall(formatted):
        if alias in alias_map:
            table = alias_map[alias]
            if table in schema_columns and column not in schema_columns[table]:
                unknown_columns.append(f"{alias}.{column}")
        elif alias in schema_columns:
            if column not in schema_columns[alias]:
                unknown_columns.append(f"{alias}.{column}")
        elif alias.upper() not in {"DATE", "DATETIME", "STRFTIME"}:
            warnings.append(f"无法确认别名或表名: {alias}")

    checks["unknown_columns"] = sorted(set(unknown_columns))
    if unknown_columns:
        errors.append("SQL 使用了不存在的字段: " + ", ".join(sorted(set(unknown_columns))))

    if strict_business and not _is_refusal_sql(formatted):
        uses_order = "DWD_TRADE_ORDER" in upper_sql
        uses_user = "DIM_USER_INFO" in upper_sql
        uses_sku = "DIM_SKU_INFO" in upper_sql

        asks_sales = _question_contains_any(
            question, ["销售额", "销售", "销量", "GMV", "gmv", "收入", "业绩", "成交额"]
        )
        asks_refund = _question_contains_any(question, ["退款", "退货", "售后"])
        asks_profit = _question_contains_any(question, ["利润", "毛利", "毛利率", "成本"])

        checks["valid_order_filter"] = not (uses_order and asks_sales) or _has_valid_order_filter(formatted)
        if uses_order and asks_sales and not checks["valid_order_filter"]:
            errors.append("销售/GMV/销量类查询必须过滤有效订单: order_status IN (20, 30)")

        checks["refund_order_filter"] = not (uses_order and asks_refund) or _has_refund_filter(formatted)
        if uses_order and asks_refund and not checks["refund_order_filter"]:
            errors.append("退款/售后类查询必须过滤退款订单: order_status = 40")

        checks["active_user_filter"] = not uses_user or _has_binary_filter(formatted, "is_deleted", 0)
        if uses_user and not checks["active_user_filter"]:
            errors.append("关联用户信息时必须过滤有效用户: is_deleted = 0")

        asks_off_sale = _question_contains_any(question, ["下架", "停售", "未上架"])
        checks["on_sale_sku_filter"] = (
            not uses_sku or asks_off_sale or _has_binary_filter(formatted, "is_on_sale", 1)
        )
        if uses_sku and not asks_off_sale and not checks["on_sale_sku_filter"]:
            errors.append("关联商品信息时必须过滤在售商品: is_on_sale = 1")

        region_errors = _region_value_errors(formatted, question)
        checks["region_value_filter"] = len(region_errors) == 0
        errors.extend(region_errors)

        checks["profit_refusal"] = not asks_profit
        if asks_profit:
            errors.append("当前数据库缺少成本字段，利润类问题必须拒答")

    return {
        "success": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
    }
