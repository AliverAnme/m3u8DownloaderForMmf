"""
数据库模型 - 定义视频记录的数据结构
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class DownloadStatus(Enum):
    """下载状态枚举"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    UPLOADED = "uploaded"


@dataclass
class VideoRecord:
    """视频记录数据模型"""
    id: str
    title: str
    url: str
    description: str
    cover: str
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    download_status: DownloadStatus = DownloadStatus.PENDING
    download_time: Optional[datetime] = None
    upload_time: Optional[datetime] = None
    cloud_path: Optional[str] = None
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'id': self.id,
            'title': self.title,
            'url': self.url,
            'description': self.description,
            'cover': self.cover,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'download_status': self.download_status.value,
            'download_time': self.download_time.isoformat() if self.download_time else None,
            'upload_time': self.upload_time.isoformat() if self.upload_time else None,
            'cloud_path': self.cloud_path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'VideoRecord':
        """从字典创建视频记录"""
        # 处理日期时间字段
        for date_field in ['download_time', 'upload_time', 'created_at', 'updated_at']:
            if data.get(date_field):
                data[date_field] = datetime.fromisoformat(data[date_field])

        # 处理下载状态枚举
        if 'download_status' in data:
            data['download_status'] = DownloadStatus(data['download_status'])

        return cls(**data)
