"""
日誌記錄模組
提供結構化的日誌記錄功能
"""
import logging
import logging.handlers
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
import sys


class JsonFormatter(logging.Formatter):
    """JSON 格式的日誌格式器 - 適合商業應用的日誌分析"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # 添加額外資訊
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        
        if hasattr(record, 'user_action'):
            log_data['user_action'] = record.user_action
        
        if hasattr(record, 'http_method'):
            log_data['http_method'] = record.http_method
            
        if hasattr(record, 'url'):
            log_data['url'] = record.url
            
        if hasattr(record, 'status_code'):
            log_data['status_code'] = record.status_code
            
        if hasattr(record, 'response_time'):
            log_data['response_time_ms'] = record.response_time
        
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """控制台友善的格式器"""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        
        # 基本格式
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        base_msg = f"{timestamp} | {record.levelname:8s} | {record.name} | {record.getMessage()}"
        
        # 添加顏色 (僅在支援的終端)
        if sys.stdout.isatty():
            return f"{color}{base_msg}{self.RESET}"
        return base_msg


class RequestLogger(logging.LoggerAdapter):
    """請求專用的日誌記錄器"""
    
    def process(self, msg, kwargs):
        extra = kwargs.get('extra', {})
        extra.update(self.extra)
        kwargs['extra'] = extra
        return msg, kwargs


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_max_size: int = 10 * 1024 * 1024,
    log_backup_count: int = 5,
    json_format: bool = True
) -> None:
    """
    設定日誌系統
    
    Args:
        log_level: 日誌等級 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日誌檔案路徑 (None 表示僅控制台輸出)
        log_max_size: 單一日誌檔案最大大小 (bytes)
        log_backup_count: 保留的備份檔案數量
        json_format: 檔案日誌是否使用 JSON 格式
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # 清除現有的 handlers
    root_logger.handlers.clear()
    
    # 控制台 Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ConsoleFormatter())
    console_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    
    # 檔案 Handler (如果指定了檔案)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=log_max_size,
            backupCount=log_backup_count,
            encoding='utf-8'
        )
        
        if json_format:
            file_handler.setFormatter(JsonFormatter())
        else:
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
            ))
        
        file_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)


def get_logger(name: str, request_id: str = None) -> logging.Logger:
    """
    取得日誌記錄器
    
    Args:
        name: 記錄器名稱 (通常使用 __name__)
        request_id: 可選的請求 ID 用於追蹤
    
    Returns:
        設定好的日誌記錄器
    """
    logger = logging.getLogger(name)
    
    if request_id:
        return RequestLogger(logger, {'request_id': request_id})
    
    return logger
