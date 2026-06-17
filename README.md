# 个人知识问答与通用聊天机器人 Demo

这是一个面向个人知识问答和通用文本聊天场景的大模型应用原型。项目包含 FastAPI 后端和 React 前端页面，用于验证大模型在垂直知识问答、工具调用、历史上下文和对话流程管理中的工程落地能力。

项目默认不需要 API Key 也能运行：没有配置大模型密钥时会使用 `offline-demo` 兜底回答，方便演示 API、SQLite、关键词、工具调用和 RAG 流程。配置 DeepSeek、通义千问或其他 OpenAI-compatible API 后，会自动调用真实模型生成回答。

## 当前实现范围

已实现：

- FastAPI 后端接口和 Swagger 文档。
- React + Vite + TypeScript 前端工作台。
- 普通文本聊天和历史上下文恢复。
- 关键词回复，例如“你好”“帮助”“项目介绍”“联系方式”。
- `/time`、`/weather`、当前天气和未来天气等工具调用。
- 本地知识库导入、上传、文本清洗、分段、向量化、相似度检索和来源展示。
- SQLite 保存会话、消息、关键词命中、知识库来源和模型回答。
- 30+ 条评估问题和 pytest 测试。

未实现：

- 登录鉴权。
- 流式输出。
- 生产级权限、限流和部署配置。

## 技术栈

- Backend：Python、FastAPI、SQLite、httpx、Pydantic
- Frontend：React、TypeScript、Vite、lucide-react
- LLM：OpenAI-compatible API，支持 DeepSeek、通义千问等
- RAG：本地轻量向量检索，可替换为 Chroma 或 FAISS
- Testing：pytest、脚本化评估

## 架构流程

```text
用户输入
 -> 保存 user message
 -> 意图识别
 -> keyword / tool / rag / chat 路由
 -> 组装 Prompt + 历史上下文 + 工具结果或检索片段
 -> 调用大模型 API 或 offline-demo
 -> 输出后处理
 -> 保存 assistant message、来源、命中信息、模型输出
 -> 返回 JSON
 -> React 前端展示消息、意图、工具结果、RAG 来源和耗时
```

## 项目结构

```text
chatbot-demo/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── schemas.py
│   ├── services/
│   ├── rag/
│   └── db/
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
├── knowledge/
├── data/
├── tests/
├── evals/
├── README.md
├── requirements.txt
└── .env.example
```

## 快速开始

以下命令假设你已经进入项目父目录。项目可以放在任意位置，不依赖 `C:\Users\ww\chatbot-demo` 这种固定路径。

### 1. 进入项目目录

```powershell
cd chatbot-demo
```

如果你把项目放在其他目录：

```powershell
cd <你的项目目录>\chatbot-demo
```

### 2. 安装后端依赖

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
```

macOS / Linux：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

### 3. 初始化后端数据

```powershell
python -m app.db.init_db
python -m app.rag.ingest
```

### 4. 启动后端

推荐使用 `python -m uvicorn`，避免 Windows 环境里 `uvicorn.exe` 不在 PATH 的问题。

```powershell
python -m uvicorn app.main:app --reload
```

后端地址：

```text
http://127.0.0.1:8000
```

Swagger：

```text
http://127.0.0.1:8000/docs
```

### 5. 启动前端

另开一个终端：

```powershell
cd chatbot-demo\frontend
npm install
copy .env.example .env
npm run dev
```

macOS / Linux：

```bash
cd chatbot-demo/frontend
npm install
cp .env.example .env
npm run dev
```

前端地址：

```text
http://127.0.0.1:5173
```

## 前端功能

React 页面采用三栏工作台布局：

- 左侧：用户 ID、会话列表、新建会话、刷新会话。
- 中间：聊天消息流、示例问题、输入框。
- 右侧：系统状态、最近一次意图、模型名、耗时、工具结果、RAG 来源、知识库导入和上传。

可演示问题：

```text
你好
/time 北京
/weather 上海
上海天气怎么样
New York weather
根据知识库介绍一下这个项目的技术栈
文档里说对话流程是怎样的？
```

## 大模型配置

`.env` 默认按 DeepSeek OpenAI-compatible 接口设计：

```env
LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=你的 DeepSeek Key
LLM_MODEL=deepseek-chat
```

通义千问示例：

```env
LLM_PROVIDER=qwen
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_API_KEY=你的通义千问 Key
LLM_MODEL=qwen-plus
```

没有 `LLM_API_KEY` 时，系统会使用 `offline-demo`，但路由、数据库、RAG 检索、工具调用和前端展示都可以正常演示。

## 天气工具

天气查询使用 Open-Meteo，不需要 API Key，也不再需要 `WEATHER_API_KEY`。系统会先调用 Open-Meteo Geocoding API 将城市名解析为经纬度，再调用 Forecast API 查询当前天气或 daily forecast。未来天气最多支持 16 天。

支持示例：

```text
/weather 上海
上海天气怎么样
查询武汉天气
明天临沂天气
后天武汉天气
武汉未来一周天气
未来十五天武汉天气
武汉未来15天天气
未来7天北京天气
查询未来一周上海天气
帮我看看东京天气
查一下乌鲁木齐天气
New York weather
London weather
```

`未来30天武汉天气` 这类超出范围的查询不会请求 30 天数据，会提示当前最多支持未来 16 天天气预报。打包后的 `dist/chatbot-demo.exe` 不需要在 `dist/.env` 配置天气 Key；`.env` 仍然用于 `LLM_API_KEY` 等模型配置。

前端 API 地址在 `frontend/.env` 中配置：

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## API 说明

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

聊天：

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"demo\",\"message\":\"根据知识库介绍一下这个项目的技术栈\"}"
```

导入默认知识库：

```bash
curl -X POST http://127.0.0.1:8000/knowledge/import \
  -H "Content-Type: application/json" \
  -d "{}"
```

会话列表：

```bash
curl "http://127.0.0.1:8000/sessions?user_id=demo"
```

会话消息：

```bash
curl http://127.0.0.1:8000/sessions/{session_id}/messages
```

## 测试与评估

后端单元测试：

```powershell
python -m pytest
```

30+ 条评估问题：

```powershell
python evals\run_demo_eval.py
```

前端构建：

```powershell
cd frontend
npm run build
```

当前验证结果：

```text
python -m pytest
38 passed

python evals\run_demo_eval.py
35/35 passed
```

## 项目迁移

### 上传 GitHub

```powershell
git init
git add .
git commit -m "Initial chatbot demo"
git remote add origin https://github.com/<your-name>/chatbot-demo.git
git branch -M main
git push -u origin main
```

### 新电脑运行

```powershell
git clone https://github.com/<your-name>/chatbot-demo.git
cd chatbot-demo
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
python -m app.db.init_db
python -m app.rag.ingest
python -m uvicorn app.main:app --reload
```

另开一个终端：

```powershell
cd chatbot-demo\frontend
npm install
copy .env.example .env
npm run dev
```

### 是否迁移运行数据

默认不迁移运行产物：

```text
data/chatbot.db
data/vector_store.json
data/eval_result.json
frontend/node_modules/
frontend/dist/
```

如果你需要保留聊天记录和知识库索引，可以手动复制：

```text
data/chatbot.db
data/vector_store.json
```

不要上传 `.env`，API Key 应该在新环境手动配置。

## SQLite 表设计

项目会自动创建以下表：

- `sessions`：用户会话。
- `messages`：用户和助手消息。
- `keyword_hits`：关键词命中记录。
- `knowledge_sources`：知识库来源和 chunk 内容。
- `model_outputs`：模型原始输出、最终回答和耗时。

默认数据库路径：

```text
data/chatbot.db
```

## RAG 实现说明

当前 Demo 使用内置轻量向量检索，便于本地快速运行：

1. 加载 `.txt`、`.md` 文件。
2. 清洗空白和换行。
3. 按 `CHUNK_SIZE` 和 `CHUNK_OVERLAP` 分段。
4. 使用哈希向量生成可复现 embedding。
5. 计算余弦相似度并取 Top K。
6. 将检索片段和来源注入 Prompt。

如果需要接入 Chroma 或 FAISS，可以替换 `app/rag/vector_store.py` 中的 `LocalVectorStore`，上层 `qa_service.py` 和 `/knowledge/import` 接口无需大改。

## 简历描述建议

```text
开发前后端分离的个人知识问答与通用聊天机器人 Demo，后端基于 FastAPI 实现对话编排、SQLite 会话持久化、关键词回复、工具调用和本地知识库 RAG 问答；前端基于 React + TypeScript 实现多会话聊天、系统状态、Agent 路由过程、RAG 来源和工具结果可视化。封装 OpenAI-compatible 大模型调用、Prompt 模板、历史上下文拼接、异常重试和离线兜底逻辑，并设计 30+ 条测试问题验证路由准确性、响应稳定性和可优化点。
```
