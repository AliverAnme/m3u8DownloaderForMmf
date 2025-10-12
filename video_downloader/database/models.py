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
    # id: str
    title: str                    # 视频标题（从description中提取）
    video_date: str              # 视频日期（4位数字）
    cover: str                   # 封面图片链接
    url: Optional[str]           # m3u8音视频流链接（可为空）
    description: str             # 原始视频描述
    uid: Optional[str] = None    # 视频UID（从JSON数据中提取）
    download: bool = False       # 下载状态（默认false，本地存在则为true）
    is_primer: bool = False      # 付费标识（url为空则true，否则false）
    author: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

        # 如果有UID，则使用UID生成新的URL格式
        if not self.url:
            self.is_primer = False  # 有UID的视频不是付费内容
        else:
            # 自动设置is_primer字段
            self.is_primer = not bool(self.url)
    @classmethod
    def from_api_data(cls, item_data) -> 'VideoRecord':
        """从API数据创建VideoRecord实例"""
        # 数据类型验证
        if not isinstance(item_data, dict):
            raise ValueError(f"期望字典类型，但收到 {type(item_data).__name__}: {item_data}")

        # 检查必要字段是否存在
        if not item_data:
            raise ValueError("API数据为空")
        id = item_data.get("id")
        title_temp = item_data.get("title")
        description = item_data.get('description', '')
        cover = item_data.get('cover', '')
        url = item_data.get('url', '')
        uid = item_data.get('uid', '')
        if not url:
            url = f"https://videodelivery.net/{uid}/manifest/video.m3u8"

        author_dict = item_data.get('author', {})
        author = author_dict.get('name', '')

        # 增强的description验证
        if not description or not isinstance(description, str):
            # 尝试从其他字段获取描述信息
            description_candidates = [
                item_data.get('title', ''),
                item_data.get('content', ''),
                item_data.get('text', ''),
                str(item_data.get('desc', ''))
            ]
            description = next((desc for desc in description_candidates
                                if desc and isinstance(desc, str) and len(desc.strip()) > 0), '')

            if not description:
                raise ValueError("无法找到有效的描述信息")

        # 提取title：截取description中"开头至第一个空格#"的内容
        title = cls._extract_title(description)

        # 如果标题提取失败或为空，再次尝试其他方法
        if not title or len(title.strip()) == 0:
            # 尝试更宽松的提取方法
            title = cls._extract_title_fallback(description)

        # 如果标题提取失败或为空，再次尝试其他方法
        if not title or len(title.strip()) == 0:
            title = title_temp
        # 提取video_date：从title中提取"连续4位数字"
        video_date = cls._extract_video_date(title)

        if not video_date:
            video_date = "0000"

        # 提取uid：从item_data中提取uid字段
        uid = item_data.get('uid', '')

        if not title or len(title.strip()) == 0:
            title = uid

        print(f"{id}")
        return cls(
            title=title,
            video_date=video_date,
            cover=cover,
            url=url,
            description=description,
            uid=uid,
            author=author
        )


    @staticmethod
    def _clean_title(title: str) -> str:
        """
        清理标题，去除换行符、多余空白符和特定标签

        Args:
            title (str): 原始标题

        Returns:
            str: 清理后的标题
        """
        if not title:
            return ""

        # 去除换行符和回车符
        title = title.replace('\n', '').replace('\r', '')

        # 去除多余的空白符（包括制表符等）
        title = re.sub(r'\s+', ' ', title)

        # 去除所有#标签（包括#逆愛等）
        title = re.sub(r'#[^\s]*', '', title)

        # 去除首尾空白
        title = title.strip()

        # 去除连续的空格
        title = re.sub(r'\s{2,}', ' ', title)

        return title

    @staticmethod
    def _extract_title(description: str) -> str:
        """从描述中提取标题"""
        if not description:
            return ""

        # 查找第一个" #"的位置
        hash_index = description.find(' #')
        if hash_index != -1:
            raw_title = description[:hash_index].strip()
        else:
            # 如果没有找到" #"，返回整个描述作为标题
            raw_title = description.strip()

        # 应用标题清理
        return VideoRecord._clean_title(raw_title)

    @staticmethod
    def _extract_title_fallback(description: str) -> str:
        """从描述中提取标题的备用方法"""
        if not description:
            return ""

        # 直接返回清理后的描述作为标题
        return VideoRecord._clean_title(description)

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

    @staticmethod
    def _extract_uid(description: str) -> str:
        """从描述中提取UID"""
        if not description:
            return ""

        # 查找"uid="及其后的内容
        match = re.search(r'uid=([^&\s]+)', description)
        if match:
            return match.group(1)
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
            'uid': self.uid,
            'download': self.download,
            'is_primer': self.is_primer,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
