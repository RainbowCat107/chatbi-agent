from app.agents.nl2sql_agent import run_nl2sql

questions = [
    "请帮我分析销量最高的前五个品类",
    "请分析华东地区近三个月销售趋势"
]

for q in questions:
    print("=" * 80)
    print("QUESTION:", q)
    resp = run_nl2sql(q)
    print("SQL:", resp["sql"])
    print("SUMMARY:", resp["summary"])
    print("CHART:", resp["chart"])
