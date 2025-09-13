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

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class APIClient:

    def __init__(self):
        self.config = Config()

    def fetch_posts_from_api(self, size: int = 50, verify_ssl: bool = False) -> Dict[str, Any]:
        """
        从API接口获取posts数据并保存到本地

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
            print(f"正在请求API: {base_url}")
            print(f"参数: {params}")
            print(f"SSL验证: {'启用' if verify_ssl else '禁用'}")

            # 发送GET请求，禁用SSL验证并设置超时
            response = requests.get(
                base_url,
                params=params,
                headers=headers,
                verify=verify_ssl,
                timeout=self.config.API_TIMEOUT
            )
            response.raise_for_status()

            # 解析JSON数据
            data = response.json()

            # 保存到本地文件
            output_file = self.config.API_RESPONSE_FILE
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"数据已成功保存到 {output_file}")
            print(f"获取到 {len(data.get('items', []))} 条记录")

            return data

        except requests.exceptions.SSLError as e:
            print(f"SSL错误: {e}")
            print("尝试禁用SSL验证重新请求...")
            if verify_ssl:
                return self.fetch_posts_from_api(size, verify_ssl=False)
            else:
                print("SSL验证已禁用，但仍然出现SSL错误")
                return {}
        except requests.exceptions.RequestException as e:
            print(f"API请求失败: {e}")
            print(f"错误类型: {type(e).__name__}")
            return {}
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            print("响应内容可能不是有效的JSON格式")
            return {}
        except Exception as e:
            print(f"发生未知错误: {e}")
            print(f"错误类型: {type(e).__name__}")
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
