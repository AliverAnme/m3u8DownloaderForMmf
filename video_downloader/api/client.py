"""
API相关功能模块
处理API数据获取、解析和保存
"""

import requests
import json
import urllib3
from typing import Dict, Any, List

from ..core.config import Config

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class APIClient:
    """API客户端类"""

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
            title = item.get('title', 'No title')
            likes = item.get('likes_count', 0)
            comments = item.get('comments_count', 0)
            print(f"{i}. {title} (👍{likes} 💬{comments})")
