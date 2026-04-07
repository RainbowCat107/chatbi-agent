from app.agents.nl2sql_agent import run_nl2sql

question = "请帮我分析销量最高的前五个品类"

resp = run_nl2sql(question)

print("========== QUESTION ==========")
print(resp["question"])

print("\n========== GENERATED SQL ==========")
print(resp["sql"])

print("\n========== RESULT ==========")
print(resp["result"])
