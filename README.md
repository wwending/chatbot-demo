# 个人知识问答与通用文本聊天机器人 Demo

这是一个面向个人知识问答和通用文本聊天场景的大模型应用原型。项目重点验证大模型在垂直知识问答、工具调用、历史上下文和对话流程管理中的工程落地能力。

项目默认不需要 API Key 也能运行：没有配置大模型密钥时会使用离线兜底回答，方便演示 API、SQLite、关键词、工具和 RAG 流程。配置 DeepSeek、通义千问或其他 OpenAI-compatible API 后，会自动调用真实模型生成回答。

## 功能特性

- 文本聊天：支持普通聊天和历史上下文拼接。
- 关键词回复：命中“你好”“帮助”“项目介绍”“联系方式”等关键词时直接返回固定回复。
- 指令识别：支持 `/time`、`现在几点`、`/weather 北京`、`上海天气` 等工具调用。
- 本地知识库问答：支持导入 `.txt`、`.md`，完成文本清洗、分段、向量化、相似度检索和来源注入。
- SQLite 持久化：保存会话、消息、关键词命中、知识库来源和模型回答。
- 可测试可复现：包含 pytest 用例和 30+ 条评估问题。
- 接口文档：FastAPI 自动生成 Swagger UI。

## 技术栈

- Python
- FastAPI
- SQLite
- OpenAI-compatible LLM API，支持 DeepSeek/通义千问等
- RAG
- 本地轻量向量检索，可替换为 Chroma/FAISS
- Prompt Engineering
- pytest

## 架构流程

```text
用户输入
 -> 保存 user message
 -> 意图识别
 -> keyword / tool / rag / chat 路由
 -> 组装 Prompt + 历史上下文 + 工具结果或检索片段
 -> 调用大模型 API 或离线兜底
 -> 输出后处理
 -> 保存 assistant message、来源、命中信息、模型输出
 -> 返回 JSON
```

## 项目结构

```text
chatbot-demo/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── schemas.py
│   ├── router.py
│   ├── services/
│   │   ├── chat_service.py
│   │   ├── intent_service.py
│   │   ├── keyword_service.py
│   │   ├── llm_service.py
│   │   ├── tool_service.py
│   │   └── history_service.py
│   ├── rag/
│   │   ├── loader.py
│   │   ├── cleaner.py
│   │   ├── splitter.py
│   │   ├── embeddings.py
│   │   ├── vector_store.py
│   │   ├── ingest.py
│   │   └── qa_service.py
│   └── db/
│       ├── database.py
│       └── init_db.py
├── knowledge/
├── data/
├── tests/
├── evals/
├── README.md
├── requirements.txt
└── .env.example
```

## 快速开始

创建虚拟环境并安装依赖：

```bash
cd C:\Users\ww\chatbot-demo
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

复制环境变量模板：

```bash
copy .env.example .env
```

初始化 SQLite：

```bash
python -m app.db.init_db
```

导入默认知识库：

```bash
python -m app.rag.ingest
```

启动 API：

```bash
uvicorn app.main:app --reload
```

打开 Swagger：

```text
http://127.0.0.1:8000/docs
```

## 大模型配置

`.env` 默认配置为 DeepSeek OpenAI-compatible 接口：

```env
LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=你的 DeepSeek Key
LLM_MODEL=deepseek-chat
```

通义千问可改成类似：

```env
LLM_PROVIDER=qwen
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_API_KEY=你的通义千问 Key
LLM_MODEL=qwen-plus
```

没有 `LLM_API_KEY` 时，系统会使用 `offline-demo` 响应，但路由、数据库、RAG 检索、工具调用仍然可演示。

## API 说明

### 健康检查

```bash
curl http://127.0.0.1:8000/health
```

返回示例：

```json
{
  "api": "ok",
  "sqlite": true,
  "vector_store": true,
  "llm_configured": false,
  "llm_provider": "deepseek",
  "llm_model": "offline-demo"
}
```

### 聊天

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"demo\",\"message\":\"根据知识库介绍一下这个项目的技术栈\"}"
```

返回字段：

- `session_id`：会话 ID，可用于连续追问。
- `intent`：`keyword`、`tool`、`rag` 或 `chat`。
- `answer`：助手回答。
- `sources`：RAG 命中的知识片段来源。
- `tool_result`：工具调用结果。
- `model`：真实模型名或 `offline-demo`。
- `latency_ms`：接口耗时。

### 导入知识库

导入默认 `knowledge/` 目录：

```bash
curl -X POST http://127.0.0.1:8000/knowledge/import \
  -H "Content-Type: application/json" \
  -d "{}"
```

导入指定文件或目录：

```bash
curl -X POST http://127.0.0.1:8000/knowledge/import \
  -H "Content-Type: application/json" \
  -d "{\"path\":\"knowledge/project_overview.md\"}"
```

### 会话列表

```bash
curl http://127.0.0.1:8000/sessions
```

按用户筛选：

```bash
curl "http://127.0.0.1:8000/sessions?user_id=demo"
```

### 会话消息

```bash
curl http://127.0.0.1:8000/sessions/{session_id}/messages
```

## 演示问题

关键词回复：

```text
你好
帮助
项目介绍
联系方式是什么？
```

工具调用：

```text
/time
/time 纽约
现在几点
/weather 北京
上海天气怎么样？
```

知识库问答：

```text
根据知识库介绍这个项目的技术栈
文档里说对话流程是怎样的？
资料里天气查询没有 API Key 时怎么处理？
根据文档总结这个项目的工程价值
```

上下文追问：

```text
根据知识库介绍这个 Demo
它的技术栈有哪些？
它如何保存聊天记录？
上面提到的工具调用包括什么？
```

## 测试与评估

运行单元测试：

```bash
pytest
```

运行 30+ 条 Demo 评估问题：

```bash
python evals/run_demo_eval.py
```

评估问题位于：

```text
evals/questions.json
```

评估结果输出到：

```text
data/eval_result.json
```

每条评估记录包含：

- 问题
- 期望路由
- 实际路由
- 是否命中来源
- 是否成功回答
- 响应耗时
- 可优化点

## SQLite 表设计

项目会自动创建以下表：

- `sessions`：用户会话。
- `messages`：用户和助手消息。
- `keyword_hits`：关键词命中记录。
- `knowledge_sources`：知识库来源和 chunk 内容。
- `model_outputs`：模型原始输出、最终回答和耗时。

数据库默认路径：

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

## 天气工具说明

没有配置 `WEATHER_API_KEY` 时：

```text
北京天气 Demo：多云，22-28 摄氏度，微风。
```

配置后，`tool_service.py` 会尝试调用 OpenWeatherMap。也可以替换为高德、和风天气或其他天气 API。


