import asyncio
import json
import logging
import queue
import shutil
import threading
import tkinter as tk
import time
from pathlib import Path
from tkinter import filedialog, font as tkfont, messagebox, ttk
from typing import Any

import customtkinter as ctk

from app.config import get_settings
from app.db.database import delete_session, init_db, list_messages, list_sessions
from app.example_questions import pick_home_examples
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
FONT_APP_TITLE = (FONT, 23, "bold")
FONT_TITLE = (FONT, 16, "bold")
FONT_SECTION = (FONT, 15, "bold")
FONT_BODY = (FONT, 14)
FONT_CHAT = (FONT, 15)
FONT_CHAT_TITLE = (FONT, 15, "bold")
FONT_INPUT = (FONT, 15)
FONT_BUTTON = (FONT, 14)
FONT_SESSION = (FONT, 14, "bold")
FONT_META = (FONT, 12)
FONT_STATUS = (FONT, 13)
FONT_STATUS_BOLD = (FONT, 13, "bold")


class ChatbotDesktopApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("个人知识问答助手")
        self.geometry("1280x800")
        self.minsize(1100, 700)
        self.configure(fg_color=BG)

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
        self.session_cards: list[ctk.CTkFrame] = []
        self.loading_row: tk.Widget | None = None
        self.loading_label: ctk.CTkLabel | None = None
        self.loading_after_id: str | None = None
        self.loading_started_at = 0.0
        self.loading_tick = 0
        self.loading_base_text = "正在处理"
        self.is_sending = False
        self.home_examples = pick_home_examples()
        self.ui_queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._configure_logging()

        self._initialize_runtime()
        self._configure_styles()
        self._build_ui()
        self.refresh_status()
        self.refresh_sessions()
        self._show_welcome()
        self._drain_ui_queue()

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
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("green")
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        ctk.set_widget_scaling(1.05)

        base_font = FONT_BODY
        style.configure(".", font=base_font, background=BG, foreground=TEXT)
        style.configure("App.TFrame", background=BG)
        style.configure("Surface.TFrame", background=CARD)
        style.configure("Chat.TFrame", background=CHAT_BG)
        style.configure("Header.TFrame", background=BG)
        style.configure("Divider.TFrame", background=BORDER)
        style.configure("Title.TLabel", background=BG, foreground=TEXT, font=FONT_APP_TITLE)
        style.configure("Subtitle.TLabel", background=BG, foreground=MUTED, font=FONT_STATUS)
        style.configure("PanelTitle.TLabel", background=CARD, foreground=TEXT, font=FONT_SECTION)
        style.configure("SmallTitle.TLabel", background=CARD, foreground=TEXT, font=FONT_STATUS_BOLD)
        style.configure("Muted.TLabel", background=CARD, foreground=MUTED, font=FONT_META)
        style.configure("Body.TLabel", background=CARD, foreground=TEXT, font=FONT_BODY)
        style.configure("Pill.TLabel", background=PRIMARY_TINT, foreground=PRIMARY_DARK, padding=(10, 4), font=FONT_STATUS_BOLD)
        style.configure("Section.TFrame", background=CARD_SOFT)
        style.configure("SectionTitle.TLabel", background=CARD_SOFT, foreground=TEXT, font=FONT_SECTION)
        style.configure("SectionBody.TLabel", background=CARD_SOFT, foreground=MUTED_DARK, font=FONT_STATUS)
        style.configure("StatusName.TLabel", background=CARD_SOFT, foreground=MUTED, font=FONT_STATUS)
        style.configure("Ok.TLabel", background=CARD_SOFT, foreground=SUCCESS, font=FONT_STATUS_BOLD)
        style.configure("Warn.TLabel", background=CARD_SOFT, foreground=WARNING, font=FONT_STATUS_BOLD)
        style.configure("Info.TLabel", background=CARD_SOFT, foreground=PRIMARY_DARK, font=FONT_STATUS_BOLD)
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

        header = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_configure(padx=22, pady=(14, 8))
        header.columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="个人知识问答助手", text_color=TEXT, font=FONT_APP_TITLE).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="本地桌面客户端 · 聊天 · 工具调用 · 知识库问答",
            text_color=MUTED,
            font=FONT_STATUS,
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))
        ctk.CTkLabel(
            header,
            textvariable=self.status,
            fg_color=PRIMARY_TINT,
            text_color=PRIMARY_DARK,
            corner_radius=14,
            padx=10,
            pady=4,
            font=FONT_STATUS_BOLD,
        ).grid(row=0, column=1, rowspan=2, sticky="e")

        body = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_configure(padx=22, pady=(8, 22))
        body.columnconfigure(0, minsize=270)
        body.columnconfigure(1, weight=1)
        body.columnconfigure(2, minsize=320)
        body.rowconfigure(0, weight=1)

        self._build_left_panel(body)
        self._build_chat_panel(body)
        self._build_right_panel(body)

    def _build_left_panel(self, parent: ctk.CTkFrame) -> None:
        left = ctk.CTkFrame(parent, fg_color=CARD, border_width=1, border_color=BORDER, corner_radius=8)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        left.grid_propagate(False)
        left.configure(width=270)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(8, weight=1)

        content = ctk.CTkFrame(left, fg_color=CARD, corner_radius=8)
        content.grid(row=0, column=0, rowspan=9, sticky="nsew")
        content.grid_configure(padx=16, pady=16)
        content.columnconfigure(0, weight=1)
        content.rowconfigure(8, weight=1)

        ctk.CTkLabel(content, text="个人知识问答助手", text_color=TEXT, font=FONT_TITLE).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            content,
            text="本地桌面客户端 · 聊天 · 工具调用 · 知识库问答",
            text_color=MUTED,
            font=FONT_STATUS,
            wraplength=230,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(4, 14))

        ctk.CTkLabel(content, text="用户 ID", text_color=MUTED, font=FONT_STATUS).grid(row=2, column=0, sticky="w")
        ctk.CTkEntry(content, textvariable=self.user_id, fg_color="#FFFFFF", border_color=BORDER_DARK, font=FONT_INPUT).grid(row=3, column=0, sticky="ew", pady=(4, 12))
        ctk.CTkButton(content, text="新建会话", fg_color=PRIMARY, hover_color=PRIMARY_DARK, font=FONT_BUTTON, command=self.new_chat).grid(row=4, column=0, sticky="ew")

        actions = ctk.CTkFrame(content, fg_color=CARD, corner_radius=0)
        actions.grid(row=5, column=0, sticky="ew", pady=(8, 0))
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        ctk.CTkButton(actions, text="刷新", fg_color=CARD_SOFT, text_color=TEXT, hover_color=PRIMARY_TINT, font=FONT_BUTTON, command=self.refresh_sessions).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(actions, text="删除", fg_color=DANGER_SOFT, text_color=DANGER, hover_color="#FEE2E2", font=FONT_BUTTON, command=self.delete_selected_session).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        ctk.CTkLabel(content, text="会话", text_color=TEXT, font=FONT_SECTION).grid(row=6, column=0, sticky="w", pady=(18, 0))
        ctk.CTkLabel(content, textvariable=self.session_count, text_color=MUTED, font=FONT_META).grid(row=7, column=0, sticky="w", pady=(2, 8))

        self.sessions_frame = ctk.CTkScrollableFrame(content, fg_color=CARD, corner_radius=0)
        self.sessions_frame.grid(row=8, column=0, sticky="nsew")

    def _build_chat_panel(self, parent: ctk.CTkFrame) -> None:
        center = ctk.CTkFrame(parent, fg_color=CARD, border_width=1, border_color=BORDER, corner_radius=8)
        center.grid(row=0, column=1, sticky="nsew")
        center.columnconfigure(0, weight=1)
        center.rowconfigure(1, weight=1)

        toolbar = ctk.CTkFrame(center, fg_color=CARD, corner_radius=8)
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.grid_configure(padx=16, pady=12)
        toolbar.columnconfigure(0, weight=1)
        ctk.CTkLabel(toolbar, text="当前对话", text_color=TEXT, font=FONT_SECTION).grid(row=0, column=0, sticky="w")
        samples = (
            ("你好", "你好"),
            ("当前时间", "现在几点？"),
            ("天气建议", "今天天气适合跑步吗？"),
            ("知识库问答", "根据知识库介绍项目"),
        )
        for idx, (label, prompt) in enumerate(samples):
            ctk.CTkButton(
                toolbar,
                text=label,
                fg_color="#FFFFFF",
                text_color=MUTED_DARK,
                hover_color=PRIMARY_TINT,
                border_width=1,
                border_color=BORDER,
                font=FONT_BUTTON,
                width=82,
                command=lambda text=prompt: self.use_sample(text),
            ).grid(
                row=0, column=idx + 1, padx=(8, 0)
            )

        self.messages_frame = ctk.CTkScrollableFrame(center, fg_color=CHAT_BG, corner_radius=0)
        self.messages_frame.grid(row=1, column=0, sticky="nsew")
        self.messages_frame.columnconfigure(0, weight=1)

        input_bar = ctk.CTkFrame(center, fg_color=CARD, corner_radius=8)
        input_bar.grid(row=2, column=0, sticky="ew")
        input_bar.grid_configure(padx=16, pady=14)
        input_bar.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            input_bar,
            textvariable=self.input_status,
            text_color=MUTED_DARK,
            font=FONT_STATUS,
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        input_shell = ctk.CTkFrame(input_bar, fg_color="#FFFFFF", border_width=1, border_color=BORDER_DARK, corner_radius=8)
        input_shell.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        input_shell.columnconfigure(0, weight=1)
        self.message_input = ctk.CTkTextbox(
            input_shell,
            height=70,
            wrap="word",
            fg_color="#FFFFFF",
            text_color=TEXT,
            border_width=0,
            padx=12,
            pady=9,
            font=FONT_INPUT,
        )
        self.message_input.grid(row=0, column=0, sticky="ew")
        self.placeholder = "输入消息，例如：今天天气适合跑步吗？ / 根据知识库介绍项目"
        self.placeholder_visible = False
        self._show_placeholder()
        self.message_input.bind("<FocusIn>", self._hide_placeholder)
        self.message_input.bind("<FocusOut>", self._maybe_show_placeholder)
        self.message_input.bind("<Return>", self._handle_enter)
        self.message_input.bind("<Shift-Return>", self._handle_shift_enter)
        self.send_button = ctk.CTkButton(input_bar, text="发送", fg_color=PRIMARY, hover_color=PRIMARY_DARK, font=FONT_BUTTON, command=self.send_message)
        self.send_button.grid(row=1, column=1, sticky="ns")

    def _build_right_panel(self, parent: ctk.CTkFrame) -> None:
        right = ctk.CTkFrame(parent, fg_color=CARD, border_width=1, border_color=BORDER, corner_radius=8)
        right.grid(row=0, column=2, sticky="ns", padx=(12, 0))
        right.grid_propagate(False)
        right.configure(width=320)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(3, weight=1)
        right.rowconfigure(4, weight=1)

        content = ctk.CTkFrame(right, fg_color=CARD, corner_radius=8)
        content.grid(row=0, column=0, sticky="nsew")
        content.grid_configure(padx=14, pady=14)
        content.columnconfigure(0, weight=1)
        content.rowconfigure(3, weight=1)
        content.rowconfigure(4, weight=1)

        status = self._section(content, 0, "系统状态")
        self.health_labels: dict[str, tk.StringVar] = {}
        self.health_value_labels: dict[str, ctk.CTkLabel] = {}
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
        ctk.CTkButton(
            knowledge,
            text="导入默认知识库",
            fg_color=CARD_SOFT,
            text_color=TEXT,
            hover_color=PRIMARY_TINT,
            font=FONT_BUTTON,
            command=self.import_default_knowledge,
        ).grid(
            row=1, column=0, sticky="ew", pady=(8, 6)
        )
        ctk.CTkButton(
            knowledge,
            text="上传 .txt / .md",
            fg_color=CARD_SOFT,
            text_color=TEXT,
            hover_color=PRIMARY_TINT,
            font=FONT_BUTTON,
            command=self.upload_knowledge_file,
        ).grid(row=2, column=0, sticky="ew")
        self.knowledge_note = tk.StringVar(value="默认知识库会在首次启动时准备。")
        ctk.CTkLabel(knowledge, textvariable=self.knowledge_note, text_color=MUTED_DARK, font=FONT_STATUS, wraplength=270, justify="left").grid(
            row=3, column=0, sticky="w", pady=(8, 0)
        )

        config = self._section(content, 5, "配置区域")
        self.config_toggle = ctk.CTkButton(
            config,
            text="显示 API Key 配置",
            fg_color=CARD_SOFT,
            text_color=TEXT,
            hover_color=PRIMARY_TINT,
            font=FONT_BUTTON,
            command=self.toggle_config_panel,
        )
        self.config_toggle.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.config_body = ctk.CTkFrame(config, fg_color=CARD_SOFT, corner_radius=8)
        self.config_body.columnconfigure(0, weight=1)
        ctk.CTkLabel(self.config_body, text="LLM API Key", text_color=MUTED, font=FONT_STATUS).grid(row=0, column=0, sticky="w", pady=(10, 3), padx=10)
        self.llm_key_entry = ctk.CTkEntry(self.config_body, textvariable=self.llm_api_key, show="*", fg_color="#FFFFFF", border_color=BORDER_DARK, font=FONT_INPUT)
        self.llm_key_entry.grid(row=1, column=0, sticky="ew")
        self.llm_key_entry.grid_configure(padx=10)
        ctk.CTkCheckBox(
            self.config_body,
            text="显示密钥",
            variable=self.show_api_keys,
            fg_color=PRIMARY,
            hover_color=PRIMARY_DARK,
            text_color=MUTED_DARK,
            font=FONT_BUTTON,
            command=self.toggle_api_key_visibility,
        ).grid(row=2, column=0, sticky="w", pady=(8, 0), padx=10)
        ctk.CTkButton(self.config_body, text="保存配置", fg_color=PRIMARY, hover_color=PRIMARY_DARK, font=FONT_BUTTON, command=self.save_api_config).grid(row=3, column=0, sticky="ew", pady=(10, 6), padx=10)
        ctk.CTkButton(self.config_body, text="重新加载配置", fg_color=CARD_SOFT, text_color=TEXT, hover_color=PRIMARY_TINT, font=FONT_BUTTON, command=self.reload_api_config).grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 10))

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
            logging.info("send_blocked_busy session_id=%s", self.session_id)
            return
        message = self._input_text()
        if not message:
            return
        self.is_sending = True
        try:
            logging.info("send_start session_id=%s", self.session_id)
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
            self._set_busy(True)
            self.update_idletasks()
            request = ChatRequest(user_id=request_user_id, message=message, session_id=self.session_id)
            threading.Thread(target=self._send_message_worker, args=(request,), daemon=True).start()
        except Exception as exc:
            logging.exception("desktop send callback failed")
            self._show_error(exc)
            self._finish_send("send_exception")

    def _send_message_worker(self, request: ChatRequest) -> None:
        try:
            response = asyncio.run(asyncio.wait_for(handle_chat(request), timeout=DESKTOP_REQUEST_TIMEOUT_SECONDS))
        except TimeoutError:
            logging.exception("desktop request timed out after %s seconds", DESKTOP_REQUEST_TIMEOUT_SECONDS)
            self._enqueue_ui("timeout", None)
            return
        except Exception as exc:
            logging.exception("desktop request failed")
            self._enqueue_ui("error", exc)
            return
        logging.info(
            "worker_response session_id=%s intent=%s model=%s latency_ms=%s",
            response.session_id,
            response.intent,
            response.model,
            response.latency_ms,
        )
        self._enqueue_ui("response", response)

    def _enqueue_ui(self, event: str, payload: Any) -> None:
        self.ui_queue.put((event, payload))

    def _drain_ui_queue(self) -> None:
        while True:
            try:
                event, payload = self.ui_queue.get_nowait()
            except queue.Empty:
                break
            request_event = event in {"response", "timeout", "error"}
            handled = False
            try:
                if event == "response":
                    self._show_response(payload)
                    handled = True
                    logging.info("ui_response_handled session_id=%s", payload.session_id)
                elif event == "timeout":
                    self._show_timeout_error()
                    handled = True
                elif event == "error":
                    self._show_error(payload)
                    handled = True
                elif event == "import_result":
                    self._show_import_result(payload)
                else:
                    logging.error("unknown desktop ui event: %s", event)
            except Exception as exc:
                logging.exception("desktop ui event failed event=%s", event)
                try:
                    self._show_error(exc)
                except Exception:
                    logging.exception("desktop error rendering failed")
                    self.status.set("发生错误")
            finally:
                if request_event:
                    self._finish_send(event if handled else f"{event}_failed")
        self.after(50, self._drain_ui_queue)

    def _show_response(self, response: ChatResponse) -> None:
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
            logging.exception("desktop knowledge import failed")
            self._enqueue_ui("error", exc)
            return
        self._enqueue_ui("import_result", result)

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
        self.input_status.set("请求失败，详情已写入 data/desktop.log")
        self._append_message("助手", f"请求失败：{exc}\n\n详情已写入 data/desktop.log。", "assistant")

    def _show_timeout_error(self) -> None:
        self.status.set("请求超时")
        self.input_status.set(f"请求超过 {DESKTOP_REQUEST_TIMEOUT_SECONDS} 秒未返回，已停止等待")
        self._append_message(
            "助手",
            (
                f"本次请求超过 {DESKTOP_REQUEST_TIMEOUT_SECONDS} 秒没有返回，客户端已停止等待。\n\n"
                "这通常是模型 API 网络超时、服务端无响应或密钥/代理配置异常导致的。"
                "你可以稍后重试，或先用“当前时间”“天气建议”确认工具链是否正常。"
            ),
            "assistant",
        )

    def _finish_send(self, reason: str) -> None:
        self._remove_loading()
        self._set_busy(False)
        self.input_status.set("")
        self.status.set("在线")
        logging.info("send_finished reason=%s session_id=%s", reason, self.session_id)
        try:
            self._focus_input()
        except tk.TclError:
            logging.exception("desktop input focus restore failed")

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
        outer = ctk.CTkFrame(self.messages_frame, fg_color=CHAT_BG, corner_radius=0)
        outer.pack(fill="both", expand=True, padx=28, pady=70)
        card = ctk.CTkFrame(outer, fg_color=CARD, border_width=1, border_color=BORDER, corner_radius=8)
        card.pack(anchor="center")
        card.pack_configure(padx=28, pady=24)
        ctk.CTkLabel(card, text="你好，我是你的本地知识问答助手", text_color=TEXT, font=FONT_APP_TITLE).pack()
        ctk.CTkLabel(
            card,
            text="可以直接提问，也可以从下面的示例开始。",
            text_color=MUTED,
            font=FONT_BODY,
        ).pack(pady=(8, 18))
        examples = ctk.CTkFrame(card, fg_color=CARD, corner_radius=0)
        examples.pack()
        for column in range(2):
            examples.columnconfigure(column, weight=1)
        for idx, sample in enumerate(self.home_examples):
            text = sample["text"]
            ctk.CTkButton(
                examples,
                text=text,
                width=180,
                fg_color="#FFFFFF",
                text_color=MUTED_DARK,
                hover_color=PRIMARY_TINT,
                border_width=1,
                border_color=BORDER,
                font=FONT_BUTTON,
                command=lambda value=text: self.use_sample(value),
            ).grid(
                row=idx // 2,
                column=idx % 2,
                padx=5,
                pady=5,
                sticky="ew",
            )
        ctk.CTkButton(
            card,
            text="换一批",
            fg_color=CARD_SOFT,
            text_color=TEXT,
            hover_color=PRIMARY_TINT,
            font=FONT_BUTTON,
            command=self.refresh_home_examples,
        ).pack(pady=(14, 0))
        self.chat_has_content = False

    def refresh_home_examples(self) -> None:
        self.home_examples = pick_home_examples()
        if not self.chat_has_content:
            self._show_welcome()

    def _append_message(
        self,
        label: str,
        content: str,
        tag: str,
        meta: str | None = None,
        response: ChatResponse | None = None,
    ) -> None:
        is_user = tag == "user"
        row = ctk.CTkFrame(self.messages_frame, fg_color=CHAT_BG, corner_radius=0)
        row.pack(fill="x", anchor="e" if is_user else "w")
        row.pack_configure(padx=24, pady=10)

        content_frame = ctk.CTkFrame(row, fg_color=CHAT_BG, corner_radius=0)
        content_frame.pack(side="right" if is_user else "left", anchor="e" if is_user else "w")

        ctk.CTkLabel(
            content_frame,
            text=label,
            text_color=PRIMARY_DARK if is_user else MUTED_DARK,
            font=FONT_STATUS_BOLD,
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
            ctk.CTkLabel(content_frame, text=meta, text_color=MUTED, font=FONT_META).pack(anchor="w", pady=(6, 0))
        self.messages_frame.update_idletasks()
        self._scroll_chat_to_bottom()
        self.chat_has_content = True

    def _append_loading_message(self, text: str) -> tk.Widget:
        row = ctk.CTkFrame(self.messages_frame, fg_color=CHAT_BG, corner_radius=0)
        row.pack(fill="x", anchor="w")
        row.pack_configure(padx=24, pady=10)
        bubble = ctk.CTkLabel(
            row,
            text=text,
            fg_color="#FFFFFF",
            text_color=MUTED_DARK,
            corner_radius=8,
            width=140,
            height=42,
            font=FONT_CHAT,
        )
        bubble.pack(side="left", anchor="w")
        self.loading_label = bubble
        self.messages_frame.update_idletasks()
        self._scroll_chat_to_bottom()
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
        self.message_input.configure(state="disabled" if busy else "normal")

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

    def _user_bubble(self, parent: tk.Widget, content: str) -> ctk.CTkLabel:
        width = max(280, int(self.messages_frame.winfo_width() * 0.58))
        return ctk.CTkLabel(
            parent,
            text=content,
            fg_color=USER_BG,
            text_color="#FFFFFF",
            corner_radius=8,
            width=width,
            height=46,
            wraplength=width,
            justify="left",
            font=FONT_CHAT,
        )

    def _weather_bubble(self, parent: tk.Widget, result: dict[str, Any], fallback: str) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent, fg_color=ASSISTANT_BG, border_width=1, border_color=BORDER, corner_radius=8)
        width = max(430, int(self.messages_frame.winfo_width() * 0.68))
        title = self._weather_title(result)
        ctk.CTkLabel(frame, text=title, text_color=TEXT, font=FONT_CHAT_TITLE, wraplength=width, justify="left").grid(
            row=0, column=0, columnspan=5, sticky="w"
        )
        daily_lines = self._weather_daily_rows(result, fallback)
        if daily_lines:
            headers = ("日期", "天气", "温度", "降水", "风速")
            for col, header in enumerate(headers):
                ctk.CTkLabel(frame, text=header, text_color=MUTED, font=FONT_STATUS_BOLD).grid(
                    row=1, column=col, sticky="w", padx=(0, 16), pady=(12, 4)
                )
            for row_idx, values in enumerate(daily_lines, start=2):
                for col, value in enumerate(values):
                    ctk.CTkLabel(frame, text=value, text_color=TEXT, font=FONT_CHAT).grid(
                        row=row_idx, column=col, sticky="w", padx=(0, 16), pady=3
                    )
        else:
            ctk.CTkLabel(
                frame,
                text=self._weather_summary(result) or fallback,
                text_color=TEXT,
                font=FONT_CHAT,
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
            font=FONT_CHAT,
        )
        base_font = tkfont.Font(font=text.cget("font"))
        bold_font = base_font.copy()
        bold_font.configure(weight="bold")
        heading_font = base_font.copy()
        heading_font.configure(weight="bold", size=16)
        code_font = tkfont.Font(family="Consolas", size=13)
        text.tag_configure("bold", font=bold_font)
        text.tag_configure("heading", font=heading_font, spacing1=4, spacing3=4)
        text.tag_configure("code_block", font=code_font, background="#F1F5F9", foreground="#1F2937", lmargin1=8, lmargin2=8)
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

    def _scroll_chat_to_bottom(self) -> None:
        canvas = getattr(self.messages_frame, "_parent_canvas", None)
        if canvas is not None:
            self.after_idle(lambda: canvas.yview_moveto(1.0))

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
        self.message_input.configure(text_color=MUTED)
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
        self.message_input.configure(text_color=TEXT)
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

    def _section(self, parent: tk.Widget, row: int, title: str) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent, fg_color=CARD_SOFT, corner_radius=8)
        frame.grid(row=row, column=0, sticky="nsew", pady=(0, 10))
        frame.grid_configure(padx=0)
        frame.columnconfigure(0, weight=1)
        ctk.CTkLabel(frame, text=title, text_color=TEXT, font=FONT_SECTION).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 0))
        return frame

    def _status_row(self, parent: ctk.CTkFrame, row: int, key: str, label: str) -> None:
        value = tk.StringVar(value="-")
        self.health_labels[key] = value
        ctk.CTkLabel(parent, text=label, text_color=MUTED, font=FONT_STATUS).grid(row=row + 1, column=0, sticky="w", padx=12, pady=(9 if row == 0 else 5, 0))
        value_label = ctk.CTkLabel(parent, textvariable=value, text_color=PRIMARY_DARK, font=FONT_STATUS_BOLD)
        value_label.grid(row=row + 1, column=1, sticky="e", padx=12, pady=(9 if row == 0 else 5, 0))
        parent.columnconfigure(1, weight=1)
        self.health_value_labels[key] = value_label

    def _kv_row(self, parent: ctk.CTkFrame, row: int, label: str, value: tk.StringVar, value_style: str = "StatusName.TLabel") -> None:
        value_color = PRIMARY_DARK if value_style == "Info.TLabel" else MUTED
        value_weight = "bold" if value_style == "Info.TLabel" else "normal"
        ctk.CTkLabel(parent, text=label, text_color=MUTED, font=FONT_STATUS).grid(row=row, column=0, sticky="w", padx=12, pady=(9 if row == 1 else 5, 0))
        ctk.CTkLabel(parent, textvariable=value, text_color=value_color, font=(FONT, 13, value_weight)).grid(row=row, column=1, sticky="e", padx=12, pady=(9 if row == 1 else 5, 0))
        parent.columnconfigure(1, weight=1)

    def _set_status(self, key: str, value: str, tone: str) -> None:
        self.health_labels[key].set(value)
        color = SUCCESS if tone == "ok" else WARNING if tone == "warn" else PRIMARY_DARK
        self.health_value_labels[key].configure(text_color=color)

    def _small_text(self, parent: ctk.CTkFrame, height: int) -> tk.Text:
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
            font=FONT_STATUS,
        )

    def _add_session_card(self, index: int, item: dict[str, Any]) -> None:
        selected = item["id"] == self.session_id
        bg = PRIMARY_TINT if selected else CARD_SOFT
        card = ctk.CTkFrame(self.sessions_frame, fg_color=bg, border_width=1, border_color=PRIMARY_SOFT if selected else BORDER, corner_radius=8)
        card.pack(fill="x", pady=(0, 8))
        card.columnconfigure(0, weight=1)
        title = str(item.get("title") or "未命名会话").replace("\n", " ").strip()[:28]
        updated = str(item.get("updated_at") or "")[:16].replace("T", " ")
        title_label = ctk.CTkLabel(card, text=title or "未命名会话", text_color=TEXT, font=FONT_SESSION, anchor="w")
        title_label.grid(row=0, column=0, sticky="ew", padx=10, pady=(9, 0))
        sub_label = ctk.CTkLabel(card, text=updated or "刚刚", text_color=MUTED, font=FONT_META, anchor="w")
        sub_label.grid(row=1, column=0, sticky="ew", padx=10, pady=(3, 9))

        def open_card(_event: object | None = None, idx: int = index) -> None:
            self.open_selected_session(idx)

        def set_hover(active: bool) -> None:
            if item["id"] == self.session_id:
                return
            next_bg = "#EFF6FF" if active else CARD_SOFT
            card.configure(fg_color=next_bg, border_color=BORDER_DARK if active else BORDER)

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
            card.configure(fg_color=bg, border_color=PRIMARY_SOFT if selected else BORDER)

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
        return max(height, 2)

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
