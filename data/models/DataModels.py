import os
import json
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Tuple
from data.models.FeedModels import FeedVideoItem, FeedAuthor, BindingTokenInfo

class Config:
    """
    配置类
    """
    def __init__(self):
        self.DEFAULT_HEADERS = {
        'User-Agent': 'Dart/3.9 (dart:io)',
        'Version': '1.2.9',
        'Accept-Encoding': 'gzip',
        'Build': '110',
        'Host': 'api.memefans.ai',
        'Authorization': 'Bearer 1HyC9FFPXFXXkhs1xR-wS8-Pid9Nl4SWKX2wOw1F7_s',
        'OS': 'Android',
        'Content-Type': 'application/json',
    }


@dataclass
class Author:
    """
    作者信息数据模型
    """
    id: str
    name: str
    username: str
    avatar: str
    region: str
    created_at: str
    role: str
    status: str
    invitation_id: Optional[str] = None

@dataclass
class VideoRecord:
    """
    视频记录数据模型
    """
    # 必需参数（无默认值）
    type: str
    title: str
    cover: str
    url: str
    url_type: str
    description: str
    status: str
    id: str
    created_at: str
    updated_at: str
    comments_count: int
    likes_count: int
    collections_count: int
    processing_status: str
    region: str
    width: int
    height: int
    is_locked: bool
    holdview_amount: str
    free_seconds: int
    author: Author
    # uid: str
    is_liked: bool
    is_in_collection: bool
    is_favorite: bool
    # 可选参数（有默认值）
    uid: str = ''
    tags: List[str] = field(default_factory=list)
    upload_url: Optional[str] = None
    binding_token_info: BindingTokenInfo | None= None
    shoot_period: str = '0000'
    video_date: str = ''


@dataclass
class CollectionData:
    """
    集合数据完整模型
    """
    id: str
    type: str
    status: str
    created_at: str
    updated_at: str
    region: str
    author_id: str
    title: str
    description: str
    cover: str
    original_cover: str
    subscriber_count: int
    contributor_count: int
    content_type: str
    contents_count: int
    contents: List[str] = field(default_factory=list)
    carnival_status: Optional[str] = None
    carnival_start_time: Optional[str] = None
    is_subscribed: Optional[bool] = None
    author: Optional[Author] = None
    is_post_in_collection: Optional[bool] = None
    is_contributor: Optional[bool] = None
    can_commit: Optional[bool] = None
    chat_join_threshold: int = 0

    @classmethod
    def from_json(cls, json_data: Dict[str, Any]) -> 'CollectionData':
        """
        从JSON数据创建CollectionData实例
        """
        # 处理嵌套的author对象
        author_data = json_data.get('author')
        author = Author(**author_data) if author_data else None

        # 创建并返回实例
        data_copy = json_data.copy()
        if author_data:
            data_copy['author'] = author
        data_copy['contents'] = json_data.get('contents', [])[::-1]

        # 过滤掉不在类字段中的键
        field_names = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data_copy.items() if k in field_names}


        return cls(**filtered_data)

    def to_json(self) -> Dict[str, Any]:
        """
        将CollectionData实例转换为JSON可序列化的字典
        """
        return asdict(self)

    def save_to_file(self, file_path: str | None = None) -> str:
        """
        保存数据到JSON文件
        """
        if not file_path:
            # 默认文件名使用集合ID
            file_path = f"collection_{self.id}.json"

        # 确保目录存在
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)

        # 保存数据
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_json(), f, ensure_ascii=False, indent=2)

        return file_path

