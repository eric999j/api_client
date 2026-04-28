"""
自定義例外類別
提供結構化的錯誤處理
"""


class ApiClientError(Exception):
    """API Client 基礎例外"""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "UNKNOWN_ERROR"
        self.details = details or {}
    
    def to_dict(self) -> dict:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }


class RequestError(ApiClientError):
    """HTTP 請求相關錯誤"""
    
    def __init__(self, message: str, status_code: int = None, 
                 response_body: str = None, **kwargs):
        super().__init__(message, **kwargs)
        self.status_code = status_code
        self.response_body = response_body


class ValidationError(ApiClientError):
    """驗證錯誤"""
    
    def __init__(self, message: str, field: str = None, **kwargs):
        super().__init__(message, error_code="VALIDATION_ERROR", **kwargs)
        self.field = field


class ConfigurationError(ApiClientError):
    """配置錯誤"""
    
    def __init__(self, message: str, config_key: str = None, **kwargs):
        super().__init__(message, error_code="CONFIGURATION_ERROR", **kwargs)
        self.config_key = config_key


class AuthenticationError(ApiClientError):
    """認證錯誤"""
    
    def __init__(self, message: str, auth_type: str = None, **kwargs):
        super().__init__(message, error_code="AUTHENTICATION_ERROR", **kwargs)
        self.auth_type = auth_type


class ConnectionError(ApiClientError):
    """連線錯誤"""
    
    def __init__(self, message: str, host: str = None, **kwargs):
        super().__init__(message, error_code="CONNECTION_ERROR", **kwargs)
        self.host = host


class TimeoutError(ApiClientError):
    """逾時錯誤"""
    
    def __init__(self, message: str, timeout_seconds: float = None, **kwargs):
        super().__init__(message, error_code="TIMEOUT_ERROR", **kwargs)
        self.timeout_seconds = timeout_seconds


class SSLError(ApiClientError):
    """SSL 憑證錯誤"""
    
    def __init__(self, message: str, cert_info: str = None, **kwargs):
        super().__init__(message, error_code="SSL_ERROR", **kwargs)
        self.cert_info = cert_info
