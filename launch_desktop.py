import asyncio
import json
import logging
import shutil
import threading
import tkinter as tk
import time
from pathlib import Path
from tkinter import filedialog, font as tkfont, messagebox, ttk
from typing import Any

from app.config import get_settings
from app.db.database import delete_session, init_db, list_messages, list_sessions
from app.rag.ingest import import_knowledge
from app.rag.vector_store import vector_store_ready
from app.runtime import runtime_path, seed_runtime_knowledge
from app.schemas import ChatRequest, ChatResponse
from app.services.chat_service import handle_chat


DESKTOP_REQUEST_TIMEOUT_SECONDS = 45

BG = "#F5F7FA"
CARD = "#FFFFFF"
CARD_SOFT = "#F8FAFC"
CHAT_BG = "#F3F6F8"
BORDER = "#E2E8F0"
BORDER_DARK = "#CBD5E1"
TEXT = "#0F172A"
MUTED = "#64748B"
MUTED_DARK = "#475569"
PRIMARY = "#0F766E"
PRIMARY_DARK = "#115E59"
PRIMARY_SOFT = "#CCFBF1"
PRIMARY_TINT = "#ECFDF5"
SUCCESS = "#16A34A"
DANGER = "#DC2626"
DANGER_SOFT = "#FEF2F2"
WARNING = "#D97706"
USER_BG = PRIMARY
ASSISTANT_BG = "#FFFFFF"

FONT = "Microsoft YaHei UI"
FONT_FALLBACK = "Segoe UI"


class ChatbotDesktopApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("个人知识问答助手")
        self.geometry("1280x800")
        self.minsize(1100, 700)
        self.configure(bg=BG)

        self.settings = get_settings()
        self.session_id: str | None = None
        self.user_id = tk.StringVar(value="demo")
        self.status = tk.StringVar(value="在线")
        self.input_status = tk.StringVar(value="")
        self.session_count = tk.StringVar(value="0 个会话")
        self.llm_api_key = tk.StringVar(value=self.settings.llm_api_key)
        self.show_api_keys = tk.BooleanVar(value=False)
        self.config_expanded = tk.BooleanVar(value=False)
        self.chat_has_content = False
        self.sessions: list[dict[str, Any]] = []
        self.session_cards: list[tk.Frame] = []
        self.loading_row: tk.Widget | None = None
        self.loading_label: tk.Label | None = None
        self.loading_after_id: str | None = None
        self.loading_started_at = 0.0
        self.loading_tick = 0
        self.loading_base_text = "正在处理"
        self.is_sending = False
        self._configure_logging()

        self._initialize_runtime()
        self._configure_styles()
        self._build_ui()
        self.refresh_status()
        self.refresh_sessions()
        self._show_welcome()

    def _configure_logging(self) -> None:
        log_path = runtime_path("data", "desktop.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            filename=log_path,
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
            encoding="utf-8",
        )

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

        base_font = (FONT, 10)
        style.configure(".", font=base_font, background=BG, foreground=TEXT)
        style.configure("App.TFrame", background=BG)
        style.configure("Surface.TFrame", background=CARD)
        style.configure("Chat.TFrame", background=CHAT_BG)
        style.configure("Header.TFrame", background=BG)
        style.configure("Divider.TFrame", background=BORDER)
        style.configure("Title.TLabel", background=BG, foreground=TEXT, font=(FONT, 17, "bold"))
        style.configure("Subtitle.TLabel", background=BG, foreground=MUTED, font=(FONT, 9))
        style.configure("PanelTitle.TLabel", background=CARD, foreground=TEXT, font=(FONT, 11, "bold"))
        style.configure("SmallTitle.TLabel", background=CARD, foreground=TEXT, font=(FONT, 10, "bold"))
        style.configure("Muted.TLabel", background=CARD, foreground=MUTED, font=(FONT, 9))
        style.configure("Body.TLabel", background=CARD, foreground=TEXT, font=(FONT, 10))
        style.configure("Pill.TLabel", background=PRIMARY_TINT, foreground=PRIMARY_DARK, padding=(10, 4), font=(FONT, 9, "bold"))
        style.configure("Section.TFrame", background=CARD_SOFT)
        style.configure("SectionTitle.TLabel", background=CARD_SOFT, foreground=TEXT, font=(FONT, 10, "bold"))
        style.configure("SectionBody.TLabel", background=CARD_SOFT, foreground=MUTED_DARK, font=(FONT, 9))
        style.configure("StatusName.TLabel", background=CARD_SOFT, foreground=MUTED, font=(FONT, 9))
        style.configure("Ok.TLabel", background=CARD_SOFT, foreground=SUCCESS, font=(FONT, 9, "bold"))
        style.configure("Warn.TLabel", background=CARD_SOFT, foreground=WARNING, font=(FONT, 9, "bold"))
        style.configure("Info.TLabel", background=CARD_SOFT, foreground=PRIMARY_DARK, font=(FONT, 9, "bold"))
        style.configure("Primary.TButton", padding=(14, 8), background=PRIMARY, foreground="#FFFFFF", bordercolor=PRIMARY)
        style.map("Primary.TButton", background=[("active", PRIMARY_DARK), ("pressed", PRIMARY_DARK)])
        style.configure("Secondary.TButton", padding=(12, 8), background=CARD_SOFT, foreground=TEXT, bordercolor=BORDER_DARK)
        style.map("Secondary.TButton", background=[("active", PRIMARY_TINT), ("pressed", PRIMARY_SOFT)])
        style.configure("Danger.TButton", padding=(12, 8), background=DANGER_SOFT, foreground=DANGER, bordercolor="#FECACA")
        style.map("Danger.TButton", background=[("active", "#FEE2E2"), ("pressed", "#FECACA")])
        style.configure("Chip.TButton", padding=(11, 6), background="#FFFFFF", foreground=MUTED_DARK, bordercolor=BORDER)
        style.map("Chip.TButton", background=[("active", PRIMARY_TINT), ("pressed", PRIMARY_SOFT)], foreground=[("active", PRIMARY_DARK)])
        style.configure("TEntry", fieldbackground="#FFFFFF", bordercolor=BORDER_DARK, lightcolor=BORDER_DARK, darkcolor=BORDER_DARK)
        style.configure("TCheckbutton", background=CARD_SOFT, foreground=MUTED_DARK)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self, style="Header.TFrame", padding=(22, 14, 22, 8))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="个人知识问答助手", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="本地桌面客户端 · 聊天 · 工具调用 · 知识库问答",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))
        ttk.Label(header, textvariable=self.status, style="Pill.TLabel").grid(row=0, column=1, rowspan=2, sticky="e")

        body = ttk.Frame(self, style="App.TFrame", padding=(22, 8, 22, 22))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, minsize=270)
        body.columnconfigure(1, weight=1)
        body.columnconfigure(2, minsize=320)
        body.rowconfigure(0, weight=1)

        self._build_left_panel(body)
        self._build_chat_panel(body)
        self._build_right_panel(body)

    def _build_left_panel(self, parent: ttk.Frame) -> None:
        left = tk.Frame(parent, bg=CARD, bd=0, highlightthickness=1, highlightbackground=BORDER)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        left.grid_propagate(False)
        left.configure(width=270)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(8, weight=1)

        content = tk.Frame(left, bg=CARD, padx=16, pady=16)
        content.grid(row=0, column=0, rowspan=9, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(8, weight=1)

        tk.Label(content, text="个人知识问答助手", bg=CARD, fg=TEXT, font=(FONT, 13, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(
            content,
            text="本地桌面客户端 · 聊天 · 工具调用 · 知识库问答",
            bg=CARD,
            fg=MUTED,
            font=(FONT, 9),
            wraplength=230,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(4, 14))

        tk.Label(content, text="用户 ID", bg=CARD, fg=MUTED, font=(FONT, 9)).grid(row=2, column=0, sticky="w")
        ttk.Entry(content, textvariable=self.user_id).grid(row=3, column=0, sticky="ew", pady=(4, 12), ipady=4)
        ttk.Button(content, text="新建会话", style="Primary.TButton", command=self.new_chat).grid(row=4, column=0, sticky="ew")

        actions = tk.Frame(content, bg=CARD)
        actions.grid(row=5, column=0, sticky="ew", pady=(8, 0))
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        ttk.Button(actions, text="刷新", style="Secondary.TButton", command=self.refresh_sessions).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(actions, text="删除", style="Danger.TButton", command=self.delete_selected_session).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        tk.Label(content, text="会话", bg=CARD, fg=TEXT, font=(FONT, 11, "bold")).grid(row=6, column=0, sticky="w", pady=(18, 0))
        tk.Label(content, textvariable=self.session_count, bg=CARD, fg=MUTED, font=(FONT, 9)).grid(row=7, column=0, sticky="w", pady=(2, 8))

        self.sessions_canvas = tk.Canvas(content, bg=CARD, highlightthickness=0, borderwidth=0)
        self.sessions_canvas.grid(row=8, column=0, sticky="nsew")
        self.sessions_frame = tk.Frame(self.sessions_canvas, bg=CARD)
        self.sessions_window = self.sessions_canvas.create_window((0, 0), window=self.sessions_frame, anchor="nw")
        session_scroll = ttk.Scrollbar(content, orient="vertical", command=self.sessions_canvas.yview)
        session_scroll.grid(row=8, column=1, sticky="ns")
        self.sessions_canvas.configure(yscrollcommand=session_scroll.set)
        self.sessions_frame.bind("<Configure>", lambda _event: self.sessions_canvas.configure(scrollregion=self.sessions_canvas.bbox("all")))
        self.sessions_canvas.bind("<Configure>", lambda event: self.sessions_canvas.itemconfigure(self.sessions_window, width=event.width))

    def _build_chat_panel(self, parent: ttk.Frame) -> None:
        center = tk.Frame(parent, bg=CARD, bd=0, highlightthickness=1, highlightbackground=BORDER)
        center.grid(row=0, column=1, sticky="nsew")
        center.columnconfigure(0, weight=1)
        center.rowconfigure(1, weight=1)

        toolbar = tk.Frame(center, bg=CARD, padx=16, pady=12)
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.columnconfigure(0, weight=1)
        tk.Label(toolbar, text="当前对话", bg=CARD, fg=TEXT, font=(FONT, 11, "bold")).grid(row=0, column=0, sticky="w")
        samples = (
            ("你好", "你好"),
            ("北京时间", "北京时间"),
            ("城市天气", "上海天气"),
            ("知识库问答", "根据知识库介绍项目"),
        )
        for idx, (label, prompt) in enumerate(samples):
            ttk.Button(toolbar, text=label, style="Chip.TButton", command=lambda text=prompt: self.use_sample(text)).grid(
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

        input_bar = tk.Frame(center, bg=CARD, padx=16, pady=14)
        input_bar.grid(row=2, column=0, columnspan=2, sticky="ew")
        input_bar.columnconfigure(0, weight=1)

        tk.Label(
            input_bar,
            textvariable=self.input_status,
            bg=CARD,
            fg=MUTED_DARK,
            font=(FONT, 9),
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        input_shell = tk.Frame(input_bar, bg="#FFFFFF", highlightthickness=1, highlightbackground=BORDER_DARK, bd=0)
        input_shell.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        input_shell.columnconfigure(0, weight=1)
        self.message_input = tk.Text(
            input_shell,
            height=2,
            wrap="word",
            bg="#FFFFFF",
            fg=TEXT,
            bd=0,
            padx=12,
            pady=9,
            insertbackground=PRIMARY,
            font=(FONT, 10),
        )
        self.message_input.grid(row=0, column=0, sticky="ew")
        self.placeholder = "输入消息，例如：明天武汉天气 / 根据知识库介绍项目"
        self.placeholder_visible = False
        self._show_placeholder()
        self.message_input.bind("<FocusIn>", self._hide_placeholder)
        self.message_input.bind("<FocusOut>", self._maybe_show_placeholder)
        self.message_input.bind("<Return>", self._handle_enter)
        self.message_input.bind("<Shift-Return>", self._handle_shift_enter)
        self.send_button = ttk.Button(input_bar, text="发送", style="Primary.TButton", command=self.send_message)
        self.send_button.grid(row=1, column=1, sticky="ns")

    def _build_right_panel(self, parent: ttk.Frame) -> None:
        right = tk.Frame(parent, bg=CARD, bd=0, highlightthickness=1, highlightbackground=BORDER)
        right.grid(row=0, column=2, sticky="ns", padx=(12, 0))
        right.grid_propagate(False)
        right.configure(width=320)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(3, weight=1)
        right.rowconfigure(4, weight=1)

        content = tk.Frame(right, bg=CARD, padx=14, pady=14)
        content.grid(row=0, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(3, weight=1)
        content.rowconfigure(4, weight=1)

        status = self._section(content, 0, "系统状态")
        self.health_labels: dict[str, tk.StringVar] = {}
        self.health_value_labels: dict[str, ttk.Label] = {}
        for row, (key, label) in enumerate((("api", "API"), ("sqlite", "SQLite"), ("vector_store", "向量库"), ("model", "模型"))):
            self._status_row(status, row, key, label)

        recent = self._section(content, 1, "最近响应")
        self.response_labels = {
            "intent": tk.StringVar(value="暂无响应"),
            "model": tk.StringVar(value="-"),
            "latency": tk.StringVar(value="-"),
            "sources": tk.StringVar(value="-"),
        }
        self._kv_row(recent, 1, "类型", self.response_labels["intent"], "Info.TLabel")
        self._kv_row(recent, 2, "模型", self.response_labels["model"])
        self._kv_row(recent, 3, "耗时", self.response_labels["latency"])
        self._kv_row(recent, 4, "来源", self.response_labels["sources"])

        tool = self._section(content, 2, "工具结果")
        self.tool_view = self._small_text(tool, height=4)
        self.tool_view.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        self._set_text(self.tool_view, "触发时间、天气等工具后会显示摘要。")

        rag = self._section(content, 3, "RAG 来源")
        rag.rowconfigure(1, weight=1)
        self.source_view = self._small_text(rag, height=5)
        self.source_view.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        self._set_text(self.source_view, "知识库问答会在这里列出引用片段。")

        knowledge = self._section(content, 4, "知识库")
        ttk.Button(knowledge, text="导入默认知识库", style="Secondary.TButton", command=self.import_default_knowledge).grid(
            row=1, column=0, sticky="ew", pady=(8, 6)
        )
        ttk.Button(knowledge, text="上传 .txt / .md", style="Secondary.TButton", command=self.upload_knowledge_file).grid(row=2, column=0, sticky="ew")
        self.knowledge_note = tk.StringVar(value="默认知识库会在首次启动时准备。")
        ttk.Label(knowledge, textvariable=self.knowledge_note, style="SectionBody.TLabel", wraplength=270).grid(
            row=3, column=0, sticky="w", pady=(8, 0)
        )

        config = self._section(content, 5, "配置区域")
        self.config_toggle = ttk.Button(config, text="显示 API Key 配置", style="Secondary.TButton", command=self.toggle_config_panel)
        self.config_toggle.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.config_body = ttk.Frame(config, style="Section.TFrame")
        self.config_body.columnconfigure(0, weight=1)
        ttk.Label(self.config_body, text="LLM API Key", style="StatusName.TLabel").grid(row=0, column=0, sticky="w", pady=(10, 3))
        self.llm_key_entry = ttk.Entry(self.config_body, textvariable=self.llm_api_key, show="*")
        self.llm_key_entry.grid(row=1, column=0, sticky="ew")
        ttk.Checkbutton(
            self.config_body,
            text="显示密钥",
            variable=self.show_api_keys,
            command=self.toggle_api_key_visibility,
        ).grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Button(self.config_body, text="保存配置", style="Primary.TButton", command=self.save_api_config).grid(row=3, column=0, sticky="ew", pady=(10, 6))
        ttk.Button(self.config_body, text="重新加载配置", style="Secondary.TButton", command=self.reload_api_config).grid(row=4, column=0, sticky="ew")

    def refresh_status(self) -> None:
        model = self.settings.llm_model if self.settings.llm_api_key else "offline-demo"
        vector_ready = vector_store_ready()
        self._set_status("api", "ok", "ok")
        self._set_status("sqlite", "ready", "ok")
        self._set_status("vector_store", "ready" if vector_ready else "missing", "ok" if vector_ready else "warn")
        self._set_status("model", model, "warn" if model == "offline-demo" else "ok")

    def refresh_sessions(self) -> None:
        self.sessions = list_sessions(self.user_id.get().strip() or "demo")
        self.session_count.set(f"{len(self.sessions)} 个会话")
        for child in self.sessions_frame.winfo_children():
            child.destroy()
        self.session_cards = []
        for idx, item in enumerate(self.sessions):
            self._add_session_card(idx, item)

    def new_chat(self) -> None:
        self.session_id = None
        self._show_welcome()
        self._reset_inspector()
        self.status.set("新会话")
        self._focus_input()

    def delete_selected_session(self) -> None:
        if not self.session_id:
            messagebox.showinfo("删除会话", "请先选择一个会话。")
            return
        item = next((row for row in self.sessions if row["id"] == self.session_id), None)
        if not item:
            messagebox.showinfo("删除会话", "请先选择一个会话。")
            return
        title = item.get("title") or "未命名会话"
        if not messagebox.askyesno("删除会话", f"确定删除会话“{title}”吗？\n删除后会移除该会话的消息和模型输出记录。"):
            return
        if delete_session(item["id"]):
            self.session_id = None
            self._show_welcome()
            self._reset_inspector()
            self.refresh_sessions()
            self.status.set("会话已删除")
        else:
            messagebox.showerror("删除失败", "没有找到这个会话。")

    def open_selected_session(self, index: int) -> None:
        if index < 0 or index >= len(self.sessions):
            return
        item = self.sessions[index]
        self.session_id = item["id"]
        self._clear_messages()
        self.chat_has_content = False
        for row in list_messages(self.session_id):
            role = "user" if row["role"] == "user" else "assistant"
            self._append_message("你" if role == "user" else "助手", row["content"], role)
        self.status.set(f"已打开：{item['title'][:22]}")
        self._paint_session_selection()

    def use_sample(self, text: str) -> None:
        self._clear_placeholder()
        self.message_input.delete("1.0", tk.END)
        self.message_input.insert("1.0", text)
        self._focus_input()

    def send_message(self, _event: object | None = None) -> None:
        if self.is_sending:
            return
        message = self._input_text()
        if not message:
            return
        self._set_busy(True)
        try:
            self.message_input.delete("1.0", tk.END)
            self._maybe_show_placeholder()
            if not self.chat_has_content:
                self._clear_messages()
            self._append_message("你", message, "user")
            self.loading_base_text = self._working_text(message)
            request_user_id = self.user_id.get().strip() or "demo"
            logging.info(
                "desktop request started user_id=%s session_id=%s message=%s",
                request_user_id,
                self.session_id,
                message,
            )
            self.status.set(self.loading_base_text)
            self.input_status.set(f"{self.loading_base_text}，请稍候")
            self.response_labels["intent"].set("正在处理")
            self.response_labels["model"].set("等待响应")
            self.response_labels["latency"].set("计时中")
            self.response_labels["sources"].set("-")
            self._set_text(self.tool_view, "请求已发送，正在等待工具或模型返回。")
            self.loading_row = self._append_loading_message(self.loading_base_text)
            self._start_loading_animation()
            self.update_idletasks()
            request = ChatRequest(user_id=request_user_id, message=message, session_id=self.session_id)
            threading.Thread(target=self._send_message_worker, args=(request,), daemon=True).start()
        except Exception as exc:
            logging.exception("desktop send callback failed")
            self._show_error(exc)

    def _send_message_worker(self, request: ChatRequest) -> None:
        try:
            response = asyncio.run(asyncio.wait_for(handle_chat(request), timeout=DESKTOP_REQUEST_TIMEOUT_SECONDS))
        except TimeoutError:
            logging.exception("desktop request timed out after %s seconds", DESKTOP_REQUEST_TIMEOUT_SECONDS)
            self.after(0, self._show_timeout_error)
            return
        except Exception as exc:
            logging.exception("desktop request failed")
            self.after(0, lambda exc=exc: self._show_error(exc))
            return
        self.after(0, lambda: self._show_response(response))

    def _show_response(self, response: ChatResponse) -> None:
        self._remove_loading()
        self._set_busy(False)
        self.input_status.set("")
        logging.info(
            "desktop request finished session_id=%s intent=%s model=%s latency_ms=%s",
            response.session_id,
            response.intent,
            response.model,
            response.latency_ms,
        )
        self.session_id = response.session_id
        meta = self._friendly_meta(response)
        self._append_message("助手", response.answer, "assistant", meta=meta, response=response)
        self.response_labels["intent"].set(self._intent_label(response.intent))
        self.response_labels["model"].set(response.model)
        self.response_labels["latency"].set(f"{response.latency_ms} ms")
        self.response_labels["sources"].set(f"{len(response.sources)} 条")
        self._set_text(self.tool_view, self._format_tool_result(response))
        self._set_text(self.source_view, self._format_sources(response))
        self.status.set("在线")
        self.refresh_status()
        self.refresh_sessions()

    def _format_tool_result(self, response: ChatResponse) -> str:
        if not response.tool_result:
            return "本次回答没有工具结果。"
        result = response.tool_result
        if result.get("tool") == "weather":
            return self._weather_summary(result)
        if result.get("tool") == "time":
            return str(result.get("summary") or result.get("time") or "时间工具已返回。")
        return json.dumps(result, ensure_ascii=False, indent=2)

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
        self._remove_loading()
        self._set_busy(False)
        self.status.set("发生错误")
        self.input_status.set("请求失败，详情已写入 data/desktop.log")
        self._append_message("助手", f"请求失败：{exc}\n\n详情已写入 data/desktop.log。", "assistant")

    def _show_timeout_error(self) -> None:
        self._remove_loading()
        self._set_busy(False)
        self.status.set("请求超时")
        self.input_status.set(f"请求超过 {DESKTOP_REQUEST_TIMEOUT_SECONDS} 秒未返回，已停止等待")
        self._append_message(
            "助手",
            (
                f"本次请求超过 {DESKTOP_REQUEST_TIMEOUT_SECONDS} 秒没有返回，客户端已停止等待。\n\n"
                "这通常是模型 API 网络超时、服务端无响应或密钥/代理配置异常导致的。"
                "你可以稍后重试，或先用“北京时间”“城市天气”确认工具链是否正常。"
            ),
            "assistant",
        )

    def toggle_config_panel(self) -> None:
        expanded = not self.config_expanded.get()
        self.config_expanded.set(expanded)
        if expanded:
            self.config_body.grid(row=2, column=0, sticky="ew")
            self.config_toggle.configure(text="隐藏 API Key 配置")
        else:
            self.config_body.grid_remove()
            self.config_toggle.configure(text="显示 API Key 配置")

    def toggle_api_key_visibility(self) -> None:
        mask = "" if self.show_api_keys.get() else "*"
        self.llm_key_entry.configure(show=mask)

    def save_api_config(self) -> None:
        try:
            self._write_env_values({"LLM_API_KEY": self.llm_api_key.get().strip()})
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
        outer = tk.Frame(self.messages_frame, bg=CHAT_BG)
        outer.pack(fill="both", expand=True, padx=28, pady=70)
        card = tk.Frame(outer, bg=CARD, highlightthickness=1, highlightbackground=BORDER, padx=28, pady=24)
        card.pack(anchor="center")
        tk.Label(card, text="你好，我是你的本地知识问答助手", bg=CARD, fg=TEXT, font=(FONT, 17, "bold")).pack()
        tk.Label(
            card,
            text="可以直接提问，也可以从下面的示例开始。",
            bg=CARD,
            fg=MUTED,
            font=(FONT, 10),
        ).pack(pady=(8, 18))
        examples = tk.Frame(card, bg=CARD)
        examples.pack()
        for idx, sample in enumerate(("北京天气", "明天武汉天气", "北京时间", "根据知识库介绍项目")):
            ttk.Button(examples, text=sample, style="Chip.TButton", command=lambda text=sample: self.use_sample(text)).grid(
                row=idx // 2,
                column=idx % 2,
                padx=5,
                pady=5,
                sticky="ew",
            )
        self.chat_has_content = False

    def _append_message(
        self,
        label: str,
        content: str,
        tag: str,
        meta: str | None = None,
        response: ChatResponse | None = None,
    ) -> None:
        is_user = tag == "user"
        row = tk.Frame(self.messages_frame, bg=CHAT_BG, padx=24, pady=10)
        row.pack(fill="x", anchor="e" if is_user else "w")

        content_frame = tk.Frame(row, bg=CHAT_BG)
        content_frame.pack(side="right" if is_user else "left", anchor="e" if is_user else "w")

        tk.Label(
            content_frame,
            text=label,
            bg=CHAT_BG,
            fg=PRIMARY_DARK if is_user else MUTED_DARK,
            font=(FONT, 9, "bold"),
        ).pack(anchor="e" if is_user else "w")

        if is_user:
            bubble = self._user_bubble(content_frame, content)
        elif response and response.tool_result and response.tool_result.get("tool") == "weather":
            bubble = self._weather_bubble(content_frame, response.tool_result, content)
        else:
            bubble = self._markdown_bubble(content_frame, content)
        bubble.pack(anchor="e" if is_user else "w", pady=(6, 0))
        self._attach_copy_menu(bubble, content)

        if meta:
            tk.Label(content_frame, text=meta, bg=CHAT_BG, fg=MUTED, font=(FONT, 9)).pack(anchor="w", pady=(6, 0))
        self.messages_frame.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)
        self.chat_has_content = True

    def _append_loading_message(self, text: str) -> tk.Widget:
        row = tk.Frame(self.messages_frame, bg=CHAT_BG, padx=24, pady=10)
        row.pack(fill="x", anchor="w")
        bubble = tk.Label(
            row,
            text=text,
            bg="#FFFFFF",
            fg=MUTED_DARK,
            padx=16,
            pady=11,
            font=(FONT, 10),
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        bubble.pack(side="left", anchor="w")
        self.loading_label = bubble
        self.messages_frame.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)
        return row

    def _remove_loading(self) -> None:
        if self.loading_after_id is not None:
            try:
                self.after_cancel(self.loading_after_id)
            except tk.TclError:
                pass
            self.loading_after_id = None
        if self.loading_row is not None and self.loading_row.winfo_exists():
            self.loading_row.destroy()
        self.loading_row = None
        self.loading_label = None

    def _start_loading_animation(self) -> None:
        self.loading_started_at = time.perf_counter()
        self.loading_tick = 0
        self._animate_loading()

    def _animate_loading(self) -> None:
        if self.loading_label is None or not self.loading_label.winfo_exists():
            self.loading_after_id = None
            return
        elapsed = max(0, int(time.perf_counter() - self.loading_started_at))
        dots = "." * ((self.loading_tick % 3) + 1)
        if elapsed >= 8:
            suffix = f"{dots} 已等待 {elapsed} 秒，仍在运行"
        else:
            suffix = dots
        text = f"{self.loading_base_text}{suffix}"
        self.loading_label.configure(text=text)
        self.status.set(text)
        self.input_status.set(f"{text}，请不要关闭窗口")
        self.response_labels["latency"].set(f"{elapsed} s")
        self.loading_tick += 1
        self.loading_after_id = self.after(500, self._animate_loading)

    def _set_busy(self, busy: bool) -> None:
        self.is_sending = busy
        self.send_button.configure(state="disabled" if busy else "normal")

    @staticmethod
    def _working_text(message: str) -> str:
        text = message.lower()
        if any(word in message for word in ("天气", "气温", "下雨", "降水")):
            return "正在查询天气"
        if any(word in message for word in ("知识库", "项目", "文档", "介绍")):
            return "正在检索知识库"
        if any(word in message for word in ("时间", "几点", "北京时间")):
            return "正在获取时间"
        if any(word in text for word in ("rag", "readme", "api")):
            return "正在检索知识库"
        return "正在调用模型"

    def _user_bubble(self, parent: tk.Widget, content: str) -> tk.Label:
        width = max(280, int(self.chat_canvas.winfo_width() * 0.58))
        return tk.Label(
            parent,
            text=content,
            bg=USER_BG,
            fg="#FFFFFF",
            padx=16,
            pady=12,
            wraplength=width,
            justify="left",
            font=(FONT, 10),
            bd=0,
        )

    def _weather_bubble(self, parent: tk.Widget, result: dict[str, Any], fallback: str) -> tk.Frame:
        frame = tk.Frame(parent, bg=ASSISTANT_BG, highlightthickness=1, highlightbackground=BORDER, padx=16, pady=14)
        width = max(430, int(self.chat_canvas.winfo_width() * 0.68))
        title = self._weather_title(result)
        tk.Label(frame, text=title, bg=ASSISTANT_BG, fg=TEXT, font=(FONT, 12, "bold"), wraplength=width, justify="left").grid(
            row=0, column=0, columnspan=5, sticky="w"
        )
        daily_lines = self._weather_daily_rows(result, fallback)
        if daily_lines:
            headers = ("日期", "天气", "温度", "降水", "风速")
            for col, header in enumerate(headers):
                tk.Label(frame, text=header, bg=ASSISTANT_BG, fg=MUTED, font=(FONT, 9, "bold")).grid(
                    row=1, column=col, sticky="w", padx=(0, 16), pady=(12, 4)
                )
            for row_idx, values in enumerate(daily_lines, start=2):
                for col, value in enumerate(values):
                    tk.Label(frame, text=value, bg=ASSISTANT_BG, fg=TEXT, font=(FONT, 10)).grid(
                        row=row_idx, column=col, sticky="w", padx=(0, 16), pady=3
                    )
        else:
            tk.Label(
                frame,
                text=self._weather_summary(result) or fallback,
                bg=ASSISTANT_BG,
                fg=TEXT,
                font=(FONT, 10),
                wraplength=width,
                justify="left",
            ).grid(row=1, column=0, columnspan=5, sticky="w", pady=(10, 0))
        return frame

    def _markdown_bubble(self, parent: tk.Widget, content: str) -> tk.Text:
        width_chars = 74
        text = tk.Text(
            parent,
            width=width_chars,
            height=self._estimate_markdown_height(content, width_chars),
            wrap="word",
            bg=ASSISTANT_BG,
            fg=TEXT,
            selectbackground="#BFDBFE",
            selectforeground=TEXT,
            inactiveselectbackground="#DBEAFE",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=BORDER,
            padx=16,
            pady=12,
            font=(FONT, 10),
        )
        base_font = tkfont.Font(font=text.cget("font"))
        bold_font = base_font.copy()
        bold_font.configure(weight="bold")
        heading_font = base_font.copy()
        heading_font.configure(weight="bold", size=11)
        code_font = tkfont.Font(family="Consolas", size=10)
        text.tag_configure("bold", font=bold_font)
        text.tag_configure("heading", font=heading_font, spacing1=4, spacing3=4)
        text.tag_configure("code_block", font=code_font, background="#F1F5F9", foreground="#1F2937", lmargin1=8, lmargin2=8)
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
            if part:
                widget.insert(tk.END, part, ("bold",) if idx % 2 else ())

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
        children = list(widget.winfo_children())
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="复制", command=lambda: self._copy_text(text))
        widget.bind("<Button-3>", lambda event: menu.tk_popup(event.x_root, event.y_root))
        for child in children:
            if isinstance(child, tk.Menu):
                continue
            self._attach_copy_menu(child, text)

    def _copy_text(self, text: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(text)

    def _show_placeholder(self) -> None:
        self.placeholder_visible = True
        self.message_input.configure(fg=MUTED)
        self.message_input.delete("1.0", tk.END)
        self.message_input.insert("1.0", self.placeholder)

    def _hide_placeholder(self, _event: object | None = None) -> None:
        if self.placeholder_visible:
            self._clear_placeholder()

    def _maybe_show_placeholder(self, _event: object | None = None) -> None:
        if not self.message_input.get("1.0", "end-1c").strip():
            self._show_placeholder()

    def _clear_placeholder(self) -> None:
        self.placeholder_visible = False
        self.message_input.configure(fg=TEXT)
        self.message_input.delete("1.0", tk.END)

    def _input_text(self) -> str:
        if self.placeholder_visible:
            return ""
        return self.message_input.get("1.0", "end-1c").strip()

    def _focus_input(self) -> None:
        self.message_input.focus_set()
        self._hide_placeholder()

    def _handle_enter(self, event: tk.Event) -> str:
        self.send_message(event)
        return "break"

    def _handle_shift_enter(self, _event: tk.Event) -> None:
        self.message_input.insert(tk.INSERT, "\n")
        return None

    @staticmethod
    def _set_text(widget: tk.Text, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _section(self, parent: tk.Widget, row: int, title: str) -> ttk.Frame:
        frame = ttk.Frame(parent, style="Section.TFrame", padding=(12, 10, 12, 12))
        frame.grid(row=row, column=0, sticky="nsew", pady=(0, 10))
        frame.columnconfigure(0, weight=1)
        ttk.Label(frame, text=title, style="SectionTitle.TLabel").grid(row=0, column=0, sticky="w")
        return frame

    def _status_row(self, parent: ttk.Frame, row: int, key: str, label: str) -> None:
        value = tk.StringVar(value="-")
        self.health_labels[key] = value
        ttk.Label(parent, text=label, style="StatusName.TLabel").grid(row=row + 1, column=0, sticky="w", pady=(9 if row == 0 else 5, 0))
        value_label = ttk.Label(parent, textvariable=value, style="Info.TLabel")
        value_label.grid(row=row + 1, column=1, sticky="e", pady=(9 if row == 0 else 5, 0))
        parent.columnconfigure(1, weight=1)
        self.health_value_labels[key] = value_label

    def _kv_row(self, parent: ttk.Frame, row: int, label: str, value: tk.StringVar, value_style: str = "StatusName.TLabel") -> None:
        ttk.Label(parent, text=label, style="StatusName.TLabel").grid(row=row, column=0, sticky="w", pady=(9 if row == 1 else 5, 0))
        ttk.Label(parent, textvariable=value, style=value_style).grid(row=row, column=1, sticky="e", pady=(9 if row == 1 else 5, 0))
        parent.columnconfigure(1, weight=1)

    def _set_status(self, key: str, value: str, tone: str) -> None:
        self.health_labels[key].set(value)
        style = "Ok.TLabel" if tone == "ok" else "Warn.TLabel" if tone == "warn" else "Info.TLabel"
        self.health_value_labels[key].configure(style=style)

    def _small_text(self, parent: ttk.Frame, height: int) -> tk.Text:
        return tk.Text(
            parent,
            width=36,
            height=height,
            wrap="word",
            state="disabled",
            bg="#FFFFFF",
            fg=MUTED_DARK,
            selectbackground="#BFDBFE",
            selectforeground=TEXT,
            inactiveselectbackground="#DBEAFE",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=BORDER,
            padx=10,
            pady=8,
            font=(FONT, 9),
        )

    def _add_session_card(self, index: int, item: dict[str, Any]) -> None:
        selected = item["id"] == self.session_id
        bg = PRIMARY_TINT if selected else CARD_SOFT
        card = tk.Frame(self.sessions_frame, bg=bg, highlightthickness=1, highlightbackground=PRIMARY_SOFT if selected else BORDER, padx=10, pady=9)
        card.pack(fill="x", pady=(0, 8))
        card.columnconfigure(0, weight=1)
        title = str(item.get("title") or "未命名会话").replace("\n", " ").strip()[:28]
        updated = str(item.get("updated_at") or "")[:16].replace("T", " ")
        title_label = tk.Label(card, text=title or "未命名会话", bg=bg, fg=TEXT, font=(FONT, 10, "bold"), anchor="w")
        title_label.grid(row=0, column=0, sticky="ew")
        sub_label = tk.Label(card, text=updated or "刚刚", bg=bg, fg=MUTED, font=(FONT, 8), anchor="w")
        sub_label.grid(row=1, column=0, sticky="ew", pady=(3, 0))

        def open_card(_event: object | None = None, idx: int = index) -> None:
            self.open_selected_session(idx)

        def set_hover(active: bool) -> None:
            if item["id"] == self.session_id:
                return
            next_bg = "#EFF6FF" if active else CARD_SOFT
            card.configure(bg=next_bg, highlightbackground=BORDER_DARK if active else BORDER)
            title_label.configure(bg=next_bg)
            sub_label.configure(bg=next_bg)

        for widget in (card, title_label, sub_label):
            widget.bind("<Button-1>", open_card)
            widget.bind("<Enter>", lambda _event: set_hover(True))
            widget.bind("<Leave>", lambda _event: set_hover(False))
        self.session_cards.append(card)

    def _paint_session_selection(self) -> None:
        for idx, card in enumerate(self.session_cards):
            if idx >= len(self.sessions):
                continue
            selected = self.sessions[idx]["id"] == self.session_id
            bg = PRIMARY_TINT if selected else CARD_SOFT
            card.configure(bg=bg, highlightbackground=PRIMARY_SOFT if selected else BORDER)
            for child in card.winfo_children():
                child.configure(bg=bg)

    def _friendly_meta(self, response: ChatResponse) -> str:
        return f"{self._intent_label(response.intent)} · {response.latency_ms} ms"

    @staticmethod
    def _intent_label(intent: str) -> str:
        return {
            "tool": "工具调用",
            "rag": "知识库问答",
            "keyword": "快捷回答",
            "chat": "模型回答",
        }.get(intent, "模型回答")

    @staticmethod
    def _estimate_markdown_height(content: str, width_chars: int = 74) -> int:
        lines = content.splitlines() or [""]
        height = 0
        for line in lines:
            if line.strip().startswith("```"):
                height += 1
            else:
                height += max(1, (len(line) // width_chars) + 1)
        return min(max(height, 2), 18)

    def _weather_title(self, result: dict[str, Any]) -> str:
        location = str(result.get("resolved_location") or result.get("city") or "天气")
        mode = str(result.get("mode") or "")
        if mode == "daily_range":
            summary = str(result.get("summary") or "")
            days = "未来天气"
            for part in summary.split():
                if part.isdigit():
                    days = f"未来 {part} 天预报"
                    break
            return f"{location}{days}"
        if mode == "daily_one_day":
            return f"{location}天气预报"
        return f"{location}当前天气"

    def _weather_summary(self, result: dict[str, Any]) -> str:
        return str(result.get("summary") or "").strip()

    def _weather_daily_rows(self, result: dict[str, Any], fallback: str) -> list[tuple[str, str, str, str, str]]:
        summary = self._weather_summary(result) or fallback
        lines = [line.strip() for line in summary.splitlines() if line.strip()]
        rows: list[tuple[str, str, str, str, str]] = []
        for line in lines[1:] if len(lines) > 1 else []:
            parts = [part.strip(" ，,。") for part in line.replace("：", "，").split("，") if part.strip()]
            if not parts:
                continue
            date = parts[0]
            desc = parts[1] if len(parts) > 1 else "-"
            temp = next((part for part in parts if "℃" in part), "-")
            rain = next((part for part in parts if "降水" in part), "-")
            wind = next((part for part in parts if "风速" in part), "-")
            rows.append((date, desc, temp, rain, wind))
        return rows

    def _reset_inspector(self) -> None:
        self.response_labels["intent"].set("暂无响应")
        self.response_labels["model"].set("-")
        self.response_labels["latency"].set("-")
        self.response_labels["sources"].set("-")
        self._set_text(self.tool_view, "触发时间、天气等工具后会显示摘要。")
        self._set_text(self.source_view, "知识库问答会在这里列出引用片段。")


def main() -> None:
    app = ChatbotDesktopApp()
    app.mainloop()


if __name__ == "__main__":
    main()
