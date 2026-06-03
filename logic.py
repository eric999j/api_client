"""
API Client Orchestrator - 核心業務邏輯層
提供 HTTP 請求協調與處理功能
"""
from typing import Dict

from core.http_client import HttpClient, HttpRequest
from core.logger import get_logger
from config.settings import config_manager
from utils import parse_headers

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
        timeout: float = None,
        retry_count: int = None,
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

        request = self._build_http_request(
            method=method,
            url=url,
            headers_text=headers_text,
            body_text=body_text,
            timeout=timeout,
            retry_count=retry_count,
            verify_ssl=config.verify_ssl,
            retry_delay=config.retry_delay,
        )
        
        return self._client.send(request)

    def _prepare_request_parts(self, url: str, headers_text: str, body_text: str):
        """處理環境替換並組裝標頭"""
        resolved_url = config_manager.resolve_url(url)
        resolved_headers_text = config_manager.apply_environment_variables(headers_text)
        resolved_body_text = config_manager.apply_environment_variables(body_text)

        request_headers = parse_headers(resolved_headers_text)
        env = config_manager.get_current_environment()
        if env and env.headers:
            for key, value in env.headers.items():
                request_headers.setdefault(key, value)

        request_headers.update(config_manager.get_auth_headers())
        return resolved_url, request_headers, resolved_body_text

    def _build_http_request(
        self,
        method: str,
        url: str,
        headers_text: str,
        body_text: str,
        timeout: float,
        retry_count: int,
        verify_ssl: bool,
        retry_delay: float,
    ) -> HttpRequest:
        resolved_url, headers, resolved_body_text = self._prepare_request_parts(url, headers_text, body_text)
        return HttpRequest(
            method=method.upper(),
            url=resolved_url,
            headers=headers,
            body=resolved_body_text if resolved_body_text else None,
            timeout=timeout,
            verify_ssl=verify_ssl,
            retry_count=retry_count,
            retry_delay=retry_delay,
        )
    
    def close(self):
        """關閉客戶端連線"""
        if self._client:
            self._client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
