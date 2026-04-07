import os
import sys
import pandas as pd
import streamlit as st

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from app.agents.nl2sql_agent import run_nl2sql

st.set_page_config(page_title="ChatBI Agent Demo", layout="wide")

st.title("ChatBI 数据分析智能体 Demo")
st.caption("自然语言问题 -> SQL -> 查询结果 -> 图表 -> 自动分析结论")

default_questions = [
    "请帮我分析销量最高的前五个品类",
    "请分析华东地区近三个月销售趋势",
    "请统计用户注册趋势",
]

selected_question = st.selectbox("选择一个示例问题", [""] + default_questions)
user_question = st.text_input("或者输入你自己的问题", value=selected_question)

if st.button("开始分析"):
    if not user_question.strip():
        st.warning("请输入问题")
    else:
        try:
            with st.spinner("正在生成 SQL 并分析数据..."):
                resp = run_nl2sql(user_question.strip())

            st.subheader("用户问题")
            st.write(resp["question"])

            st.subheader("生成的 SQL")
            st.code(resp["sql"], language="sql")

            st.subheader("自动分析结论")
            st.write(resp["summary"])

            result = resp.get("result", {})
            rows = result.get("rows", [])
            if rows:
                st.subheader("查询结果表")
                df = pd.DataFrame(rows)
                st.dataframe(df)
            else:
                st.warning("查询结果为空。")

            chart_info = resp.get("chart", {})
            chart_path = chart_info.get("chart_path")
            if chart_path and os.path.exists(chart_path):
                st.subheader("自动生成图表")
                st.image(chart_path)
            else:
                st.info(chart_info.get("message", "暂无图表"))

            attempts = resp.get("attempts", [])
            if attempts:
                st.subheader("SQL 执行与修正过程")
                st.json(attempts)
            with st.expander("查看完整返回结果"):
                st.json(resp)

        except Exception as e:
            st.error(f"运行出错: {e}")
            raise
