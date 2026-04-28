from app.agents.nl2sql_agent import run_nl2sql

questions = [
    "请按品类统计GMV最高的前五名",
    "请按月份统计销售额趋势",
    "请分析华东地区各城市GMV",
    "请统计各渠道GMV排名",
    "请计算本月利润",
]

for q in questions:
    print("=" * 80)
    print("QUESTION:", q)
    resp = run_nl2sql(q)
    print("SQL:", resp["sql"])
    print("SUMMARY:", resp["summary"])
    print("CHART:", resp["chart"])
