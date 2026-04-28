"""
API Client - Enterprise Edition
專業級 API 測試工具

版本: 2.0.0
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import json
import re
import os
import sys

# 初始化核心模組
try:
    from config.settings import config_manager, Environment
    from core.logger import setup_logging, get_logger
    from core.exceptions import ApiClientError
    ENTERPRISE_MODE = True
except ImportError:
    ENTERPRISE_MODE = False
    config_manager = None
    ApiClientError = RuntimeError

from logic import ApiClientOrchestrator
from utils import format_json, format_size, format_headers_display, validate_url, validate_json

# 設定日誌
if ENTERPRISE_MODE:
    setup_logging(
        log_level=config_manager.app_config.log_level,
        log_file=config_manager.app_config.log_file
    )
    logger = get_logger(__name__)
else:
    logger = None

class ApiClientApp:
    """企業級 API 測試客戶端應用程式"""
    
    HISTORY_FILE = "api_client_history.json"
    VERSION = "2.0.0"
    FALLBACK_HISTORY_ITEMS = 20
    MAX_SYNTAX_HIGHLIGHT_CHARS = 120_000
    JSON_STRING_PATTERN = re.compile(r'"(?:[^"\\]|\\.)*"')
    JSON_BOOL_PATTERN = re.compile(r'\b(true|false|null)\b')

    def __init__(self, root):
        self.root = root
        self._syntax_theme_key = None
        
        # 使用配置或預設值
        if ENTERPRISE_MODE:
            config = config_manager.app_config
            self.root.title(f"{config.app_name} v{self.VERSION}")
            self.root.geometry(f"{config.window_width}x{config.window_height}")
        else:
            self.root.title(f"API Client - Enterprise Edition v{self.VERSION}")
            self.root.geometry("1200x900")
        
        # 設置主題和樣式 (初始化)
        self.setup_styles()
        
        # 歷史記錄
        self.request_history = self.load_history()
        self.current_response_headers = {}
        
        # 初始化業務邏輯協調器
        self.orchestrator = ApiClientOrchestrator()
        
        # 環境變數
        self.current_environment = tk.StringVar(value="無")

        self.create_widgets()
        
        # 確保所有組件創建後應用主題
        self.apply_theme()
        
        # 記錄啟動
        if ENTERPRISE_MODE and logger:
            logger.info("API Client 啟動", extra={'user_action': 'app_start'})
    
    def setup_styles(self):
        """設置現代化主題與配色"""
        if ENTERPRISE_MODE:
            self.is_dark_mode = config_manager.app_config.theme == "dark"
        else:
            self.is_dark_mode = False
            
        self.colors = {
            "light": {
                "bg": "#f3f3f3",
                "fg": "#333333",
                "panel": "#ffffff",
                "input_bg": "#ffffff",
                "input_fg": "#333333",
                "accent": "#0078d4",
                "border": "#e1e1e1",
                "success": "#107c10",
                "error": "#d13438",
                "select": "#e1dfdd",
                "json_key": "#0451a5",
                "json_string": "#a31515",
                "json_number": "#098658",
                "json_bool": "#0000ff"
            },
            "dark": {
                "bg": "#202020",
                "fg": "#cccccc",
                "panel": "#2d2d2d",
                "input_bg": "#1e1e1e",
                "input_fg": "#d4d4d4",
                "accent": "#4cc9f0",
                "border": "#3e3e42",
                "success": "#4ec9b0",
                "error": "#f14c4c",
                "select": "#3f3f46",
                "json_key": "#9cdcfe",
                "json_string": "#ce9178",
                "json_number": "#b5cea8",
                "json_bool": "#569cd6"
            }
        }
        self.apply_theme()

    def toggle_theme(self):
        """切換深色/淺色模式"""
        self.is_dark_mode = not self.is_dark_mode
        
        if ENTERPRISE_MODE:
            config_manager.app_config.theme = "dark" if self.is_dark_mode else "light"
            config_manager.save_config()
            
        self.apply_theme()

    def apply_theme(self):
        """應用當前主題"""
        theme_key = "dark" if self.is_dark_mode else "light"
        c = self.colors[theme_key]
        
        style = ttk.Style()
        style.theme_use('clam')
        
        # 基礎樣式配置
        style.configure('.', background=c['bg'], foreground=c['fg'], font=('Segoe UI', 9))
        
        # 確保輸入框文字在深色模式下維持黑色 (Method, URL, Timeout, Retry)
        style.configure('TEntry', foreground='black', fieldbackground='white')
        style.configure('TCombobox', foreground='black', fieldbackground='white')
        style.map('TCombobox', 
            fieldbackground=[('readonly', 'white')],
            foreground=[('readonly', 'black')]
        )
        
        style.configure('TFrame', background=c['bg'])
        style.configure('TLabel', background=c['bg'], foreground=c['fg'])
        style.configure('TButton', padding=(10, 5), font=('Segoe UI', 9), borderwidth=1)
        
        # 按鈕交互樣式
        style.map('TButton',
            background=[('pressed', c['select']), ('active', c['select']), ('!disabled', c['panel'])],
            foreground=[('!disabled', c['fg'])],
            relief=[('pressed', 'sunken'), ('!pressed', 'raised')]
        )
        
        # 強調按鈕
        style.configure('Accent.TButton', background=c['accent'], foreground='#ffffff', font=('Segoe UI', 9, 'bold'))
        style.map('Accent.TButton',
            background=[('pressed', c['accent']), ('active', c['accent'])],
            foreground=[('!disabled', '#ffffff')]
        )
        
        # 分組框
        style.configure('TLabelframe', background=c['bg'], foreground=c['fg'], bordercolor=c['border'])
        style.configure('TLabelframe.Label', background=c['bg'], foreground=c['accent'], font=('Segoe UI', 10, 'bold'))
        
        # 選項卡
        style.configure('TNotebook', background=c['bg'], tabposition='nw', borderwidth=0)
        style.configure('TNotebook.Tab', padding=(15, 6), background=c['bg'], foreground=c['fg'], borderwidth=0)
        style.map('TNotebook.Tab',
            background=[('selected', c['panel']), ('active', c['select'])],
            foreground=[('selected', c['accent'])],
            font=[('selected', ('Segoe UI', 9, 'bold'))]
        )
        
        style.configure('TPanedwindow', background=c['bg'])
        style.configure('Horizontal.TScrollbar', gripcount=0, background=c['bg'], troughcolor=c['bg'], bordercolor=c['bg'], lightcolor=c['bg'], darkcolor=c['bg'], arrowcolor=c['fg'])
        style.configure('Vertical.TScrollbar', gripcount=0, background=c['bg'], troughcolor=c['bg'], bordercolor=c['bg'], lightcolor=c['bg'], darkcolor=c['bg'], arrowcolor=c['fg'])

        # 更新 TK 原生組件
        self.root.configure(bg=c['bg'])
        
        # 文本框
        text_widgets = [
            getattr(self, 'headers_text', None),
            getattr(self, 'body_text', None),
            getattr(self, 'response_text', None),
            getattr(self, 'response_headers_text', None)
        ]
        
        for w in text_widgets:
            if w:
                w.config(
                    bg=c['input_bg'], 
                    fg=c['input_fg'], 
                    insertbackground=c['fg'], 
                    selectbackground=c['accent'],
                    relief=tk.FLAT,
                    padx=5, pady=5
                )

        # 更新按鈕文字和圖標
        if hasattr(self, 'theme_btn'):
            self.theme_btn.config(text="☀ 淺色模式" if self.is_dark_mode else "🌙 深色模式")
            
        # 重新應用語法高亮如果存在內容
        if hasattr(self, 'response_text'):
            self.apply_syntax_highlight()

    def create_widgets(self):
        # === 底部 Footer (主題切換) ===
        # 優先 Pack 在底部
        footer_frame = ttk.Frame(self.root, padding=(10, 5))
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.theme_btn = ttk.Button(footer_frame, text="🌙 深色模式", command=self.toggle_theme, style='Accent.TButton')
        self.theme_btn.pack(side=tk.RIGHT)
        
        ttk.Label(footer_frame, text="Ready", font=('Segoe UI', 8), foreground="gray").pack(side=tk.LEFT)

        # === 頂部工具欄 ===
        toolbar = ttk.Frame(self.root, padding="10")
        toolbar.pack(fill=tk.X, side=tk.TOP)
        
        ttk.Button(toolbar, text="🗑 清除全部", command=self.clear_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🕒 歷史記錄", command=self.show_history).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="⚙ 設定", command=self.show_settings).pack(side=tk.LEFT, padx=2)
        ttk.Label(toolbar, text="|", foreground="#cccccc").pack(side=tk.LEFT, padx=10)
        
        # 環境選擇器
        ttk.Label(toolbar, text="環境:", font=('Segoe UI', 9, 'bold')).pack(side=tk.LEFT, padx=(0, 5))
        self.env_combo = ttk.Combobox(toolbar, textvariable=self.current_environment, state="readonly", width=15)
        self.update_environment_list()
        self.env_combo.pack(side=tk.LEFT, padx=(0, 5))
        self.env_combo.bind('<<ComboboxSelected>>', self.on_environment_change)
        ttk.Button(toolbar, text="🌐 管理環境", command=self.show_environment_manager).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(toolbar, text="|", foreground="#cccccc").pack(side=tk.LEFT, padx=10)
        ttk.Label(toolbar, text="API Client Enterprise", font=('Segoe UI', 12, 'bold')).pack(side=tk.LEFT)

        # === 請求欄 ===
        req_frame = ttk.Frame(self.root, padding="10")
        req_frame.pack(fill=tk.X, side=tk.TOP)

        # Method Selector
        ttk.Label(req_frame, text="Method:", font=('Segoe UI', 9, 'bold')).pack(side=tk.LEFT)
        self.method_var = tk.StringVar(value="GET")
        methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
        self.method_combo = ttk.Combobox(req_frame, textvariable=self.method_var, values=methods, state="readonly", width=10)
        self.method_combo.pack(side=tk.LEFT, padx=(5, 15))

        # URL Input
        ttk.Label(req_frame, text="URL:", font=('Segoe UI', 9, 'bold')).pack(side=tk.LEFT)
        self.url_entry = ttk.Entry(req_frame, font=('Segoe UI', 10))
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.url_entry.insert(0, "https://jsonplaceholder.typicode.com/posts/1")

        # Timeout Input
        ttk.Label(req_frame, text="逾時(s):", font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=(5, 2))
        default_timeout = "30"
        if ENTERPRISE_MODE:
            default_timeout = str(config_manager.app_config.default_timeout)
        self.timeout_var = tk.StringVar(value=default_timeout)
        self.timeout_entry = ttk.Entry(req_frame, textvariable=self.timeout_var, width=4)
        self.timeout_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        # 重試次數
        ttk.Label(req_frame, text="重試:", font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=(5, 2))
        default_retry = "0"
        if ENTERPRISE_MODE:
            default_retry = str(config_manager.app_config.retry_count)
        self.retry_var = tk.StringVar(value=default_retry)
        self.retry_entry = ttk.Entry(req_frame, textvariable=self.retry_var, width=3)
        self.retry_entry.pack(side=tk.LEFT, padx=(0, 5))

        # Send Button
        self.send_btn = ttk.Button(req_frame, text="🚀 發送請求", style='Accent.TButton', command=self.on_send)
        self.send_btn.pack(side=tk.LEFT, padx=(10, 0))

        # === 中間區域: 標籤頁 (Headers & Body) ===
        self.paned_window = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 輸入標籤頁框架
        input_frame = ttk.LabelFrame(self.paned_window, text="📤 請求配置", padding=5)
        self.paned_window.add(input_frame, weight=1)

        self.notebook = ttk.Notebook(input_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Tab 1: Headers
        self.headers_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.headers_frame, text="📋 Headers")
        
        headers_toolbar = ttk.Frame(self.headers_frame)
        headers_toolbar.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(headers_toolbar, text="格式: Key: Value (每行一個)", font=('Segoe UI', 9, 'italic')).pack(side=tk.LEFT)
        ttk.Button(headers_toolbar, text="清除", command=lambda: self.headers_text.delete(1.0, tk.END)).pack(side=tk.RIGHT)
        
        headers_scroll = ttk.Scrollbar(self.headers_frame)
        headers_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.headers_text = tk.Text(self.headers_frame, height=6, font=("Consolas", 10), yscrollcommand=headers_scroll.set, wrap=tk.NONE)
        headers_scroll.config(command=self.headers_text.yview)
        self.headers_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.headers_text.insert(1.0, "Content-Type: application/json\nUser-Agent: PyClient/1.0")

        # Tab 2: Body
        self.body_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.body_frame, text="📝 Body")
        
        body_toolbar = ttk.Frame(self.body_frame)
        body_toolbar.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(body_toolbar, text="原始內容 (JSON/Text):", font=('Segoe UI', 9, 'italic')).pack(side=tk.LEFT)
        ttk.Button(body_toolbar, text="格式化 JSON", command=self.format_body_json).pack(side=tk.RIGHT, padx=2)
        ttk.Button(body_toolbar, text="清除", command=lambda: self.body_text.delete(1.0, tk.END)).pack(side=tk.RIGHT)
        
        body_scroll = ttk.Scrollbar(self.body_frame)
        body_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.body_text = tk.Text(self.body_frame, height=6, font=("Consolas", 10), yscrollcommand=body_scroll.set, wrap=tk.NONE)
        body_scroll.config(command=self.body_text.yview)
        self.body_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # === 響應查看區 ===
        response_container = ttk.LabelFrame(self.paned_window, text="📥 響應結果", padding=5)
        self.paned_window.add(response_container, weight=2)

        # 狀態欄 - 顯示詳細信息
        self.status_bar_frame = ttk.Frame(response_container)
        self.status_bar_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.status_label = ttk.Label(self.status_bar_frame, text="● 就緒", font=("Segoe UI", 9, "bold"), foreground="gray")
        self.status_label.pack(side=tk.LEFT)
        
        self.time_label = ttk.Label(self.status_bar_frame, text="", font=("Segoe UI", 9))
        self.time_label.pack(side=tk.LEFT, padx=10)
        
        self.size_label = ttk.Label(self.status_bar_frame, text="", font=("Segoe UI", 9))
        self.size_label.pack(side=tk.LEFT, padx=10)
        
        # 響應操作按鈕
        response_btn_frame = ttk.Frame(self.status_bar_frame)
        response_btn_frame.pack(side=tk.RIGHT)
        ttk.Button(response_btn_frame, text="複製響應", command=self.copy_response).pack(side=tk.LEFT, padx=2)
        ttk.Button(response_btn_frame, text="查看Headers", command=self.view_response_headers).pack(side=tk.LEFT, padx=2)
        ttk.Button(response_btn_frame, text="清除", command=self.clear_response).pack(side=tk.LEFT, padx=2)

        # 響應標籤頁
        response_notebook = ttk.Notebook(response_container)
        response_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Body標籤頁
        body_response_frame = ttk.Frame(response_notebook)
        response_notebook.add(body_response_frame, text="📄 Body")
        
        self.response_text = tk.Text(body_response_frame, wrap=tk.NONE, font=("Consolas", 10), state=tk.DISABLED, bg="#ffffff")
        v_scroll = ttk.Scrollbar(body_response_frame, orient="vertical", command=self.response_text.yview)
        h_scroll = ttk.Scrollbar(body_response_frame, orient="horizontal", command=self.response_text.xview)
        self.response_text.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.response_text.pack(fill=tk.BOTH, expand=True)
        
        # Headers標籤頁
        headers_response_frame = ttk.Frame(response_notebook)
        response_notebook.add(headers_response_frame, text="📋 Response Headers")
        
        self.response_headers_text = tk.Text(headers_response_frame, wrap=tk.NONE, font=("Consolas", 9), state=tk.DISABLED, bg="#ffffff")
        headers_v_scroll = ttk.Scrollbar(headers_response_frame, orient="vertical", command=self.response_headers_text.yview)
        self.response_headers_text.configure(yscrollcommand=headers_v_scroll.set)
        headers_v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.response_headers_text.pack(fill=tk.BOTH, expand=True)

    def on_send(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("警告", "請輸入 URL")
            return
        
        # 驗證 URL
        is_valid, error_msg = validate_url(url)
        if not is_valid and not url.startswith('{{'):  # 允許變數格式
            messagebox.showwarning("URL 格式錯誤", error_msg)
            return

        method = self.method_var.get()
        headers = self.headers_text.get(1.0, tk.END).strip()
        body = self.body_text.get(1.0, tk.END).strip()
        
        # 驗證 Body JSON (如果有內容且看起來像 JSON)
        if body and (body.startswith('{') or body.startswith('[')):
            is_valid, error_msg = validate_json(body)
            if not is_valid:
                if not messagebox.askyesno("JSON 格式警告", f"{error_msg}\n\n是否仍要發送請求？"):
                    return
        
        try:
            timeout = float(self.timeout_var.get())
        except ValueError:
            timeout = 10
            
        try:
            retry_count = int(self.retry_var.get())
        except ValueError:
            retry_count = 0

        # 添加到歷史記錄
        self.add_to_history(method, url, headers, body)

        # UI Loading State
        self.send_btn.config(state=tk.DISABLED, text="⏳ 發送中...")
        self.status_label.config(text="● 發送中...", foreground="#0078d4")
        self.time_label.config(text="")
        self.size_label.config(text="")
        self.set_response_text("正在發送請求...")
        self.set_response_headers("")

        # Run in thread
        thread = threading.Thread(target=self.run_request, args=(method, url, headers, body, timeout, retry_count))
        thread.daemon = True
        thread.start()

    def run_request(self, method, url, headers, body, timeout, retry_count):
        try:
            timeout_value = max(float(timeout), 0.1)
            response = self.orchestrator.send_request_new(
                method=method,
                url=url,
                headers_text=headers,
                body_text=body,
                timeout=timeout_value,
                retry_count=retry_count
            )
            
            # 將 HttpResponse 轉回 update_ui 期待的格式
            # Tuple: (status_code, content, error_msg, elapsed_time, response_headers, content_size)
            self.root.after(0, self.update_ui, 
                            response.status_code, 
                            response.content, 
                            response.error, 
                            response.elapsed_time, 
                            response.headers, 
                            response.content_size)
        except (ApiClientError, RuntimeError, ValueError, TypeError) as e:
            if ENTERPRISE_MODE and logger:
                logger.exception(
                    f"請求處理失敗: {method} {url}",
                    extra={'http_method': method, 'url': url}
                )
            self.root.after(0, self.update_ui, 0, "", str(e), 0.0, {}, 0)

    def update_ui(self, code, content, error, elapsed_time, response_headers, content_size):
        self.send_btn.config(state=tk.NORMAL, text="🚀 發送請求")
        self.current_response_headers = response_headers
        
        if error:
            self.status_label.config(text=f"● 錯誤", foreground="#dc3545")
            self.time_label.config(text="")
            self.size_label.config(text="")
            self.set_response_text(f"錯誤詳情:\n{error}")
            self.set_response_headers("發生錯誤，無響應頭")
        else:
            # 狀態碼顏色
            if 200 <= code < 300:
                color = "#28a745"
                status_text = "● 成功"
            elif 300 <= code < 400:
                color = "#ffc107"
                status_text = "● 重定向"
            elif 400 <= code < 500:
                color = "#fd7e14"
                status_text = "● 客戶端錯誤"
            else:
                color = "#dc3545"
                status_text = "● 服務器錯誤"
            
            self.status_label.config(text=f"{status_text} {code}", foreground=color)
            self.time_label.config(text=f"⏱ {elapsed_time*1000:.0f} ms")
            self.size_label.config(text=f"📦 {format_size(content_size)}")
            
            formatted_content = format_json(content)
            self.set_response_text(formatted_content)
            self.set_response_headers(format_headers_display(response_headers))

    def set_response_text(self, text):
        self.response_text.config(state=tk.NORMAL)
        self.response_text.delete(1.0, tk.END)
        self.response_text.insert(tk.END, text)
        self.apply_syntax_highlight()
        self.response_text.config(state=tk.DISABLED)
    
    def apply_syntax_highlight(self):
        """Apply simple JSON syntax highlighting"""
        content = self.response_text.get(1.0, tk.END)
        stripped_content = content.strip()
        if not stripped_content:
            return

        # Remove existing tags
        for tag in ["json_string", "json_number", "json_bool", "json_key"]:
            self.response_text.tag_remove(tag, 1.0, tk.END)

        # 回應過大時略過高亮，避免 UI 卡頓
        if len(content) > self.MAX_SYNTAX_HIGHLIGHT_CHARS:
            return

        # We only highlight if it looks like JSON structure
        if not stripped_content.startswith(("{", "[")):
            return

        theme_key = "dark" if self.is_dark_mode else "light"
        c = self.colors[theme_key]
        if self._syntax_theme_key != theme_key:
            self.response_text.tag_config("json_string", foreground=c['json_string'])
            self.response_text.tag_config("json_number", foreground=c['json_number'])
            self.response_text.tag_config("json_bool", foreground=c['json_bool'])
            self.response_text.tag_config("json_key", foreground=c['json_key'], font=("Consolas", 10, "bold"))
            self._syntax_theme_key = theme_key

        try:
            # Highlight all strings first and infer key/value by nearby ':'
            for match in self.JSON_STRING_PATTERN.finditer(content):
                start = f"1.0 + {match.start()} chars"
                end = f"1.0 + {match.end()} chars"
                after_str = content[match.end():match.end() + 10]
                if ":" in after_str.split("\n", 1)[0]:
                    self.response_text.tag_add("json_key", start, end)
                else:
                    self.response_text.tag_add("json_string", start, end)

            for match in self.JSON_BOOL_PATTERN.finditer(content):
                start = f"1.0 + {match.start()} chars"
                end = f"1.0 + {match.end()} chars"
                self.response_text.tag_add("json_bool", start, end)

        except (tk.TclError, re.error) as e:
            if ENTERPRISE_MODE and logger:
                logger.warning(f"語法高亮失敗: {e}")
    
    def set_response_headers(self, text):
        self.response_headers_text.config(state=tk.NORMAL)
        self.response_headers_text.delete(1.0, tk.END)
        self.response_headers_text.insert(tk.END, text)
        self.response_headers_text.config(state=tk.DISABLED)

    def clear_response(self):
        """清除響應區域"""
        self.set_response_text("")
        self.set_response_headers("")
        self.status_label.config(text="● 就緒", foreground="gray")
        self.time_label.config(text="")
        self.size_label.config(text="")
    
    def clear_all(self):
        """清除所有輸入和輸出"""
        if messagebox.askyesno("確認", "確定要清除所有內容嗎？"):
            self.url_entry.delete(0, tk.END)
            self.headers_text.delete(1.0, tk.END)
            self.body_text.delete(1.0, tk.END)
            self.clear_response()
    
    def copy_response(self):
        """複製響應內容到剪貼板"""
        content = self.response_text.get(1.0, tk.END).strip()
        if content:
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            messagebox.showinfo("成功", "已複製響應內容到剪貼板")
        else:
            messagebox.showwarning("警告", "沒有可複製的內容")
    
    def view_response_headers(self):
        """在彈窗中查看響應頭"""
        if not self.current_response_headers:
            messagebox.showinfo("提示", "沒有響應頭可顯示")
            return
        
        headers_win = tk.Toplevel(self.root)
        headers_win.title("響應頭詳情")
        headers_win.geometry("600x400")
        
        text = tk.Text(headers_win, font=("Consolas", 10), wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert(1.0, format_headers_display(self.current_response_headers))
        text.config(state=tk.DISABLED)
        
        ttk.Button(headers_win, text="關閉", command=headers_win.destroy).pack(pady=5)
    
    def format_body_json(self):
        """格式化Body中的JSON"""
        content = self.body_text.get(1.0, tk.END).strip()
        if content:
            formatted = format_json(content)
            self.body_text.delete(1.0, tk.END)
            self.body_text.insert(1.0, formatted)

    def get_history_limit(self) -> int:
        """取得歷史記錄上限"""
        if ENTERPRISE_MODE and config_manager:
            return max(1, int(config_manager.app_config.max_history_items))
        return self.FALLBACK_HISTORY_ITEMS
    
    def add_to_history(self, method, url, headers, body):
        """添加到請求歷史"""
        
        entry = {
            "method": method,
            "url": url,
            "headers": headers,
            "body": body,
            "display": f"{method} {url}"
        }

        # 相同請求移到最新位置
        signature = (method, url, headers, body)
        self.request_history = [
            item for item in self.request_history
            if not (
                isinstance(item, dict) and
                (item.get("method"), item.get("url"), item.get("headers", ""), item.get("body", "")) == signature
            )
        ]
        
        self.request_history.append(entry)
        history_limit = self.get_history_limit()
        if len(self.request_history) > history_limit:
            self.request_history = self.request_history[-history_limit:]
        
        self.save_history()
    
    def save_history(self):
        """Save history to file"""
        try:
            with open(self.HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.request_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save history: {e}")

    def load_history(self):
        """Load history from file"""
        if os.path.exists(self.HISTORY_FILE):
            try:
                with open(self.HISTORY_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Migrate old string based history to dict based
                    cleaned_data = []
                    for item in data:
                        if isinstance(item, str):
                            parts = item.split(' ', 1)
                            if len(parts) >= 1:
                                cleaned_data.append({
                                    "method": parts[0],
                                    "url": parts[1] if len(parts) > 1 else "",
                                    "headers": "",
                                    "body": "",
                                    "display": item
                                })
                        elif isinstance(item, dict):
                            cleaned_data.append(item)
                    history_limit = self.get_history_limit()
                    return cleaned_data[-history_limit:]
            except Exception:
                return []
        return []

    def show_history(self):
        """顯示請求歷史"""
        if not self.request_history:
            messagebox.showinfo("提示", "暫無歷史記錄")
            return
        
        history_win = tk.Toplevel(self.root)
        history_win.title("請求歷史記錄")
        history_win.geometry("600x400")
        
        ttk.Label(history_win, text="點擊記錄可重新載入", font=('Segoe UI', 9, 'italic')).pack(pady=5)
        
        listbox = tk.Listbox(history_win, font=("Consolas", 10))
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        for item in reversed(self.request_history):
            if isinstance(item, dict):
                display_text = item.get("display", f"{item.get('method')} {item.get('url')}")
            else:
                display_text = str(item)
            listbox.insert(tk.END, display_text)
        
        def on_select(event):
            selection = listbox.curselection()
            if selection:
                index = selection[0]
                # Map back to history list (reversed view)
                history_index = len(self.request_history) - 1 - index
                
                if 0 <= history_index < len(self.request_history):
                    data = self.request_history[history_index]
                    
                    # Handle both new dict format and old string format just in case
                    if isinstance(data, dict):
                        self.method_var.set(data.get("method", "GET"))
                        self.url_entry.delete(0, tk.END)
                        self.url_entry.insert(0, data.get("url", ""))
                        
                        self.headers_text.delete(1.0, tk.END)
                        self.headers_text.insert(1.0, data.get("headers", ""))
                        
                        self.body_text.delete(1.0, tk.END)
                        self.body_text.insert(1.0, data.get("body", ""))
                    else:
                        try:
                            method, url = str(data).split(' ', 1)
                            self.method_var.set(method)
                            self.url_entry.delete(0, tk.END)
                            self.url_entry.insert(0, url)
                        except ValueError:
                            pass
                    
                    history_win.destroy()
        
        def delete_selected():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("警告", "請先選擇要刪除的記錄")
                return
            
            index = selection[0]
            history_index = len(self.request_history) - 1 - index
            
            # 從 UI 移除
            listbox.delete(index)
            
            # 從數據中移除
            if 0 <= history_index < len(self.request_history):
                self.request_history.pop(history_index)
                self.save_history()
        
        listbox.bind('<Double-Button-1>', on_select)
        
        btn_frame = ttk.Frame(history_win)
        btn_frame.pack(pady=5)
        
        ttk.Button(btn_frame, text="刪除選中", command=delete_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="關閉", command=history_win.destroy).pack(side=tk.LEFT, padx=5)
    
    def update_environment_list(self):
        """更新環境下拉選單"""
        env_names = ["無"]
        if ENTERPRISE_MODE and config_manager:
            env_names.extend(config_manager.environments.keys())
        self.env_combo['values'] = env_names
    
    def on_environment_change(self, event=None):
        """環境變更處理"""
        selected = self.current_environment.get()
        if ENTERPRISE_MODE and config_manager:
            if selected == "無":
                config_manager.current_environment = None
            else:
                config_manager.current_environment = selected
            
            if logger:
                logger.info(f"切換環境: {selected}", extra={'user_action': 'environment_change'})
    
    def show_environment_manager(self):
        """顯示環境管理器"""
        if not ENTERPRISE_MODE:
            messagebox.showinfo("提示", "環境管理功能需要企業版模組")
            return
        
        env_win = tk.Toplevel(self.root)
        env_win.title("環境管理")
        env_win.geometry("700x500")
        env_win.transient(self.root)
        
        # 環境列表
        list_frame = ttk.LabelFrame(env_win, text="環境列表", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        columns = ('name', 'base_url', 'auth_type')
        tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10)
        tree.heading('name', text='環境名稱')
        tree.heading('base_url', text='基礎 URL')
        tree.heading('auth_type', text='認證方式')
        tree.column('name', width=120)
        tree.column('base_url', width=350)
        tree.column('auth_type', width=100)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(fill=tk.BOTH, expand=True)
        
        # 填充資料
        def refresh_list():
            for item in tree.get_children():
                tree.delete(item)
            for name, env in config_manager.environments.items():
                auth = env.auth_type or "無"
                tree.insert('', tk.END, values=(name, env.base_url, auth))
        
        refresh_list()
        
        # 按鈕區
        btn_frame = ttk.Frame(env_win)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def add_environment():
            add_win = tk.Toplevel(env_win)
            add_win.title("新增環境")
            add_win.geometry("500x400")
            add_win.transient(env_win)
            
            ttk.Label(add_win, text="環境名稱:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
            name_entry = ttk.Entry(add_win, width=40)
            name_entry.grid(row=0, column=1, padx=10, pady=5)
            
            ttk.Label(add_win, text="基礎 URL:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
            url_entry = ttk.Entry(add_win, width=40)
            url_entry.grid(row=1, column=1, padx=10, pady=5)
            
            ttk.Label(add_win, text="說明:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
            desc_entry = ttk.Entry(add_win, width=40)
            desc_entry.grid(row=2, column=1, padx=10, pady=5)
            
            ttk.Label(add_win, text="認證方式:").grid(row=3, column=0, sticky=tk.W, padx=10, pady=5)
            auth_var = tk.StringVar(value="none")
            auth_combo = ttk.Combobox(add_win, textvariable=auth_var, 
                                       values=["none", "bearer", "basic", "api_key"], state="readonly")
            auth_combo.grid(row=3, column=1, sticky=tk.W, padx=10, pady=5)
            
            ttk.Label(add_win, text="認證值:").grid(row=4, column=0, sticky=tk.W, padx=10, pady=5)
            auth_entry = ttk.Entry(add_win, width=40, show="*")
            auth_entry.grid(row=4, column=1, padx=10, pady=5)
            
            ttk.Label(add_win, text="預設標頭 (Key: Value):").grid(row=5, column=0, sticky=tk.NW, padx=10, pady=5)
            headers_text = tk.Text(add_win, height=4, width=40, font=("Consolas", 9))
            headers_text.grid(row=5, column=1, padx=10, pady=5)
            
            def save_env():
                name = name_entry.get().strip()
                if not name:
                    messagebox.showwarning("警告", "請輸入環境名稱")
                    return
                
                from utils import parse_headers
                headers = parse_headers(headers_text.get(1.0, tk.END).strip())
                
                auth_type = auth_var.get() if auth_var.get() != "none" else None
                
                env = Environment(
                    name=name,
                    base_url=url_entry.get().strip(),
                    description=desc_entry.get().strip(),
                    auth_type=auth_type,
                    auth_value=auth_entry.get().strip() if auth_type else None,
                    headers=headers
                )
                config_manager.add_environment(env)
                refresh_list()
                self.update_environment_list()
                add_win.destroy()
                messagebox.showinfo("成功", f"環境 '{name}' 已新增")
            
            ttk.Button(add_win, text="儲存", command=save_env, style='Accent.TButton').grid(
                row=6, column=1, sticky=tk.E, padx=10, pady=20)
        
        def delete_environment():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("警告", "請選擇要刪除的環境")
                return
            
            item = tree.item(selection[0])
            name = item['values'][0]
            
            if messagebox.askyesno("確認刪除", f"確定要刪除環境 '{name}' 嗎？"):
                config_manager.remove_environment(name)
                refresh_list()
                self.update_environment_list()
        
        ttk.Button(btn_frame, text="➕ 新增環境", command=add_environment, style='Accent.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🗑 刪除環境", command=delete_environment).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="關閉", command=env_win.destroy).pack(side=tk.RIGHT, padx=5)
    
    def show_settings(self):
        """顯示設定對話框"""
        settings_win = tk.Toplevel(self.root)
        settings_win.title("應用程式設定")
        settings_win.geometry("500x450")
        settings_win.transient(self.root)
        
        notebook = ttk.Notebook(settings_win)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 一般設定頁籤
        general_frame = ttk.Frame(notebook, padding=15)
        notebook.add(general_frame, text="一般")
        
        row = 0
        ttk.Label(general_frame, text="預設逾時 (秒):", font=('Segoe UI', 9)).grid(
            row=row, column=0, sticky=tk.W, pady=5)
        timeout_var = tk.StringVar(value=str(config_manager.app_config.default_timeout if ENTERPRISE_MODE else 30))
        ttk.Entry(general_frame, textvariable=timeout_var, width=10).grid(
            row=row, column=1, sticky=tk.W, pady=5)
        
        row += 1
        ttk.Label(general_frame, text="預設重試次數:", font=('Segoe UI', 9)).grid(
            row=row, column=0, sticky=tk.W, pady=5)
        retry_var = tk.StringVar(value=str(config_manager.app_config.retry_count if ENTERPRISE_MODE else 0))
        ttk.Entry(general_frame, textvariable=retry_var, width=10).grid(
            row=row, column=1, sticky=tk.W, pady=5)
        
        row += 1
        ttk.Label(general_frame, text="最大歷史記錄:", font=('Segoe UI', 9)).grid(
            row=row, column=0, sticky=tk.W, pady=5)
        history_var = tk.StringVar(value=str(config_manager.app_config.max_history_items if ENTERPRISE_MODE else 100))
        ttk.Entry(general_frame, textvariable=history_var, width=10).grid(
            row=row, column=1, sticky=tk.W, pady=5)
        
        # 網路設定頁籤
        network_frame = ttk.Frame(notebook, padding=15)
        notebook.add(network_frame, text="網路")
        
        row = 0
        ssl_var = tk.BooleanVar(value=config_manager.app_config.verify_ssl if ENTERPRISE_MODE else True)
        ttk.Checkbutton(network_frame, text="驗證 SSL 憑證", variable=ssl_var).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        row += 1
        proxy_var = tk.BooleanVar(value=config_manager.app_config.proxy_enabled if ENTERPRISE_MODE else False)
        ttk.Checkbutton(network_frame, text="啟用代理伺服器", variable=proxy_var).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        row += 1
        ttk.Label(network_frame, text="HTTP Proxy:", font=('Segoe UI', 9)).grid(
            row=row, column=0, sticky=tk.W, pady=5)
        http_proxy_var = tk.StringVar(value=config_manager.app_config.http_proxy or "" if ENTERPRISE_MODE else "")
        ttk.Entry(network_frame, textvariable=http_proxy_var, width=40).grid(
            row=row, column=1, sticky=tk.W, pady=5)
        
        row += 1
        ttk.Label(network_frame, text="HTTPS Proxy:", font=('Segoe UI', 9)).grid(
            row=row, column=0, sticky=tk.W, pady=5)
        https_proxy_var = tk.StringVar(value=config_manager.app_config.https_proxy or "" if ENTERPRISE_MODE else "")
        ttk.Entry(network_frame, textvariable=https_proxy_var, width=40).grid(
            row=row, column=1, sticky=tk.W, pady=5)
        
        # 日誌設定頁籤
        log_frame = ttk.Frame(notebook, padding=15)
        notebook.add(log_frame, text="日誌")
        
        row = 0
        ttk.Label(log_frame, text="日誌等級:", font=('Segoe UI', 9)).grid(
            row=row, column=0, sticky=tk.W, pady=5)
        log_level_var = tk.StringVar(value=config_manager.app_config.log_level if ENTERPRISE_MODE else "INFO")
        log_combo = ttk.Combobox(log_frame, textvariable=log_level_var, 
                                  values=["DEBUG", "INFO", "WARNING", "ERROR"], state="readonly")
        log_combo.grid(row=row, column=1, sticky=tk.W, pady=5)
        
        row += 1
        ttk.Label(log_frame, text="日誌檔案:", font=('Segoe UI', 9)).grid(
            row=row, column=0, sticky=tk.W, pady=5)
        log_file_var = tk.StringVar(value=config_manager.app_config.log_file if ENTERPRISE_MODE else "api_client.log")
        ttk.Entry(log_frame, textvariable=log_file_var, width=40).grid(
            row=row, column=1, sticky=tk.W, pady=5)
        
        # 儲存按鈕
        def save_settings():
            if ENTERPRISE_MODE:
                try:
                    config_manager.app_config.default_timeout = int(timeout_var.get())
                    config_manager.app_config.retry_count = int(retry_var.get())
                    config_manager.app_config.max_history_items = int(history_var.get())
                    config_manager.app_config.verify_ssl = ssl_var.get()
                    config_manager.app_config.proxy_enabled = proxy_var.get()
                    config_manager.app_config.http_proxy = http_proxy_var.get() or None
                    config_manager.app_config.https_proxy = https_proxy_var.get() or None
                    config_manager.app_config.log_level = log_level_var.get()
                    config_manager.app_config.log_file = log_file_var.get()
                    
                    config_manager.save_config()
                    messagebox.showinfo("成功", "設定已儲存")
                    settings_win.destroy()
                except ValueError as e:
                    messagebox.showerror("錯誤", f"設定值無效: {e}")
            else:
                messagebox.showinfo("提示", "完整設定功能需要企業版模組")
                settings_win.destroy()
        
        btn_frame = ttk.Frame(settings_win)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_frame, text="儲存", command=save_settings, style='Accent.TButton').pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=settings_win.destroy).pack(side=tk.RIGHT, padx=5)

if __name__ == "__main__":
    try:
        # Increase DPI awareness on Windows for sharper text
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    
    # 啟動提示
    print("=" * 50)
    print("  API Client - Enterprise Edition v2.0.0")
    print("=" * 50)
    if ENTERPRISE_MODE:
        print(f"  企業版模組: 已載入")
        print(f"  日誌等級: {config_manager.app_config.log_level}")
        print(f"  日誌檔案: {config_manager.app_config.log_file}")
    else:
        print("  企業版模組: 未載入 (使用基本功能)")
    print("=" * 50)

    root = tk.Tk()
    app = ApiClientApp(root)
    root.mainloop()
