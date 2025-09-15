import json
import re
from typing import Dict, Any, List

from ..core.config import Config


class DataProcessor:
    """数据处理类"""

    def __init__(self):
        self.config = Config()

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
                data = json.load(f)
            return data
        except FileNotFoundError:
            print(f"文件 {file_path} 不存在")
            return {}
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            return {}
        except Exception as e:
            print(f"读取文件时发生错误: {e}")
            return {}

    def clean_title(self, title: str) -> str:
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
