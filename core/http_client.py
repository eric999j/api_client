"""
HTTP 客戶端模組
提供企業級的 HTTP 請求處理功能
"""
import requests
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional, Any, Tuple, List
from urllib.parse import urlparse

from .logger import get_logger
from .exceptions import (
    RequestError, ValidationError, ConnectionError, 
    TimeoutError, SSLError, AuthenticationError
)

logger = get_logger(__name__)


@dataclass
class HttpResponse:
    """HTTP 響應資料類別"""
    status_code: int
    content: str
    headers: Dict[str, str]
    elapsed_time: float  # 秒
    content_size: int  # bytes
    request_id: str
    error: Optional[str] = None
    
    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300
    
    @property
    def is_client_error(self) -> bool:
        return 400 <= self.status_code < 500
    
    @property
    def is_server_error(self) -> bool:
        return 500 <= self.status_code < 600
    
    def to_dict(self) -> dict:
        return {
            'status_code': self.status_code,
            'content': self.content,
            'headers': self.headers,
            'elapsed_time_ms': self.elapsed_time * 1000,
            'content_size': self.content_size,
            'request_id': self.request_id,
            'error': self.error
        }


@dataclass
class HttpRequest:
    """HTTP 請求資料類別"""
    method: str
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[str] = None
    timeout: int = 30
    verify_ssl: bool = True
    follow_redirects: bool = True
    max_redirects: int = 10
    retry_count: int = 0
    retry_delay: float = 1.0
    
    def validate(self) -> None:
        """驗證請求參數"""
        valid_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
        
        if not self.method:
            raise ValidationError("HTTP 方法不能為空", field="method")
        
        if self.method.upper() not in valid_methods:
            raise ValidationError(
                f"不支援的 HTTP 方法: {self.method}", 
                field="method",
                details={"valid_methods": valid_methods}
            )
        
        if not self.url:
            raise ValidationError("URL 不能為空", field="url")
        
        parsed = urlparse(self.url)
        if not parsed.scheme:
            raise ValidationError("URL 必須包含協議 (http:// 或 https://)", field="url")
        
        if parsed.scheme not in ['http', 'https']:
            raise ValidationError(
                f"不支援的協議: {parsed.scheme}", 
                field="url",
                details={"supported_schemes": ["http", "https"]}
            )
        
        if self.timeout <= 0:
            raise ValidationError("逾時時間必須大於 0", field="timeout")
        
        if self.timeout > 300:
            raise ValidationError("逾時時間不能超過 300 秒", field="timeout")


class HttpClient:
    """
    企業級 HTTP 客戶端
    
    功能特點:
    - 請求 ID 追蹤
    - 自動重試機制
    - 結構化錯誤處理
    - 詳細日誌記錄
    - SSL 憑證驗證選項
    - Proxy 支援
    """
    
    SUPPORTED_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
    
    def __init__(
        self,
        default_headers: Dict[str, str] = None,
        verify_ssl: bool = True,
        proxies: Dict[str, str] = None
    ):
        self.default_headers = default_headers or {}
        self.verify_ssl = verify_ssl
        self.proxies = proxies or {}
        self.session = requests.Session()
        
        # 設定預設 headers
        self.session.headers.update(self.default_headers)
    
    def send(self, request: HttpRequest) -> HttpResponse:
        """
        發送 HTTP 請求
        
        Args:
            request: HttpRequest 物件
            
        Returns:
            HttpResponse 物件
        """
        request_id = str(uuid.uuid4())
        request.validate()
        
        logger.info(
            f"發送請求 [{request_id}]: {request.method} {request.url}",
            extra={
                'request_id': request_id,
                'http_method': request.method,
                'url': request.url
            }
        )
        
        attempt = 0
        last_error = None
        
        while attempt <= request.retry_count:
            if attempt > 0:
                logger.warning(f"重試請求 [{request_id}] (嘗試 {attempt + 1}/{request.retry_count + 1})")
                time.sleep(request.retry_delay)
            
            try:
                response = self._execute_request(request, request_id)
                
                logger.info(
                    f"請求完成 [{request_id}]: {response.status_code} ({response.elapsed_time*1000:.0f}ms)",
                    extra={
                        'request_id': request_id,
                        'status_code': response.status_code,
                        'response_time': response.elapsed_time * 1000
                    }
                )
                
                return response
                
            except (ConnectionError, TimeoutError) as e:
                last_error = e
                attempt += 1
                if attempt <= request.retry_count:
                    logger.warning(f"請求失敗 [{request_id}]，準備重試: {e.message}")
                continue
            except Exception as e:
                # 其他錯誤不重試
                raise
        
        # 所有重試都失敗
        logger.error(f"請求失敗 [{request_id}]: 已達最大重試次數")
        return HttpResponse(
            status_code=0,
            content="",
            headers={},
            elapsed_time=0,
            content_size=0,
            request_id=request_id,
            error=str(last_error) if last_error else "未知錯誤"
        )
    
    def _execute_request(self, request: HttpRequest, request_id: str) -> HttpResponse:
        """執行實際的 HTTP 請求"""
        start_time = time.perf_counter()
        
        try:
            # 合併 headers
            headers = {**self.default_headers, **request.headers}
            
            # 準備請求資料
            data = request.body.encode('utf-8') if request.body else None
            
            response = self.session.request(
                method=request.method.upper(),
                url=request.url,
                headers=headers,
                data=data,
                timeout=request.timeout,
                verify=request.verify_ssl if request.verify_ssl else self.verify_ssl,
                proxies=self.proxies if self.proxies else None,
                allow_redirects=request.follow_redirects
            )
            
            elapsed_time = time.perf_counter() - start_time
            
            return HttpResponse(
                status_code=response.status_code,
                content=response.text,
                headers=dict(response.headers),
                elapsed_time=elapsed_time,
                content_size=len(response.content),
                request_id=request_id
            )
            
        except requests.exceptions.Timeout as e:
            elapsed_time = time.perf_counter() - start_time
            raise TimeoutError(
                f"請求逾時 (>{request.timeout}秒)",
                timeout_seconds=request.timeout
            )
            
        except requests.exceptions.SSLError as e:
            elapsed_time = time.perf_counter() - start_time
            raise SSLError(
                f"SSL 憑證驗證失敗: {str(e)}",
                cert_info=str(e)
            )
            
        except requests.exceptions.ConnectionError as e:
            elapsed_time = time.perf_counter() - start_time
            parsed = urlparse(request.url)
            raise ConnectionError(
                f"無法連線到 {parsed.netloc}",
                host=parsed.netloc
            )
            
        except requests.exceptions.RequestException as e:
            elapsed_time = time.perf_counter() - start_time
            raise RequestError(
                f"請求失敗: {str(e)}",
                error_code="REQUEST_FAILED"
            )
    
    @staticmethod
    def parse_headers(headers_text: str) -> Dict[str, str]:
        """解析標頭文字為字典"""
        headers = {}
        if not headers_text:
            return headers
        
        for line in headers_text.strip().split('\n'):
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                if key:
                    headers[key] = value
        
        return headers
    
    def close(self):
        """關閉 HTTP 客戶端"""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
