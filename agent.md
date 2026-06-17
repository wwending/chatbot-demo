# Agent Progress

## 当前分支

- 分支：`exe-package`
- 目标：把现有聊天机器人 Demo 打包成原生 Windows 桌面客户端，不再通过浏览器打开本地网页。
- 正式产物目录：只使用 `dist/`
- 当前可执行文件：`dist/chatbot-demo.exe`

## 已完成工作

- 新增原生 Tkinter 桌面客户端：`launch_desktop.py`
- 桌面客户端直接调用 Python 业务层 `handle_chat()`，不通过 HTTP 调用后端。
- 客户端不打开浏览器，也不依赖 React dev server。
- 新增运行时路径辅助：`app/runtime.py`
- 更新打包环境配置：`app/config.py`
  - exe 运行时会读取 exe 同目录下的 `.env`
  - `data/`、`knowledge/`、向量库文件写入 exe 同目录
- 新增 PyInstaller 打包配置：
  - `chatbot-demo.spec`
  - `requirements-build.txt`
  - `packaging/build_exe.ps1`
  - `docs/PACKAGING_EXE.md`
- `packaging/build_exe.ps1` 已设置：
  - `PYTHONUTF8=1`
  - UTF-8 控制台输出
- `.gitignore` 已忽略构建产物目录：
  - `build/`
  - `dist/`

## 桌面 UI 进度

- UI 已改为中文优先，已编辑文件使用 UTF-8 中文字符串。
- 布局接近原网页端：
  - 左侧：品牌区、用户 ID、会话列表
  - 中间：聊天对话区
  - 右侧：信息检查面板
- 右侧面板已拆分为多个区块：
  - 系统状态
  - 最近响应
  - 工具结果
  - RAG 来源
  - 知识库
- 系统状态支持颜色标识：
  - `ok` / `ready` 使用绿色
  - `offline-demo` / `missing` 使用橙色
- 已添加小图标符号，靠近网页端风格。
- 聊天区已改成网页端类似的左右气泡形式：
  - 用户消息靠右，使用绿色气泡
  - 助手消息靠左，使用浅色气泡
  - 助手消息下方显示 `intent | model | latency`
- 消息气泡支持右键复制。
- 新会话有中文欢迎态。
- 复制/选中时不会再出现文字变白不可见的问题。

## 会话删除

- 桌面客户端左侧已增加“删除会话”按钮。
- 删除前会弹出确认框。
- 新增数据库函数：`delete_session(session_id)`
- 删除会话时会同步删除：
  - `sessions`
  - `messages`
  - `keyword_hits`
  - `model_outputs`
- 已新增测试覆盖会话删除。

## 示例问题

桌面端示例按钮：

- `你好`
- `北京时间`
- `城市天气`，点击后填入 `上海天气`
- `知识库问答`，点击后填入 `根据知识库介绍项目技术栈`

## 工具和天气

- `app/services/tool_service.py` 已重写为正常 UTF-8 中文。
- `app/services/intent_service.py` 已重写为正常 UTF-8 中文。
- `北京时间` 会识别为时间工具。
- `上海天气怎么样`、`查询武汉天气`、`明天临沂天气`、`武汉未来一周天气`、`未来十五天武汉天气`、`New York weather` 等输入会识别为天气工具。
- 天气工具使用 Open-Meteo Geocoding API 解析城市，再使用 Open-Meteo Forecast API 查询当前天气和 daily forecast。
- 已支持当前天气、明天、后天、未来 N 天天气预报；Open-Meteo daily forecast 最多支持未来 16 天。
- 天气查询不需要 `WEATHER_API_KEY`，也不需要用户在 `dist/.env` 中配置天气 Key。
- `.env` 仍用于 `LLM_API_KEY` 等模型配置。

```text
https://geocoding-api.open-meteo.com/v1/search
https://api.open-meteo.com/v1/forecast
```

## 验证结果

最近通过的验证：

```powershell
python -m py_compile launch_desktop.py app\config.py app\services\tool_service.py app\services\intent_service.py app\db\database.py
python -m pytest
python -m PyInstaller chatbot-demo.spec --clean --noconfirm
```

当前测试结果：

```text
38 passed
```

## 注意事项

- 正式构建和运行统一使用 `dist/chatbot-demo.exe`。
- 如果 `dist/chatbot-demo.exe` 正在运行，PyInstaller 无法覆盖它，需要先关闭客户端。
- React 前端仍保留给原网页 Demo，不要误删 `frontend/`。
- 仓库中仍有少量旧文件可能存在历史乱码，当前桌面客户端主链路、工具链路、天气链路和测试已改成 UTF-8 中文。

## 建议下一步

- 继续对照网页端截图微调桌面客户端间距、颜色和气泡尺寸。
- 给 `chatbot-demo.spec` 增加正式 app 图标。
- 增加设置面板，用于在客户端内编辑 `.env` 配置。
- 如果 Tkinter 的视觉上限不够，后续可评估 PySide6 / Qt，但这会增加打包体积和依赖复杂度。
