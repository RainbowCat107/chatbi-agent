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

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

default_questions = [
    "请按品类统计GMV最高的前五名",
    "请按月份统计近三个月销售额趋势",
    "请分析华东地区各城市GMV",
    "请统计各渠道GMV排名",
    "请计算本月利润",
]

selected_question = st.selectbox("选择一个示例问题", [""] + default_questions)
user_question = st.text_input("或者输入你自己的问题", value=selected_question)

if st.button("开始分析"):
    if not user_question.strip():
        st.warning("请输入问题")
    else:
        try:
            with st.spinner("正在生成 SQL 并分析数据..."):
                resp = run_nl2sql(user_question.strip(), history=st.session_state.chat_history)
                
            st.subheader("用户问题")
            st.write(resp["question"])

            st.subheader("生成的 SQL")
            st.code(resp["sql"], language="sql")

            st.subheader("自动分析结论")
            st.write(resp["summary"])

            with st.expander("Agent 规划与 Schema Linking"):
                st.json(resp.get("agent_plan", {}))

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
                st.subheader("SQL 审计、执行与修正过程")
                st.json(attempts)
            with st.expander("查看完整返回结果"):
                st.json(resp)
            
            st.session_state.chat_history.append({"role": "user", "content": user_question.strip()})
            assistant_memory = f"我为你生成了这条SQL：{resp['sql']}。结论是：{resp['summary']}"
            st.session_state.chat_history.append({"role": "assistant", "content": assistant_memory})
            if len(st.session_state.chat_history) > 6:
                st.session_state.chat_history = st.session_state.chat_history[-6:]

        except Exception as e:
            st.error(f"运行出错: {e}")
            raise
