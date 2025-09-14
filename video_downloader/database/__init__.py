"""
数据库模块 - 处理本地数据存储和管理
"""

from .manager import DatabaseManager
from .models import VideoRecord

__all__ = ['DatabaseManager', 'VideoRecord']
