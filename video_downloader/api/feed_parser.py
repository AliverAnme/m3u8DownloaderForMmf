"""
Feed JSON 解析器 - 专门处理feed.json格式的数据
从feed.json中提取ID列表，然后批量请求详细数据
"""

import json
import time
import requests
import urllib3
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..core.config import Config
from ..database.models import VideoRecord

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class FeedParser:
    """Feed JSON解析器"""

    def __init__(self):
        self.config = Config()
        # 创建会话，禁用代理
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.proxies = {}

        # 请求设置
        self.request_delay = 2.0  # 请求间隔时间（秒）
        self.max_retries = 3     # 最大重试次数
        self.timeout = 30        # 请求超时时间

    def parse_feed_file(self, file_path: str) -> List[str]:
        """
        解析feed.json文件，提取所有视频ID

        Args:
            file_path (str): feed.json文件路径

        Returns:
            List[str]: 视频ID列表
        """
        try:
            print(f"📖 正在读取feed文件: {file_path}")

            with open(file_path, 'r', encoding='utf-8') as f:
                feed_data = json.load(f)

            # 验证数据格式
            if not isinstance(feed_data, dict):
                raise ValueError("Feed文件格式错误：期望JSON对象")

            items = feed_data.get('items', [])
            if not isinstance(items, list):
                raise ValueError("Feed文件格式错误：items字段应为数组")

            # 提取ID列表
            id_list = []
            for i, item in enumerate(items):
                if isinstance(item, dict) and 'id' in item:
                    video_id = item['id']
                    if video_id and isinstance(video_id, str):
                        id_list.append(video_id)
                        print(f"✅ 提取ID {i+1}: {video_id}")
                    else:
                        print(f"⚠️ 跳过无效ID (第{i+1}项): {video_id}")
                else:
                    print(f"⚠️ 跳过无效项目 (第{i+1}项): 缺少ID字段")

            print(f"🎯 成功提取 {len(id_list)} 个视频ID")

            # 显示feed文件统计信息
            total = feed_data.get('total', 'N/A')
            page = feed_data.get('page', 'N/A')
            size = feed_data.get('size', 'N/A')
            pages = feed_data.get('pages', 'N/A')
            print(f"📊 Feed信息 - 总记录: {total}, 当前页: {page}, 页面大小: {size}, 总页数: {pages}")

            return id_list

        except FileNotFoundError:
            print(f"❌ 文件不存在: {file_path}")
            return []
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}")
            return []
        except Exception as e:
            print(f"❌ 解析feed文件失败: {e}")
            return []

    def fetch_video_details(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        根据视频ID获取详细信息

        Args:
            video_id (str): 视频ID

        Returns:
            Optional[Dict[str, Any]]: 视频详细信息，失败时返回None
        """
        url = f"https://api.memefans.ai/v2/posts/videos/{video_id}"
        headers = self.config.DEFAULT_HEADERS

        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    delay = self.request_delay * (2 ** attempt)  # 指数退避
                    print(f"⏳ 第 {attempt} 次重试，等待 {delay:.1f} 秒...")
                    time.sleep(delay)

                print(f"🔄 请求视频详情: {video_id} (尝试 {attempt + 1}/{self.max_retries})")

                response = self.session.get(
                    url,
                    headers=headers,
                    verify=False,
                    timeout=self.timeout
                )

                response.raise_for_status()

                video_data = response.json()
                print(f"✅ 成功获取视频详情: {video_id}")

                return video_data

            except requests.exceptions.RequestException as e:
                print(f"❌ 请求失败 (尝试 {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    print(f"💥 最终失败，跳过视频ID: {video_id}")
                    return None
            except json.JSONDecodeError as e:
                print(f"❌ JSON解析失败: {e}")
                return None
            except Exception as e:
                print(f"❌ 未知错误: {e}")
                return None

        return None

    def process_video_data(self, video_data: Dict[str, Any]) -> Optional[VideoRecord]:
        """
        将获取到的视频详情转换为VideoRecord对象

        Args:
            video_data (Dict[str, Any]): 视频详细数据

        Returns:
            Optional[VideoRecord]: VideoRecord对象，失败时返回None
        """
        try:
            # 使用现有的VideoRecord.from_api_data方法
            video_record = VideoRecord.from_api_data(video_data)
            return video_record

        except Exception as e:
            print(f"❌ 转换VideoRecord失败: {e}")
            print(f"   数据内容: {str(video_data)[:200]}...")
            return None

    def batch_process_feed(self, file_path: str) -> List[VideoRecord]:
        """
        批量处理feed文件：提取ID -> 请求详情 -> 转换为VideoRecord

        Args:
            file_path (str): feed.json文件路径

        Returns:
            List[VideoRecord]: 成功解析的VideoRecord列表
        """
        print(f"🚀 开始批量处理feed文件: {file_path}")

        # 1. 提取ID列表
        id_list = self.parse_feed_file(file_path)
        if not id_list:
            print("❌ 未能提取到有效的视频ID")
            return []

        # 2. 批量请求视频详情并转换
        video_records = []
        failed_count = 0

        total_ids = len(id_list)
        print(f"📦 开始批量请求 {total_ids} 个视频的详细信息...")

        for i, video_id in enumerate(id_list):
            print(f"\n📹 处理视频 {i+1}/{total_ids}: {video_id}")

            # 请求视频详情
            video_data = self.fetch_video_details(video_id)
            if not video_data:
                failed_count += 1
                continue

            # 转换为VideoRecord
            video_record = self.process_video_data(video_data)
            if video_record:
                video_records.append(video_record)
                print(f"✅ 成功处理: {video_record.title} ({video_record.video_date})")
            else:
                failed_count += 1

            # 请求间隔，避免过于频繁的请求
            if i < total_ids - 1:  # 最后一个请求不需要等待
                print(f"⏳ 等待 {self.request_delay} 秒后继续...")
                time.sleep(self.request_delay)

        # 汇总结果
        success_count = len(video_records)
        print(f"\n🎯 批量处理完成!")
        print(f"   总计: {total_ids} 个ID")
        print(f"   成功: {success_count} 个")
        print(f"   失败: {failed_count} 个")
        print(f"   成功率: {success_count/total_ids*100:.1f}%")

        return video_records

    def save_cache_file(self, video_records: List[VideoRecord], cache_file_path: str):
        """
        将处理结果保存到缓存文件

        Args:
            video_records (List[VideoRecord]): 视频记录列表
            cache_file_path (str): 缓存文件路径
        """
        try:
            cache_data = []
            for record in video_records:
                cache_data.append({
                    'title': record.title,
                    'video_date': record.video_date,
                    'cover': record.cover,
                    'url': record.url,
                    'description': record.description,
                    'uid': record.uid,
                    'download': record.download,
                    'is_primer': record.is_primer,
                    'created_at': record.created_at.isoformat() if record.created_at else None,
                    'updated_at': record.updated_at.isoformat() if record.updated_at else None
                })

            with open(cache_file_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)

            print(f"💾 缓存文件已保存: {cache_file_path}")

        except Exception as e:
            print(f"❌ 保存缓存文件失败: {e}")
