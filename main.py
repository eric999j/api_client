"""
API Client - Enterprise Edition
專業級 API 測試工具

版本: 2.0.0
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import json
import re
import os
import sys

# 初始化核心模組
from config.settings import config_manager
from core.logger import setup_logging, get_logger
from core.exceptions import ApiClientError

from logic import ApiClientOrchestrator
from ui.dialogs import AppDialogsMixin
from ui.layout import AppLayoutMixin
from utils import (
    DIFY_BLOCKING_RECOMMENDED_TIMEOUT,
    format_json,
    format_size,
    format_headers_display,
    get_dify_response_mode,
    headers_to_text,
    normalize_dify_request_body,
    parse_headers,
    validate_url,
    validate_json,
)

# 設定日誌
setup_logging(
    log_level=config_manager.app_config.log_level,
    log_file=config_manager.app_config.log_file
)
logger = get_logger(__name__)

class ApiClientApp(AppLayoutMixin, AppDialogsMixin):
    """企業級 API 測試客戶端應用程式"""
    
    HISTORY_FILE = "api_client_history.json"
    VERSION = "2.0.0"
    DEFAULT_URL = "https://jsonplaceholder.typicode.com/posts/1"
    FALLBACK_HISTORY_ITEMS = 20
    MAX_SYNTAX_HIGHLIGHT_CHARS = 120_000
    JSON_STRING_PATTERN = re.compile(r'"(?:[^"\\]|\\.)*"')
    JSON_BOOL_PATTERN = re.compile(r'\b(true|false|null)\b')

    def __init__(self, root):
        self.root = root
        self._syntax_theme_key = None
        
        # 使用配置
        config = config_manager.app_config
        self.root.title(f"{config.app_name} v{self.VERSION}")
        self.root.geometry(f"{config.window_width}x{config.window_height}")
        
        # 設置主題和樣式 (初始化)
        self.setup_styles()
        
        # 歷史記錄
        self.request_history = self.load_history()
        self.current_response_headers = {}
        
        # 初始化業務邏輯協調器
        self.orchestrator = ApiClientOrchestrator()
        
        # 環境變數
        initial_environment = config_manager.current_environment or "無"
        self.current_environment = tk.StringVar(value=initial_environment)
        self.url_var = tk.StringVar(value=self.DEFAULT_URL)
        self.environment_summary_var = tk.StringVar(value="")
        self.environment_details_var = tk.StringVar(value="")

        self.create_widgets()

        self.apply_environment_to_request(None, config_manager.get_current_environment())
        self.update_environment_context()
        
        # 確保所有組件創建後應用主題
        self.apply_theme()
        
        # 記錄啟動
        logger.info("API Client 啟動", extra={'user_action': 'app_start'})
    
    def setup_styles(self):
        """設置現代化主題與配色"""
        self.is_dark_mode = config_manager.app_config.theme == "dark"
            
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

    def on_send(self):
        url = self.url_var.get().strip()
        env = config_manager.get_current_environment()

        if not url:
            if env and env.base_url:
                url = env.base_url
                self.url_var.set(url)
            else:
                messagebox.showwarning("警告", "請輸入 URL")
                return
        
        # 驗證 URL
        resolved_url = self.build_resolved_request_url(url)
        is_valid, error_msg = validate_url(resolved_url)
        if not is_valid and not url.startswith('{{'):  # 允許變數格式
            extra_detail = ""
            if resolved_url and resolved_url != url:
                extra_detail = f"\n\n解析後 URL: {resolved_url}"
            messagebox.showwarning("URL 格式錯誤", f"{error_msg}{extra_detail}")
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

            normalized_body, moved_fields = normalize_dify_request_body(body)
            if moved_fields:
                field_list = ", ".join(moved_fields)
                decision = messagebox.askyesnocancel(
                    "Dify Payload 提醒",
                    f"偵測到頂層欄位應移入 inputs：{field_list}\n\n選擇「是」會自動修正後送出；選擇「否」會保持原內容送出；選擇「取消」會返回編輯。"
                )
                if decision is None:
                    return
                if decision:
                    body = normalized_body
                    self.body_text.delete(1.0, tk.END)
                    self.body_text.insert(1.0, body)
        
        try:
            timeout = float(self.timeout_var.get())
        except ValueError:
            timeout = 10

        response_mode = get_dify_response_mode(body)
        if response_mode == 'blocking' and timeout < DIFY_BLOCKING_RECOMMENDED_TIMEOUT:
            decision = messagebox.askyesnocancel(
                "Blocking Timeout 提醒",
                f"偵測到此請求使用 blocking 模式，目前逾時為 {timeout:.0f} 秒。\n\n建議至少使用 {DIFY_BLOCKING_RECOMMENDED_TIMEOUT:.0f} 秒，否則很容易在工作流完成前逾時。\n\n選擇「是」會自動改為 {DIFY_BLOCKING_RECOMMENDED_TIMEOUT:.0f} 秒後送出；選擇「否」會保持目前值送出；選擇「取消」會返回編輯。"
            )
            if decision is None:
                return
            if decision:
                timeout = DIFY_BLOCKING_RECOMMENDED_TIMEOUT
                self.timeout_var.set(str(int(DIFY_BLOCKING_RECOMMENDED_TIMEOUT)))
            
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
        return max(1, int(config_manager.app_config.max_history_items))
    
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
                            history_item = dict(item)
                            normalized_body, _ = normalize_dify_request_body(history_item.get("body", ""))
                            if normalized_body != history_item.get("body", ""):
                                history_item["body"] = normalized_body
                            cleaned_data.append(history_item)
                    history_limit = self.get_history_limit()
                    return cleaned_data[-history_limit:]
            except Exception:
                return []
        return []

if __name__ == "__main__":
    try:
        # Increase DPI awareness on Windows for sharper text
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    
    # 啟動提示
    print("=" * 50)
    print("  API Client - Enterprise Edition v2.0.0")
    print("=" * 50)
    print(f"  日誌等級: {config_manager.app_config.log_level}")
    print(f"  日誌檔案: {config_manager.app_config.log_file}")
    print("=" * 50)

    root = tk.Tk()
    app = ApiClientApp(root)
    root.mainloop()
