# ChatBI Agent

面向电商数仓的可控 NL2SQL 数据分析智能体。项目目标不是简单调用大模型生成 SQL，而是展示一个可评测、可审计、可拒答、可自修复的 ChatBI Agent pipeline。

## 核心能力

- 自然语言问数：中文业务问题自动转换为 SQLite SQL。
- Schema Linking：在生成 SQL 前识别问题中的业务实体、指标、维度和必要字段。
- 业务口径约束：GMV/销售额过滤有效订单，用户过滤注销数据，商品过滤下架数据。
- 拒答机制：利润、供应商、厂家、地址等缺失字段问题会返回明确拒答 SQL。
- SQL 安全审计：限制只读单条查询，拦截危险关键字，检查表字段和业务规则。
- 自我修复：SQL 执行或审计失败后，把错误和审计报告交给大模型重写。
- 结果分析：返回表格、自动图表和模板化分析结论。
- Benchmark：提供 JSONL 评测集和自动化评测脚本，输出 pass rate、执行成功率、拒答准确率等指标。

## 技术栈

- Backend: FastAPI
- Frontend: Streamlit
- Database: SQLite
- LLM: DashScope / 阿里云百炼 OpenAI 兼容接口，默认模型 `qwen-max`
- Data/Chart: pandas, matplotlib
- SQL parsing: sqlparse

## 项目结构

```text
app/
  agents/
    nl2sql_agent.py      # Agent 主编排：规划、生成、审计、执行、修复、总结
    planner.py           # 意图识别、Schema Linking、拒答规划
  services/
    llm_service.py       # Prompt 构建、SQL 生成、SQL 修复
    analysis_service.py  # 图表生成和结果摘要
  tools/
    schema_tool.py       # SQLite Schema 读取
    sql_tool.py          # SQL 安全执行
    sql_audit.py         # SQL 语义审计和业务规则审计
  main.py                # FastAPI 接口
eval/
  datasets/
    nl2sql_benchmark.jsonl
  scripts/
    run_benchmark.py
frontend/
  streamlit_app.py
scripts/
  init_db.py             # 初始化模拟电商数仓
```

## 数据模型

初始化脚本会生成一个模拟电商数仓：

- `dim_user_info`：用户维表，包含会员等级、注册时间、注销标记。
- `dim_sku_info`：商品维表，包含商品名、品类、标价、上下架标记。
- `dim_region_info`：地区维表，包含大区、省份、城市。
- `dim_channel_info`：渠道维表，包含 APP、小程序、直播间等渠道。
- `dwd_trade_order`：订单事实表，包含用户、商品、地区、渠道、支付金额、优惠金额、订单状态和下单时间。

业务口径：

- GMV / 销售额 / 收入 / 业绩：`order_status IN (20, 30)`，金额字段为 `pay_amount`。
- 退款 / 售后：`order_status = 40`。
- 有效用户：`is_deleted = 0`。
- 在售商品：`is_on_sale = 1`。
- 利润：当前没有成本字段，必须拒答。

## 快速开始

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 配置环境变量

复制 `.env.example` 为 `.env`，填入：

```text
DASHSCOPE_API_KEY=你的API_KEY
MODEL_NAME=qwen-max
DB_PATH=./data/db/chatbi.db
```

3. 初始化数据库

```bash
python scripts/init_db.py
```

如果你是从旧版本仓库升级，务必重新运行初始化脚本；否则本地 `data/db/chatbi.db` 可能还没有地区和渠道维表。

4. 启动 FastAPI

```bash
uvicorn app.main:app --reload
```

5. 启动 Streamlit 前端

```bash
streamlit run frontend/streamlit_app.py
```

## API

- `GET /schema`：查看当前 SQLite Schema。
- `POST /execute_sql`：执行只读 SQL。
- `POST /audit_sql`：审计 SQL 是否满足安全和业务规则。
- `POST /nl2sql`：完整自然语言问数链路。

示例：

```json
{
  "question": "请按品类统计GMV最高的前五名"
}
```

返回中包含：

- `agent_plan`：意图、字段映射、业务规则、是否拒答。
- `sql`：最终 SQL。
- `result`：查询结果。
- `chart`：图表路径和图表类型。
- `summary`：自动分析结论。
- `attempts`：每轮 SQL 审计、执行和修复记录。

## Benchmark

运行评测：

```bash
python eval/scripts/run_benchmark.py
```

只跑前 3 条：

```bash
python eval/scripts/run_benchmark.py --limit 3
```

报告会输出到 `eval/reports/`，指标包括：

- `pass_rate`
- `execution_success_rate`
- `audit_success_rate`
- `refusal_accuracy`
- `avg_keyword_score`
- `avg_latency_sec`
- `avg_attempt_count`

评测集路径：`eval/datasets/nl2sql_benchmark.jsonl`。

## 简历表述参考

构建面向电商数仓的可控 NL2SQL ChatBI Agent，支持 Schema Linking、业务口径约束、SQL 安全审计、自修复执行、结果可视化与自动洞察生成；设计中文问数 benchmark，从执行成功率、业务规则命中率、拒答准确率、自修复成功率等维度评估 Agent 效果。

## 后续可继续增强

- 引入 SQL AST 级别校验，替代部分正则审计。
- 增加真实企业指标体系，如客单价、复购率、转化率、毛利率。
- 支持多轮追问中的上下文改写，例如“那华东呢”“换成按渠道看”。
- 引入 RAG 文档，把指标口径和字段解释从 Prompt 中拆到知识库。
- 使用更大规模评测集，加入模型对比和 Prompt ablation。
