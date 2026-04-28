"""
工具函數模組
提供格式化、解析等輔助功能
"""
import json
import re
from typing import Dict, Any, Optional
from datetime import datetime


def format_json(content: str, indent: int = 4) -> str:
    """
    格式化 JSON 字串
    
    Args:
        content: 要格式化的 JSON 字串
        indent: 縮排空格數
        
    Returns:
        格式化後的 JSON 字串，如果解析失敗則返回原始內容
    """
    if not content:
        return ""
    try:
        parsed = json.loads(content)
        return json.dumps(parsed, indent=indent, ensure_ascii=False, sort_keys=False)
    except (json.JSONDecodeError, TypeError):
        return content


def minify_json(content: str) -> str:
    """
    壓縮 JSON 字串 (移除多餘空白)
    
    Args:
        content: 要壓縮的 JSON 字串
        
    Returns:
        壓縮後的 JSON 字串
    """
    if not content:
        return ""
    try:
        parsed = json.loads(content)
        return json.dumps(parsed, separators=(',', ':'), ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        return content


def parse_headers(header_text: str) -> Dict[str, str]:
    """
    解析多行標頭文字為字典
    
    Args:
        header_text: 標頭文字，格式為 "Key: Value" 每行一個
        
    Returns:
        標頭字典
    """
    headers = {}
    if not header_text:
        return headers
    
    lines = header_text.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):  # 支援註解
            continue
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            if key:
                if key in headers:
                    # 處理重複的標頭 (如多個 Cookie)
                    headers[key] = f"{headers[key]}, {value}"
                else:
                    headers[key] = value
    return headers


def headers_to_text(headers: Dict[str, str]) -> str:
    """
    將標頭字典轉換為文字格式
    
    Args:
        headers: 標頭字典
        
    Returns:
        多行文字格式的標頭
    """
    if not headers:
        return ""
    return "\n".join(f"{key}: {value}" for key, value in headers.items())


def format_size(size_bytes: int) -> str:
    """
    格式化位元組大小為人類可讀格式
    
    Args:
        size_bytes: 位元組數
        
    Returns:
        格式化後的大小字串
    """
    if size_bytes < 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} B"
    return f"{size:.2f} {units[unit_index]}"


def format_headers_display(headers_dict: Dict[str, str]) -> str:
    """
    格式化標頭字典為顯示用的多行字串
    
    Args:
        headers_dict: 標頭字典
        
    Returns:
        格式化後的多行字串
    """
    if not headers_dict:
        return "無標頭資訊"
    
    lines = []
    for key, value in headers_dict.items():
        lines.append(f"{key}: {value}")
    return "\n".join(lines)


def format_timestamp(dt: datetime = None, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化時間戳
    
    Args:
        dt: datetime 物件，預設為當前時間
        format_str: 格式化字串
        
    Returns:
        格式化後的時間字串
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime(format_str)


def validate_url(url: str) -> tuple[bool, Optional[str]]:
    """
    驗證 URL 格式
    
    Args:
        url: 要驗證的 URL
        
    Returns:
        Tuple[是否有效, 錯誤訊息]
    """
    if not url:
        return False, "URL 不能為空"
    
    url = url.strip()
    
    # 基本格式檢查
    url_pattern = re.compile(
        r'^https?://'  # http:// 或 https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # 域名
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP 地址
        r'(?::\d+)?'  # 可選的端口
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    
    if not url_pattern.match(url):
        return False, "URL 格式不正確，請確保包含 http:// 或 https://"
    
    return True, None


def validate_json(content: str) -> tuple[bool, Optional[str]]:
    """
    驗證 JSON 格式
    
    Args:
        content: 要驗證的 JSON 字串
        
    Returns:
        Tuple[是否有效, 錯誤訊息]
    """
    if not content or not content.strip():
        return True, None  # 空內容視為有效
    
    try:
        json.loads(content)
        return True, None
    except json.JSONDecodeError as e:
        return False, f"JSON 格式錯誤 (行 {e.lineno}, 列 {e.colno}): {e.msg}"


def extract_variables(text: str) -> list[str]:
    """
    從文字中提取變數 (格式: {{variable_name}})
    
    Args:
        text: 包含變數的文字
        
    Returns:
        變數名稱列表
    """
    if not text:
        return []
    
    pattern = r'\{\{(\w+)\}\}'
    matches = re.findall(pattern, text)
    return list(set(matches))


def replace_variables(text: str, variables: Dict[str, str]) -> str:
    """
    替換文字中的變數
    
    Args:
        text: 包含變數的文字
        variables: 變數字典 {name: value}
        
    Returns:
        替換後的文字
    """
    if not text or not variables:
        return text
    
    for name, value in variables.items():
        text = text.replace(f"{{{{{name}}}}}", value)
    
    return text


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    截斷文字
    
    Args:
        text: 要截斷的文字
        max_length: 最大長度
        suffix: 截斷後的後綴
        
    Returns:
        截斷後的文字
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def safe_get(data: dict, *keys, default=None) -> Any:
    """
    安全地從嵌套字典中獲取值
    
    Args:
        data: 資料字典
        *keys: 鍵的路徑
        default: 預設值
        
    Returns:
        獲取到的值或預設值
    """
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        else:
            return default
    return data


def mask_sensitive_data(text: str, patterns: list[str] = None) -> str:
    """
    遮蔽敏感資料
    
    Args:
        text: 原始文字
        patterns: 要遮蔽的模式列表
        
    Returns:
        遮蔽後的文字
    """
    if not text:
        return text
    
    if patterns is None:
        patterns = [
            r'(Authorization:\s*Bearer\s+)\S+',
            r'(Authorization:\s*Basic\s+)\S+',
            r'(X-API-Key:\s*)\S+',
            r'(password["\':\s]*)\S+',
            r'(token["\':\s]*)\S+',
            r'(secret["\':\s]*)\S+',
        ]
    
    result = text
    for pattern in patterns:
        result = re.sub(pattern, r'\1*****', result, flags=re.IGNORECASE)
    
    return result
