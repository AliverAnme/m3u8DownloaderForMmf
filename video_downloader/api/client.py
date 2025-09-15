"""
API相关功能模块
处理API数据获取、解析和保存
"""

import requests
import json
import urllib3
import re
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..core.config import Config
from ..database.models import VideoRecord
from ..utils.enhanced_json_parser import EnhancedJSONParser

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class APIClient:

    def __init__(self):
        self.config = Config()

    def fetch_api_data_with_retry(self,
                                  size: int = 50,
                                  verify_ssl: bool = False,
                                  max_retries: int = 3,
                                  retry_delay: float = 1.0,
                                  backoff_factor: float = 2.0) -> Dict[str, Any]:
        """
        带重试机制的API数据获取

        Args:
            size (int): 每页返回的数据条数，默认为50
            verify_ssl (bool): 是否验证SSL证书，默认为False
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
                    print(f"⏳ 第 {attempt} 次重试，等待 {delay:.1f} 秒...")
                    time.sleep(delay)

                print(f"🔄 API请求尝试 {attempt + 1}/{max_retries + 1}")

                # 调用原有的API请求方法
                result = self.fetch_api_data(size, verify_ssl)

                if result:  # 如果获取到数据，直接返回
                    if attempt > 0:
                        print(f"✅ 重试成功！")
                    return result
                else:
                    if attempt < max_retries:
                        print(f"⚠️ 第 {attempt + 1} 次请求失败，准备重试...")
                    continue

            except Exception as e:
                if attempt < max_retries:
                    print(f"❌ 第 {attempt + 1} 次请求异常: {e}，准备重试...")
                else:
                    print(f"❌ 所有重试都失败，最后错误: {e}")

        print(f"💥 API请求失败，已重试 {max_retries} 次")
        return {}

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
        支持多种数据格式的智能解析

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
            print(f"❌ API数据格式错误：期望字典，但收到 {type(api_data).__name__}")
            return video_records

        # 获取items数组
        items = api_data.get('items', [])
        if not items:
            print("⚠️ API数据中未找到items数组")
            return video_records

        if not isinstance(items, list):
            print(f"❌ items字段格式错误：期望列表，但收到 {type(items).__name__}")
            return video_records

        print(f"📋 找到 {len(items)} 条数据项")

        # 输出API总体信息
        total = api_data.get('total', 'N/A')
        page = api_data.get('page', 'N/A')
        size = api_data.get('size', 'N/A')
        print(f"📊 API信息 - 总记录数: {total}, 当前页: {page}, 页面大小: {size}")

        for i, item in enumerate(items):
            try:
                # 预检查：快速跳过明显无效的数据
                if self._should_skip_item(item):
                    skipped_count += 1
                    continue

                # 多种解析方式处理不同数据格式
                video_record = self._parse_single_item(item, i + 1)

                if video_record:
                    video_records.append(video_record)
                    print(f"✅ 解析第 {i+1} 条：{video_record.title} ({video_record.video_date})")
                else:
                    skipped_count += 1

            except Exception as e:
                failed_count += 1
                print(f"❌ 解析第 {i+1} 条数据失败 (未知错误): {e}")
                print(f"   数据类型: {type(item).__name__}")
                print(f"   数据内容: {str(item)[:200]}...")
                continue

        # 汇总信息
        print(f"🎯 解析完成 - 成功: {len(video_records)}, 跳过: {skipped_count}, 失败: {failed_count}")
        if skipped_count > 0:
            print(f"💡 跳过的数据可能包含：对象表示、空值或格式不兼容的内容")

        return video_records

    def _should_skip_item(self, item) -> bool:
        """预检查是否应该跳过某个数据项"""
        try:
            # 空值检查
            if item is None:
                return True

            # 字符串类型的快速检查
            if isinstance(item, str):
                item = item.strip()
                if not item or len(item) < 5:
                    return True
                # 检查是否是对象表示
                if ('<' in item and 'object at 0x' in item and '>' in item) or \
                   (item.startswith('<') and item.endswith('>') and 'object' in item) or \
                   item in ['None', 'null', '{}', '[]', '""', "''"] or \
                   item.lower() in ['undefined', 'nan']:
                    return True

            # 字典类型的检查 - 根据实际API数据结构调整
            elif isinstance(item, dict):
                # 如果字典为空，直接跳过
                if not item:
                    return True

                # 检查是否有基本的视频信息字段（更宽松的检查）
                has_video_fields = any(key in item for key in [
                    'description', 'title', 'content', 'desc', 'url', 'cover', 'id'
                ])

                # 如果没有任何视频相关字段，跳过
                if not has_video_fields:
                    return True

                # 检查description字段是否有效
                description = item.get('description', '')
                if description and isinstance(description, str) and len(description.strip()) > 0:
                    return False  # 有有效的description，不跳过

                # 如果没有description，检查是否有其他可用字段
                title = item.get('title', '')
                if title and isinstance(title, str) and len(title.strip()) > 0:
                    return False  # 有有效的title，不跳过

                # 如果既没有description也没有title，但有其他字段，也不跳过（让后续处理）
                return False

            # 列表类型的检查
            elif isinstance(item, list):
                if not item:
                    return True

            return False

        except Exception:
            return True

    def _parse_single_item(self, item, index: int) -> Optional[VideoRecord]:
        """
        解析单个数据项，支持多种数据格式

        Args:
            item: 单个数据项（可能是字典、对象或其他格式）
            index: 数据项索引（用于错误提示）

        Returns:
            Optional[VideoRecord]: 解析成功返回VideoRecord，失败返回None
        """
        try:
            # 解析方式1: 标准字典格式（正确的API格式）
            if isinstance(item, dict):
                return self._parse_dict_format(item, index)

            # 解析方式2: Video对象格式
            elif hasattr(item, '__dict__') and hasattr(item, 'description'):
                return self._parse_object_format(item, index)

            # 解析方式3: 字符串格式（可能是JSON字符串）
            elif isinstance(item, str):
                return self._parse_string_format(item, index)

            # 解析方式4: 列表格式（嵌套数据）
            elif isinstance(item, list):
                return self._parse_list_format(item, index)

            # 解析方式5: 其他可能的格式
            else:
                return self._parse_unknown_format(item, index)

        except Exception as e:
            print(f"❌ 第 {index} 条数据解析异常: {e}")
            return None

    def _parse_dict_format(self, item: dict, index: int) -> Optional[VideoRecord]:
        """解析字典格式的数据（标准API格式）"""
        try:
            # 检查必要的字段
            required_fields = ['description']
            missing_fields = [field for field in required_fields if not item.get(field)]

            if missing_fields:
                print(f"⚠️ 跳过第 {index} 条数据：缺少必要字段 {missing_fields}")
                return None

            # 验证数据类型
            description = item.get('description', '')
            if not isinstance(description, str):
                print(f"⚠️ 跳过第 {index} 条数据：description字段类型错误")
                return None

            # 创建标准格式的数据字典
            standardized_data = {
                'description': description,
                'cover': item.get('cover', ''),
                'url': item.get('url', ''),
                # 支持其他可能的字段名称
                'image': item.get('image', ''),
                'video_url': item.get('video_url', ''),
                'stream_url': item.get('stream_url', ''),
            }

            # 使用标准方法创建VideoRecord
            video_record = VideoRecord.from_api_data(standardized_data)

            # 验证解析结果
            if not video_record.title or not video_record.video_date:
                print(f"⚠️ 跳过第 {index} 条数据：提取字段为空 (title: '{video_record.title}', date: '{video_record.video_date}')")
                return None

            return video_record

        except Exception as e:
            print(f"❌ 字典格式解析失败 (第 {index} 条): {e}")
            # 尝试降级解析
            return self._fallback_parse_dict(item, index)

    def _fallback_parse_dict(self, item: dict, index: int) -> Optional[VideoRecord]:
        """字典格式的降级解析方法"""
        try:
            # 尝试从所有可能的字段中提取信息
            description_candidates = [
                item.get('description', ''),
                item.get('desc', ''),
                item.get('title', ''),
                item.get('content', ''),
                str(item.get('text', ''))
            ]

            description = next((desc for desc in description_candidates if desc and isinstance(desc, str)), '')

            if not description:
                print(f"⚠️ 跳过第 {index} 条数据：无法找到有效的描述信息")
                return None

            # 尝试提取其他字段
            cover_candidates = [
                item.get('cover', ''),
                item.get('cover_url', ''),
                item.get('image', ''),
                item.get('thumbnail', ''),
                item.get('poster', '')
            ]

            url_candidates = [
                item.get('url', ''),
                item.get('video_url', ''),
                item.get('stream_url', ''),
                item.get('play_url', ''),
                item.get('download_url', '')
            ]

            cover = next((c for c in cover_candidates if c and isinstance(c, str)), '')
            url = next((u for u in url_candidates if u and isinstance(u, str)), '')

            # 创建简化的数据字典
            simple_data = {
                'description': description,
                'cover': cover,
                'url': url
            }

            return VideoRecord.from_api_data(simple_data)

        except Exception as e:
            print(f"❌ 降级解析也失败 (第 {index} 条): {e}")
            return None

    def _parse_object_format(self, item, index: int) -> Optional[VideoRecord]:
        """解析对象格式的数据"""
        try:
            # 尝试从对象属性中提取数据
            description = getattr(item, 'description', '')
            if not description:
                description = getattr(item, 'desc', '')
            if not description:
                description = getattr(item, 'title', '')

            if not description:
                print(f"⚠️ 跳过第 {index} 条数据：对象中找不到有效的描述字段")
                return None

            # 提取其他属性
            cover = getattr(item, 'cover', '') or getattr(item, 'cover_url', '') or getattr(item, 'image', '')
            url = getattr(item, 'url', '') or getattr(item, 'video_url', '') or getattr(item, 'stream_url', '')

            # 创建字典格式然后使用标准方法
            item_dict = {
                'description': str(description),
                'cover': str(cover),
                'url': str(url)
            }

            return VideoRecord.from_api_data(item_dict)

        except Exception as e:
            print(f"❌ 对象格式解析失败 (第 {index} 条): {e}")
            return None

    def _parse_string_format(self, item: str, index: int) -> Optional[VideoRecord]:
        """解析字符串格式的数据（可能是JSON字符串）"""
        try:
            # 预先检查和清理字符串
            item = item.strip()

            # 跳过明显无效的数据，但不输出警告（避免噪音）
            if not item or len(item) < 5:
                return None

            # 检查是否是对象表示（静默跳过）
            if ('<' in item and 'object at 0x' in item and '>' in item) or \
               (item.startswith('<') and item.endswith('>') and 'object' in item) or \
               item.strip() in ['None', 'null', '{}', '[]', '""', "''"] or \
               item.strip().lower() in ['undefined', 'nan']:
                return None

            # 尝试解析为JSON
            if item.startswith('{') and item.endswith('}'):
                try:
                    item_dict = json.loads(item)
                    return self._parse_dict_format(item_dict, index)
                except json.JSONDecodeError:
                    # JSON解析失败，继续当作普通字符串处理
                    pass

            # 验证字符串是否包含有意义的内容
            if self._is_meaningful_content(item):
                item_dict = {
                    'description': item,
                    'cover': '',
                    'url': ''
                }

                try:
                    video_record = VideoRecord.from_api_data(item_dict)
                    # 验证解析结果
                    if video_record.title and len(video_record.title.strip()) > 0:
                        return video_record
                except Exception:
                    pass

            return None

        except Exception as e:
            # 只在真正的异常情况下输出错误
            if "解析失败" not in str(e):
                print(f"❌ 字符串格式解析异常 (第 {index} 条): {e}")
            return None

    def _is_meaningful_content(self, content: str) -> bool:
        """检查内容是否有意义"""
        if not content or len(content.strip()) < 10:
            return False

        # 排除HTML标签
        if content.startswith('<') and content.endswith('>'):
            return False

        # 排除纯数字或特殊字符
        if content.isdigit() or not any(c.isalnum() for c in content):
            return False

        return True

    def _parse_list_format(self, item: list, index: int) -> Optional[VideoRecord]:
        """解析列表格式的数据"""
        try:
            if not item:
                print(f"⚠️ 跳过第 {index} 条数据：空列表")
                return None

            # 取第一个非空元素尝试解析
            for sub_item in item:
                if sub_item:
                    return self._parse_single_item(sub_item, index)

            print(f"⚠️ 跳过第 {index} 条数据：列表中无有效数据")
            return None

        except Exception as e:
            print(f"❌ 列表格式解析失败 (第 {index} 条): {e}")
            return None

    def _parse_unknown_format(self, item, index: int) -> Optional[VideoRecord]:
        """解析未知格式的数据"""
        try:
            # 尝试转换为字符串然后当作description处理
            description = str(item)

            # 检查是否有有用的信息
            if len(description.strip()) > 10 and 'object at 0x' not in description:
                # 额外检查：避免处理明显无意义的数据
                if description.startswith('<') and description.endswith('>'):
                    print(f"⚠️ 跳过第 {index} 条数据：看起来是HTML或XML标签")
                    return None

                item_dict = {
                    'description': description,
                    'cover': '',
                    'url': ''
                }
                return VideoRecord.from_api_data(item_dict)
            else:
                print(f"⚠️ 跳过第 {index} 条数据：未知格式且无有效信息 ({type(item).__name__})")
                return None

        except Exception as e:
            print(f"❌ 未知格式解析失败 (第 {index} 条): {e}")
            return None

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

    def fetch_and_parse_videos_with_retry(self,
                                          size: int = 50,
                                          max_retries: int = 3,
                                          retry_delay: float = 1.0,
                                          backoff_factor: float = 2.0) -> List[VideoRecord]:
        """
        带重试机制的API请求和数据解析

        Args:
            size (int): 每页返回的数据条数
            max_retries (int): 最大重试次数
            retry_delay (float): 初始重试延迟时间（秒）
            backoff_factor (float): 延迟时间递增因子

        Returns:
            List[VideoRecord]: 解析后的视频记录列表
        """
        print("🚀 开始执行带重试的API解析...")
        print(f"📊 请求数据条数: {size}")
        print(f"🔄 最大重试次数: {max_retries}")

        # 1. 使用重试机制获取API数据
        api_data = self.fetch_api_data_with_retry(
            size=size,
            max_retries=max_retries,
            retry_delay=retry_delay,
            backoff_factor=backoff_factor
        )

        if not api_data:
            print("❌ 重试后仍无法获取API数据")
            return []

        # 2. 解析为VideoRecord列表
        video_records = self.parse_items_to_video_records(api_data)

        print(f"📊 带重试的API解析完成，共处理 {len(video_records)} 条数据")
        return video_records

    def fetch_and_parse_videos_with_retry_enhanced(self,
                                                  size: int = 50,
                                                  max_retries: int = 3,
                                                  retry_delay: float = 1.0,
                                                  backoff_factor: float = 2.0,
                                                  use_enhanced_parsing: bool = True) -> List[VideoRecord]:
        """
        带重试机制和增强JSON解析的API请求和数据解析

        Args:
            size (int): 每页返回的数据条数
            max_retries (int): 最大重试次数
            retry_delay (float): 初始重试延迟时间（秒）
            backoff_factor (float): 延迟时间递增因子
            use_enhanced_parsing (bool): 是否使用增强JSON解析

        Returns:
            List[VideoRecord]: 解析后的视频记录列表
        """
        print("🚀 开始执行带重试机制的增强API解析...")
        print(f"📊 请求数据条数: {size}")
        print(f"🔄 最大重试次数: {max_retries}")
        print(f"🔍 增强解析: {'启用' if use_enhanced_parsing else '禁用'}")

        # 1. 使用重试机制获取API数据
        api_data = self.fetch_api_data_with_retry(
            size=size,
            max_retries=max_retries,
            retry_delay=retry_delay,
            backoff_factor=backoff_factor
        )

        if not api_data:
            print("❌ 重试后仍无法获取API数据")
            return []

        # 2. 根据选择使用不同的解析方式
        if use_enhanced_parsing:
            print("🔍 使用增强JSON解析器处理API数据...")
            video_records = self.parse_api_response_enhanced(api_data)
        else:
            print("📋 使用标准解析器处理API数据...")
            video_records = self.parse_items_to_video_records(api_data)

        print(f"📊 带重试的增强API解析完成，共处理 {len(video_records)} 条数据")
        return video_records

    def fetch_multiple_pages_with_retry(self,
                                        pages: List[int],
                                        size: int = 50,
                                        max_retries: int = 3,
                                        retry_delay: float = 1.0,
                                        page_delay: float = 0.5) -> List[VideoRecord]:
        """
        带重试机制的多页API数据获取

        Args:
            pages (List[int]): 要获取的页码列表
            size (int): 每页返回的数据条数
            max_retries (int): 每页的最大重试次数
            retry_delay (float): 重试延迟时间
            page_delay (float): 页面间的延迟时间

        Returns:
            List[VideoRecord]: 所有页面解析后的视频记录列表
        """
        all_video_records = []
        successful_pages = 0
        failed_pages = 0

        print(f"🚀 开始多页API请求，共 {len(pages)} 页")
        print(f"📄 页码: {pages}")

        for i, page_num in enumerate(pages, 1):
            print(f"\n📄 处理第 {i}/{len(pages)} 页 (页码: {page_num})")

            try:
                # 页面间延迟，避免请求过于频繁
                if i > 1:
                    print(f"⏳ 页面间延迟 {page_delay} 秒...")
                    time.sleep(page_delay)

                # 修改API请求以支持指定页码
                page_data = self.fetch_page_data_with_retry(
                    page=page_num,
                    size=size,
                    max_retries=max_retries,
                    retry_delay=retry_delay
                )

                if page_data:
                    page_records = self.parse_items_to_video_records(page_data)
                    all_video_records.extend(page_records)
                    successful_pages += 1
                    print(f"✅ 第 {page_num} 页处理完成，获得 {len(page_records)} 条记录")
                else:
                    failed_pages += 1
                    print(f"❌ 第 {page_num} 页获取失败")

            except Exception as e:
                failed_pages += 1
                print(f"❌ 第 {page_num} 页处理异常: {e}")

        print(f"\n📊 多页请求完成:")
        print(f"✅ 成功页面: {successful_pages}")
        print(f"❌ 失败页面: {failed_pages}")
        print(f"📋 总记录数: {len(all_video_records)}")

        return all_video_records

    def fetch_multiple_pages_with_retry_enhanced(self,
                                                pages: List[int],
                                                size: int = 50,
                                                max_retries: int = 3,
                                                retry_delay: float = 1.0,
                                                page_delay: float = 0.5,
                                                use_enhanced_parsing: bool = True) -> List[VideoRecord]:
        """
        带重试机制和增强JSON解析的多页API数据获取

        Args:
            pages (List[int]): 要获取的页码列表
            size (int): 每页返回的数据条数
            max_retries (int): 每页的最大重试次数
            retry_delay (float): 重试延迟时间
            page_delay (float): 页面间的延迟时间
            use_enhanced_parsing (bool): 是否使用增强JSON解析

        Returns:
            List[VideoRecord]: 所有页面解析后的视频记录列表
        """
        all_video_records = []
        successful_pages = 0
        failed_pages = 0

        print(f"🚀 开始多页增强API请求，共 {len(pages)} 页")
        print(f"📄 页码: {pages}")
        print(f"🔍 增强解析: {'启用' if use_enhanced_parsing else '禁用'}")

        for i, page_num in enumerate(pages, 1):
            print(f"\n📄 处理第 {i}/{len(pages)} 页 (页码: {page_num})")

            try:
                # 页面间延迟，避免请求过于频繁
                if i > 1:
                    print(f"⏳ 页面间延迟 {page_delay} 秒...")
                    time.sleep(page_delay)

                # 获取页面数据
                page_data = self.fetch_page_data_with_retry(
                    page=page_num,
                    size=size,
                    max_retries=max_retries,
                    retry_delay=retry_delay
                )

                if page_data:
                    # 根据选择使用不同的解析方式
                    if use_enhanced_parsing:
                        print(f"🔍 使用增强解析器处理第 {page_num} 页数据...")
                        page_records = self.parse_api_response_enhanced(page_data)
                    else:
                        print(f"📋 使用标准解析器处理第 {page_num} 页数据...")
                        page_records = self.parse_items_to_video_records(page_data)

                    all_video_records.extend(page_records)
                    successful_pages += 1
                    print(f"✅ 第 {page_num} 页处理完成，获得 {len(page_records)} 条记录")
                else:
                    failed_pages += 1
                    print(f"❌ 第 {page_num} 页获取失败")

            except Exception as e:
                failed_pages += 1
                print(f"❌ 第 {page_num} 页处理异常: {e}")

        print(f"\n📊 多页增强请求完成:")
        print(f"✅ 成功页面: {successful_pages}")
        print(f"❌ 失败页面: {failed_pages}")
        print(f"📋 总记录数: {len(all_video_records)}")

        return all_video_records

    def fetch_page_data_with_retry(self,
                                   page: int = 1,
                                   size: int = 50,
                                   verify_ssl: bool = False,
                                   max_retries: int = 3,
                                   retry_delay: float = 1.0,
                                   backoff_factor: float = 2.0) -> Dict[str, Any]:
        """
        带重试机制的指定页面API数据获取

        Args:
            page (int): 页码
            size (int): 每页返回的数据条数
            verify_ssl (bool): 是否验证SSL证书
            max_retries (int): 最大重试次数
            retry_delay (float): 初始重试延迟时间（秒）
            backoff_factor (float): 延迟时间递增因子

        Returns:
            Dict[str, Any]: API返回的JSON数据
        """
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    delay = retry_delay * (backoff_factor ** (attempt - 1))
                    print(f"⏳ 第 {attempt} 次重试，等待 {delay:.1f} 秒...")
                    time.sleep(delay)

                print(f"🔄 页面 {page} 请求尝试 {attempt + 1}/{max_retries + 1}")

                # 调用指定页面的API请求方法
                result = self.fetch_page_data(page, size, verify_ssl)

                if result:  # 如果获取到数据，直接返回
                    if attempt > 0:
                        print(f"✅ 页面 {page} 重试成功！")
                    return result
                else:
                    if attempt < max_retries:
                        print(f"⚠️ 页面 {page} 第 {attempt + 1} 次请求失败，准备重试...")
                    continue

            except Exception as e:
                if attempt < max_retries:
                    print(f"❌ 页面 {page} 第 {attempt + 1} 次请求异常: {e}，准备重试...")
                else:
                    print(f"❌ 页面 {page} 所有重试都失败，最后错误: {e}")

        print(f"💥 页面 {page} API请求失败，已重试 {max_retries} 次")
        return {}

    def fetch_page_data(self, page: int = 1, size: int = 50, verify_ssl: bool = False) -> Dict[str, Any]:
        """
        获取指定页面的API数据

        Args:
            page (int): 页码
            size (int): 每页返回的数据条数
            verify_ssl (bool): 是否验证SSL证书

        Returns:
            Dict[str, Any]: API返回的JSON数据
        """
        # API接口URL
        base_url = self.config.API_BASE_URL

        # 设置参数，包含页码
        params = {
            "author_id": self.config.DEFAULT_AUTHOR_ID,
            "page": page,
            "size": size
        }

        # 设置请求头
        headers = self.config.DEFAULT_HEADERS

        try:
            print(f"🔄 正在请求API页面 {page}: {base_url}")
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

            print(f"✅ 页面 {page} API请求成功，状态码: {response.status_code}")

            return api_data

        except requests.exceptions.RequestException as e:
            print(f"❌ 页面 {page} API请求失败: {e}")
            return {}
        except json.JSONDecodeError as e:
            print(f"❌ 页面 {page} JSON解析失败: {e}")
            return {}

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

    def parse_api_response_enhanced(self, api_data: Dict[str, Any]) -> List[VideoRecord]:
        """
        使用增强JSON解析器处理API响应数据

        Args:
            api_data (Dict[str, Any]): API返回的数据

        Returns:
            List[VideoRecord]: 解析后的视频记录列表
        """
        print("🔍 使用增强JSON解析器处理API响应...")

        # 创建增强解析器实例
        parser = EnhancedJSONParser()

        # 使用增强解析器处理数据
        parsed_data = parser.parse_api_response(api_data)

        # 获取解析后的items
        items = parsed_data.get('items', [])
        if not items:
            print("⚠️ 增强解析器未找到有效的items数据")
            return []

        video_records = []
        for i, item in enumerate(items):
            try:
                # 确保item是字典格式
                if not isinstance(item, dict):
                    print(f"⚠️ 跳过第 {i+1} 条：不是字典格式")
                    continue

                # 检查必要字段
                if not any(key in item for key in ['description', 'title', 'content']):
                    print(f"⚠️ 跳过第 {i+1} 条：缺少必要字段")
                    continue

                # 准备标准化数据
                description = item.get('description', '') or item.get('content', '') or item.get('title', '')
                if not description:
                    continue

                standardized_data = {
                    'description': str(description),
                    'cover': item.get('cover', ''),
                    'url': item.get('url', ''),
                    'id': item.get('id', ''),
                    'title': item.get('title', '')
                }

                # 创建VideoRecord
                video_record = VideoRecord.from_api_data(standardized_data)
                if video_record and video_record.title:
                    video_records.append(video_record)
                    print(f"✅ 增强解析第 {i+1} 条：{video_record.title}")

            except Exception as e:
                print(f"❌ 增强解析第 {i+1} 条失败: {e}")
                continue

        # 输出解析统计
        stats = parser.get_parse_stats()
        print(f"📊 增强解析完成 - 成功: {len(video_records)}")
        print(f"   字符串对象解析: {stats['string_object_parses']}")
        print(f"   JSON字符串解析: {stats['json_string_parses']}")
        print(f"   降级解析: {stats['fallback_parses']}")

        return video_records
