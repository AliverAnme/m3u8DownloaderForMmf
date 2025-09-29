"""
Feed JSON解析器
专门处理feed.json格式，提取ID列表并获取详细数据
"""

import json
import requests
import time
import urllib3
from typing import List, Dict, Any, Optional
from ..core.config import Config
from ..database.models import VideoRecord

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class FeedParser:
    """Feed JSON解析器"""

    def __init__(self):
        self.config = Config()
        self.session = requests.Session()
        self.session.headers.update(self.config.DEFAULT_HEADERS)

        # 配置SSL和代理设置
        self.session.verify = False  # 禁用SSL验证以避免证书问题
        self.session.trust_env = False  # 不使用环境变量中的代理设置
        self.session.proxies = {}  # 清空代理设置

        self.id_cache = []

    def parse_feed_json(self, feed_file_path: str) -> List[str]:
        """
        解析feed.json文件，提取ID列表

        Args:
            feed_file_path: feed.json文件路径

        Returns:
            List[str]: ID列表
        """
        try:
            with open(feed_file_path, 'r', encoding='utf-8') as f:
                feed_data = json.load(f)

            id_list = []
            items = feed_data.get('items', [])

            for item in items:
                item_id = item.get('id')
                if item_id:
                    id_list.append(item_id)

            print(f"📋 从feed.json中提取到 {len(id_list)} 个ID")
            self.id_cache = id_list
            return id_list

        except Exception as e:
            print(f"❌ 解析feed.json失败: {e}")
            return []

    def fetch_video_data_by_id(self, video_id: str, wait_time: float = 1.0) -> Optional[Dict[str, Any]]:
        """
        根据ID获取视频详细数据

        Args:
            video_id: 视频ID
            wait_time: 请求间隔时间（秒）

        Returns:
            dict: 视频数据，如果失败返回None
        """
        try:
            # 添加请求等待时间
            time.sleep(wait_time)

            url = f"https://api.memefans.ai/v2/posts/videos/{video_id}"
            print(f"🔍 正在获取视频数据: {video_id}")

            # 发送请求时禁用SSL验证
            response = self.session.get(
                url,
                timeout=self.config.API_TIMEOUT,
                verify=False  # 明确禁用SSL验证
            )
            response.raise_for_status()

            data = response.json()
            print(f"✅ 成功获取视频数据: {video_id}")
            return data

        except requests.exceptions.SSLError as e:
            print(f"❌ SSL错误 {video_id}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ 请求失败 {video_id}: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败 {video_id}: {e}")
            return None
        except Exception as e:
            print(f"❌ 获取视频数据异常 {video_id}: {e}")
            return None

    def process_feed_ids(self, feed_file_path: str, wait_time: float = 1.0,
                        max_retries: int = 3) -> List[VideoRecord]:
        """
        处理feed文件中的所有ID，获取详细数据并转换为VideoRecord

        Args:
            feed_file_path: feed.json文件路径
            wait_time: 请求间隔时间（秒）
            max_retries: 最大重试次数

        Returns:
            List[VideoRecord]: 视频记录列表
        """
        # 1. 解析feed.json提取ID列表
        id_list = self.parse_feed_json(feed_file_path)
        if not id_list:
            print("❌ 没有找到有效的ID")
            return []

        video_records = []
        total_ids = len(id_list)

        print(f"🚀 开始处理 {total_ids} 个视频ID...")

        # 2. 依次请求每个ID获取详细数据
        for index, video_id in enumerate(id_list, 1):
            print(f"📍 处理进度: {index}/{total_ids} - ID: {video_id}")

            # 重试机制
            for attempt in range(max_retries + 1):
                try:
                    video_data = self.fetch_video_data_by_id(video_id, wait_time)

                    if video_data:
                        # 3. 使用原有的解析方式转换数据
                        video_record = self._convert_to_video_record(video_data, video_id)
                        if video_record:
                            video_records.append(video_record)
                            print(f"✅ 成功处理: {video_record.title}")
                        break
                    else:
                        if attempt < max_retries:
                            retry_wait = wait_time * (2 ** attempt)  # 指数退避
                            print(f"⏳ 重试 {attempt + 1}/{max_retries}，等待 {retry_wait:.1f}s...")
                            time.sleep(retry_wait)
                        else:
                            print(f"❌ 最终失败: {video_id}")

                except Exception as e:
                    print(f"❌ 处理异常 {video_id}: {e}")
                    if attempt < max_retries:
                        time.sleep(wait_time)
                    break

        print(f"🎉 处理完成，成功获取 {len(video_records)} 个视频记录")
        return video_records

    @staticmethod
    def _convert_to_video_record(video_data: Dict[str, Any], video_id: str) -> Optional[VideoRecord]:
        """
        将API返回的视频数据转换为VideoRecord对象

        Args:
            video_data: API返回的视频数据
            video_id: 视频ID

        Returns:
            VideoRecord: 视频记录对象，失败返回None
        """
        try:
            # 确保数据中包含ID
            if 'id' not in video_data:
                video_data['id'] = video_id

            # 使用现有的VideoRecord.from_api_data方法
            video_record = VideoRecord.from_api_data(video_data)
            return video_record

        except Exception as e:
            print(f"❌ 转换VideoRecord失败 {video_id}: {e}")
            return None

    def get_cached_ids(self) -> List[str]:
        """
        获取缓存的ID列表

        Returns:
            List[str]: 缓存的ID列表
        """
        return self.id_cache.copy()

    def clear_cache(self):
        """清空ID缓存"""
        self.id_cache = []
        print("🗑️ ID缓存已清空")
