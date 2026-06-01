"""
應用程式配置設定模組
提供集中化的配置管理，支援環境變數覆寫
"""
import os
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path
import json

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

logger = logging.getLogger(__name__)

KEYRING_SERVICE = "api_client"


@dataclass
class AppConfig:
    """應用程式主配置"""
    app_name: str = "API Client - Enterprise Edition"
    version: str = "2.0.0"
    window_width: int = 1200
    window_height: int = 900
    
    # 預設請求設定
    default_timeout: int = 30
    max_timeout: int = 300
    retry_count: int = 3
    retry_delay: float = 1.0
    
    # 歷史記錄設定
    max_history_items: int = 100
    history_file: str = "api_client_history.json"
    current_environment: Optional[str] = None
    
    # 日誌設定
    log_level: str = "INFO"
    log_file: str = "api_client.log"
    log_max_size: int = 10 * 1024 * 1024  # 10MB
    log_backup_count: int = 5
    
    # UI 設定
    font_family: str = "Segoe UI"
    mono_font_family: str = "Consolas"
    font_size: int = 10
    theme: str = "light"
    
    # SSL 設定
    verify_ssl: bool = True
    ssl_cert_path: Optional[str] = None
    
    # Proxy 設定
    proxy_enabled: bool = False
    http_proxy: Optional[str] = None
    https_proxy: Optional[str] = None
    no_proxy: Optional[str] = None


@dataclass
class Environment:
    """環境配置 - 用於管理多個測試環境"""
    name: str
    base_url: str
    variables: Dict[str, str] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    auth_type: Optional[str] = None  # bearer, basic, api_key
    auth_value: Optional[str] = None
    description: str = ""


class ConfigManager:
    """配置管理器 - 負責載入、保存和管理配置"""
    
    _instance = None
    _config_dir = Path.home() / ".api_client"
    _config_file = _config_dir / "config.json"
    _environments_file = _config_dir / "environments.json"
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._config_dir.mkdir(parents=True, exist_ok=True)
        
        self.app_config = self._load_app_config()
        self.environments: Dict[str, Environment] = self._load_environments()
        configured_environment = self.app_config.current_environment
        self.current_environment: Optional[str] = (
            configured_environment if configured_environment in self.environments else None
        )
        self.app_config.current_environment = self.current_environment
        
        # 載入環境變數覆寫
        self._apply_env_overrides()
    
    def _load_app_config(self) -> AppConfig:
        """載入應用程式配置"""
        if self._config_file.exists():
            try:
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return AppConfig(**{k: v for k, v in data.items() 
                                       if k in AppConfig.__dataclass_fields__})
            except Exception:
                logger.warning("無法載入配置檔 %s，使用預設值", self._config_file, exc_info=True)
        return AppConfig()
    
    def _load_environments(self) -> Dict[str, Environment]:
        """載入環境配置"""
        environments = {}
        if self._environments_file.exists():
            try:
                with open(self._environments_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for name, env_data in data.items():
                        auth_value = self._load_credential(name) or env_data.get('auth_value')
                        environments[name] = Environment(
                            name=name,
                            base_url=env_data.get('base_url', ''),
                            variables=env_data.get('variables', {}),
                            headers=env_data.get('headers', {}),
                            auth_type=env_data.get('auth_type'),
                            auth_value=auth_value,
                            description=env_data.get('description', '')
                        )
            except Exception:
                logger.warning("無法載入環境配置檔 %s，使用預設環境", self._environments_file, exc_info=True)
        
        # 預設環境
        if not environments:
            environments['Development'] = Environment(
                name='Development',
                base_url='http://localhost:8080',
                description='本地開發環境'
            )
            environments['Staging'] = Environment(
                name='Staging',
                base_url='https://staging.example.com',
                description='測試環境'
            )
            environments['Production'] = Environment(
                name='Production',
                base_url='https://api.example.com',
                description='生產環境'
            )
        
        return environments
    
    def _apply_env_overrides(self):
        """從環境變數套用配置覆寫"""
        env_mappings = {
            'API_CLIENT_TIMEOUT': ('default_timeout', int),
            'API_CLIENT_LOG_LEVEL': ('log_level', str),
            'API_CLIENT_VERIFY_SSL': ('verify_ssl', lambda x: x.lower() == 'true'),
            'HTTP_PROXY': ('http_proxy', str),
            'HTTPS_PROXY': ('https_proxy', str),
            'NO_PROXY': ('no_proxy', str),
        }
        
        for env_key, (config_key, converter) in env_mappings.items():
            value = os.environ.get(env_key)
            if value:
                try:
                    setattr(self.app_config, config_key, converter(value))
                except (ValueError, TypeError):
                    logger.warning("環境變數 %s 值無效: %s", env_key, value)
    
    def save_config(self):
        """保存應用程式配置"""
        try:
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(self.app_config.__dict__, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise RuntimeError(f"無法保存配置: {e}")
    
    def save_environments(self):
        """保存環境配置（憑證存入系統金鑰庫）"""
        try:
            data = {}
            for name, env in self.environments.items():
                self._save_credential(name, env.auth_value)
                data[name] = {
                    'base_url': env.base_url,
                    'variables': env.variables,
                    'headers': env.headers,
                    'auth_type': env.auth_type,
                    'auth_value': env.auth_value if not KEYRING_AVAILABLE else None,
                    'description': env.description
                }
            with open(self._environments_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise RuntimeError(f"無法保存環境配置: {e}")

    def _save_credential(self, env_name: str, auth_value: Optional[str]):
        """將憑證存入系統金鑰庫"""
        if not KEYRING_AVAILABLE:
            return
        key = f"{KEYRING_SERVICE}:env:{env_name}"
        try:
            if auth_value:
                keyring.set_password(KEYRING_SERVICE, key, auth_value)
            else:
                keyring.delete_password(KEYRING_SERVICE, key)
        except keyring.errors.PasswordDeleteError:
            pass
        except Exception:
            logger.warning("無法將憑證存入金鑰庫 (env=%s)", env_name, exc_info=True)

    def _load_credential(self, env_name: str) -> Optional[str]:
        """從系統金鑰庫讀取憑證"""
        if not KEYRING_AVAILABLE:
            return None
        key = f"{KEYRING_SERVICE}:env:{env_name}"
        try:
            return keyring.get_password(KEYRING_SERVICE, key)
        except Exception:
            logger.warning("無法從金鑰庫讀取憑證 (env=%s)", env_name, exc_info=True)
            return None
    
    def add_environment(self, env: Environment):
        """新增環境"""
        self.environments[env.name] = env
        self.save_environments()
    
    def remove_environment(self, name: str):
        """移除環境"""
        if name in self.environments:
            del self.environments[name]
            if self.current_environment == name:
                self.set_current_environment(None)
            self.save_environments()

    def set_current_environment(self, name: Optional[str]):
        """設定當前環境並持久化"""
        self.current_environment = name if name in self.environments else None
        self.app_config.current_environment = self.current_environment
        self.save_config()
    
    def get_current_environment(self) -> Optional[Environment]:
        """取得當前環境"""
        if self.current_environment:
            return self.environments.get(self.current_environment)
        return None

    def apply_environment_variables(self, text: str) -> str:
        """將環境變數套用到任意文字內容"""
        if not text:
            return text

        env = self.get_current_environment()
        if env and env.variables:
            for key, value in env.variables.items():
                text = text.replace(f"{{{{{key}}}}}", value)

        return text
    
    def resolve_url(self, url: str) -> str:
        """解析 URL - 替換變數並套用基礎 URL"""
        env = self.get_current_environment()

        url = self.apply_environment_variables(url)

        if not url:
            return env.base_url if env and env.base_url else url
        
        # 如果 URL 是相對路徑且有基礎 URL
        if env and not url.startswith(('http://', 'https://')):
            base = env.base_url.rstrip('/')
            path = url.lstrip('/')
            url = f"{base}/{path}"
        
        return url
    
    def get_auth_headers(self) -> Dict[str, str]:
        """取得認證標頭"""
        env = self.get_current_environment()
        if not env or not env.auth_type or not env.auth_value:
            return {}
        
        if env.auth_type == 'bearer':
            return {'Authorization': f'Bearer {env.auth_value}'}
        elif env.auth_type == 'basic':
            import base64
            encoded = base64.b64encode(env.auth_value.encode()).decode()
            return {'Authorization': f'Basic {encoded}'}
        elif env.auth_type == 'api_key':
            return {'X-API-Key': env.auth_value}
        
        return {}


# 全域配置實例
config_manager = ConfigManager()
