from typing import Optional

from app.tools.schema_tool import get_schema


PROFIT_REFUSAL_SQL = "SELECT '缺乏成本数据，无法计算利润' AS message;"
MISSING_DIMENSION_REFUSAL_SQL = "SELECT '当前数据库缺乏相关维度数据，无法满足该查询' AS message;"


TERM_RULES = {
    "sales": {
        "keywords": ["销售额", "销售", "销量", "GMV", "gmv", "收入", "业绩", "成交额"],
        "linked_fields": [
            "dwd_trade_order.pay_amount",
            "dwd_trade_order.order_status",
            "dwd_trade_order.create_time",
        ],
        "required_rules": ["valid_order_filter"],
    },
    "refund": {
        "keywords": ["退款", "退货", "售后"],
        "linked_fields": ["dwd_trade_order.order_status", "dwd_trade_order.pay_amount"],
        "required_rules": ["refund_order_filter"],
    },
    "user": {
        "keywords": ["用户", "会员", "注册", "vip", "VIP"],
        "linked_fields": ["dim_user_info.uid", "dim_user_info.reg_time", "dim_user_info.is_deleted"],
        "required_rules": ["active_user_filter"],
    },
    "sku": {
        "keywords": ["商品", "品类", "类目", "sku", "SKU", "spu", "SPU"],
        "linked_fields": ["dim_sku_info.sku_id", "dim_sku_info.cat_name", "dim_sku_info.is_on_sale"],
        "required_rules": ["on_sale_sku_filter"],
    },
    "region": {
        "keywords": ["地区", "区域", "省份", "省", "城市", "华东", "华南", "华北", "西南"],
        "linked_fields": ["dim_region_info.region_name", "dim_region_info.province_name", "dim_region_info.city_name"],
        "required_rules": [],
    },
    "channel": {
        "keywords": ["渠道", "来源", "小程序", "直播", "APP", "app"],
        "linked_fields": ["dim_channel_info.channel_name"],
        "required_rules": [],
    },
}

UNAVAILABLE_DIMENSIONS = {
    "supplier": ["供应商", "供货商", "厂家", "厂商", "品牌商"],
    "address": ["地址", "收货地址", "门店地址", "详细地址"],
    "inventory": ["库存", "仓库", "入库", "出库"],
}

REGION_NAME_VALUES = ["华东", "华南", "华北", "西南"]
CHANNEL_NAME_VALUES = ["APP", "app", "小程序", "直播间", "官网", "线下门店"]


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _schema_columns(schema: dict) -> set[str]:
    columns = set()
    for table_info in schema.values():
        for column in table_info.get("columns", []):
            columns.add(column["name"])
    return columns


def _schema_has_any(schema: dict, names: list[str]) -> bool:
    available = set(schema.keys()) | _schema_columns(schema)
    return any(name in available for name in names)


def _infer_intent(question: str) -> str:
    if _contains_any(question, ["趋势", "走势", "按月", "每日", "每天", "近三个月", "最近"]):
        return "trend"
    if _contains_any(question, ["top", "Top", "TOP", "最高", "最低", "前", "排名", "排行"]):
        return "ranking"
    if _contains_any(question, ["占比", "比例", "分布"]):
        return "distribution"
    if _contains_any(question, ["多少", "总计", "统计", "求和"]):
        return "metric"
    return "ad_hoc_query"


def build_agent_plan(question: str, schema: Optional[dict] = None) -> dict:
    """Create a deterministic plan before asking the LLM to write SQL.

    The plan is intentionally lightweight: it gives the model schema-linking hints,
    surfaces mandatory business rules, and blocks questions that the current
    warehouse cannot answer.
    """
    if schema is None:
        schema = get_schema()

    linked_terms = []
    linked_fields = []
    required_rules = []
    value_hints = []

    for term_name, config in TERM_RULES.items():
        if _contains_any(question, config["keywords"]):
            linked_terms.append(term_name)
            linked_fields.extend(config["linked_fields"])
            required_rules.extend(config["required_rules"])

    missing_dimensions = []
    for dim_name, keywords in UNAVAILABLE_DIMENSIONS.items():
        if _contains_any(question, keywords):
            missing_dimensions.append(dim_name)

    if "region" in linked_terms and not _schema_has_any(
        schema, ["dim_region_info", "region_name", "province_name", "city_name"]
    ):
        missing_dimensions.append("region")

    if "channel" in linked_terms and not _schema_has_any(schema, ["dim_channel_info", "channel_name"]):
        missing_dimensions.append("channel")

    for value in REGION_NAME_VALUES:
        if value in question:
            value_hints.append({
                "value": value,
                "field": "dim_region_info.region_name",
                "note": f"{value} 是大区名称，必须过滤 region_name = '{value}'，不要写 province_name = '{value}'。",
            })

    for value in CHANNEL_NAME_VALUES:
        if value in question:
            value_hints.append({
                "value": value,
                "field": "dim_channel_info.channel_name",
                "note": f"{value} 是渠道名称，必须过滤 channel_name = '{value}'。",
            })

    if _contains_any(question, ["利润", "毛利", "毛利率", "成本"]):
        return {
            "intent": "refusal",
            "linked_terms": linked_terms,
            "linked_fields": sorted(set(linked_fields)),
            "required_rules": sorted(set(required_rules)),
            "value_hints": value_hints,
            "should_refuse": True,
            "refusal_reason": "cost_data_missing",
            "refusal_sql": PROFIT_REFUSAL_SQL,
        }

    if missing_dimensions:
        return {
            "intent": "refusal",
            "linked_terms": linked_terms,
            "linked_fields": sorted(set(linked_fields)),
            "required_rules": sorted(set(required_rules)),
            "value_hints": value_hints,
            "should_refuse": True,
            "refusal_reason": f"schema_missing_dimensions:{','.join(sorted(set(missing_dimensions)))}",
            "refusal_sql": MISSING_DIMENSION_REFUSAL_SQL,
        }

    return {
        "intent": _infer_intent(question),
        "linked_terms": linked_terms,
        "linked_fields": sorted(set(linked_fields)),
        "required_rules": sorted(set(required_rules)),
        "value_hints": value_hints,
        "should_refuse": False,
        "refusal_reason": None,
        "refusal_sql": None,
    }
