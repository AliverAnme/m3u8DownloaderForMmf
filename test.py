import requests
import json
import os
import urllib3
import re
from typing import Dict, Any, Optional, List

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def fetch_posts_from_api(size: int = 50, verify_ssl: bool = False) -> Dict[str, Any]:
    """
    从API接口获取posts数据并保存到本地

    Args:
        size (int): 每页返回的数据条数，默认为50
        verify_ssl (bool): 是否验证SSL证书，默认为False

    Returns:
        Dict[str, Any]: API返回的JSON数据
    """
    # API接口URL
    base_url = "https://api.memefans.ai/v2/posts/"

    # 固定参数
    params = {
        "author_id": "BhhLJPlVvjU",
        "page": 1,
        "size": size
    }

    # 设置请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    try:
        print(f"正在请求API: {base_url}")
        print(f"参数: {params}")
        print(f"SSL验证: {'启用' if verify_ssl else '禁用'}")

        # 发送GET请求，禁用SSL验证并设置超时
        response = requests.get(
            base_url,
            params=params,
            headers=headers,
            verify=verify_ssl,  # 禁用SSL证书验证
            timeout=30  # 设置30秒超时
        )
        response.raise_for_status()  # 检查HTTP错误

        # 解析JSON数据
        data = response.json()

        # 保存到本地文件
        output_file = "api_response.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"数据已成功保存到 {output_file}")
        print(f"获取到 {len(data.get('items', []))} 条记录")

        return data

    except requests.exceptions.SSLError as e:
        print(f"SSL错误: {e}")
        print("尝试禁用SSL验证重新请求...")
        if verify_ssl:
            # 如果之前启用了SSL验证，现在禁用重试
            return fetch_posts_from_api(size, verify_ssl=False)
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


def read_json_file(file_path: str) -> Dict[str, Any]:
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


def extract_title_from_description(description: str) -> str:
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
    # 匹配模式：【xxxx】后面的内容直到遇到 # 或者特定关键词
    pattern1 = r'【[^】]+】([^#]+?)(?:\s*#|\s*$)'
    match1 = re.search(pattern1, description)
    if match1:
        title = match1.group(0).strip()
        # 移除末尾的空格和特殊字符
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


def extract_items_data(json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
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
        # 提取基本字段
        description = item.get('description', '')

        # 提取标题
        title = extract_title_from_description(description)

        extracted_item = {
            'id': item.get('id', ''),
            'url': item.get('url', ''),
            'title': title,  # 新增标题字段
            'description': description,
            'cover': item.get('cover', '')
        }
        extracted_items.append(extracted_item)

    return extracted_items


def save_extracted_data(extracted_data: List[Dict[str, Any]], output_file: str = "extracted_items.json"):
    """
    保存提取的数据到新的JSON文件

    Args:
        extracted_data (List[Dict[str, Any]]): 提取的数据
        output_file (str): 输出文件名
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(extracted_data, f, ensure_ascii=False, indent=2)
        print(f"提取的数据已保存到 {output_file}")
    except Exception as e:
        print(f"保存文件时发生错误: {e}")


def process_posts_data(data: Dict[str, Any]) -> None:
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


def complete_workflow(size: int = 50) -> List[Dict[str, Any]]:
    """
    完整工作流程：从API获取数据 -> 保存到本地 -> 提取指定字段 -> 保存提取结果

    Args:
        size (int): 每页返回的数据条数，默认为50

    Returns:
        List[Dict[str, Any]]: 提取的字段列表
    """
    print("=== 开始完整工作流程 ===")

    # 步骤1：从API获取数据
    print("\n步骤1: 从API获取数据...")
    api_data = fetch_posts_from_api(size, verify_ssl=False)  # 默认禁用SSL验证

    if not api_data:
        print("❌ 从API获取数据失败，工作流程中断")
        return []

    # 步骤2：显示API数据概览
    print("\n步骤2: 处理API数据...")
    process_posts_data(api_data)

    # 步骤3：提取指定字段
    print("\n步骤3: 提取指定字段 (id、url、title、description、cover)...")
    extracted_items = extract_items_data(api_data)

    if not extracted_items:
        print("❌ 提取字段失败")
        return []

    print(f"✅ 成功提取了 {len(extracted_items)} 条记录")

    # 步骤4：保存提取的数据
    print("\n步骤4: 保存提取的数据...")
    save_extracted_data(extracted_items)

    # 步骤5：显示提取结果预览
    print("\n步骤5: 显示提取结果预览...")
    print("前5条提取的记录:")
    for i, item in enumerate(extracted_items[:5], 1):
        print(f"\n记录 {i}:")
        print(f"  ID: {item['id']}")
        print(f"  标题: {item['title']}")  # 显示提取的标题
        print(f"  URL: {item['url'][:50]}..." if len(item['url']) > 50 else f"  URL: {item['url']}")
        print(f"  封面: {item['cover']}")
        print(f"  完整描述: {item['description'][:150]}..." if len(item['description']) > 150 else f"  完整描述: {item['description']}")

    print("\n=== 完整工作流程执行完成 ===")
    return extracted_items


if __name__ == "__main__":
    # 选择执行模式
    print("请选择执行模式:")
    print("1. 完整工作流程 (API获取 -> 提取字段 -> 保存)")
    print("2. 仅从本地JSON文件提取字段")
    print("3. 仅从API获取数据")

    mode = input("请输入选择 (1/2/3, 默认为1): ").strip() or "1"

    if mode == "1":
        # 完整工作流程
        size = input("请输入每页数据条数 (默认50): ").strip()
        size = int(size) if size.isdigit() else 50

        extracted_items = complete_workflow(size)

        if extracted_items:
            print(f"\n🎉 工作流程成功完成！共处理了 {len(extracted_items)} 条记录")
        else:
            print("\n❌ 工作流程执行失败")

    elif mode == "2":
        # 仅从本地JSON文件提取字段
        print("\n=== 从JSON文件中提取数据 ===")

        json_file_path = input("请输入JSON文件路径 (默认example.json): ").strip() or "example.json"
        json_data = read_json_file(json_file_path)

        if json_data:
            extracted_items = extract_items_data(json_data)

            if extracted_items:
                print(f"成功提取了 {len(extracted_items)} 条记录")
                save_extracted_data(extracted_items)

                # 显示前5条记录作为示例
                print("\n前5条提取的记录:")
                for i, item in enumerate(extracted_items[:5], 1):
                    print(f"\n记录 {i}:")
                    print(f"  ID: {item['id']}")
                    print(f"  标题: {item['title']}")  # 显示提取的标题
                    print(f"  URL: {item['url'][:50]}..." if len(item['url']) > 50 else f"  URL: {item['url']}")
                    print(f"  封面: {item['cover']}")
                    print(f"  完整描述: {item['description'][:150]}..." if len(item['description']) > 150 else f"  完整描述: {item['description']}")
            else:
                print("没有提取到任何数据")
        else:
            print("无法读取JSON文件")

    elif mode == "3":
        # 仅从API获取数据
        print("\n=== 从API获取数据 ===")

        size = input("请输入每页数据条数 (默认50): ").strip()
        size = int(size) if size.isdigit() else 50

        # 询问是否启用SSL验证
        ssl_choice = input("是否启用SSL证书验证? (y/n, 默认n): ").strip().lower()
        verify_ssl = ssl_choice == 'y'

        api_data = fetch_posts_from_api(size, verify_ssl=verify_ssl)

        if api_data:
            process_posts_data(api_data)
            print("✅ API数据获取完成")
        else:
            print("❌ API数据获取失败")

    else:
        print("❌ 无效的选择，程序退出")
