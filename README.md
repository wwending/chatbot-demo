# 个人知识问答聊天助手

一个面向本地知识问答、通用聊天、工具调用和桌面端使用场景的大模型应用 Demo。

项目支持 FastAPI 后端、React Web 前端，以及可打包为 Windows EXE 的 CustomTkinter 桌面客户端。没有配置大模型 API Key 时，系统会使用 `offline-demo` 兜底回答，方便演示会话、SQLite、关键词、工具调用和 RAG 流程；配置 DeepSeek、通义千问或其他 OpenAI-compatible API 后，可调用真实模型生成回答。

## 功能特性

### 桌面客户端

- 基于 CustomTkinter 的 Windows 桌面客户端。
- 可打包为 `dist/chatbot-demo.exe`。
- 不需要启动浏览器，也不依赖 React dev server。
- 直接调用 Python 业务层 `handle_chat()`。
- 支持会话列表、新建会话、删除会话、历史会话恢复。
- 支持系统状态、最近响应、工具结果、RAG 来源和知识库操作展示。
- 支持在客户端内配置 LLM API Key。
- 支持本地 `.txt` / `.md` 知识库上传。
- 支持右键复制消息。
- 支持长回答滚动阅读。

### 聊天与工具调用

- 普通文本聊天。
- 历史上下文恢复。
- 关键词回复，例如“你好”“帮助”“项目介绍”“联系方式”。
- 时间工具，例如“北京时间”“当前时间”。
- 天气工具，支持当前天气和未来天气。
- RAG 知识库问答。
- SQLite 持久化会话、消息、关键词命中、模型输出和知识库来源。

### 天气查询

天气服务使用 Open-Meteo，不需要 API Key，也不再需要 `WEATHER_API_KEY`。

系统会先使用 Open-Meteo Geocoding API 将城市名解析为经纬度，再使用 Forecast API 查询当前天气或 daily forecast。

支持示例：

```text
上海天气怎么样
查询武汉天气
明天临沂天气
后天武汉天气
武汉未来一周天气
未来十五天武汉天气
武汉未来15天天气
New York weather
London weather
```

未来天气最多支持 16 天。类似“未来30天武汉天气”这类超出范围的问题会返回友好提示，不会请求不支持的数据范围。

## 技术栈

| 模块 | 技术 |
|---|---|
| 后端 | Python, FastAPI, Pydantic, httpx |
| 数据库 | SQLite |
| 桌面端 | CustomTkinter |
| Web 前端 | React, TypeScript, Vite |
| LLM | OpenAI-compatible API, DeepSeek, 通义千问 |
| RAG | 本地轻量向量检索 |
| 打包 | PyInstaller |
| 测试 | pytest |

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
  -> 返回 ChatResponse
  -> 桌面端或 Web 前端展示消息、工具结果、RAG 来源和耗时
```

## 项目结构

```text
chatbot-demo/
├── app/
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 配置读取
│   ├── runtime.py              # 桌面端/打包运行时路径
│   ├── schemas.py              # 请求和响应模型
│   ├── example_questions.py    # 桌面端欢迎页示例问题池
│   ├── services/               # 聊天、意图、工具、LLM 等服务
│   ├── rag/                    # 知识库导入、分段、向量检索
│   └── db/                     # SQLite 初始化和数据访问
├── frontend/                   # React Web 前端
├── knowledge/                  # 默认知识库
├── data/                       # 运行时数据，默认不提交
├── tests/                      # 单元测试
├── evals/                      # Demo 评估脚本
├── docs/
│   └── PACKAGING_EXE.md        # Windows EXE 打包说明
├── packaging/
│   └── build_exe.ps1           # Windows 打包脚本
├── launch_desktop.py           # CustomTkinter 桌面客户端入口
├── chatbot-demo.spec           # PyInstaller 配置
├── requirements.txt
├── requirements-build.txt
├── .env.example
└── README.md
```

## 快速开始：桌面客户端

### 1. 克隆项目

```powershell
git clone https://github.com/<your-name>/chatbot-demo.git
cd chatbot-demo
```

### 2. 创建虚拟环境

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -U pip
python -m pip install -r requirements.txt
```

### 3. 准备配置文件

```powershell
copy .env.example .env
```

没有配置 `LLM_API_KEY` 时，系统会使用 `offline-demo` 兜底回答。

配置 DeepSeek 示例：

```env
LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=你的 DeepSeek Key
LLM_MODEL=deepseek-chat
```

配置通义千问示例：

```env
LLM_PROVIDER=qwen
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_API_KEY=你的通义千问 Key
LLM_MODEL=qwen-plus
```

### 4. 初始化数据库和知识库

```powershell
python -m app.db.init_db
python -m app.rag.ingest
```

### 5. 运行桌面客户端

```powershell
python launch_desktop.py
```

## 打包为 Windows EXE

### 一键打包

从项目根目录运行：

```powershell
.\packaging\build_exe.ps1
```

如果依赖已经安装：

```powershell
.\packaging\build_exe.ps1 -SkipInstall
```

打包产物：

```text
dist\chatbot-demo.exe
```

### 直接运行 PyInstaller

```powershell
python -m PyInstaller chatbot-demo.spec --clean --noconfirm
```

### 运行 EXE

```powershell
.\dist\chatbot-demo.exe
```

打包后的运行时数据会写在 exe 同级目录：

```text
data\chatbot.db
data\vector_store.json
knowledge\
```

打包后的 `.env` 也应放在 exe 同级目录，例如：

```text
dist\.env
```

天气功能使用 Open-Meteo，不需要在 `dist\.env` 中配置天气 Key；`.env` 仍用于 `LLM_API_KEY` 等模型配置。

## Web 前端开发运行

### 1. 启动后端

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

### 2. 启动前端

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

前端地址：

```text
http://127.0.0.1:5173
```

前端 API 地址在 `frontend/.env` 中配置：

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## API 示例

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

## 测试

运行单元测试：

```powershell
python -m pytest
```

运行评估脚本：

```powershell
python evals\run_demo_eval.py
```

打包前建议执行：

```powershell
python -m py_compile launch_desktop.py app\config.py app\services\tool_service.py app\services\intent_service.py app\db\database.py
python -m pytest
python -m PyInstaller chatbot-demo.spec --clean --noconfirm
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

## 运行数据与 Git 忽略

默认不提交运行产物：

```text
.env
data/chatbot.db
data/vector_store.json
data/eval_result.json
data/*.log
build/
dist/
frontend/node_modules/
frontend/dist/
```

如果需要迁移聊天记录和知识库索引，可以手动复制：

```text
data/chatbot.db
data/vector_store.json
knowledge/
```

## 当前限制

当前版本仍是 Demo / Preview，不是生产级部署版本：

- 未实现登录鉴权。
- 未实现流式输出。
- 未实现生产级权限控制。
- 未实现生产级限流。
- 桌面 GUI 仍可继续优化设置面板、间距、气泡尺寸和应用图标。
- React 前端仍保留为原 Web Demo。

## 后续计划

- 增加正式应用图标。
- 优化桌面端设置面板。
- 优化右侧 Inspector 展示。
- 增强地名消歧策略。
- 增加更多知识库管理能力。
- 评估 Chroma / FAISS 等向量库替换方案。
- 增加流式输出和更完整的异常提示。

## 简历描述参考

开发前后端分离的个人知识问答与通用聊天机器人 Demo，后端基于 FastAPI 实现对话编排、SQLite 会话持久化、关键词回复、工具调用和本地知识库 RAG 问答；桌面端基于 CustomTkinter 实现本地聊天客户端、会话管理、工具结果和 RAG 来源展示；前端基于 React + TypeScript 实现 Web 工作台。项目封装 OpenAI-compatible 大模型调用、Prompt 模板、历史上下文拼接、异常重试和离线兜底逻辑，并设计测试用例验证路由准确性、响应稳定性和可优化点。
