"""Main window layout construction mixin."""
import tkinter as tk
from tkinter import ttk

from config.settings import config_manager


class AppLayoutMixin:
    """Layout-building behaviors extracted from ApiClientApp."""

    def create_widgets(self):
        self._create_footer()
        self._create_toolbar()
        self._create_request_section()
        self._create_response_section()

    def _create_footer(self):
        footer_frame = ttk.Frame(self.root, padding=(10, 5))
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.theme_btn = ttk.Button(
            footer_frame,
            text="🌙 深色模式",
            command=self.toggle_theme,
            style="Accent.TButton",
        )
        self.theme_btn.pack(side=tk.RIGHT)

        ttk.Label(footer_frame, text="Ready", font=("Segoe UI", 8), foreground="gray").pack(side=tk.LEFT)

    def _create_toolbar(self):
        toolbar = ttk.Frame(self.root, padding="10")
        toolbar.pack(fill=tk.X, side=tk.TOP)

        ttk.Button(toolbar, text="🗑 清除全部", command=self.clear_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🕒 歷史記錄", command=self.show_history).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="⚙ 設定", command=self.show_settings).pack(side=tk.LEFT, padx=2)
        ttk.Label(toolbar, text="|", foreground="#cccccc").pack(side=tk.LEFT, padx=10)

        ttk.Label(toolbar, text="環境:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        self.env_combo = ttk.Combobox(toolbar, textvariable=self.current_environment, state="readonly", width=15)
        self.update_environment_list()
        self.env_combo.pack(side=tk.LEFT, padx=(0, 5))
        self.env_combo.bind("<<ComboboxSelected>>", self.on_environment_change)
        ttk.Button(toolbar, text="🌐 管理環境", command=self.show_environment_manager).pack(side=tk.LEFT, padx=2)

        ttk.Label(toolbar, text="|", foreground="#cccccc").pack(side=tk.LEFT, padx=10)
        ttk.Label(toolbar, text="API Client Enterprise", font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT)

    def _create_request_section(self):
        req_container = ttk.Frame(self.root, padding="10")
        req_container.pack(fill=tk.X, side=tk.TOP)

        req_frame = ttk.Frame(req_container)
        req_frame.pack(fill=tk.X, side=tk.TOP)

        ttk.Label(req_frame, text="Method:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        self.method_var = tk.StringVar(value="GET")
        methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
        self.method_combo = ttk.Combobox(req_frame, textvariable=self.method_var, values=methods, state="readonly", width=10)
        self.method_combo.pack(side=tk.LEFT, padx=(5, 15))

        ttk.Label(req_frame, text="URL:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        self.url_entry = ttk.Entry(req_frame, textvariable=self.url_var, font=("Segoe UI", 10))
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        ttk.Label(req_frame, text="逾時(s):", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(5, 2))
        self.timeout_var = tk.StringVar(value=str(config_manager.app_config.default_timeout))
        self.timeout_entry = ttk.Entry(req_frame, textvariable=self.timeout_var, width=4)
        self.timeout_entry.pack(side=tk.LEFT, padx=(0, 5))

        ttk.Label(req_frame, text="重試:", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(5, 2))
        self.retry_var = tk.StringVar(value=str(config_manager.app_config.retry_count))
        self.retry_entry = ttk.Entry(req_frame, textvariable=self.retry_var, width=3)
        self.retry_entry.pack(side=tk.LEFT, padx=(0, 5))

        self.send_btn = ttk.Button(req_frame, text="🚀 發送請求", style="Accent.TButton", command=self.on_send)
        self.send_btn.pack(side=tk.LEFT, padx=(10, 0))

        self.url_var.trace_add("write", self.update_environment_context)

        context_frame = ttk.Frame(req_container)
        context_frame.pack(fill=tk.X, side=tk.TOP, pady=(8, 0))

        ttk.Label(
            context_frame,
            textvariable=self.environment_summary_var,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor=tk.W)
        ttk.Label(
            context_frame,
            textvariable=self.environment_details_var,
            font=("Segoe UI", 8),
            foreground="gray",
        ).pack(anchor=tk.W, pady=(2, 0))

        self.paned_window = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        input_frame = ttk.LabelFrame(self.paned_window, text="📤 請求配置", padding=5)
        self.paned_window.add(input_frame, weight=1)

        self.notebook = ttk.Notebook(input_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.headers_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.headers_frame, text="📋 Headers")

        headers_toolbar = ttk.Frame(self.headers_frame)
        headers_toolbar.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(headers_toolbar, text="格式: Key: Value (每行一個)", font=("Segoe UI", 9, "italic")).pack(side=tk.LEFT)
        ttk.Button(headers_toolbar, text="清除", command=lambda: self.headers_text.delete(1.0, tk.END)).pack(side=tk.RIGHT)

        headers_scroll = ttk.Scrollbar(self.headers_frame)
        headers_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.headers_text = tk.Text(
            self.headers_frame,
            height=6,
            font=("Consolas", 10),
            yscrollcommand=headers_scroll.set,
            wrap=tk.NONE,
        )
        headers_scroll.config(command=self.headers_text.yview)
        self.headers_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.headers_text.insert(1.0, "Content-Type: application/json\nUser-Agent: PyClient/1.0")

        self.body_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.body_frame, text="📝 Body")

        body_toolbar = ttk.Frame(self.body_frame)
        body_toolbar.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(body_toolbar, text="原始內容 (JSON/Text):", font=("Segoe UI", 9, "italic")).pack(side=tk.LEFT)
        ttk.Button(body_toolbar, text="格式化 JSON", command=self.format_body_json).pack(side=tk.RIGHT, padx=2)
        ttk.Button(body_toolbar, text="清除", command=lambda: self.body_text.delete(1.0, tk.END)).pack(side=tk.RIGHT)

        body_scroll = ttk.Scrollbar(self.body_frame)
        body_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.body_text = tk.Text(
            self.body_frame,
            height=6,
            font=("Consolas", 10),
            yscrollcommand=body_scroll.set,
            wrap=tk.NONE,
        )
        body_scroll.config(command=self.body_text.yview)
        self.body_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def _create_response_section(self):
        response_container = ttk.LabelFrame(self.paned_window, text="📥 響應結果", padding=5)
        self.paned_window.add(response_container, weight=2)

        self.status_bar_frame = ttk.Frame(response_container)
        self.status_bar_frame.pack(fill=tk.X, padx=5, pady=5)

        self.status_label = ttk.Label(self.status_bar_frame, text="● 就緒", font=("Segoe UI", 9, "bold"), foreground="gray")
        self.status_label.pack(side=tk.LEFT)

        self.time_label = ttk.Label(self.status_bar_frame, text="", font=("Segoe UI", 9))
        self.time_label.pack(side=tk.LEFT, padx=10)

        self.size_label = ttk.Label(self.status_bar_frame, text="", font=("Segoe UI", 9))
        self.size_label.pack(side=tk.LEFT, padx=10)

        response_btn_frame = ttk.Frame(self.status_bar_frame)
        response_btn_frame.pack(side=tk.RIGHT)
        ttk.Button(response_btn_frame, text="複製響應", command=self.copy_response).pack(side=tk.LEFT, padx=2)
        ttk.Button(response_btn_frame, text="查看Headers", command=self.view_response_headers).pack(side=tk.LEFT, padx=2)
        ttk.Button(response_btn_frame, text="清除", command=self.clear_response).pack(side=tk.LEFT, padx=2)

        response_notebook = ttk.Notebook(response_container)
        response_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        body_response_frame = ttk.Frame(response_notebook)
        response_notebook.add(body_response_frame, text="📄 Body")

        self.response_text = tk.Text(body_response_frame, wrap=tk.NONE, font=("Consolas", 10), state=tk.DISABLED, bg="#ffffff")
        v_scroll = ttk.Scrollbar(body_response_frame, orient="vertical", command=self.response_text.yview)
        h_scroll = ttk.Scrollbar(body_response_frame, orient="horizontal", command=self.response_text.xview)
        self.response_text.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.response_text.pack(fill=tk.BOTH, expand=True)

        headers_response_frame = ttk.Frame(response_notebook)
        response_notebook.add(headers_response_frame, text="📋 Response Headers")

        self.response_headers_text = tk.Text(
            headers_response_frame,
            wrap=tk.NONE,
            font=("Consolas", 9),
            state=tk.DISABLED,
            bg="#ffffff",
        )
        headers_v_scroll = ttk.Scrollbar(headers_response_frame, orient="vertical", command=self.response_headers_text.yview)
        self.response_headers_text.configure(yscrollcommand=headers_v_scroll.set)
        headers_v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.response_headers_text.pack(fill=tk.BOTH, expand=True)
