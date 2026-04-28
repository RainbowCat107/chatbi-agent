from app.agents.nl2sql_agent import run_nl2sql

resp = run_nl2sql("请按供应商统计GMV")

print("FINAL SQL:")
print(resp["sql"])
print("\nATTEMPTS:")
for item in resp["attempts"]:
    print(item)

print("\nRESULT:")
print(resp["result"])

print("\nSUMMARY:")
print(resp["summary"])
