"""
API相关功能模块
处理API数据获取、解析和保存
"""

import requests
import json
import urllib3
import re
from typing import Dict, Any, List

from ..core.config import Config
from ..database.models import VideoRecord

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class APIClient:

    def __init__(self):
        self.config = Config()

    def fetch_api_data(self, size: int = 50, verify_ssl: bool = False) -> Dict[str, Any]:
        """
        从API接口获取数据

        Args:
            size (int): 每页返回的数据条数，默认为50
            verify_ssl (bool): 是否验证SSL证书，默认为False

        Returns:
            Dict[str, Any]: API返回的JSON数据
        """
        # API接口URL
        base_url = self.config.API_BASE_URL

        # 固定参数
        params = {
            "author_id": self.config.DEFAULT_AUTHOR_ID,
            "page": 1,
            "size": size
        }

        # 设置请求头
        headers = self.config.DEFAULT_HEADERS

        try:
            print(f"🔄 正在请求API: {base_url}")
            print(f"📊 参数: {params}")
            print(f"🔒 SSL验证: {'启用' if verify_ssl else '禁用'}")

            # 发送请求
            response = requests.get(
                base_url,
                params=params,
                headers=headers,
                verify=verify_ssl,
                timeout=30
            )

            # 检查响应状态
            response.raise_for_status()

            # 解析JSON响应
            api_data = response.json()

            print(f"✅ API请求成功，状态码: {response.status_code}")

            return api_data

        except requests.exceptions.RequestException as e:
            print(f"❌ API请求失败: {e}")
            return {}
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}")
            return {}

    def parse_items_to_video_records(self, api_data: Dict[str, Any]) -> List[VideoRecord]:
        """
        从API数据中解析items数组，转换为VideoRecord列表

        Args:
            api_data (Dict[str, Any]): API返回的数据

        Returns:
            List[VideoRecord]: 解析后的视频记录列表
        """
        video_records = []

        # 获取items数组
        items = api_data.get('items', [])
        if not items:
            print("⚠️ API数据中未找到items数组")
            return video_records

        print(f"📋 找到 {len(items)} 条数据项")

        for i, item in enumerate(items):
            try:
                # 从API数据创建VideoRecord
                video_record = VideoRecord.from_api_data(item)

                # 验证必要字段
                if not video_record.title or not video_record.video_date:
                    print(f"⚠️ 跳过第 {i+1} 条数据：缺少必要字段")
                    continue

                video_records.append(video_record)
                print(f"✅ 解析第 {i+1} 条：{video_record.title} ({video_record.video_date})")

            except Exception as e:
                print(f"❌ 解析第 {i+1} 条数据失败: {e}")
                continue

        print(f"🎯 成功解析 {len(video_records)} 条有效记录")
        return video_records

    def fetch_and_parse_videos(self, size: int = 50) -> List[VideoRecord]:
        """
        一次性完成API请求和数据解析

        Args:
            size (int): 每页返回的数据条数

        Returns:
            List[VideoRecord]: 解析后的视频记录列表
        """
        print("🚀 开始执行API解析...")
        print(f"📊 请求数据条数: {size}")

        # 1. 获取API数据
        api_data = self.fetch_api_data(size)
        if not api_data:
            print("❌ 无法获取API数据")
            return []

        # 2. 解析为VideoRecord列表
        video_records = self.parse_items_to_video_records(api_data)

        print(f"📊 API解析完成，共处理 {len(video_records)} 条数据")
        return video_records

    def extract_title_from_description(self, description: str) -> str:
        """
        从description中提取标题内容（与DataProcessor保持一致）

        Args:
            description (str): 完整的描述文本

        Returns:
            str: 提取的标题
        """
        if not description:
            return ""

        # 方法1: 提取【】开头到第一个 # 或者特定关键词之前的内容
        pattern1 = r'【[^】]+】([^#]+?)(?:\s*#|\s*$)'
        match1 = re.search(pattern1, description)
        if match1:
            title = match1.group(0).strip()
            title = re.sub(r'\s*#.*$', '', title).strip()
            return title

        # 方法2: 如果没有【】格式，提取第一个#之前的内容
        pattern2 = r'^([^#]+?)(?:\s*#|$)'
        match2 = re.search(pattern2, description)
        if match2:
            title = match2.group(1).strip()
            return title

        # 方法3: 如果都没有匹配，返回前100个字符
        return description[:100] + "..." if len(description) > 100 else description

    def process_posts_data(self, data: Dict[str, Any]) -> None:
        """
        处理从API获取的posts数据

        Args:
            data (Dict[str, Any]): API返回的数据
        """
        if not data or 'items' not in data:
            print("数据为空或格式不正确")
            return

        items = data['items']
        total = data.get('total', 0)
        page = data.get('page', 1)
        size = data.get('size', 50)

        print(f"\n数据概览:")
        print(f"总记录数: {total}")
        print(f"当前页: {page}")
        print(f"每页大小: {size}")
        print(f"当前页记录数: {len(items)}")

        print(f"\n前3条记录的标题:")
        for i, item in enumerate(items[:3], 1):
            # 使用与其他模式一致的标题提取方法
            description = item.get('description', '')
            title = self.extract_title_from_description(description)
            if not title:
                title = item.get('title', 'No title')

            likes = item.get('likes_count', 0)
            comments = item.get('comments_count', 0)
            print(f"{i}. {title} (👍{likes} 💬{comments})")
