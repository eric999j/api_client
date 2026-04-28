"""
API Client Orchestrator - 核心業務邏輯層
提供 HTTP 請求協調與處理功能
"""
import requests
import time
from typing import Tuple, Dict, Optional, Any
from utils import parse_headers

# 嘗試匯入新架構模組，如果失敗則使用原有邏輯
try:
    from core.http_client import HttpClient, HttpRequest, HttpResponse
    from core.logger import get_logger
    from core.exceptions import ApiClientError, ValidationError
    from config.settings import config_manager
    NEW_ARCHITECTURE_AVAILABLE = True
    logger = get_logger(__name__)
except ImportError:
    NEW_ARCHITECTURE_AVAILABLE = False
    logger = None


class ApiClientOrchestrator:
    """
    API 請求協調器
    
    職責:
    - 協調 HTTP 請求的發送
    - 整合配置管理器
    - 提供向下相容的介面
    """
    
    def __init__(self):
        if NEW_ARCHITECTURE_AVAILABLE:
            self._client = HttpClient(
                verify_ssl=config_manager.app_config.verify_ssl,
                proxies=self._build_proxies()
            )
        else:
            self._client = None
    
    def _build_proxies(self) -> Dict[str, str]:
        """構建代理設定"""
        if not NEW_ARCHITECTURE_AVAILABLE:
            return {}
            
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
        if not NEW_ARCHITECTURE_AVAILABLE:
            raise RuntimeError("新架構模組未載入")
            
        config = config_manager.app_config
        
        if timeout is None:
            timeout = config.default_timeout
        if retry_count is None:
            retry_count = config.retry_count
        
        # 解析 URL
        resolved_url = config_manager.resolve_url(url)
        
        # 解析標頭
        headers = HttpClient.parse_headers(headers_text)
        
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
            body=body_text if body_text else None,
            timeout=timeout,
            verify_ssl=config.verify_ssl,
            retry_count=retry_count,
            retry_delay=config.retry_delay
        )
        
        return self._client.send(request)
    
    @staticmethod
    def send_request(
        method: str, 
        url: str, 
        headers_text: str = "", 
        body_text: str = "", 
        timeout: int = 10
    ) -> Tuple[int, str, Optional[str], float, Dict[str, str], int]:
        """
        執行 HTTP 請求並返回結果 (向下相容介面)
        
        Returns:
            Tuple: (status_code, content, error_msg, elapsed_time, response_headers, content_size)
        """
        start_time = time.perf_counter()
        elapsed_time = 0.0

        try:
            # 解析 URL (如果新架構可用)
            resolved_url = url
            if NEW_ARCHITECTURE_AVAILABLE:
                resolved_url = config_manager.resolve_url(url)
            
            # Parse headers
            headers = parse_headers(headers_text)
            
            # 套用環境標頭和認證 (如果新架構可用)
            if NEW_ARCHITECTURE_AVAILABLE:
                env = config_manager.get_current_environment()
                if env and env.headers:
                    for key, value in env.headers.items():
                        if key not in headers:
                            headers[key] = value
                auth_headers = config_manager.get_auth_headers()
                headers.update(auth_headers)
            
            data = body_text if body_text else None

            # 取得 SSL 驗證設定
            verify_ssl = True
            if NEW_ARCHITECTURE_AVAILABLE:
                verify_ssl = config_manager.app_config.verify_ssl

            response = requests.request(
                method=method,
                url=resolved_url,
                headers=headers,
                data=data.encode('utf-8') if data else None,
                timeout=timeout,
                verify=verify_ssl
            )
            elapsed_time = time.perf_counter() - start_time
            
            content_size = len(response.content)
            
            # 記錄日誌 (如果新架構可用)
            if NEW_ARCHITECTURE_AVAILABLE and logger:
                logger.info(
                    f"請求完成: {method} {resolved_url} -> {response.status_code}",
                    extra={
                        'http_method': method,
                        'url': resolved_url,
                        'status_code': response.status_code,
                        'response_time': elapsed_time * 1000
                    }
                )
            
            return response.status_code, response.text, None, elapsed_time, dict(response.headers), content_size

        except requests.exceptions.Timeout:
            elapsed_time = time.perf_counter() - start_time
            error_msg = "錯誤: 請求逾時"
            if NEW_ARCHITECTURE_AVAILABLE and logger:
                logger.error(f"請求逾時: {method} {url}")
            return 0, "", error_msg, elapsed_time, {}, 0
            
        except requests.exceptions.SSLError as e:
            elapsed_time = time.perf_counter() - start_time
            error_msg = f"錯誤: SSL 憑證驗證失敗 - {str(e)}"
            if NEW_ARCHITECTURE_AVAILABLE and logger:
                logger.error(f"SSL 錯誤: {method} {url} - {e}")
            return 0, "", error_msg, elapsed_time, {}, 0
            
        except requests.exceptions.ConnectionError:
            elapsed_time = time.perf_counter() - start_time
            error_msg = "錯誤: 連線失敗 (請檢查 URL 或網路連線)"
            if NEW_ARCHITECTURE_AVAILABLE and logger:
                logger.error(f"連線失敗: {method} {url}")
            return 0, "", error_msg, elapsed_time, {}, 0
            
        except requests.exceptions.RequestException as e:
            elapsed_time = time.perf_counter() - start_time
            error_msg = f"錯誤: {str(e)}"
            if NEW_ARCHITECTURE_AVAILABLE and logger:
                logger.error(f"請求錯誤: {method} {url} - {e}")
            return 0, "", error_msg, elapsed_time, {}, 0
            
        except Exception as e:
            elapsed_time = time.perf_counter() - start_time
            error_msg = f"未預期的錯誤: {str(e)}"
            if NEW_ARCHITECTURE_AVAILABLE and logger:
                logger.exception(f"未預期錯誤: {method} {url}")
            return 0, "", error_msg, elapsed_time, {}, 0
    
    def close(self):
        """關閉客戶端連線"""
        if self._client:
            self._client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
