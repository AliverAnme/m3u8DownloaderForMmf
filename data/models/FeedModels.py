#!/usr/bin/env python3
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import os


@dataclass
class BindingTokenInfo:
    """绑定的代币信息数据类"""

    token_address: str
    token_symbol: str
    image_url: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BindingTokenInfo":
        """从字典创建BindingTokenInfo实例"""
        return cls(
            token_address=data.get("token_address", ""),
            token_symbol=data.get("token_symbol", ""),
            image_url=data.get("image_url", ""),
        )


@dataclass
class FeedAuthor:
    """订阅作者信息数据类"""

    id: str
    username: str
    name: str
    avatar: str
    description: str
    display_name: str
    avatar_url: str
    bio: str
    follower_count: int | None = None
    following_count: int | None = None
    followers_count: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeedAuthor":
        """从字典创建FeedAuthor实例"""
        return cls(
            id=data.get("id", ""),
            username=data.get("username", ""),
            name=data.get("name", ""),
            avatar=data.get("avatar", ""),
            description=data.get("description", ""),
            follower_count=data.get("follower_count"),
            following_count=data.get("following_count"),
            display_name=data.get("display_name", ""),
            avatar_url=data.get("avatar_url", ""),
            bio=data.get("bio", ""),
            followers_count=data.get("followers_count", 0),
        )


@dataclass
class FeedVideoItem:
    """订阅视频项目数据类"""

    id: str
    type: str
    status: str
    created_at: str
    updated_at: str
    comments_count: int
    likes_count: int
    collections_count: int
    view_count: int
    region: str
    language: str
    author_id: str
    tags: List[str] = field(default_factory=list)
    title: str = ""
    text: Optional[str] = None
    description: str = ""
    cover: str = ""
    url: str = ""
    url_type: str = ""
    content_type: Optional[str] = None
    contents_count: Optional[int] = None
    original_cover: Optional[str] = None
    is_in_collection: bool = False
    is_liked: bool = False
    width: int = 0
    height: int = 0
    images_data: List[Any] = field(default_factory=list)
    is_locked: bool = False
    holdview_amount: str = ""
    binding_token_info: Optional[BindingTokenInfo] = None
    author: Optional[FeedAuthor] = None
    recall_info: Optional[Any] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeedVideoItem":
        """从字典创建FeedVideoItem实例"""
        # 处理嵌套对象
        binding_token_data = data.get("binding_token_info")
        binding_token_info = (
            BindingTokenInfo.from_dict(binding_token_data)
            if binding_token_data
            else None
        )

        author_data = data.get("author")
        author = FeedAuthor.from_dict(author_data) if author_data else None

        return cls(
            id=data.get("id", ""),
            type=data.get("type", ""),
            status=data.get("status", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            comments_count=data.get("comments_count", 0),
            likes_count=data.get("likes_count", 0),
            collections_count=data.get("collections_count", 0),
            view_count=data.get("view_count", 0),
            region=data.get("region", ""),
            language=data.get("language", ""),
            author_id=data.get("author_id", ""),
            tags=data.get("tags", []),
            title=data.get("title", ""),
            text=data.get("text"),
            description=data.get("description", ""),
            cover=data.get("cover", ""),
            url=data.get("url", ""),
            url_type=data.get("url_type", ""),
            content_type=data.get("content_type"),
            contents_count=data.get("contents_count"),
            original_cover=data.get("original_cover"),
            is_in_collection=data.get("is_in_collection", False),
            is_liked=data.get("is_liked", False),
            width=data.get("width", 0),
            height=data.get("height", 0),
            images_data=data.get("images_data", []),
            is_locked=data.get("is_locked", False),
            holdview_amount=data.get("holdview_amount", ""),
            binding_token_info=binding_token_info,
            author=author,
            recall_info=data.get("recall_info"),
        )

    def get_datetime_created(self) -> Optional[datetime]:
        """将created_at字符串转换为datetime对象"""
        try:
            return datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None

    def get_datetime_updated(self) -> Optional[datetime]:
        """将updated_at字符串转换为datetime对象"""
        try:
            return datetime.fromisoformat(self.updated_at.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None

    def to_dict(self) -> Dict[str, Any]:
        """将FeedVideoItem实例转换为字典"""
        result = {
            "id": self.id,
            "type": self.type,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "comments_count": self.comments_count,
            "likes_count": self.likes_count,
            "collections_count": self.collections_count,
            "view_count": self.view_count,
            "region": self.region,
            "language": self.language,
            "author_id": self.author_id,
            "tags": self.tags,
            "title": self.title,
            "text": self.text,
            "description": self.description,
            "cover": self.cover,
            "url": self.url,
            "url_type": self.url_type,
            "content_type": self.content_type,
            "contents_count": self.contents_count,
            "original_cover": self.original_cover,
            "is_in_collection": self.is_in_collection,
            "is_liked": self.is_liked,
            "width": self.width,
            "height": self.height,
            "images_data": self.images_data,
            "is_locked": self.is_locked,
            "holdview_amount": self.holdview_amount,
            "recall_info": self.recall_info,
        }

        # 添加嵌套对象
        if self.binding_token_info:
            result["binding_token_info"] = {
                "token_address": self.binding_token_info.token_address,
                "token_symbol": self.binding_token_info.token_symbol,
                "image_url": self.binding_token_info.image_url,
            }

        if self.author:
            result["author"] = {
                "id": self.author.id,
                "username": self.author.username,
                "name": self.author.name,
                "avatar": self.author.avatar,
                "description": self.author.description,
                "follower_count": self.author.follower_count,
                "following_count": self.author.following_count,
                "display_name": self.author.display_name,
                "avatar_url": self.author.avatar_url,
                "bio": self.author.bio,
                "followers_count": self.author.followers_count,
            }

        return result


@dataclass
class Feed:
    """Feed数据类，包含多个视频项目"""

    items: List[FeedVideoItem] = field(default_factory=list)
    total: int = 0
    page: int = 0
    size: int = 0
    pages: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Feed":
        """从字典创建Feed实例

        Args:
            data: 包含Feed数据的字典，应包含'items'、'total'、'page'、'size'和'pages'字段

        Returns:
            Feed实例
        """
        # 确保data是字典类型

        # 处理items字段
        items_data = data.get("items", [])
        items = []
        if isinstance(items_data, list):
            # 安全地创建FeedVideoItem实例列表
            for item_data in items_data:
                if isinstance(item_data, dict):
                    try:
                        items.append(FeedVideoItem.from_dict(item_data))
                    except Exception:
                        # 忽略单个项目的错误，继续处理其他项目
                        pass

        return cls(
            items=items,
            total=int(data.get("total", 0)),
            page=int(data.get("page", 0)),
            size=int(data.get("size", 0)),
            pages=int(data.get("pages", 0)),
        )

    @classmethod
    def from_json_file(cls, file_path: str) -> "Feed":
        """从JSON文件创建Feed实例

        Args:
            file_path: JSON文件路径

        Returns:
            Feed实例

        Raises:
            FileNotFoundError: 文件不存在时抛出
            json.JSONDecodeError: JSON解析错误时抛出
        """
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return cls.from_dict(data)
        except json.JSONDecodeError as e:
            # JSON解析错误
            raise json.JSONDecodeError(f"JSON解析错误: {e.msg}", e.doc, e.pos)
        except Exception as e:
            # 捕获其他可能的错误
            raise RuntimeError(f"从JSON文件创建Feed实例失败: {str(e)}")

    @classmethod
    def from_api_response(cls, response: Dict[str, Any]) -> "Feed":
        """从API响应创建Feed实例"""
        # 从响应中提取分页相关信息
        total = response.get("total", 0)
        page = response.get("page", 0)
        size = response.get("size", 0)
        pages = response.get("pages", 0)

        # 获取items数组
        items_data = response.get("items", [])

        # 创建Feed实例
        feed = cls(
            items=[],  # 初始化为空列表
            total=total,
            page=page,
            size=size,
            pages=pages,
        )

        # 处理items - 直接从response中获取items数组
        if isinstance(items_data, list):
            feed.items = [
                FeedVideoItem.from_dict(item_data) for item_data in items_data
            ]

        return feed

    def to_dict(self) -> Dict[str, Any]:
        """将Feed实例转换为字典"""
        return {
            "items": [item.to_dict() for item in self.items],
            "total": self.total,
            "page": self.page,
            "size": self.size,
            "pages": self.pages,
        }

    def to_json_file(self, file_path: str) -> None:
        """将Feed实例保存为JSON文件"""
        import json

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    def get_item_by_id(self, item_id: str) -> Optional[FeedVideoItem]:
        """根据ID获取视频项目"""
        for item in self.items:
            if item.id == item_id:
                return item
        return None

    def filter_by_author_id(self, author_id: str) -> List[FeedVideoItem]:
        """根据作者ID过滤视频项目"""
        return [item for item in self.items if item.author_id == author_id]

    def filter_by_tags(self, tags: List[str]) -> List[FeedVideoItem]:
        """根据标签过滤视频项目"""
        return [item for item in self.items if any(tag in item.tags for tag in tags)]

    def sort_by_created_at(self, reverse: bool = True) -> None:
        """按创建时间排序视频项目"""
        self.items.sort(
            key=lambda x: x.get_datetime_created() or datetime.min, reverse=reverse
        )
