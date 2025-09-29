import json
import re
from typing import Dict, Any, List

from ..core.config import Config
from ..utils.enhanced_json_parser import EnhancedJSONParser


class DataProcessor:
    """数据处理类"""

    def __init__(self):
        self.config = Config()
        self.enhanced_parser = EnhancedJSONParser()

    def read_json_file(self, file_path: str) -> Dict[str, Any]:
        """
        读取本地JSON文件

        Args:
            file_path (str): JSON文件路径

        Returns:
            Dict[str, Any]: JSON数据
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 尝试标准JSON解析
            try:
                data = json.loads(content)
                return data
            except json.JSONDecodeError:
                # 如果标准解析失败，使用增强解析器
                print("🔄 标准JSON解析失败，尝试增强解析...")
                return self.enhanced_parser.parse_api_response(content)

        except FileNotFoundError:
            print(f"文件 {file_path} 不存在")
            return {}
        except Exception as e:
            print(f"读取文件时发生错误: {e}")
            return {}

    def read_json_file_enhanced(self, file_path: str) -> Dict[str, Any]:
        """
        使用增强解析器读取JSON文件，支持复杂格式

        Args:
            file_path (str): JSON文件路径

        Returns:
            Dict[str, Any]: 解析后的数据
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            print(f"📖 使用增强解析器读取文件: {file_path}")
            parsed_data = self.enhanced_parser.parse_api_response(content)

            # 输出解析统计
            stats = self.enhanced_parser.get_parse_stats()
            if stats['total_items'] > 0:
                print(f"📊 文件解析统计:")
                print(f"   总项目数: {stats['total_items']}")
                print(f"   字符串对象解析: {stats['string_object_parses']}")
                print(f"   JSON字符串解析: {stats['json_string_parses']}")
                print(f"   降级解析: {stats['fallback_parses']}")

            return parsed_data

        except FileNotFoundError:
            print(f"❌ 文件不存在: {file_path}")
            return {}
        except Exception as e:
            print(f"❌ 增强解析文件时发生错误: {e}")
            return {}

    @staticmethod
    def clean_title(title: str) -> str:
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

    def extract_title_from_description(self, description: str) -> str:
        """
        从description中提取标题内容

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
            return self.clean_title(title)

        # 方法2: 如果没有【】格式，提取第一个#之前的内容
        pattern2 = r'^([^#]+?)(?:\s*#|$)'
        match2 = re.search(pattern2, description)
        if match2:
            title = match2.group(1).strip()
            return self.clean_title(title)

        # 方法3: 如果都没有匹配，返回前100个字符
        raw_title = description[:100] + "..." if len(description) > 100 else description
        return self.clean_title(raw_title)

    def extract_items_data(self, json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从JSON数据中提取items下每项的id、url、description、cover字段，并提取标题

        Args:
            json_data (Dict[str, Any]): 完整的JSON数据

        Returns:
            List[Dict[str, Any]]: 提取的字段列表
        """
        extracted_items = []

        if 'items' not in json_data:
            print("JSON数据中没有找到'items'字段")
            return extracted_items

        items = json_data['items']

        for item in items:
            description = item.get('description', '')
            title = self.extract_title_from_description(description)

            extracted_item = {
                'id': item.get('id', ''),
                'url': item.get('url', ''),
                'title': title,
                'description': description,
                'cover': item.get('cover', '')
            }
            extracted_items.append(extracted_item)

        return extracted_items

    def save_extracted_data(self, extracted_data: List[Dict[str, Any]],
                           output_file: str = None) -> None:
        """
        保存提取的数据到新的JSON文件

        Args:
            extracted_data (List[Dict[str, Any]]): 提取的数据
            output_file (str): 输出文件名
        """
        if output_file is None:
            output_file = self.config.EXTRACTED_ITEMS_FILE

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(extracted_data, f, ensure_ascii=False, indent=2)
            print(f"提取的数据已保存到 {output_file}")
        except Exception as e:
            print(f"保存文件时发生错误: {e}")

    def display_video_list(self, json_file: str = None) -> List[Dict[str, Any]]:
        """
        显示视频列表，供用户选择

        Args:
            json_file (str): 包含视频信息的JSON文件

        Returns:
            List[Dict[str, Any]]: 视频数据列表
        """
        if json_file is None:
            json_file = self.config.EXTRACTED_ITEMS_FILE

        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if not data:
                print("❌ 没有找到视频数据")
                return []

            print(f"\n📺 视频列表 (共 {len(data)} 个视频):")
            print("=" * 80)

            for i, item in enumerate(data, 1):
                title = item.get('title', f"Video_{item.get('id', i)}")
                video_id = item.get('id', 'Unknown')
                url = item.get('url', '')
                cover = item.get('cover', '')

                print(f"\n[{i:2d}] {title}")
                print(f"     ID: {video_id}")
                print(f"     URL: {url}")
                if cover:
                    print(f"     封面: {cover}")
                print()

            return data

        except FileNotFoundError:
            print(f"❌ 文件不存在: {json_file}")
            return []
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}")
            return []
        except Exception as e:
            print(f"❌ 读取文件时发生错误: {e}")
            return []

    def save_extracted_items(self, extracted_data: List[Dict[str, Any]],
                           output_file: str = None) -> None:
        """
        保存提取的数据到新的JSON文件 (别名方法)

        Args:
            extracted_data (List[Dict[str, Any]]): 提取的数据
            output_file (str): 输出文件名
        """
        self.save_extracted_data(extracted_data, output_file)

    def parse_local_json_with_uid(self, file_path: str) -> List[Dict[str, Any]]:
        """
        从本地JSON文件解析数据，特别提取UID字段

        Args:
            file_path (str): JSON文件路径

        Returns:
            List[Dict[str, Any]]: 解析后的数据列表，包含UID字段
        """
        try:
            json_data = self.read_json_file_enhanced(file_path)

            if not json_data or 'items' not in json_data:
                print("❌ JSON文件中没有找到有效的items数据")
                return []

            items = json_data['items']
            processed_items = []

            print(f"📋 开始解析 {len(items)} 条数据项，查找UID字段...")

            for i, item in enumerate(items):
                try:
                    if isinstance(item, dict):
                        # 提取UID字段
                        uid = self._extract_uid_from_item(item)

                        # 创建标准化的数据项
                        processed_item = {
                            'description': item.get('description', '') or item.get('content', '') or item.get('title', ''),
                            'cover': item.get('cover', ''),
                            'url': item.get('url', ''),
                            'id': item.get('id', ''),
                            'title': item.get('title', ''),
                            'uid': uid
                        }

                        # 只有当描述信息存在时才添加
                        if processed_item['description']:
                            processed_items.append(processed_item)
                            if uid:
                                print(f"✅ 第 {i+1} 条：找到UID = {uid}")
                            else:
                                print(f"⚠️ 第 {i+1} 条：未找到UID字段")

                except Exception as e:
                    print(f"❌ 处理第 {i+1} 条数据时出错: {e}")
                    continue

            print(f"🎯 本地JSON解析完成 - 成功处理: {len(processed_items)} 条")
            uid_count = sum(1 for item in processed_items if item.get('uid'))
            print(f"📊 找到UID的数据: {uid_count} 条")

            return processed_items

        except Exception as e:
            print(f"❌ 解析本地JSON文件失败: {e}")
            return []

    @staticmethod
    def _extract_uid_from_item(item: Dict[str, Any]) -> str:
        """
        从数据项中提取UID字段

        Args:
            item (Dict[str, Any]): 数据项

        Returns:
            str: 提取的UID，如果没有找到则返回空字符串
        """
        if not isinstance(item, dict):
            return ""

        # 直接查找uid字段
        if 'uid' in item and item['uid']:
            return str(item['uid']).strip()

        # 在URL中查找UID
        url = item.get('url', '')
        if url and isinstance(url, str):
            # 查找类似 videodelivery.net/{uid}/manifest 的模式
            import re
            match = re.search(r'videodelivery\.net/([^/]+)/manifest', url)
            if match:
                return match.group(1)

        # 在描述中查找UID模式
        description = item.get('description', '') or item.get('content', '')
        if description and isinstance(description, str):
            import re
            # 查找"uid="后面的内容
            match = re.search(r'uid[=:]\s*([a-f0-9]{32})', description, re.IGNORECASE)
            if match:
                return match.group(1)

            # 查找32位十六进制字符串（UID的常见格式）
            match = re.search(r'\b([a-f0-9]{32})\b', description, re.IGNORECASE)
            if match:
                return match.group(1)

        return ""
