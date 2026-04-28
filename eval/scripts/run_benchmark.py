import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from app.agents.nl2sql_agent import run_nl2sql


DEFAULT_DATASET = ROOT_DIR / "eval" / "datasets" / "nl2sql_benchmark.jsonl"
DEFAULT_REPORT_DIR = ROOT_DIR / "eval" / "reports"


def load_jsonl(path: Path) -> list[dict]:
    items = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def normalize_text(text: str) -> str:
    return " ".join((text or "").replace("\n", " ").split()).lower()


def contains_keyword(text: str, keyword: str) -> bool:
    normalized_text = normalize_text(text)
    normalized_keyword = normalize_text(keyword)
    compact_text = normalized_text.replace(" ", "")
    compact_keyword = normalized_keyword.replace(" ", "")
    return normalized_keyword in normalized_text or compact_keyword in compact_text


def score_keywords(sql: str, required: list[str], forbidden: list[str]) -> tuple[float, list[str], list[str]]:
    missing = [keyword for keyword in required if not contains_keyword(sql, keyword)]
    forbidden_hits = [keyword for keyword in forbidden if contains_keyword(sql, keyword)]

    required_score = 1.0
    if required:
        required_score = (len(required) - len(missing)) / len(required)

    forbidden_score = 0.0 if forbidden_hits else 1.0
    return round((required_score + forbidden_score) / 2, 4), missing, forbidden_hits


def is_refusal(resp: dict) -> bool:
    sql = resp.get("sql", "")
    rows = (resp.get("result") or {}).get("rows", [])
    row_text = json.dumps(rows, ensure_ascii=False)
    return "AS message" in sql or "as message" in sql.lower() or "无法" in row_text or "缺乏" in row_text


def response_contains(resp: dict, substrings: list[str]) -> tuple[bool, list[str]]:
    text = json.dumps(resp, ensure_ascii=False)
    missing = [item for item in substrings if item not in text]
    return len(missing) == 0, missing


def evaluate_case(case: dict) -> dict:
    start = time.time()
    resp = run_nl2sql(case["question"])
    latency = round(time.time() - start, 3)
    sql = resp.get("sql", "")
    result = resp.get("result") or {}
    chart = resp.get("chart") or {}
    attempts = resp.get("attempts") or []
    final_audit = attempts[-1].get("audit", {}) if attempts else {}

    keyword_score, missing_keywords, forbidden_hits = score_keywords(
        sql,
        case.get("required_sql_keywords", []),
        case.get("forbidden_sql_keywords", []),
    )

    expected_chart_types = case.get("expected_chart_type", [])
    chart_ok = True
    if expected_chart_types:
        chart_ok = chart.get("chart_type") in expected_chart_types

    expected_refusal = bool(case.get("should_refuse", False))
    refusal_ok = is_refusal(resp) if expected_refusal else not is_refusal(resp)
    response_ok, missing_response = response_contains(resp, case.get("expected_response_substrings", []))

    execution_ok = bool(result.get("success", False))
    audit_ok = bool(final_audit.get("success", False))
    passed = all([keyword_score == 1.0, refusal_ok, response_ok, execution_ok, audit_ok, chart_ok])

    return {
        "id": case["id"],
        "question": case["question"],
        "passed": passed,
        "latency_sec": latency,
        "sql": sql,
        "summary": resp.get("summary"),
        "keyword_score": keyword_score,
        "missing_keywords": missing_keywords,
        "forbidden_hits": forbidden_hits,
        "execution_ok": execution_ok,
        "audit_ok": audit_ok,
        "refusal_ok": refusal_ok,
        "response_ok": response_ok,
        "missing_response_substrings": missing_response,
        "chart_ok": chart_ok,
        "chart_type": chart.get("chart_type"),
        "attempt_count": len(attempts),
        "agent_plan": resp.get("agent_plan"),
        "errors": result.get("error"),
    }


def summarize(results: list[dict]) -> dict:
    total = len(results)
    if total == 0:
        return {}

    latencies = [item["latency_sec"] for item in results if item.get("latency_sec") is not None]
    return {
        "total": total,
        "pass_rate": round(sum(item["passed"] for item in results) / total, 4),
        "execution_success_rate": round(sum(item["execution_ok"] for item in results) / total, 4),
        "audit_success_rate": round(sum(item["audit_ok"] for item in results) / total, 4),
        "refusal_accuracy": round(sum(item["refusal_ok"] for item in results) / total, 4),
        "avg_keyword_score": round(sum(item["keyword_score"] for item in results) / total, 4),
        "avg_latency_sec": round(sum(latencies) / len(latencies), 3) if latencies else None,
        "avg_attempt_count": round(sum(item["attempt_count"] for item in results) / total, 3),
    }


def write_reports(summary: dict, results: list[dict], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"benchmark_{ts}.json"
    md_path = output_dir / f"benchmark_{ts}.md"

    payload = {"summary": summary, "results": results}
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# ChatBI Agent Benchmark Report",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")

    lines.extend(["", "## Cases", ""])
    for item in results:
        status = "PASS" if item["passed"] else "FAIL"
        lines.extend(
            [
                f"### {item['id']} - {status}",
                "",
                f"- question: {item['question']}",
                f"- keyword_score: {item['keyword_score']}",
                f"- execution_ok: {item['execution_ok']}",
                f"- audit_ok: {item['audit_ok']}",
                f"- refusal_ok: {item['refusal_ok']}",
                f"- chart_type: {item['chart_type']}",
                f"- latency_sec: {item['latency_sec']}",
                "",
                "```sql",
                item["sql"],
                "```",
                "",
            ]
        )
        if item["missing_keywords"] or item["forbidden_hits"] or item["errors"]:
            lines.append(f"- missing_keywords: {item['missing_keywords']}")
            lines.append(f"- forbidden_hits: {item['forbidden_hits']}")
            lines.append(f"- errors: {item['errors']}")
            lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def main():
    parser = argparse.ArgumentParser(description="Run ChatBI Agent NL2SQL benchmark.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET), help="Path to JSONL benchmark dataset.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR), help="Directory to write reports.")
    parser.add_argument("--limit", type=int, default=None, help="Only run the first N cases.")
    args = parser.parse_args()

    dataset = load_jsonl(Path(args.dataset))
    if args.limit:
        dataset = dataset[: args.limit]

    results = []
    for idx, case in enumerate(dataset, start=1):
        print(f"[{idx}/{len(dataset)}] {case['id']}: {case['question']}")
        try:
            results.append(evaluate_case(case))
        except Exception as exc:
            results.append(
                {
                    "id": case["id"],
                    "question": case["question"],
                    "passed": False,
                    "latency_sec": None,
                    "sql": "",
                    "summary": "",
                    "keyword_score": 0,
                    "missing_keywords": case.get("required_sql_keywords", []),
                    "forbidden_hits": [],
                    "execution_ok": False,
                    "audit_ok": False,
                    "refusal_ok": False,
                    "response_ok": False,
                    "missing_response_substrings": case.get("expected_response_substrings", []),
                    "chart_ok": False,
                    "chart_type": None,
                    "attempt_count": 0,
                    "agent_plan": None,
                    "errors": str(exc),
                }
            )

    summary = summarize(results)
    json_path, md_path = write_reports(summary, results, Path(args.report_dir))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {md_path}")


if __name__ == "__main__":
    main()
