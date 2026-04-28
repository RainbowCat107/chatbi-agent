import os
import uuid
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
matplotlib.rcParams['axes.unicode_minus'] = False

OUTPUT_DIR = "./outputs/charts"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _safe_to_dataframe(result: dict) -> pd.DataFrame:
    rows = result.get("rows", [])
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def _is_time_series(df: pd.DataFrame) -> bool:
    time_cols = {"month", "date", "order_date", "create_time", "月份", "日期", "下单月份", "注册月份"}
    return any(col in df.columns for col in time_cols)


def _pick_chart_type(df: pd.DataFrame) -> str:
    if df.empty:
        return "none"
    if _is_time_series(df):
        return "line"
    if len(df.columns) >= 2:
        return "bar"
    return "table"


def generate_chart(result: dict):
    df = _safe_to_dataframe(result)
    if df.empty:
        return {
            "chart_path": None,
            "chart_type": "none",
            "message": "查询结果为空，无法生成图表"
        }

    chart_type = _pick_chart_type(df)
    chart_filename = f"{uuid.uuid4().hex}.png"
    chart_path = os.path.join(OUTPUT_DIR, chart_filename)

    try:
        plt.figure(figsize=(10, 6))

        if chart_type == "line":
            x_col = df.columns[0]
            y_col = df.columns[1]
            plt.plot(df[x_col], df[y_col], marker="o")
            plt.xlabel(str(x_col))
            plt.ylabel(str(y_col))
            plt.title(f"{y_col} over {x_col}")
            plt.xticks(rotation=45)
            plt.tight_layout()

        elif chart_type == "bar":
            x_col = df.columns[0]
            y_col = df.columns[1]
            plt.bar(df[x_col].astype(str), df[y_col])
            plt.xlabel(str(x_col))
            plt.ylabel(str(y_col))
            plt.title(f"{y_col} by {x_col}")
            plt.xticks(rotation=45)
            plt.tight_layout()

        else:
            plt.close()
            return {
                "chart_path": None,
                "chart_type": "table",
                "message": "当前结果不适合自动绘图"
            }

        plt.savefig(chart_path, bbox_inches="tight")
        plt.close()

        return {
            "chart_path": chart_path,
            "chart_type": chart_type,
            "message": "图表生成成功"
        }

    except Exception as e:
        plt.close()
        return {
            "chart_path": None,
            "chart_type": "error",
            "message": f"图表生成失败: {str(e)}"
        }


def summarize_result(question: str, result: dict) -> str:
    df = _safe_to_dataframe(result)

    if df.empty:
        return "本次查询未返回有效数据，因此无法完成进一步分析。"

    if "message" in df.columns and len(df) >= 1:
        return str(df.iloc[0]["message"])

    row_count = len(df)
    columns = df.columns.tolist()

    if row_count == 1 and len(columns) >= 2:
        parts = []
        for col in columns:
            parts.append(f"{col}为 {df.iloc[0][col]}")
        return "查询返回单条结果，" + "，".join(parts) + "。"

    if _is_time_series(df) and len(columns) >= 2:
        x_col = columns[0]
        y_col = columns[1]
        max_idx = df[y_col].idxmax()
        min_idx = df[y_col].idxmin()
        return (
            f"该问题属于时间趋势分析。共返回 {row_count} 条记录。"
            f"{y_col} 在 {df.loc[max_idx, x_col]} 达到最高值 {df.loc[max_idx, y_col]}，"
            f"在 {df.loc[min_idx, x_col]} 达到最低值 {df.loc[min_idx, y_col]}。"
        )

    if len(columns) >= 2:
        x_col = columns[0]
        y_col = columns[1]
        sorted_df = df.sort_values(by=y_col, ascending=False)
        top_row = sorted_df.iloc[0]
        bottom_row = sorted_df.iloc[-1]
        return (
            f"该问题属于类别对比分析。共返回 {row_count} 条记录。"
            f"{x_col} 为 {top_row[x_col]} 的 {y_col} 最高，数值为 {top_row[y_col]}；"
            f"{x_col} 为 {bottom_row[x_col]} 的 {y_col} 最低，数值为 {bottom_row[y_col]}。"
        )

    return f"查询已成功执行，共返回 {row_count} 条记录。"
