from app.tools.schema_tool import get_schema_text
from app.tools.sql_tool import execute_sql
from app.services.llm_service import (
    build_nl2sql_prompt,
    mock_generate_sql,
    mock_fix_sql,
    extract_sql,
)
from app.services.analysis_service import generate_chart, summarize_result


def run_nl2sql(question: str, max_retry: int = 2):
    schema_text = get_schema_text()
    prompt = build_nl2sql_prompt(question, schema_text)

    llm_output = mock_generate_sql(question, schema_text)
    sql = extract_sql(llm_output)

    attempts = []
    result = None
    final_sql = sql

    for attempt_idx in range(max_retry + 1):
        result = execute_sql(final_sql)
        attempts.append({
            "attempt": attempt_idx + 1,
            "sql": final_sql,
            "success": result["success"],
            "error": result["error"],
        })

        if result["success"]:
            break

        if attempt_idx < max_retry:
            fixed_sql = mock_fix_sql(
                question=question,
                schema_text=schema_text,
                bad_sql=final_sql,
                error_message=result["error"] or ""
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
        "prompt": prompt,
        "llm_output": llm_output,
        "sql": final_sql,
        "result": result,
        "chart": chart_info,
        "summary": summary,
        "attempts": attempts,
    }