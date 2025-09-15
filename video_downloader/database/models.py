"""
数据库模型 - 定义视频记录的数据结构
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import re


@dataclass
class VideoRecord:
    """视频记录数据模型"""
    title: str                    # 视频标题（从description中提取）
    video_date: str              # 视频日期（4位数字）
    cover: str                   # 封面图片链接
    url: Optional[str]           # m3u8音视频流链接（可为空）
    description: str             # 原始视频描述
    download: bool = False       # 下载状态（默认false，本地存在则为true）
    is_primer: bool = False      # 付费标识（url为空则true，否则false）
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

        # 自动设置is_primer字段
        self.is_primer = not bool(self.url)

    @classmethod
    def from_api_data(cls, item_data: dict) -> 'VideoRecord':
        """从API数据创建VideoRecord实例"""
        description = item_data.get('description', '')
        cover = item_data.get('cover', '')
        url = item_data.get('url', '')

        # 提取title：截取description中"开头至第一个空格#"的内容
        title = cls._extract_title(description)

        # 提取video_date：从description中提取"连续4位数字"
        video_date = cls._extract_video_date(description)

        return cls(
            title=title,
            video_date=video_date,
            cover=cover,
            url=url,
            description=description
        )

    @staticmethod
    def _extract_title(description: str) -> str:
        """从描述中提取标题"""
        if not description:
            return ""

        # 查找第一个" #"的位置
        hash_index = description.find(' #')
        if hash_index != -1:
            return description[:hash_index].strip()
        else:
            # 如果没有找到" #"，返回整个描述作为标题
            return description.strip()

    @staticmethod
    def _extract_video_date(description: str) -> str:
        """从描述中提取4位数字日期"""
        if not description:
            return ""

        # 查找连续的4位数字
        match = re.search(r'\d{4}', description)
        if match:
            return match.group()
        return ""

    def get_unique_key(self) -> str:
        """获取唯一标识键（title + video_date）"""
        return f"{self.title}_{self.video_date}"

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'title': self.title,
            'video_date': self.video_date,
            'cover': self.cover,
            'url': self.url,
            'description': self.description,
            'download': self.download,
            'is_primer': self.is_primer,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
