# 🚀 ChatBI 企业级数据分析智能体 (Enterprise ChatBI Agent)

基于大模型（Qwen-Max）与 ReAct 架构构建的“文本到 SQL（NL2SQL）”智能数据探索平台。本项目不仅实现了基础的自然语言查询，更着重解决了大模型在真实企业落地中面临的**业务口径幻觉**与**跨方言语法报错**两大核心痛点。

## ✨ 核心亮点 (Core Features)

* **🛡️ 业务边界硬控 (动态数据字典与拒答机制)**
  摒弃了传统大模型“不懂装懂、瞎编字段”的毛病。通过 Prompt 注入企业级数据字典，严格规范 GMV（排除退款订单）、有效用户（排除软删除注销用户）等核心财务指标口径。当遇到缺失维度查询时，触发拒答兜底机制，确保数据分析的 100% 严谨性。
* **🔄 自治愈容错闭环 (Self-Correction)**
  构建了基于 Traceback 的异常捕获与反馈链路。当大模型写出不兼容 SQLite 的方言（如 MySQL 的 `MONTH()` 函数）或遭遇底层库报错时，Agent 能自主拦截报错堆栈，并将其反喂给大模型进行 SQL 语义重构，极大提升了系统的鲁棒性。
* **🧠 连贯性记忆引擎 (Contextual Memory)**
  采用状态机 (Streamlit Session State) 持久化上下文历史，突破了大模型 API 的无状态限制。完美支持复杂的指代消解（如：“那只看3C数码的呢？”）与条件动态叠加的多轮数据探索。
* **⚡ 极简轻量化部署 (Full-stack Integration)**
  采用 FastAPI + Streamlit 前后端解耦思路（当前 Demo 融合演示），底层挂载 SQLite 轻量级数据库，无需复杂的环境配置即可实现极速本地启动。

## 📁 目录结构 (Project Structure)

```text
chatbi-agent/
├── app/                  # 后端核心逻辑层
│   ├── agents/           # 智能体大脑 (nl2sql_agent.py，包含自纠错循环)
│   ├── services/         # LLM 服务层 (llm_service.py，包含提示词与数据字典)
│   └── tools/            # 工具类 (sql_tool.py，包含 SQL 安全校验拦截)
├── data/db/              # 本地数据库目录 (存放 chatbi.db)
├── frontend/             # 前端展示层
│   └── streamlit_app.py  # 交互式 Web UI
├── scripts/              # 脚本库
│   └── init_db.py        # 数据库初始化与企业级脏数据 Mock 脚本
├── .env.example          # 环境变量配置模板 (请勿上传真实 .env)
├── .gitignore            # Git 忽略配置
├── requirements.txt      # Python 依赖清单
└── README.md             # 项目说明文档

## 🛠️ 技术栈 (Tech Stack)

* **编程语言:** Python 3.8+
* **大语言模型:** 阿里云百炼通义千问 API (`qwen-max`)
* **前端框架:** Streamlit
* **后端引擎:** 纯原生 Python 构建的 ReAct 调度逻辑
* **数据存储:** SQLite3

## 🚀 快速启动 (Getting Started)

### 1. 克隆项目与安装依赖

首先，将本项目克隆到本地并进入根目录：

```bash
git clone [https://github.com/你的用户名/你的仓库名.git](https://github.com/你的用户名/你的仓库名.git)
cd 你的仓库名
```

推荐使用虚拟环境，然后安装所需的 Python 依赖：

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量 (.env)

本项目依赖阿里云的百炼大模型服务。请复制环境变量模板并填入你的真实秘钥：

# 在 .env 文件中填入
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
```

### 3. 初始化企业级测试数据库

本项目自带一个模拟真实电商数仓（包含软删除、退款状态机等脏数据）的 Mock 脚本。运行以下命令生成 `chatbi.db` 数据库：

```bash
python scripts/init_db.py
```
*(看到输出“企业级脏数据 Mock 库初始化完成”即代表成功)*

### 4. 启动可视化系统

在终端运行以下命令，启动 Streamlit 前端服务：

```bash
streamlit run frontend/streamlit_app.py
```

终端启动成功后，会自动在浏览器中打开 `http://localhost:8501`。你现在可以开始向智能体进行提问了！

## 💡 精彩测试用例体验 (Showcases)

强烈建议在页面中输入以下三个问题，体验 Agent 的核心能力：

1. **测试业务边界硬控：**
   * *输入：* `帮我统计一下各个类目的总销售额。`
   * *亮点：* 观察大模型生成的 SQL，它会自动加入 `order_status IN (20, 30)` 和 `is_on_sale = 1` 等复杂业务过滤条件。
2. **测试拒答兜底机制：**
   * *输入：* `销量最高的前5个商品的供应商是谁？`
   * *亮点：* 大模型不会胡编乱造字段，而是触发拒答提示：“当前数据库缺乏相关维度数据”。
3. **测试 Agent 自纠错循环 (Self-Correction)：**
   * *输入：* `帮我统计一下今年每个月的总销售额分别是多少？`
   * *亮点：* 如果大模型习惯性写出 MySQL 的 `MONTH()` 函数，系统会在底层捕获报错，并发回给 LLM 重新生成 SQLite 支持的 `strftime()` 函数。请关注后台终端 (Terminal) 打印的纠错全过程日志！

## 🤝 许可证与交流 (License & Contact)

本项目采用 MIT 许可证。这是一个作为技术展示与实践探索的优质 Demo，如果您在运行过程中遇到任何问题或对 AI 架构有探讨兴趣，欢迎提交 Issue。
