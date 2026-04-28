from app.agents.nl2sql_agent import run_nl2sql

question = "请按品类统计GMV最高的前五名"

resp = run_nl2sql(question)

print("========== QUESTION ==========")
print(resp["question"])

print("\n========== GENERATED SQL ==========")
print(resp["sql"])

print("\n========== RESULT ==========")
print(resp["result"])
