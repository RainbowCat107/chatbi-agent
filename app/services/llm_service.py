import os
import re
import json
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# 初始化阿里云百炼的大模型客户端 (使用 OpenAI 兼容模式)
client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# 默认使用通义千问 Max，可通过环境变量切换。
MODEL_NAME = os.getenv("MODEL_NAME", "qwen-max")

def build_nl2sql_prompt(question: str, schema_text: str, agent_plan: Optional[dict] = None) -> str:
    """【带数据字典的提示词构建】"""
    
    data_dictionary = """
【企业核心业务数据字典】(写 SQL 时必须严格遵守以下口径)
1. 销售额 / 总收入 / 业绩 / GMV：计算时，必须过滤掉未支付和退款的订单，必须加上条件 `order_status IN (20, 30)`。求和金额使用 `pay_amount`。
2. 有效用户：关联用户信息时，必须排除注销用户，加上条件 `is_deleted = 0`。
3. 退货/退款金额：只统计 `order_status = 40` 的订单。
4. 正常在售商品：关联商品时，必须加上 `is_on_sale = 1`。
5. 利润：数据库中目前缺乏“成本”等相关数据，绝对无法计算利润。当遇到查询利润时，必须只输出：SELECT '缺乏成本数据，无法计算利润' AS message;
6. 【拒答铁律】数据缺失拦截：如果用户询问的信息（如厂家、供应商、地址、省份等）在 Schema 中完全不存在，绝对不允许用其他字段（如商品名、日期等）强行凑数！必须直接输出：SELECT '当前数据库缺乏相关维度数据，无法满足该查询' AS message;
    """

    plan_text = json.dumps(agent_plan or {}, ensure_ascii=False, indent=2)
    
    return f"""
你是一个专业的数据分析 SQL 架构师。
请基于给定的数据库 Schema 和【企业核心业务数据字典】，将用户问题转换为 SQLite 可执行的 SQL。

要求：
1. 只能输出一条 SQL，不要输出其他任何解释性文字。
2. 严格遵守【企业核心业务数据字典】中的过滤口径！这是最重要的一点！
3. SQL 必须是 SQLite 语法。
4. 只允许使用 schema 中存在的表和字段。
5. 默认只读查询，不能包含 INSERT/UPDATE/DELETE/DROP 等语句。

数据库 Schema:
{schema_text}

Agent 规划与 Schema Linking 提示:
{plan_text}

{data_dictionary}

用户问题:
{question}

请直接输出 SQL:
""".strip()

def generate_sql(question: str, schema_text: str, history: list = None, agent_plan: Optional[dict] = None) -> str:
    if history is None:
        history = []
        
    prompt = build_nl2sql_prompt(question, schema_text, agent_plan)
    
    messages = [
        {"role": "system", "content": "你是一个极其专业的数据分析 SQL 架构师。"}
    ]
    
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
        
    messages.append({"role": "user", "content": prompt})
    
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.1, 
    )
    
    return response.choices[0].message.content

def fix_sql(
    question: str,
    schema_text: str,
    bad_sql: str,
    error_message: str,
    audit_report: Optional[dict] = None,
    agent_plan: Optional[dict] = None,
) -> str:
    """【真·自我纠错调用】如果 SQL 报错了，把报错信息甩给大模型让它重写"""
    audit_text = json.dumps(audit_report or {}, ensure_ascii=False, indent=2)
    plan_text = json.dumps(agent_plan or {}, ensure_ascii=False, indent=2)
    fix_prompt = f"""
你之前生成的 SQL 执行报错了。请帮我修复它。
用户问题: {question}

错误的 SQL:
{bad_sql}

数据库返回的报错信息:
{error_message}

SQL 审计报告:
{audit_text}

Agent 规划与 Schema Linking 提示:
{plan_text}

数据库 Schema:
{schema_text}

请分析错误原因，并输出修复后的正确 SQLite SQL。必须继续遵守业务数据字典里的口径：
1. 销售/GMV/销量类查询过滤 `order_status IN (20, 30)`。
2. 退款/售后类查询过滤 `order_status = 40`。
3. 用户表过滤 `is_deleted = 0`。
4. 商品表过滤 `is_on_sale = 1`。
5. 缺少字段时输出拒答 SQL，不要硬凑字段。
只输出 SQL，不要解释。
"""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "你是一个数据库纠错专家，擅长根据报错信息修复 SQL。"},
            {"role": "user", "content": fix_prompt}
        ],
        temperature=0.1,
    )
    return response.choices[0].message.content

def extract_sql(text: str) -> str:
    """正则提取大模型生成的 Markdown 代码块中的 SQL"""
    text = text.strip()
    
    # 匹配 ```sql ... ```
    code_block_match = re.search(r"```sql\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if code_block_match:
        return code_block_match.group(1).strip()
    
    # 匹配 ``` ... ```
    code_block_match = re.search(r"```\s*(.*?)```", text, re.DOTALL)
    if code_block_match:
        return code_block_match.group(1).strip()
    
    return text
