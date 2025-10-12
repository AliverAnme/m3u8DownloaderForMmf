"""
Memefans API客户端
处理Memefans API数据获取、解析和处理
"""

import requests
import json
import urllib3
import time
from typing import Dict, Any, List, Optional

from ..core.config import Config
from ..database.models import VideoRecord

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class MemefansAPIClient:
    """Memefans API客户端"""

    def __init__(self):
        self.config = Config()
        # 创建会话，禁用代理
        self.session = requests.Session()
        self.session.trust_env = False  # 不使用环境变量中的代理设置
        self.session.proxies = {}  # 清空代理设置

        # Memefans API配置
        self.base_url = "https://api.memefans.ai/v2/feed"
        self.default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
            # 'authorization': 'Bearer PL5eSlmQlaWxUetfKt_1hYWfwqrUDVC1y_5cUlUP3as',
            'authorization': 'Bearer 1HyC9FFPXFXXkhs1xR-wS8-Pid9Nl4SWKX2wOw1F7_s'
        }
        self.session.headers.update(self.default_headers)

    def fetch_data_with_retry(self,
                             page: int = 1,
                             size: int = 20,
                             max_retries: int = 3,
                             retry_delay: float = 1.0,
                             backoff_factor: float = 2.0) -> Dict[str, Any]:
        """
        带重试机制的Memefans API数据获取

        Args:
            page (int): 页码，默认为1
            size (int): 每页数据量，默认为10
            max_retries (int): 最大重试次数，默认为3
            retry_delay (float): 初始重试延迟时间（秒），默认为1.0
            backoff_factor (float): 延迟时间递增因子，默认为2.0

        Returns:
            Dict[str, Any]: API返回的JSON数据
        """
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    delay = retry_delay * (backoff_factor ** (attempt - 1))
                    print(f"⏳ Memefans API 第 {attempt} 次重试，等待 {delay:.1f} 秒...")
                    time.sleep(delay)

                print(f"🔄 Memefans API请求尝试 {attempt + 1}/{max_retries + 1}")

                # 调用原有的API请求方法
                result = self.fetch_data(page, size)

                if result:  # 如果获取到数据，直接返回
                    if attempt > 0:
                        print(f"✅ Memefans API重试成功！")
                    return result
                else:
                    if attempt < max_retries:
                        print(f"⚠️ Memefans API第 {attempt + 1} 次请求失败，准备重试...")
                    continue

            except Exception as e:
                if attempt < max_retries:
                    print(f"❌ Memefans API第 {attempt + 1} 次请求异常: {e}，准备重试...")
                else:
                    print(f"❌ Memefans API所有重试都失败，最后错误: {e}")

        print(f"💥 Memefans API请求失败，已重试 {max_retries} 次")
        return {}

    def fetch_data(self, page: int = 1, size: int = 10) -> Dict[str, Any]:
        """
        从Memefans API接口获取数据

        Args:
            page (int): 页码，默认为1
            size (int): 每页数据量，默认为10

        Returns:
            Dict[str, Any]: API返回的JSON数据
        """
        # 构建请求参数
        params = {
            "page": page,
            "size": size
        }

        try:
            print(f"🔄 正在请求Memefans API: {self.base_url}")
            print(f"📊 参数: page={page}, size={size}")

            # 发送请求
            response = self.session.get(
                self.base_url,
                params=params,
                verify=False,  # 禁用SSL验证
                timeout=30
            )

            # 检查响应状态
            response.raise_for_status()

            # 解析JSON响应
            api_data = response.json()

            print(f"✅ Memefans API请求成功，状态码: {response.status_code}")

            # 显示数据统计信息
            if isinstance(api_data, dict):
                total = api_data.get('total', 'N/A')
                current_page = api_data.get('page', page)
                page_size = api_data.get('size', size)
                items_count = len(api_data.get('items', []))
                print(f"📊 获取数据 - 总记录: {total}, 当前页: {current_page}, 页面大小: {page_size}, 本页条数: {items_count}")

            return api_data

        except requests.exceptions.RequestException as e:
            print(f"❌ Memefans API请求失败: {e}")
            return {}
        except json.JSONDecodeError as e:
            print(f"❌ Memefans API JSON解析失败: {e}")
            return {}

    def parse_items_to_video_records(self, api_data: Dict[str, Any]) -> List[VideoRecord]:
        """
        从Memefans API数据中解析items数组，转换为VideoRecord列表
        完全照搬feed解析器的实现

        Args:
            api_data (Dict[str, Any]): API返回的数据

        Returns:
            List[VideoRecord]: 解析后的视频记录列表
        """
        video_records = []
        skipped_count = 0
        failed_count = 0

        # 验证API数据结构
        if not isinstance(api_data, dict):
            print(f"❌ Memefans API数据格式错误：期望字典，但收到 {type(api_data).__name__}")
            return video_records

        # 获取items数组
        items = api_data.get('items', [])
        if not items:
            print("⚠️ Memefans API数据中未找到items数组")
            return video_records

        if not isinstance(items, list):
            print(f"❌ Memefans items字段格式错误：期望列表，但收到 {type(items).__name__}")
            return video_records

        print(f"📋 Memefans找到 {len(items)} 条数据项")

        # 输出API总体信息
        total = api_data.get('total', 'N/A')
        page = api_data.get('page', 'N/A')
        size = api_data.get('size', 'N/A')
        print(f"📊 Memefans API信息 - 总记录数: {total}, 当前页: {page}, 页面大小: {size}")

        for i, item in enumerate(items):
            author_id = item.get('author_id', "")
            try:
                # 预检查：快速跳过明显无效的数据
                if self._should_skip_item(item):
                    skipped_count += 1
                    continue

                if author_id != "BhhLJPlVvjU":
                    skipped_count += 1
                    continue
                # 完全照搬feed解析器的实现
                video_record = self._parse_single_item(item, i + 1)

                if video_record:
                    video_records.append(video_record)
                    print(f"✅ Memefans解析第 {i+1} 条：{video_record.title} ({video_record.video_date})")
                else:
                    skipped_count += 1

            except Exception as e:
                failed_count += 1
                print(f"❌ Memefans解析第 {i+1} 条数据失败: {e}")
                continue

        # 汇总信息
        print(f"🎯 Memefans解析完成 - 成功: {len(video_records)}, 跳过: {skipped_count}, 失败: {failed_count}")
        if skipped_count > 0:
            print(f"💡 跳过的数据可能包含：对象表示、空值或格式不兼容的内容")

        return video_records

    @staticmethod
    def _should_skip_item(item) -> bool:
        """预检查是否应该跳过某个数据项"""
        try:
            # 空值检查
            if item is None:
                return True

            # 字典类型的检查
            if isinstance(item, dict):
                # 如果字典为空，直接跳过
                if not item:
                    return True

                # 检查是否有视频ID
                if not item.get('id'):
                    return True

                return False

            # 其他类型直接跳过
            return True

        except Exception:
            return True

    def _parse_single_item(self, item, index: int) -> Optional[VideoRecord]:
        """
        解析单个数据项为VideoRecord
        完全照搬feed解析器的实现 - 直接调用详情API获取完整数据
        """
        try:
            # 获取视频ID
            video_id = item.get('id', '')
            if not video_id:
                print(f"❌ 第{index}项缺少视频ID")
                return None

            print(f"🔍 正在处理第{index}项，视频ID: {video_id}")

            # 直接调用详情API获取完整数据（照搬feed解析器的做法）
            detail_data = self.fetch_video_detail(str(video_id))

            if not detail_data:
                print(f"❌ 无法获取视频详情: {video_id}")
                return None

            # 确保数据中包含ID（照搬feed解析器的做法）
            if 'id' not in detail_data:
                detail_data['id'] = video_id

            # 直接使用VideoRecord.from_api_data方法（照搬feed解析器的做法）
            video_record = VideoRecord.from_api_data(detail_data)

            if video_record:
                print(f"✅ 成功解析第{index}项: {video_record.title} (UID: {video_record.uid})")
                return video_record
            else:
                print(f"❌ VideoRecord创建失败: {video_id}")
                return None

        except Exception as e:
            print(f"❌ 解析单个Memefans数据项失败 (第{index}项): {e}")
            return None

    def fetch_video_detail(self, video_id: str) -> Dict[str, Any]:
        """
        根据视频ID获取视频详细信息 - 使用与feed解析器相同的API端点

        Args:
            video_id (str): 视频ID

        Returns:
            Dict[str, Any]: 视频详细信息
        """
        if not video_id:
            print("❌ 视频ID为空")
            return {}

        # 使用与feed解析器相同的正确API端点
        detail_url = f"https://api.memefans.ai/v2/posts/videos/{video_id}"

        try:
            print(f"🔍 正在获取视频详情: {video_id}")

            response = self.session.get(
                detail_url,
                verify=False,
                timeout=30
            )

            response.raise_for_status()
            detail_data = response.json()

            print(f"✅ 视频详情获取成功: {video_id}")
            return detail_data

        except requests.exceptions.RequestException as e:
            print(f"❌ 获取视频详情失败 ({video_id}): {e}")
            return {}
        except json.JSONDecodeError as e:
            print(f"❌ 视频详情JSON解析失败 ({video_id}): {e}")
            return {}
