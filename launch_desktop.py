import asyncio
import json
import shutil
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from app.config import get_settings
from app.db.database import delete_session, init_db, list_messages, list_sessions
from app.rag.ingest import import_knowledge
from app.rag.vector_store import vector_store_ready
from app.runtime import seed_runtime_knowledge
from app.schemas import ChatRequest, ChatResponse
from app.services.chat_service import handle_chat


BG = "#eef3f8"
PANEL = "#ffffff"
BORDER = "#d6e0ea"
TEXT = "#152231"
MUTED = "#667789"
ACCENT = "#1f6feb"
ACCENT_DARK = "#1756bd"
USER_BG = "#d9eaff"
ASSISTANT_BG = "#f7fafc"
SOFT_BLUE = "#eaf3ff"
SUCCESS = "#16803c"
WARNING = "#b45309"
SECTION_BG = "#f8fbff"


class ChatbotDesktopApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("个人知识问答聊天助手")
        self.geometry("1240x780")
        self.minsize(1040, 680)
        self.configure(bg=BG)

        self.settings = get_settings()
        self.session_id: str | None = None
        self.user_id = tk.StringVar(value="demo")
        self.status = tk.StringVar(value="就绪")
        self.session_count = tk.StringVar(value="0 个会话")
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
        style.configure("Title.TLabel", background=BG, foreground=TEXT, font=("Microsoft YaHei UI", 18, "bold"))
        style.configure("Subtitle.TLabel", background=BG, foreground=MUTED, font=("Microsoft YaHei UI", 9))
        style.configure("PanelTitle.TLabel", background=PANEL, foreground=TEXT, font=("Microsoft YaHei UI", 11, "bold"))
        style.configure("Muted.TLabel", background=PANEL, foreground=MUTED)
        style.configure("Status.TLabel", background=SOFT_BLUE, foreground=ACCENT_DARK, padding=(12, 5), font=("Microsoft YaHei UI", 9, "bold"))
        style.configure("BrandIcon.TLabel", background="#0f8b80", foreground="#ffffff", padding=(8, 5), font=("Microsoft YaHei UI", 15, "bold"))
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
        style.configure("Tool.TButton", padding=(10, 6), background="#f8fbff", foreground=TEXT, bordercolor=BORDER)
        style.map("Tool.TButton", background=[("active", SOFT_BLUE), ("pressed", "#dbeafe")])
        style.configure("TEntry", fieldbackground="#ffffff", bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self, style="Header.TFrame", padding=(20, 16, 20, 10))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="个人知识问答聊天助手", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="本地桌面客户端：支持聊天、工具调用、会话记录和知识库问答",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))
        ttk.Label(header, textvariable=self.status, style="Status.TLabel").grid(row=0, column=1, rowspan=2, sticky="e")

        body = ttk.Frame(self, style="App.TFrame", padding=(20, 8, 20, 18))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_left_panel(body)
        self._build_chat_panel(body)
        self._build_right_panel(body)

    def _build_left_panel(self, parent: ttk.Frame) -> None:
        left = ttk.Frame(parent, style="Panel.TFrame", padding=14)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 12))
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
        ttk.Button(left, text="删除会话", style="Tool.TButton", command=self.delete_selected_session).grid(
            row=6, column=0, sticky="ew", pady=(6, 0)
        )
        ttk.Label(left, text="↺  会话", style="PanelTitle.TLabel").grid(row=7, column=0, sticky="w", pady=(18, 2))
        ttk.Label(left, textvariable=self.session_count, style="Muted.TLabel").grid(row=8, column=0, sticky="w", pady=(0, 4))

        self.session_list = tk.Listbox(
            left,
            width=30,
            activestyle="none",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=BORDER,
            selectbackground=ACCENT,
            selectforeground="#ffffff",
            bg="#fbfcfe",
            fg=TEXT,
            font=("Microsoft YaHei UI", 10),
        )
        self.session_list.grid(row=9, column=0, sticky="nsew")
        self.session_list.bind("<<ListboxSelect>>", self.open_selected_session)

    def _build_chat_panel(self, parent: ttk.Frame) -> None:
        center = ttk.Frame(parent, style="Panel.TFrame", padding=0)
        center.grid(row=0, column=1, sticky="nsew")
        center.columnconfigure(0, weight=1)
        center.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(center, style="Panel.TFrame", padding=(14, 12))
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
                row=0, column=idx + 1, padx=(6, 0)
            )

        self.chat_canvas = tk.Canvas(center, bg="#edf4fb", highlightthickness=0, borderwidth=0)
        self.chat_canvas.grid(row=1, column=0, sticky="nsew")
        chat_scroll = ttk.Scrollbar(center, orient="vertical", command=self.chat_canvas.yview)
        chat_scroll.grid(row=1, column=1, sticky="ns")
        self.chat_canvas.configure(yscrollcommand=chat_scroll.set)
        self.messages_frame = tk.Frame(self.chat_canvas, bg="#edf4fb")
        self.messages_window = self.chat_canvas.create_window((0, 0), window=self.messages_frame, anchor="nw")
        self.messages_frame.bind("<Configure>", self._sync_message_scrollregion)
        self.chat_canvas.bind("<Configure>", self._sync_message_width)
        self.chat_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        input_bar = ttk.Frame(center, style="Panel.TFrame", padding=(14, 14))
        input_bar.grid(row=2, column=0, columnspan=2, sticky="ew")
        input_bar.columnconfigure(0, weight=1)

        self.message_input = ttk.Entry(input_bar)
        self.message_input.grid(row=0, column=0, sticky="ew", padx=(0, 8), ipady=5)
        self.message_input.bind("<Return>", self.send_message)
        ttk.Button(input_bar, text="发送", style="Accent.TButton", command=self.send_message).grid(row=0, column=1)

    def _build_right_panel(self, parent: ttk.Frame) -> None:
        right = ttk.Frame(parent, style="Panel.TFrame", padding=14)
        right.grid(row=0, column=2, sticky="ns", padx=(12, 0))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(3, weight=1)
        right.rowconfigure(4, weight=1)

        status = self._section(right, 0, "⌁  系统状态")
        self.health_labels: dict[str, tk.StringVar] = {}
        self.health_value_labels: dict[str, ttk.Label] = {}
        for row, (key, label) in enumerate(
            (("api", "API"), ("sqlite", "SQLite"), ("vector_store", "向量库"), ("model", "大模型")),
            start=0,
        ):
            self._status_row(status, row, key, label)

        recent = self._section(right, 1, "◷  最近响应")
        self.response_labels = {
            "intent": tk.StringVar(value="暂无响应数据。"),
            "model": tk.StringVar(value="-"),
            "latency": tk.StringVar(value="-"),
            "sources": tk.StringVar(value="-"),
        }
        ttk.Label(recent, text="意图", style="StatusName.TLabel").grid(row=0, column=0, sticky="w", pady=(8, 0))
        ttk.Label(recent, textvariable=self.response_labels["intent"], style="Info.TLabel").grid(row=0, column=1, sticky="e", pady=(8, 0))
        ttk.Label(recent, text="模型", style="StatusName.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Label(recent, textvariable=self.response_labels["model"], style="StatusName.TLabel").grid(row=1, column=1, sticky="e", pady=(4, 0))
        ttk.Label(recent, text="耗时", style="StatusName.TLabel").grid(row=2, column=0, sticky="w", pady=(4, 0))
        ttk.Label(recent, textvariable=self.response_labels["latency"], style="StatusName.TLabel").grid(row=2, column=1, sticky="e", pady=(4, 0))
        ttk.Label(recent, text="来源", style="StatusName.TLabel").grid(row=3, column=0, sticky="w", pady=(4, 0))
        ttk.Label(recent, textvariable=self.response_labels["sources"], style="StatusName.TLabel").grid(row=3, column=1, sticky="e", pady=(4, 0))

        tool = self._section(right, 2, "▣  工具结果")
        self.tool_view = self._small_text(tool, height=4)
        self.tool_view.grid(row=0, column=0, sticky="nsew", pady=(8, 0))
        self._set_text(self.tool_view, "触发 时间 或 天气 后会显示。")

        rag = self._section(right, 3, "▤  RAG 来源")
        rag.rowconfigure(0, weight=1)
        self.source_view = self._small_text(rag, height=5)
        self.source_view.grid(row=0, column=0, sticky="nsew", pady=(8, 0))
        self._set_text(self.source_view, "RAG 问答会在这里列出引用片段。")

        knowledge = self._section(right, 4, "↥  知识库")
        ttk.Button(knowledge, text="▣  导入默认知识库", style="Tool.TButton", command=self.import_default_knowledge).grid(
            row=0, column=0, sticky="ew", pady=(8, 6)
        )
        ttk.Button(knowledge, text="↥  上传 .txt / .md", style="Tool.TButton", command=self.upload_knowledge_file).grid(
            row=1, column=0, sticky="ew"
        )
        self.knowledge_note = tk.StringVar(value="默认知识库会在首次启动时准备。")
        ttk.Label(knowledge, textvariable=self.knowledge_note, style="SectionBody.TLabel", wraplength=280).grid(
            row=2, column=0, sticky="w", pady=(8, 0)
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

    def _show_welcome(self) -> None:
        self._clear_messages()
        box = tk.Frame(self.messages_frame, bg="#edf4fb", pady=70)
        box.pack(fill="both", expand=True)
        tk.Label(
            box,
            text="个人知识问答助手",
            bg="#edf4fb",
            fg=TEXT,
            font=("Microsoft YaHei UI", 17, "bold"),
        ).pack()
        tk.Label(
            box,
            text="选择上方示例问题，或直接输入你的问题。\n支持北京时间、城市天气、知识库问答和普通聊天。",
            bg="#edf4fb",
            fg=MUTED,
            font=("Microsoft YaHei UI", 10),
            justify="center",
        ).pack(pady=(8, 0))
        self.chat_has_content = False

    def _append_message(self, label: str, content: str, tag: str, meta: str | None = None) -> None:
        is_user = tag == "user"
        row = tk.Frame(self.messages_frame, bg="#edf4fb", padx=18, pady=8)
        row.pack(fill="x", anchor="e" if is_user else "w")

        content_frame = tk.Frame(row, bg="#edf4fb")
        content_frame.pack(side="right" if is_user else "left", anchor="e" if is_user else "w")

        top = tk.Frame(content_frame, bg="#edf4fb")
        top.pack(fill="x")
        if is_user:
            tk.Label(top, text="你", bg="#edf4fb", fg=ACCENT, font=("Microsoft YaHei UI", 9, "bold")).pack(side="right")
        else:
            tk.Label(top, text="助手", bg="#edf4fb", fg=ACCENT, font=("Microsoft YaHei UI", 9, "bold")).pack(side="left")

        bubble = tk.Label(
            content_frame,
            text=content,
            bg="#0f8b80" if is_user else "#f8fbff",
            fg="#ffffff" if is_user else TEXT,
            padx=16,
            pady=12,
            wraplength=520,
            justify="left",
            font=("Microsoft YaHei UI", 10),
            relief="flat",
            bd=0,
        )
        bubble.pack(anchor="e" if is_user else "w", pady=(6, 0))
        self._attach_copy_menu(bubble, content)

        if meta:
            tk.Label(
                content_frame,
                text=meta,
                bg="#edf4fb",
                fg=MUTED,
                font=("Microsoft YaHei UI", 9),
            ).pack(anchor="w", pady=(5, 0))
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
        frame = ttk.Frame(parent, style="Section.TFrame", padding=(0, 0, 0, 14))
        frame.grid(row=row, column=0, sticky="nsew", pady=(0, 12))
        frame.columnconfigure(0, weight=1)
        ttk.Label(frame, text=title, style="SectionTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Separator(frame).grid(row=99, column=0, sticky="ew", pady=(12, 0))
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
            bg=SECTION_BG,
            fg=MUTED,
            selectbackground="#bfdbfe",
            selectforeground=TEXT,
            inactiveselectbackground="#dbeafe",
            borderwidth=0,
            highlightthickness=0,
            padx=0,
            pady=0,
            font=("Microsoft YaHei UI", 9),
        )

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
