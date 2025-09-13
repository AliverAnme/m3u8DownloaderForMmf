#!/usr/bin/env python3
"""
测试封面图片下载功能
"""
import sys
import os
from pathlib import Path

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from test import download_cover_image, read_json_file

def test_cover_download():
    """测试封面图片下载功能"""
    print("=== 测试封面图片下载功能 ===\n")

    # 创建测试目录
    test_dir = Path("test_cover_download")
    test_dir.mkdir(exist_ok=True)

    # 测试1: 从extracted_items.json获取真实的封面URL
    print("测试1: 从extracted_items.json获取真实封面URL")
    try:
        json_data = read_json_file('extracted_items.json')
        if json_data and len(json_data) > 0:
            # 获取第一个有封面的项目
            test_item = None
            for item in json_data[:5]:  # 检查前5个项目
                if item.get('cover'):
                    test_item = item
                    break

            if test_item:
                cover_url = test_item['cover']
                title = test_item['title']

                print(f"视频标题: {title[:50]}...")
                print(f"封面URL: {cover_url}")

                # 下载封面
                cover_file = download_cover_image(cover_url, test_dir)

                if cover_file and cover_file.exists():
                    file_size = cover_file.stat().st_size
                    print(f"✅ 封面下载成功!")
                    print(f"文件路径: {cover_file}")
                    print(f"文件大小: {file_size} bytes")
                    print(f"文件扩展名: {cover_file.suffix}")

                    # 检查是否是图片文件
                    if cover_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                        print("✅ 文件格式正确")
                    else:
                        print(f"⚠️ 文件格式可能不正确: {cover_file.suffix}")
                else:
                    print("❌ 封面下载失败")
            else:
                print("⚠️ 没有找到包含封面的视频项目")
        else:
            print("⚠️ 无法读取extracted_items.json或数据为空")
    except Exception as e:
        print(f"❌ 测试1失败: {e}")

    print("\n" + "="*50)

    # 测试2: 测试常见的图片URL格式
    print("测试2: 测试不同格式的图片URL")

    test_urls = [
        # 测试JPG格式
        "https://httpbin.org/image/jpeg",
        # 测试PNG格式
        "https://images.memefans.ai/5cb58af1-d859-4e84-844a-73217d0eb3f6",
        # 测试WebP格式
        "https://httpbin.org/image/webp"
    ]

    for i, url in enumerate(test_urls, 1):
        print(f"\n测试URL {i}: {url}")
        try:
            cover_file = download_cover_image(url, test_dir)
            if cover_file and cover_file.exists():
                file_size = cover_file.stat().st_size
                print(f"✅ 下载成功: {cover_file.name}, 大小: {file_size} bytes")
            else:
                print("❌ 下载失败")
        except Exception as e:
            print(f"❌ 下载异常: {e}")

    print("\n" + "="*50)
    print("测试完成! 检查test_cover_download目录中的文件")

    # 列出下载的文件
    if test_dir.exists():
        files = list(test_dir.glob("*"))
        if files:
            print(f"\n下载的文件列表:")
            for file in files:
                file_size = file.stat().st_size
                print(f"  - {file.name} ({file_size} bytes)")
        else:
            print("\n没有下载任何文件")

def test_png_specific():
    """专门测试PNG格式图片下载"""
    print("\n=== 专门测试PNG格式下载 ===")

    test_dir = Path("test_png_download")
    test_dir.mkdir(exist_ok=True)

    # 使用一个确定返回PNG格式的URL
    png_url = "https://httpbin.org/image/png"

    print(f"测试PNG URL: {png_url}")

    try:
        cover_file = download_cover_image(png_url, test_dir)

        if cover_file and cover_file.exists():
            file_size = cover_file.stat().st_size
            print(f"✅ PNG下载成功!")
            print(f"文件路径: {cover_file}")
            print(f"文件大小: {file_size} bytes")
            print(f"文件扩展名: {cover_file.suffix}")

            if cover_file.suffix.lower() == '.png':
                print("✅ 文件格式正确，确认为PNG格式")
            else:
                print(f"⚠️ 文件扩展名不是PNG: {cover_file.suffix}")
        else:
            print("❌ PNG下载失败")

    except Exception as e:
        print(f"❌ PNG下载异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_cover_download()
    test_png_specific()
