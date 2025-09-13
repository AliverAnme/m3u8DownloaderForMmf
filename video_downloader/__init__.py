"""
视频下载器 - 一个功能完整的m3u8视频下载工具

主要功能:
- API数据获取和处理
- 视频列表展示和选择
- m3u8视频下载和转换
- 交互式用户界面
"""

__version__ = "1.0.0"
__author__ = "Video Downloader Team"

from .core.config import Config
from .core.main import VideoDownloaderApp

__all__ = ['Config', 'VideoDownloaderApp']
