"""
API Client Orchestrator - 核心業務邏輯層
提供 HTTP 請求協調與處理功能
"""
import time
from typing import Tuple, Dict, Optional, Any

from core.http_client import HttpClient, HttpRequest, HttpResponse
from core.logger import get_logger
from core.exceptions import ApiClientError, ValidationError
from config.settings import config_manager

logger = get_logger(__name__)


class ApiClientOrchestrator:
    """
    API 請求協調器
    
    職責:
    - 協調 HTTP 請求的發送
    - 整合配置管理器
    """
    
    def __init__(self):
        self._client = HttpClient(
            verify_ssl=config_manager.app_config.verify_ssl,
            proxies=self._build_proxies()
        )
    
    def _build_proxies(self) -> Dict[str, str]:
        """構建代理設定"""
        proxies = {}
        config = config_manager.app_config
        
        if config.proxy_enabled:
            if config.http_proxy:
                proxies['http'] = config.http_proxy
            if config.https_proxy:
                proxies['https'] = config.https_proxy
        
        return proxies
    
    def send_request_new(
        self,
        method: str,
        url: str,
        headers_text: str = "",
        body_text: str = "",
        timeout: int = None,
        retry_count: int = None
    ):
        """
        使用新架構發送 HTTP 請求
        
        Args:
            method: HTTP 方法
            url: 目標 URL
            headers_text: 標頭文字
            body_text: 請求主體
            timeout: 逾時時間
            retry_count: 重試次數
            
        Returns:
            HttpResponse 物件
        """
        config = config_manager.app_config
        
        if timeout is None:
            timeout = config.default_timeout
        if retry_count is None:
            retry_count = config.retry_count
        
        # 解析 URL
        resolved_url = config_manager.resolve_url(url)
        resolved_headers_text = config_manager.apply_environment_variables(headers_text)
        resolved_body_text = config_manager.apply_environment_variables(body_text)
        
        # 解析標頭
        headers = HttpClient.parse_headers(resolved_headers_text)
        
        # 套用環境預設標頭
        env = config_manager.get_current_environment()
        if env and env.headers:
            for key, value in env.headers.items():
                if key not in headers:
                    headers[key] = value
        
        # 套用認證標頭
        auth_headers = config_manager.get_auth_headers()
        headers.update(auth_headers)
        
        # 建立請求
        request = HttpRequest(
            method=method.upper(),
            url=resolved_url,
            headers=headers,
            body=resolved_body_text if resolved_body_text else None,
            timeout=timeout,
            verify_ssl=config.verify_ssl,
            retry_count=retry_count,
            retry_delay=config.retry_delay
        )
        
        return self._client.send(request)
    
    def close(self):
        """關閉客戶端連線"""
        if self._client:
            self._client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
