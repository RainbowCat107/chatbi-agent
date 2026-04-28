from app.agents.planner import build_agent_plan
from app.tools.schema_tool import get_schema, get_schema_text
from app.tools.sql_tool import execute_sql
from app.tools.sql_audit import audit_sql
from app.services.llm_service import (
    build_nl2sql_prompt,
    generate_sql,  
    fix_sql,       
    extract_sql,
)
from app.services.analysis_service import generate_chart, summarize_result


def run_nl2sql(question: str, history: list = None, max_retry: int = 2):
    schema = get_schema()
    schema_text = get_schema_text()
    agent_plan = build_agent_plan(question, schema)
    prompt = build_nl2sql_prompt(question, schema_text, agent_plan)

    if agent_plan["should_refuse"]:
        llm_output = agent_plan["refusal_sql"]
    else:
        llm_output = generate_sql(question, schema_text, history, agent_plan)
    sql = extract_sql(llm_output)

    attempts = []
    result = None
    final_sql = sql

    for attempt_idx in range(max_retry + 1):
        audit_report = audit_sql(final_sql, question=question, schema=schema)
        if audit_report["success"]:
            result = execute_sql(final_sql)
        else:
            result = {
                "success": False,
                "error": "；".join(audit_report["errors"]),
                "sql": final_sql,
                "rows": [],
                "columns": [],
                "row_count": 0,
            }

        attempts.append({
            "attempt": attempt_idx + 1,
            "sql": final_sql,
            "success": result["success"],
            "error": result["error"],
            "audit": audit_report,
        })

        if result["success"]:
            break

        if attempt_idx < max_retry and not agent_plan["should_refuse"]:
            fixed_sql = fix_sql(
                question=question,
                schema_text=schema_text,
                bad_sql=final_sql,
                error_message=result["error"] or "",
                audit_report=audit_report,
                agent_plan=agent_plan,
            )
            final_sql = extract_sql(fixed_sql)

    chart_info = generate_chart(result) if result else {
        "chart_path": None,
        "chart_type": "none",
        "message": "无结果，无法生成图表"
    }
    summary = summarize_result(question, result) if result else "查询失败，无法总结。"

    return {
        "question": question,
        "agent_plan": agent_plan,
        "prompt": prompt,
        "llm_output": llm_output,
        "sql": final_sql,
        "result": result,
        "chart": chart_info,
        "summary": summary,
        "attempts": attempts,
    }
