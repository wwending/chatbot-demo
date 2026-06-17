import asyncio
import json
import shutil
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, font as tkfont, messagebox, ttk

from app.config import get_settings
from app.db.database import delete_session, init_db, list_messages, list_sessions
from app.rag.ingest import import_knowledge
from app.rag.vector_store import vector_store_ready
from app.runtime import runtime_path, seed_runtime_knowledge
from app.schemas import ChatRequest, ChatResponse
from app.services.chat_service import handle_chat


BG = "#eef2f6"
PANEL = "#ffffff"
PANEL_SUBTLE = "#f7f9fc"
BORDER = "#d8e0ea"
BORDER_STRONG = "#c5cfdd"
TEXT = "#172033"
MUTED = "#697789"
MUTED_DARK = "#455466"
ACCENT = "#176b87"
ACCENT_DARK = "#10546c"
ACCENT_SOFT = "#e7f3f7"
USER_BG = "#0f766e"
ASSISTANT_BG = "#ffffff"
CHAT_BG = "#edf2f7"
SOFT_BLUE = "#e8f1fb"
SUCCESS = "#087f5b"
WARNING = "#b7791f"
DANGER = "#c2413d"
SECTION_BG = "#f8fafc"


class ChatbotDesktopApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("个人知识问答聊天助手")
        self.geometry("1280x800")
        self.minsize(1100, 700)
        self.configure(bg=BG)

        self.settings = get_settings()
        self.session_id: str | None = None
        self.user_id = tk.StringVar(value="demo")
        self.status = tk.StringVar(value="就绪")
        self.session_count = tk.StringVar(value="0 个会话")
        self.llm_api_key = tk.StringVar(value=self.settings.llm_api_key)
        self.show_api_keys = tk.BooleanVar(value=False)
        self.chat_has_content = False

        self._initialize_runtime()
        self._configure_styles()
        self._build_ui()
        self.refresh_status()
        self.refresh_sessions()
        self._show_welcome()

    def _initialize_runtime(self) -> None:
        init_db()
        self.settings.knowledge_dir.mkdir(parents=True, exist_ok=True)
        self.settings.vector_store_path.parent.mkdir(parents=True, exist_ok=True)
        seed_runtime_knowledge()
        if not self.settings.vector_store_path.exists():
            import_knowledge()

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        base_font = ("Microsoft YaHei UI", 10)
        style.configure(".", font=base_font, background=BG, foreground=TEXT)
        style.configure("App.TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL, relief="solid", borderwidth=1)
        style.configure("Header.TFrame", background=BG)
        style.configure("Toolbar.TFrame", background=PANEL)
        style.configure("Title.TLabel", background=BG, foreground=TEXT, font=("Microsoft YaHei UI", 18, "bold"))
        style.configure("Subtitle.TLabel", background=BG, foreground=MUTED, font=("Microsoft YaHei UI", 9))
        style.configure("PanelTitle.TLabel", background=PANEL, foreground=TEXT, font=("Microsoft YaHei UI", 11, "bold"))
        style.configure("Muted.TLabel", background=PANEL, foreground=MUTED)
        style.configure("Status.TLabel", background=ACCENT_SOFT, foreground=ACCENT_DARK, padding=(12, 5), font=("Microsoft YaHei UI", 9, "bold"))
        style.configure("BrandIcon.TLabel", background=ACCENT, foreground="#ffffff", padding=(9, 6), font=("Microsoft YaHei UI", 15, "bold"))
        style.configure("BrandTitle.TLabel", background=PANEL, foreground=TEXT, font=("Microsoft YaHei UI", 12, "bold"))
        style.configure("Section.TFrame", background=SECTION_BG)
        style.configure("SectionTitle.TLabel", background=SECTION_BG, foreground=TEXT, font=("Microsoft YaHei UI", 10, "bold"))
        style.configure("SectionBody.TLabel", background=SECTION_BG, foreground=MUTED, font=("Microsoft YaHei UI", 9))
        style.configure("StatusName.TLabel", background=SECTION_BG, foreground=MUTED, font=("Microsoft YaHei UI", 9))
        style.configure("Ok.TLabel", background=SECTION_BG, foreground=SUCCESS, font=("Microsoft YaHei UI", 9, "bold"))
        style.configure("Warn.TLabel", background=SECTION_BG, foreground=WARNING, font=("Microsoft YaHei UI", 9, "bold"))
        style.configure("Info.TLabel", background=SECTION_BG, foreground=ACCENT_DARK, font=("Microsoft YaHei UI", 9, "bold"))
        style.configure("Accent.TButton", padding=(14, 8), background=ACCENT, foreground="#ffffff", bordercolor=ACCENT)
        style.map("Accent.TButton", background=[("active", ACCENT_DARK), ("pressed", ACCENT_DARK)], foreground=[("disabled", "#dbe4ef")])
        style.configure("Tool.TButton", padding=(10, 7), background=PANEL_SUBTLE, foreground=TEXT, bordercolor=BORDER_STRONG)
        style.map("Tool.TButton", background=[("active", ACCENT_SOFT), ("pressed", SOFT_BLUE)])
        style.configure("Danger.TButton", padding=(10, 7), background="#fff5f5", foreground=DANGER, bordercolor="#f1c3c1")
        style.map("Danger.TButton", background=[("active", "#ffe4e3"), ("pressed", "#ffd8d6")])
        style.configure("TEntry", fieldbackground="#ffffff", bordercolor=BORDER_STRONG, lightcolor=BORDER_STRONG, darkcolor=BORDER_STRONG)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self, style="Header.TFrame", padding=(24, 18, 24, 10))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="个人知识问答聊天助手", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="本地桌面客户端 · 聊天、工具调用、会话记录和知识库问答",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))
        ttk.Label(header, textvariable=self.status, style="Status.TLabel").grid(row=0, column=1, rowspan=2, sticky="e")

        body = ttk.Frame(self, style="App.TFrame", padding=(24, 10, 24, 22))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_left_panel(body)
        self._build_chat_panel(body)
        self._build_right_panel(body)

    def _build_left_panel(self, parent: ttk.Frame) -> None:
        left = ttk.Frame(parent, style="Panel.TFrame", padding=16)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 14))
        left.rowconfigure(9, weight=1)

        brand = ttk.Frame(left, style="Panel.TFrame")
        brand.grid(row=0, column=0, sticky="ew")
        brand.columnconfigure(1, weight=1)
        ttk.Label(brand, text="✦", style="BrandIcon.TLabel").grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 10))
        ttk.Label(brand, text="Knowledge Chatbot", style="BrandTitle.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Label(brand, text="FastAPI + RAG + Tools", style="Muted.TLabel").grid(row=1, column=1, sticky="w")

        ttk.Separator(left).grid(row=1, column=0, sticky="ew", pady=16)
        ttk.Label(left, text="用户 ID", style="Muted.TLabel").grid(row=2, column=0, sticky="w", pady=(0, 3))
        ttk.Entry(left, textvariable=self.user_id, width=26).grid(row=3, column=0, sticky="ew")
        ttk.Button(left, text="新建会话", style="Accent.TButton", command=self.new_chat).grid(
            row=4, column=0, sticky="ew", pady=(12, 6)
        )
        ttk.Button(left, text="刷新会话", style="Tool.TButton", command=self.refresh_sessions).grid(
            row=5, column=0, sticky="ew"
        )
        ttk.Button(left, text="删除会话", style="Danger.TButton", command=self.delete_selected_session).grid(
            row=6, column=0, sticky="ew", pady=(6, 0)
        )
        ttk.Label(left, text="会话记录", style="PanelTitle.TLabel").grid(row=7, column=0, sticky="w", pady=(18, 2))
        ttk.Label(left, textvariable=self.session_count, style="Muted.TLabel").grid(row=8, column=0, sticky="w", pady=(0, 4))

        self.session_list = tk.Listbox(
            left,
            width=30,
            activestyle="none",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
            selectbackground=ACCENT,
            selectforeground="#ffffff",
            bg=PANEL_SUBTLE,
            fg=TEXT,
            font=("Microsoft YaHei UI", 10),
            relief="flat",
        )
        self.session_list.grid(row=9, column=0, sticky="nsew")
        self.session_list.bind("<<ListboxSelect>>", self.open_selected_session)

    def _build_chat_panel(self, parent: ttk.Frame) -> None:
        center = ttk.Frame(parent, style="Panel.TFrame", padding=0)
        center.grid(row=0, column=1, sticky="nsew")
        center.columnconfigure(0, weight=1)
        center.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(center, style="Toolbar.TFrame", padding=(16, 13))
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew")
        toolbar.columnconfigure(0, weight=1)
        ttk.Label(toolbar, text="当前对话", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")
        samples = (
            ("你好", "你好"),
            ("北京时间", "北京时间"),
            ("城市天气", "上海天气"),
            ("知识库问答", "根据知识库介绍项目技术栈"),
        )
        for idx, (label, prompt) in enumerate(samples):
            ttk.Button(toolbar, text=label, style="Tool.TButton", command=lambda text=prompt: self.use_sample(text)).grid(
                row=0, column=idx + 1, padx=(8, 0)
            )

        self.chat_canvas = tk.Canvas(center, bg=CHAT_BG, highlightthickness=0, borderwidth=0)
        self.chat_canvas.grid(row=1, column=0, sticky="nsew")
        chat_scroll = ttk.Scrollbar(center, orient="vertical", command=self.chat_canvas.yview)
        chat_scroll.grid(row=1, column=1, sticky="ns")
        self.chat_canvas.configure(yscrollcommand=chat_scroll.set)
        self.messages_frame = tk.Frame(self.chat_canvas, bg=CHAT_BG)
        self.messages_window = self.chat_canvas.create_window((0, 0), window=self.messages_frame, anchor="nw")
        self.messages_frame.bind("<Configure>", self._sync_message_scrollregion)
        self.chat_canvas.bind("<Configure>", self._sync_message_width)
        self.chat_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        input_bar = ttk.Frame(center, style="Toolbar.TFrame", padding=(16, 15))
        input_bar.grid(row=2, column=0, columnspan=2, sticky="ew")
        input_bar.columnconfigure(0, weight=1)

        self.message_input = ttk.Entry(input_bar)
        self.message_input.grid(row=0, column=0, sticky="ew", padx=(0, 10), ipady=6)
        self.message_input.bind("<Return>", self.send_message)
        ttk.Button(input_bar, text="发送", style="Accent.TButton", command=self.send_message).grid(row=0, column=1)

    def _build_right_panel(self, parent: ttk.Frame) -> None:
        right = ttk.Frame(parent, style="Panel.TFrame", padding=16)
        right.grid(row=0, column=2, sticky="ns", padx=(14, 0))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(3, weight=1)
        right.rowconfigure(4, weight=1)

        status = self._section(right, 0, "系统状态")
        self.health_labels: dict[str, tk.StringVar] = {}
        self.health_value_labels: dict[str, ttk.Label] = {}
        for row, (key, label) in enumerate(
            (("api", "API"), ("sqlite", "SQLite"), ("vector_store", "向量库"), ("model", "大模型")),
            start=0,
        ):
            self._status_row(status, row, key, label)

        recent = self._section(right, 1, "最近响应")
        self.response_labels = {
            "intent": tk.StringVar(value="暂无响应数据。"),
            "model": tk.StringVar(value="-"),
            "latency": tk.StringVar(value="-"),
            "sources": tk.StringVar(value="-"),
        }
        ttk.Label(recent, text="意图", style="StatusName.TLabel").grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Label(recent, textvariable=self.response_labels["intent"], style="Info.TLabel").grid(row=1, column=1, sticky="e", pady=(10, 0))
        ttk.Label(recent, text="模型", style="StatusName.TLabel").grid(row=2, column=0, sticky="w", pady=(5, 0))
        ttk.Label(recent, textvariable=self.response_labels["model"], style="StatusName.TLabel").grid(row=2, column=1, sticky="e", pady=(5, 0))
        ttk.Label(recent, text="耗时", style="StatusName.TLabel").grid(row=3, column=0, sticky="w", pady=(5, 0))
        ttk.Label(recent, textvariable=self.response_labels["latency"], style="StatusName.TLabel").grid(row=3, column=1, sticky="e", pady=(5, 0))
        ttk.Label(recent, text="来源", style="StatusName.TLabel").grid(row=4, column=0, sticky="w", pady=(5, 0))
        ttk.Label(recent, textvariable=self.response_labels["sources"], style="StatusName.TLabel").grid(row=4, column=1, sticky="e", pady=(5, 0))

        tool = self._section(right, 2, "工具结果")
        self.tool_view = self._small_text(tool, height=4)
        self.tool_view.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        self._set_text(self.tool_view, "触发 时间 或 天气 后会显示。")

        rag = self._section(right, 3, "RAG 来源")
        rag.rowconfigure(1, weight=1)
        self.source_view = self._small_text(rag, height=5)
        self.source_view.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        self._set_text(self.source_view, "RAG 问答会在这里列出引用片段。")

        knowledge = self._section(right, 4, "知识库")
        ttk.Button(knowledge, text="导入默认知识库", style="Tool.TButton", command=self.import_default_knowledge).grid(
            row=1, column=0, sticky="ew", pady=(10, 6)
        )
        ttk.Button(knowledge, text="上传 .txt / .md", style="Tool.TButton", command=self.upload_knowledge_file).grid(
            row=2, column=0, sticky="ew"
        )
        self.knowledge_note = tk.StringVar(value="默认知识库会在首次启动时准备。")
        ttk.Label(knowledge, textvariable=self.knowledge_note, style="SectionBody.TLabel", wraplength=280).grid(
            row=3, column=0, sticky="w", pady=(8, 0)
        )

        config = self._section(right, 5, "API 配置")
        ttk.Label(config, text="LLM API Key", style="StatusName.TLabel").grid(row=1, column=0, sticky="w", pady=(10, 3))
        self.llm_key_entry = ttk.Entry(config, textvariable=self.llm_api_key, show="*")
        self.llm_key_entry.grid(row=2, column=0, sticky="ew")
        ttk.Checkbutton(
            config,
            text="显示密钥",
            variable=self.show_api_keys,
            command=self.toggle_api_key_visibility,
        ).grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Button(config, text="保存配置", style="Accent.TButton", command=self.save_api_config).grid(
            row=4, column=0, sticky="ew", pady=(10, 6)
        )
        ttk.Button(config, text="重新加载配置", style="Tool.TButton", command=self.reload_api_config).grid(
            row=5, column=0, sticky="ew"
        )

    def refresh_status(self) -> None:
        model = self.settings.llm_model if self.settings.llm_api_key else "offline-demo"
        self._set_status("api", "ok", "ok")
        self._set_status("sqlite", "ready", "ok")
        self._set_status("vector_store", "ready" if vector_store_ready() else "missing", "ok" if vector_store_ready() else "warn")
        self._set_status("model", model, "warn" if model == "offline-demo" else "ok")

    def refresh_sessions(self) -> None:
        self.sessions = list_sessions(self.user_id.get().strip() or "demo")
        self.session_count.set(f"{len(self.sessions)} 个会话")
        self.session_list.delete(0, tk.END)
        for item in self.sessions:
            title = item["title"].replace("\n", " ").strip()[:26]
            self.session_list.insert(tk.END, title or "未命名会话")

    def new_chat(self) -> None:
        self.session_id = None
        self._show_welcome()
        self._reset_inspector()
        self.status.set("新会话")
        self.message_input.focus_set()

    def delete_selected_session(self) -> None:
        selection = self.session_list.curselection()
        if not selection:
            messagebox.showinfo("删除会话", "请先选择一个会话。")
            return
        item = self.sessions[selection[0]]
        title = item.get("title") or "未命名会话"
        if not messagebox.askyesno("删除会话", f"确定删除会话“{title}”吗？\n删除后会移除该会话的消息、关键词命中和模型输出记录。"):
            return
        if delete_session(item["id"]):
            if self.session_id == item["id"]:
                self.session_id = None
                self._show_welcome()
                self._reset_inspector()
            self.refresh_sessions()
            self.status.set("会话已删除")
        else:
            messagebox.showerror("删除失败", "没有找到这个会话。")

    def open_selected_session(self, _event: object | None = None) -> None:
        selection = self.session_list.curselection()
        if not selection:
            return
        item = self.sessions[selection[0]]
        self.session_id = item["id"]
        self._clear_messages()
        self.chat_has_content = False
        for row in list_messages(self.session_id):
            role = "user" if row["role"] == "user" else "assistant"
            label = "你" if role == "user" else "助手"
            self._append_message(label, row["content"], role)
        self.status.set(f"已打开：{item['title'][:28]}")

    def use_sample(self, text: str) -> None:
        self.message_input.delete(0, tk.END)
        self.message_input.insert(0, text)
        self.message_input.focus_set()

    def send_message(self, _event: object | None = None) -> None:
        message = self.message_input.get().strip()
        if not message:
            return
        self.message_input.delete(0, tk.END)
        if not self.chat_has_content:
            self._clear_messages()
        self._append_message("你", message, "user")
        self.status.set("思考中...")
        request = ChatRequest(user_id=self.user_id.get().strip() or "demo", message=message, session_id=self.session_id)
        threading.Thread(target=self._send_message_worker, args=(request,), daemon=True).start()

    def _send_message_worker(self, request: ChatRequest) -> None:
        try:
            response = asyncio.run(handle_chat(request))
        except Exception as exc:
            self.after(0, lambda exc=exc: self._show_error(exc))
            return
        self.after(0, lambda: self._show_response(response))

    def _show_response(self, response: ChatResponse) -> None:
        self.session_id = response.session_id
        meta = f"{response.intent} | {response.model} | {response.latency_ms} ms"
        self._append_message("助手", response.answer, "assistant", meta=meta)
        self.response_labels["intent"].set(response.intent)
        self.response_labels["model"].set(response.model)
        self.response_labels["latency"].set(f"{response.latency_ms} ms")
        self.response_labels["sources"].set(str(len(response.sources)))
        self._set_text(self.tool_view, self._format_tool_result(response))
        self._set_text(self.source_view, self._format_sources(response))
        self.status.set("就绪")
        self.refresh_status()
        self.refresh_sessions()

    def _format_tool_result(self, response: ChatResponse) -> str:
        if not response.tool_result:
            return "本次回答没有工具结果。"
        return json.dumps(response.tool_result, ensure_ascii=False, indent=2)

    def _format_sources(self, response: ChatResponse) -> str:
        if not response.sources:
            return "本次回答没有 RAG 来源。"
        lines: list[str] = []
        for idx, source in enumerate(response.sources, start=1):
            lines.append(f"{idx}. {source.file_name}")
            lines.append(f"相似度：{source.score}")
            lines.append(f"分段：{source.chunk_id}")
            lines.append(source.content_preview)
            lines.append("")
        return "\n".join(lines).strip()

    def import_default_knowledge(self) -> None:
        self.status.set("正在导入知识库...")
        threading.Thread(target=self._import_worker, args=(None,), daemon=True).start()

    def upload_knowledge_file(self) -> None:
        selected = filedialog.askopenfilename(filetypes=[("知识库文件", "*.txt *.md")])
        if not selected:
            return
        source = Path(selected)
        target = self.settings.knowledge_dir / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        self.status.set("正在导入上传文件...")
        threading.Thread(target=self._import_worker, args=(str(target),), daemon=True).start()

    def _import_worker(self, path: str | None) -> None:
        try:
            result = import_knowledge(path)
        except Exception as exc:
            self.after(0, lambda exc=exc: self._show_error(exc))
            return
        self.after(0, lambda: self._show_import_result(result))

    def _show_import_result(self, result: dict[str, object]) -> None:
        lines = [f"已导入 {result.get('imported_files', 0)} 个文件，生成 {result.get('chunks', 0)} 个片段。"]
        files = result.get("files") or []
        if files:
            lines.append(f"最近文件：{Path(str(files[-1])).name}")
        self.knowledge_note.set("\n".join(lines))
        self.refresh_status()
        self.status.set("知识库已导入")

    def _show_error(self, exc: Exception) -> None:
        self.status.set("发生错误")
        messagebox.showerror("错误", str(exc))

    def toggle_api_key_visibility(self) -> None:
        mask = "" if self.show_api_keys.get() else "*"
        self.llm_key_entry.configure(show=mask)

    def save_api_config(self) -> None:
        try:
            self._write_env_values(
                {
                    "LLM_API_KEY": self.llm_api_key.get().strip(),
                }
            )
            self._reload_settings_from_disk()
            self.status.set("配置已保存")
        except Exception as exc:
            self._show_error(exc)

    def reload_api_config(self) -> None:
        try:
            self._reload_settings_from_disk()
            self.llm_api_key.set(self.settings.llm_api_key)
            self.status.set("配置已重新加载")
        except Exception as exc:
            self._show_error(exc)

    def _reload_settings_from_disk(self) -> None:
        get_settings.cache_clear()
        self.settings = get_settings()
        self.refresh_status()

    def _write_env_values(self, values: dict[str, str]) -> None:
        env_path = runtime_path(".env")
        env_path.parent.mkdir(parents=True, exist_ok=True)
        lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
        pending = dict(values)
        next_lines: list[str] = []

        for line in lines:
            stripped = line.lstrip()
            if not stripped or stripped.startswith("#") or "=" not in line:
                next_lines.append(line)
                continue
            key = line.split("=", 1)[0].strip()
            if key in pending:
                next_lines.append(f"{key}={pending.pop(key)}")
            else:
                next_lines.append(line)

        for key, value in pending.items():
            next_lines.append(f"{key}={value}")

        env_path.write_text("\n".join(next_lines).rstrip() + "\n", encoding="utf-8")

    def _show_welcome(self) -> None:
        self._clear_messages()
        box = tk.Frame(self.messages_frame, bg=CHAT_BG, pady=84)
        box.pack(fill="both", expand=True)
        tk.Label(
            box,
            text="●",
            bg=CHAT_BG,
            fg=ACCENT,
            font=("Microsoft YaHei UI", 22, "bold"),
        ).pack()
        tk.Label(
            box,
            text="开始一次可观测的智能问答",
            bg=CHAT_BG,
            fg=TEXT,
            font=("Microsoft YaHei UI", 18, "bold"),
        ).pack(pady=(8, 0))
        tk.Label(
            box,
            text="选择上方示例问题，或直接输入你的问题。\n支持时间、天气、知识库问答和普通聊天。",
            bg=CHAT_BG,
            fg=MUTED,
            font=("Microsoft YaHei UI", 10),
            justify="center",
        ).pack(pady=(10, 0))
        self.chat_has_content = False

    def _append_message(self, label: str, content: str, tag: str, meta: str | None = None) -> None:
        is_user = tag == "user"
        row = tk.Frame(self.messages_frame, bg=CHAT_BG, padx=24, pady=10)
        row.pack(fill="x", anchor="e" if is_user else "w")

        content_frame = tk.Frame(row, bg=CHAT_BG)
        content_frame.pack(side="right" if is_user else "left", anchor="e" if is_user else "w")

        top = tk.Frame(content_frame, bg=CHAT_BG)
        top.pack(fill="x")
        if is_user:
            tk.Label(top, text="你", bg=CHAT_BG, fg=ACCENT_DARK, font=("Microsoft YaHei UI", 9, "bold")).pack(side="right")
        else:
            tk.Label(top, text="助手", bg=CHAT_BG, fg=ACCENT_DARK, font=("Microsoft YaHei UI", 9, "bold")).pack(side="left")

        bubble = tk.Label(
            content_frame,
            text=content,
            bg=USER_BG,
            fg="#ffffff",
            padx=17,
            pady=13,
            wraplength=620,
            justify="left",
            font=("Microsoft YaHei UI", 10),
            relief="flat",
            bd=0,
        ) if is_user else self._markdown_bubble(content_frame, content)
        bubble.pack(anchor="e" if is_user else "w", pady=(6, 0))
        self._attach_copy_menu(bubble, content)

        if meta:
            tk.Label(
                content_frame,
                text=meta,
                bg=CHAT_BG,
                fg=MUTED_DARK,
                font=("Microsoft YaHei UI", 9),
            ).pack(anchor="w", pady=(6, 0))
        self.messages_frame.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)
        self.chat_has_content = True

    def _clear_messages(self) -> None:
        for child in self.messages_frame.winfo_children():
            child.destroy()

    def _sync_message_scrollregion(self, _event: object | None = None) -> None:
        self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all"))

    def _sync_message_width(self, event: tk.Event) -> None:
        self.chat_canvas.itemconfigure(self.messages_window, width=event.width)

    def _on_mousewheel(self, event: tk.Event) -> None:
        self.chat_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _attach_copy_menu(self, widget: tk.Widget, text: str) -> None:
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="复制", command=lambda: self._copy_text(text))
        widget.bind("<Button-3>", lambda event: menu.tk_popup(event.x_root, event.y_root))

    def _copy_text(self, text: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(text)

    @staticmethod
    def _set_text(widget: tk.Text, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _section(self, parent: ttk.Frame, row: int, title: str) -> ttk.Frame:
        frame = ttk.Frame(parent, style="Section.TFrame", padding=(12, 10, 12, 12))
        frame.grid(row=row, column=0, sticky="nsew", pady=(0, 12))
        frame.columnconfigure(0, weight=1)
        ttk.Label(frame, text=title, style="SectionTitle.TLabel").grid(row=0, column=0, sticky="w")
        return frame

    def _status_row(self, parent: ttk.Frame, row: int, key: str, label: str) -> None:
        value = tk.StringVar(value="-")
        self.health_labels[key] = value
        ttk.Label(parent, text=label, style="StatusName.TLabel").grid(row=row + 1, column=0, sticky="w", pady=(10 if row == 0 else 6, 0))
        value_label = ttk.Label(parent, textvariable=value, style="Info.TLabel")
        value_label.grid(row=row + 1, column=1, sticky="e", pady=(10 if row == 0 else 6, 0))
        parent.columnconfigure(1, weight=1)
        self.health_value_labels[key] = value_label

    def _set_status(self, key: str, value: str, tone: str) -> None:
        self.health_labels[key].set(value)
        style = "Ok.TLabel" if tone == "ok" else "Warn.TLabel" if tone == "warn" else "Info.TLabel"
        self.health_value_labels[key].configure(style=style)

    def _small_text(self, parent: ttk.Frame, height: int) -> tk.Text:
        return tk.Text(
            parent,
            width=38,
            height=height,
            wrap="word",
            state="disabled",
            bg=PANEL,
            fg=MUTED_DARK,
            selectbackground="#bfdbfe",
            selectforeground=TEXT,
            inactiveselectbackground="#dbeafe",
            borderwidth=1,
            relief="solid",
            highlightthickness=0,
            padx=10,
            pady=9,
            font=("Microsoft YaHei UI", 9),
        )

    def _markdown_bubble(self, parent: tk.Widget, content: str) -> tk.Text:
        text = tk.Text(
            parent,
            width=76,
            height=self._estimate_markdown_height(content),
            wrap="word",
            bg=ASSISTANT_BG,
            fg=TEXT,
            selectbackground="#bfdbfe",
            selectforeground=TEXT,
            inactiveselectbackground="#dbeafe",
            borderwidth=1,
            relief="solid",
            highlightthickness=0,
            padx=17,
            pady=13,
            font=("Microsoft YaHei UI", 10),
        )
        base_font = tkfont.Font(font=text.cget("font"))
        bold_font = base_font.copy()
        bold_font.configure(weight="bold")
        code_font = tkfont.Font(family="Consolas", size=10)
        text.tag_configure("bold", font=bold_font)
        text.tag_configure("heading", font=bold_font, spacing1=4, spacing3=4)
        text.tag_configure("code", font=code_font, background="#f1f5f9", foreground="#1f2937")
        text.tag_configure("code_block", font=code_font, background="#f1f5f9", foreground="#1f2937", lmargin1=8, lmargin2=8)
        text.bind("<MouseWheel>", lambda event: (self._on_mousewheel(event), "break")[1])
        self._insert_markdown(text, content)
        text.configure(state="disabled")
        return text

    def _insert_markdown(self, widget: tk.Text, content: str) -> None:
        in_code_block = False
        for raw_line in content.splitlines() or [""]:
            line = raw_line.rstrip()
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                widget.insert(tk.END, line + "\n", ("code_block",))
                continue

            stripped = line.lstrip()
            if stripped.startswith("#"):
                heading = stripped.lstrip("#").strip()
                if heading:
                    widget.insert(tk.END, heading + "\n", ("heading",))
                    continue
            self._insert_inline_markdown(widget, line)
            widget.insert(tk.END, "\n")

        if widget.get("end-2c", "end-1c") == "\n":
            widget.delete("end-2c", "end-1c")

    def _insert_inline_markdown(self, widget: tk.Text, line: str) -> None:
        parts = line.split("**")
        for idx, part in enumerate(parts):
            if not part:
                continue
            widget.insert(tk.END, part, ("bold",) if idx % 2 else ())

    @staticmethod
    def _estimate_markdown_height(content: str) -> int:
        lines = content.splitlines() or [""]
        height = 0
        for line in lines:
            visible = line.strip()
            if visible.startswith("```"):
                height += 1
                continue
            height += max(1, (len(line) // 64) + 1)
        return max(height, 2)

    def _reset_inspector(self) -> None:
        self.response_labels["intent"].set("暂无响应数据。")
        self.response_labels["model"].set("-")
        self.response_labels["latency"].set("-")
        self.response_labels["sources"].set("-")
        self._set_text(self.tool_view, "触发 时间 或 天气 后会显示。")
        self._set_text(self.source_view, "RAG 问答会在这里列出引用片段。")

    @staticmethod
    def _status_label(key: str) -> str:
        labels = {
            "sqlite": "数据库",
            "vector_store": "向量库",
            "model": "模型",
            "data_dir": "数据目录",
        }
        return labels.get(key, key)


def main() -> None:
    app = ChatbotDesktopApp()
    app.mainloop()


if __name__ == "__main__":
    main()
