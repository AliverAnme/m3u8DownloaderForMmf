"""
安全配置和验证模块 - 处理输入验证、安全检查和配置管理
"""

import os
import re
import json
import hashlib
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse
import logging


class SecurityValidator:
    """安全验证器"""

    # 安全配置
    MAX_FILENAME_LENGTH = 255
    MAX_PATH_LENGTH = 4096
    MAX_URL_LENGTH = 2048
    MAX_TITLE_LENGTH = 500
    MAX_DESCRIPTION_LENGTH = 5000

    # 允许的文件扩展名
    ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm'}
    ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}

    # 危险字符模式
    DANGEROUS_CHARS = re.compile(r'[<>:"|?*\x00-\x1f]')
    PATH_TRAVERSAL = re.compile(r'\.\.[\\/]')

    @classmethod
    def validate_video_id(cls, video_id: str) -> bool:
        """验证视频ID"""
        if not video_id or not isinstance(video_id, str):
            return False

        # 检查长度
        if len(video_id) > 100:
            return False

        # 检查字符：只允许字母、数字、下划线、连字符
        if not re.match(r'^[a-zA-Z0-9_-]+$', video_id):
            return False

        return True

    @classmethod
    def validate_url(cls, url: str) -> bool:
        """验证URL"""
        if not url or not isinstance(url, str):
            return False

        # 检查长度
        if len(url) > cls.MAX_URL_LENGTH:
            return False

        # 解析URL
        try:
            parsed = urlparse(url)

            # 检查协议
            if parsed.scheme not in ('http', 'https'):
                return False

            # 检查主机名
            if not parsed.netloc:
                return False

            # 检查是否有危险字符
            if cls.DANGEROUS_CHARS.search(url):
                return False

            return True

        except Exception:
            return False

    @classmethod
    def validate_file_path(cls, file_path: str, base_dir: str = None) -> bool:
        """验证文件路径"""
        if not file_path or not isinstance(file_path, str):
            return False

        # 检查长度
        if len(file_path) > cls.MAX_PATH_LENGTH:
            return False

        # 检查路径遍历
        if cls.PATH_TRAVERSAL.search(file_path):
            return False

        # 规范化路径
        try:
            normalized_path = os.path.normpath(file_path)
            abs_path = os.path.abspath(normalized_path)

            # 如果指定了基础目录，检查是否在允许范围内
            if base_dir:
                abs_base = os.path.abspath(base_dir)
                if not abs_path.startswith(abs_base):
                    return False

            return True

        except Exception:
            return False

    @classmethod
    def validate_filename(cls, filename: str) -> bool:
        """验证文件名"""
        if not filename or not isinstance(filename, str):
            return False

        # 检查长度
        if len(filename) > cls.MAX_FILENAME_LENGTH:
            return False

        # 检查危险字符
        if cls.DANGEROUS_CHARS.search(filename):
            return False

        # 检查保留名称（Windows）
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5',
            'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4',
            'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }

        name_without_ext = os.path.splitext(filename)[0].upper()
        if name_without_ext in reserved_names:
            return False

        return True

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """清理文件名"""
        if not filename:
            return "untitled"

        # 移除危险字符
        safe_name = cls.DANGEROUS_CHARS.sub('_', filename)

        # 限制长度
        if len(safe_name) > cls.MAX_FILENAME_LENGTH:
            name, ext = os.path.splitext(safe_name)
            max_name_len = cls.MAX_FILENAME_LENGTH - len(ext)
            safe_name = name[:max_name_len] + ext

        # 确保不为空
        if not safe_name.strip():
            safe_name = "untitled"

        return safe_name

    @classmethod
    def validate_text_content(cls, text: str, max_length: int = None) -> bool:
        """验证文本内容"""
        if not isinstance(text, str):
            return False

        # 检查长度
        if max_length and len(text) > max_length:
            return False

        # 检查是否包含null字节
        if '\x00' in text:
            return False

        return True

    @classmethod
    def validate_file_extension(cls, filename: str, allowed_extensions: set = None) -> bool:
        """验证文件扩展名"""
        if not filename:
            return False

        ext = os.path.splitext(filename)[1].lower()

        if allowed_extensions is None:
            allowed_extensions = cls.ALLOWED_VIDEO_EXTENSIONS | cls.ALLOWED_IMAGE_EXTENSIONS

        return ext in allowed_extensions

    @classmethod
    def check_file_size(cls, file_path: str, max_size_bytes: int = None) -> bool:
        """检查文件大小"""
        try:
            if not os.path.exists(file_path):
                return False

            file_size = os.path.getsize(file_path)

            if max_size_bytes and file_size > max_size_bytes:
                return False

            return True

        except Exception:
            return False


class ConfigurationManager:
    """配置管理器"""

    def __init__(self, config_file: str = "security_config.json"):
        self.config_file = config_file
        self.config = self._load_config()
        self.logger = logging.getLogger(__name__)

    def _load_config(self) -> Dict[str, Any]:
        """加载安全配置"""
        default_config = {
            "security": {
                "max_file_size_gb": 5,
                "max_concurrent_downloads": 3,
                "download_timeout_seconds": 3600,
                "upload_timeout_seconds": 7200,
                "max_retry_attempts": 3,
                "rate_limit_requests_per_minute": 60,
                "allowed_domains": [
                    "memefans.ai",
                    "api.memefans.ai"
                ],
                "blocked_extensions": [
                    ".exe", ".bat", ".cmd", ".scr", ".com", ".pif"
                ]
            },
            "logging": {
                "max_log_size_mb": 50,
                "log_retention_days": 30,
                "log_sensitive_data": False
            },
            "database": {
                "backup_interval_hours": 24,
                "max_database_size_mb": 1000,
                "vacuum_interval_days": 7
            },
            "cloud_storage": {
                "connection_timeout_seconds": 30,
                "upload_chunk_size_mb": 10,
                "max_upload_retries": 3,
                "verify_ssl": True
            }
        }

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # 合并配置
                    self._merge_config(default_config, loaded_config)
                    return default_config
            except Exception as e:
                self.logger.error(f"加载配置文件失败: {e}")

        # 保存默认配置
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"保存配置文件失败: {e}")

        return default_config

    def _merge_config(self, default: dict, loaded: dict):
        """合并配置"""
        for key, value in loaded.items():
            if key in default:
                if isinstance(value, dict) and isinstance(default[key], dict):
                    self._merge_config(default[key], value)
                else:
                    default[key] = value

    def get(self, path: str, default: Any = None) -> Any:
        """获取配置值"""
        keys = path.split('.')
        current = self.config

        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default

    def set(self, path: str, value: Any) -> bool:
        """设置配置值"""
        try:
            keys = path.split('.')
            current = self.config

            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]

            current[keys[-1]] = value
            return self._save_config()

        except Exception as e:
            self.logger.error(f"设置配置失败: {e}")
            return False

    def _save_config(self) -> bool:
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            self.logger.error(f"保存配置失败: {e}")
            return False

    def validate_config(self) -> List[str]:
        """验证配置"""
        errors = []

        # 验证安全配置
        security_config = self.config.get('security', {})

        max_file_size = security_config.get('max_file_size_gb')
        if not isinstance(max_file_size, (int, float)) or max_file_size <= 0:
            errors.append("security.max_file_size_gb 必须是正数")

        max_concurrent = security_config.get('max_concurrent_downloads')
        if not isinstance(max_concurrent, int) or max_concurrent <= 0:
            errors.append("security.max_concurrent_downloads 必须是正整数")

        # 验证域名列表
        allowed_domains = security_config.get('allowed_domains', [])
        if not isinstance(allowed_domains, list):
            errors.append("security.allowed_domains 必须是列表")
        else:
            for domain in allowed_domains:
                if not isinstance(domain, str) or not domain.strip():
                    errors.append(f"无效的域名: {domain}")

        return errors


class RateLimiter:
    """速率限制器"""

    def __init__(self, max_requests: int = 60, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = {}
        self.logger = logging.getLogger(__name__)

    def is_allowed(self, identifier: str) -> bool:
        """检查是否允许请求"""
        import time
        current_time = time.time()

        if identifier not in self.requests:
            self.requests[identifier] = []

        # 清理过期的请求记录
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if current_time - req_time < self.time_window
        ]

        # 检查是否超过限制
        if len(self.requests[identifier]) >= self.max_requests:
            self.logger.warning(f"速率限制触发: {identifier}")
            return False

        # 记录当前请求
        self.requests[identifier].append(current_time)
        return True

    def get_remaining_requests(self, identifier: str) -> int:
        """获取剩余请求数"""
        import time
        current_time = time.time()

        if identifier not in self.requests:
            return self.max_requests

        # 清理过期的请求记录
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if current_time - req_time < self.time_window
        ]

        return max(0, self.max_requests - len(self.requests[identifier]))


class SecurityAudit:
    """安全审计"""

    def __init__(self, log_file: str = "security_audit.log"):
        self.log_file = log_file
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """设置审计日志记录器"""
        logger = logging.getLogger('security_audit')
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            from logging.handlers import RotatingFileHandler
            handler = RotatingFileHandler(
                self.log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            formatter = logging.Formatter(
                '%(asctime)s - SECURITY - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def log_security_event(self, event_type: str, details: str, severity: str = "INFO"):
        """记录安全事件"""
        message = f"[{event_type}] {details}"

        if severity == "CRITICAL":
            self.logger.critical(message)
        elif severity == "ERROR":
            self.logger.error(message)
        elif severity == "WARNING":
            self.logger.warning(message)
        else:
            self.logger.info(message)

    def log_file_access(self, file_path: str, operation: str, user: str = "system"):
        """记录文件访问"""
        self.log_security_event(
            "FILE_ACCESS",
            f"User: {user}, Operation: {operation}, File: {file_path}"
        )

    def log_network_request(self, url: str, method: str = "GET", user: str = "system"):
        """记录网络请求"""
        self.log_security_event(
            "NETWORK_REQUEST",
            f"User: {user}, Method: {method}, URL: {url}"
        )

    def log_authentication_attempt(self, user: str, success: bool, source: str = "local"):
        """记录认证尝试"""
        status = "SUCCESS" if success else "FAILURE"
        self.log_security_event(
            "AUTH_ATTEMPT",
            f"User: {user}, Status: {status}, Source: {source}",
            "WARNING" if not success else "INFO"
        )

    def log_data_access(self, data_type: str, operation: str, user: str = "system"):
        """记录数据访问"""
        self.log_security_event(
            "DATA_ACCESS",
            f"User: {user}, Operation: {operation}, Type: {data_type}"
        )
