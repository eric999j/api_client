"""GUI dialog and environment management mixins."""
import tkinter as tk
from tkinter import ttk, messagebox

from config.settings import Environment, config_manager
from core.logger import get_logger
from utils import headers_to_text, parse_headers, validate_url

logger = get_logger(__name__)


class AppDialogsMixin:
    """Dialog-related behaviors extracted from ApiClientApp."""

    def show_history(self):
        """顯示請求歷史"""
        if not self.request_history:
            messagebox.showinfo("提示", "暫無歷史記錄")
            return

        history_win = tk.Toplevel(self.root)
        history_win.title("請求歷史記錄")
        history_win.geometry("600x400")

        ttk.Label(history_win, text="點擊記錄可重新載入", font=("Segoe UI", 9, "italic")).pack(pady=5)

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
                history_index = len(self.request_history) - 1 - index

                if 0 <= history_index < len(self.request_history):
                    data = self.request_history[history_index]

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
                            method, url = str(data).split(" ", 1)
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
            listbox.delete(index)

            if 0 <= history_index < len(self.request_history):
                self.request_history.pop(history_index)
                self.save_history()

        listbox.bind("<Double-Button-1>", on_select)

        btn_frame = ttk.Frame(history_win)
        btn_frame.pack(pady=5)

        ttk.Button(btn_frame, text="刪除選中", command=delete_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="關閉", command=history_win.destroy).pack(side=tk.LEFT, padx=5)

    def update_environment_list(self):
        """更新環境下拉選單"""
        env_names = ["無"]
        env_names.extend(config_manager.environments.keys())
        self.env_combo["values"] = env_names

        selected = self.current_environment.get()
        if selected not in env_names:
            self.current_environment.set("無")
        self.update_environment_context()

    def build_resolved_request_url(self, url: str) -> str:
        """建立目前請求的解析後 URL"""
        return config_manager.resolve_url(url)

    def apply_environment_to_request(self, previous_env, current_env):
        """依照環境切換結果更新目前請求目標"""
        if not current_env or not current_env.base_url:
            return

        current_url = self.url_var.get().strip()
        if not current_url or current_url == self.DEFAULT_URL:
            self.url_var.set(current_env.base_url)
            return

        if previous_env and previous_env.base_url:
            previous_base = previous_env.base_url.rstrip("/")
            current_base = current_env.base_url.rstrip("/")
            if current_url == previous_env.base_url:
                self.url_var.set(current_env.base_url)
                return
            if current_url.startswith(previous_base + "/"):
                suffix = current_url[len(previous_base):]
                self.url_var.set(f"{current_base}{suffix}")

    def update_environment_context(self, *args):
        """更新環境摘要與解析後 URL 顯示"""
        if not hasattr(self, "environment_summary_var"):
            return

        env = config_manager.get_current_environment()
        request_target = self.url_var.get().strip()

        if not env:
            self.environment_summary_var.set("目前未選擇環境")
            self.environment_details_var.set("請輸入完整 URL；選擇環境後也可輸入相對路徑，例如 /v1/users")
            return

        auth_label = env.auth_type or "無認證"
        header_count = len(env.headers)
        variable_count = len(env.variables)
        description = f" | {env.description}" if env.description else ""
        self.environment_summary_var.set(
            f"目前環境: {env.name} | Base URL: {env.base_url or '未設定'}{description}"
        )

        if request_target:
            resolved_url = self.build_resolved_request_url(request_target)
            self.environment_details_var.set(
                f"解析後 URL: {resolved_url} | 預設 Headers: {header_count} | 變數: {variable_count} | 認證: {auth_label}"
            )
            return

        self.environment_details_var.set(
            f"將自動使用 Base URL；預設 Headers: {header_count} | 變數: {variable_count} | 認證: {auth_label}"
        )

    def format_environment_mapping(self, data, separator=" = "):
        """格式化環境用的鍵值對"""
        if not data:
            return ""
        return "\n".join(f"{key}{separator}{value}" for key, value in data.items())

    def parse_environment_mapping(self, text):
        """解析環境編輯器中的鍵值對"""
        mapping = {}
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" in line:
                key, value = line.split("=", 1)
            elif ":" in line:
                key, value = line.split(":", 1)
            else:
                continue

            key = key.strip()
            value = value.strip()
            if key:
                mapping[key] = value

        return mapping

    def open_environment_editor(self, parent, refresh_callback, env=None):
        """開啟新增/編輯環境視窗"""
        editor = tk.Toplevel(parent)
        editor.title("編輯環境" if env else "新增環境")
        editor.geometry("620x560")
        editor.transient(parent)
        editor.grab_set()

        original_name = env.name if env else None

        form = ttk.Frame(editor, padding=15)
        form.pack(fill=tk.BOTH, expand=True)
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="環境名稱:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=6)
        name_entry = ttk.Entry(form, width=40)
        name_entry.grid(row=0, column=1, sticky=tk.EW, pady=6)

        ttk.Label(form, text="基礎 URL:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=6)
        url_entry = ttk.Entry(form, width=40)
        url_entry.grid(row=1, column=1, sticky=tk.EW, pady=6)

        ttk.Label(form, text="說明:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=6)
        desc_entry = ttk.Entry(form, width=40)
        desc_entry.grid(row=2, column=1, sticky=tk.EW, pady=6)

        ttk.Label(form, text="認證方式:").grid(row=3, column=0, sticky=tk.W, padx=(0, 10), pady=6)
        auth_var = tk.StringVar(value="none")
        auth_combo = ttk.Combobox(
            form,
            textvariable=auth_var,
            values=["none", "bearer", "basic", "api_key"],
            state="readonly",
        )
        auth_combo.grid(row=3, column=1, sticky=tk.W, pady=6)

        ttk.Label(form, text="認證值:").grid(row=4, column=0, sticky=tk.W, padx=(0, 10), pady=6)
        auth_entry = ttk.Entry(form, width=40, show="*")
        auth_entry.grid(row=4, column=1, sticky=tk.EW, pady=6)

        ttk.Label(form, text="預設 Headers:").grid(row=5, column=0, sticky=tk.NW, padx=(0, 10), pady=6)
        headers_text = tk.Text(form, height=7, width=50, font=("Consolas", 9), wrap=tk.NONE)
        headers_text.grid(row=5, column=1, sticky=tk.EW, pady=6)

        ttk.Label(form, text="環境變數:").grid(row=6, column=0, sticky=tk.NW, padx=(0, 10), pady=6)
        variables_text = tk.Text(form, height=7, width=50, font=("Consolas", 9), wrap=tk.NONE)
        variables_text.grid(row=6, column=1, sticky=tk.EW, pady=6)

        ttk.Label(
            form,
            text="變數可用在 URL / Headers / Body，例如 {{tenant_id}}；支援 key=value 或 key: value。",
            font=("Segoe UI", 8),
            foreground="gray",
        ).grid(row=7, column=0, columnspan=2, sticky=tk.W, pady=(4, 10))

        if env:
            name_entry.insert(0, env.name)
            url_entry.insert(0, env.base_url)
            desc_entry.insert(0, env.description)
            auth_var.set(env.auth_type or "none")
            if env.auth_value:
                auth_entry.insert(0, env.auth_value)
            if env.headers:
                headers_text.insert(1.0, headers_to_text(env.headers))
            if env.variables:
                variables_text.insert(1.0, self.format_environment_mapping(env.variables))

        def save_environment():
            name = name_entry.get().strip()
            base_url = url_entry.get().strip()
            description = desc_entry.get().strip()

            if not name:
                messagebox.showwarning("警告", "請輸入環境名稱", parent=editor)
                return

            if name != original_name and name in config_manager.environments:
                messagebox.showwarning("警告", f"環境 '{name}' 已存在", parent=editor)
                return

            if base_url:
                is_valid, error_msg = validate_url(base_url)
                if not is_valid:
                    messagebox.showwarning("基礎 URL 格式錯誤", error_msg, parent=editor)
                    return

            auth_type = auth_var.get() if auth_var.get() != "none" else None
            headers = parse_headers(headers_text.get(1.0, tk.END).strip())
            variables = self.parse_environment_mapping(variables_text.get(1.0, tk.END).strip())

            updated_env = Environment(
                name=name,
                base_url=base_url,
                variables=variables,
                headers=headers,
                auth_type=auth_type,
                auth_value=auth_entry.get().strip() if auth_type else None,
                description=description,
            )

            was_current = original_name and config_manager.current_environment == original_name
            if original_name and original_name != name:
                config_manager.remove_environment(original_name)

            config_manager.add_environment(updated_env)

            if was_current:
                config_manager.set_current_environment(name)
                self.current_environment.set(name)

            refresh_callback(selected_name=name)
            self.update_environment_list()
            self.update_environment_context()
            editor.destroy()

        action_frame = ttk.Frame(form)
        action_frame.grid(row=8, column=0, columnspan=2, sticky=tk.E, pady=(10, 0))
        ttk.Button(action_frame, text="取消", command=editor.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(action_frame, text="儲存", command=save_environment, style="Accent.TButton").pack(side=tk.RIGHT)

    def on_environment_change(self, event=None):
        """環境變更處理"""
        selected = self.current_environment.get()
        previous_env = config_manager.get_current_environment()
        if selected == "無":
            config_manager.set_current_environment(None)
        else:
            config_manager.set_current_environment(selected)

        self.apply_environment_to_request(previous_env, config_manager.get_current_environment())
        self.update_environment_context()
        logger.info(f"切換環境: {selected}", extra={"user_action": "environment_change"})

    def show_environment_manager(self):
        """顯示環境管理器"""
        env_win = tk.Toplevel(self.root)
        env_win.title("環境管理")
        env_win.geometry("820x620")
        env_win.transient(self.root)
        env_win.grab_set()

        list_frame = ttk.LabelFrame(env_win, text="環境列表", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("active", "name", "base_url", "auth_type", "variables")
        tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
        tree.heading("active", text="狀態")
        tree.heading("name", text="環境名稱")
        tree.heading("base_url", text="基礎 URL")
        tree.heading("auth_type", text="認證方式")
        tree.heading("variables", text="變數數量")
        tree.column("active", width=70, anchor=tk.CENTER)
        tree.column("name", width=120)
        tree.column("base_url", width=360)
        tree.column("auth_type", width=100)
        tree.column("variables", width=90, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(fill=tk.BOTH, expand=True)

        preview_frame = ttk.LabelFrame(env_win, text="環境預覽", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        preview_text = tk.Text(preview_frame, height=12, font=("Consolas", 9), wrap=tk.WORD, state=tk.DISABLED)
        preview_scrollbar = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=preview_text.yview)
        preview_text.configure(yscrollcommand=preview_scrollbar.set)
        preview_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        preview_text.pack(fill=tk.BOTH, expand=True)

        def set_preview(content):
            preview_text.config(state=tk.NORMAL)
            preview_text.delete(1.0, tk.END)
            preview_text.insert(1.0, content)
            preview_text.config(state=tk.DISABLED)

        def get_selected_environment_name():
            selection = tree.selection()
            if not selection:
                return None
            item = tree.item(selection[0])
            values = item.get("values", [])
            return values[1] if len(values) > 1 else None

        def refresh_list(selected_name=None):
            for item in tree.get_children():
                tree.delete(item)
            current_name = config_manager.current_environment
            for name, env in config_manager.environments.items():
                auth = env.auth_type or "無"
                active = "使用中" if name == current_name else ""
                row_id = tree.insert("", tk.END, values=(active, name, env.base_url, auth, len(env.variables)))
                if selected_name and name == selected_name:
                    tree.selection_set(row_id)
                    tree.focus(row_id)

            if not selected_name and current_name:
                for item in tree.get_children():
                    values = tree.item(item).get("values", [])
                    if len(values) > 1 and values[1] == current_name:
                        tree.selection_set(item)
                        tree.focus(item)
                        break

            update_preview()

        def update_preview(event=None):
            name = get_selected_environment_name()
            if not name:
                set_preview("選擇環境後可查看 Base URL、認證、預設 Headers 與變數。")
                return

            env = config_manager.environments.get(name)
            if not env:
                set_preview("找不到所選環境。")
                return

            preview_content = (
                f"名稱: {env.name}\n"
                f"Base URL: {env.base_url or '未設定'}\n"
                f"說明: {env.description or '無'}\n"
                f"認證: {env.auth_type or '無'}\n"
                f"認證值: {'已設定' if env.auth_value else '未設定'}\n\n"
                f"預設 Headers:\n{headers_to_text(env.headers) or '無'}\n\n"
                f"環境變數:\n{self.format_environment_mapping(env.variables) or '無'}\n\n"
                "提示: 變數可用在 URL / Headers / Body，例如 {{tenant_id}}"
            )
            set_preview(preview_content)

        refresh_list()
        tree.bind("<<TreeviewSelect>>", update_preview)

        btn_frame = ttk.Frame(env_win)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        def add_environment():
            self.open_environment_editor(env_win, refresh_list)

        def edit_environment():
            name = get_selected_environment_name()
            if not name:
                messagebox.showwarning("警告", "請先選擇要編輯的環境", parent=env_win)
                return

            env = config_manager.environments.get(name)
            if not env:
                messagebox.showwarning("警告", "找不到所選環境", parent=env_win)
                return

            self.open_environment_editor(env_win, refresh_list, env=env)

        def activate_environment():
            name = get_selected_environment_name()
            if not name:
                messagebox.showwarning("警告", "請先選擇要套用的環境", parent=env_win)
                return

            self.current_environment.set(name)
            self.on_environment_change()
            refresh_list(selected_name=name)
            messagebox.showinfo("成功", f"已切換到環境 '{name}'", parent=env_win)

        def delete_environment():
            name = get_selected_environment_name()
            if not name:
                messagebox.showwarning("警告", "請選擇要刪除的環境", parent=env_win)
                return

            if messagebox.askyesno("確認刪除", f"確定要刪除環境 '{name}' 嗎？", parent=env_win):
                config_manager.remove_environment(name)
                self.update_environment_list()
                self.current_environment.set(config_manager.current_environment or "無")
                refresh_list()
                self.update_environment_context()

        tree.bind("<Double-Button-1>", lambda event: edit_environment())

        ttk.Button(btn_frame, text="➕ 新增環境", command=add_environment, style="Accent.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="✏ 編輯環境", command=edit_environment).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="✅ 設為目前環境", command=activate_environment).pack(side=tk.LEFT, padx=5)
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

        general_frame = ttk.Frame(notebook, padding=15)
        notebook.add(general_frame, text="一般")

        row = 0
        ttk.Label(general_frame, text="預設逾時 (秒):", font=("Segoe UI", 9)).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        timeout_var = tk.StringVar(value=str(config_manager.app_config.default_timeout))
        ttk.Entry(general_frame, textvariable=timeout_var, width=10).grid(
            row=row, column=1, sticky=tk.W, pady=5
        )

        row += 1
        ttk.Label(general_frame, text="預設重試次數:", font=("Segoe UI", 9)).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        retry_var = tk.StringVar(value=str(config_manager.app_config.retry_count))
        ttk.Entry(general_frame, textvariable=retry_var, width=10).grid(
            row=row, column=1, sticky=tk.W, pady=5
        )

        row += 1
        ttk.Label(general_frame, text="最大歷史記錄:", font=("Segoe UI", 9)).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        history_var = tk.StringVar(value=str(config_manager.app_config.max_history_items))
        ttk.Entry(general_frame, textvariable=history_var, width=10).grid(
            row=row, column=1, sticky=tk.W, pady=5
        )

        network_frame = ttk.Frame(notebook, padding=15)
        notebook.add(network_frame, text="網路")

        row = 0
        ssl_var = tk.BooleanVar(value=config_manager.app_config.verify_ssl)
        ttk.Checkbutton(network_frame, text="驗證 SSL 憑證", variable=ssl_var).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=5
        )

        row += 1
        proxy_var = tk.BooleanVar(value=config_manager.app_config.proxy_enabled)
        ttk.Checkbutton(network_frame, text="啟用代理伺服器", variable=proxy_var).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=5
        )

        row += 1
        ttk.Label(network_frame, text="HTTP Proxy:", font=("Segoe UI", 9)).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        http_proxy_var = tk.StringVar(value=config_manager.app_config.http_proxy or "")
        ttk.Entry(network_frame, textvariable=http_proxy_var, width=40).grid(
            row=row, column=1, sticky=tk.W, pady=5
        )

        row += 1
        ttk.Label(network_frame, text="HTTPS Proxy:", font=("Segoe UI", 9)).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        https_proxy_var = tk.StringVar(value=config_manager.app_config.https_proxy or "")
        ttk.Entry(network_frame, textvariable=https_proxy_var, width=40).grid(
            row=row, column=1, sticky=tk.W, pady=5
        )

        log_frame = ttk.Frame(notebook, padding=15)
        notebook.add(log_frame, text="日誌")

        row = 0
        ttk.Label(log_frame, text="日誌等級:", font=("Segoe UI", 9)).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        log_level_var = tk.StringVar(value=config_manager.app_config.log_level)
        log_combo = ttk.Combobox(
            log_frame,
            textvariable=log_level_var,
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            state="readonly",
        )
        log_combo.grid(row=row, column=1, sticky=tk.W, pady=5)

        row += 1
        ttk.Label(log_frame, text="日誌檔案:", font=("Segoe UI", 9)).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        log_file_var = tk.StringVar(value=config_manager.app_config.log_file)
        ttk.Entry(log_frame, textvariable=log_file_var, width=40).grid(
            row=row, column=1, sticky=tk.W, pady=5)

        def save_settings():
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
            except ValueError as error:
                messagebox.showerror("錯誤", f"設定值無效: {error}")

        btn_frame = ttk.Frame(settings_win)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_frame, text="儲存", command=save_settings, style="Accent.TButton").pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=settings_win.destroy).pack(side=tk.RIGHT, padx=5)
