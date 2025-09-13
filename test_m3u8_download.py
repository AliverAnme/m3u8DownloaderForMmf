#!/usr/bin/env python3
"""
测试m3u8视频下载功能
"""
import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from test import check_ffmpeg, parse_m3u8, download_m3u8_video

def test_ffmpeg():
    """测试FFmpeg是否可用"""
    print("=== 测试FFmpeg ===")
    if check_ffmpeg():
        print("✅ FFmpeg可用")
    else:
        print("❌ FFmpeg不可用")

def test_m3u8_parsing():
    """测试m3u8解析功能"""
    print("\n=== 测试M3U8解析 ===")

    # 使用extracted_items.json中的一个URL进行测试
    try:
        import json
        with open('extracted_items.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        if data and len(data) > 0:
            test_url = data[0]['url']
            print(f"测试URL: {test_url[:50]}...")

            playlist = parse_m3u8(test_url)
            if playlist:
                print("✅ M3U8解析成功")
                print(f"是否有多个质量选项: {'是' if playlist.playlists else '否'}")
                print(f"片段数量: {len(playlist.segments) if playlist.segments else 0}")
            else:
                print("❌ M3U8解析失败")
        else:
            print("⚠️ 没有找到测试数据")
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")

def test_single_download():
    """测试单个视频下载"""
    print("\n=== 测试单个视频下载 ===")

    try:
        import json
        with open('extracted_items.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        if data and len(data) > 0:
            # 选择第一个视频进行测试
            test_item = data[0]
            video_url = test_item['url']
            title = test_item['title']

            print(f"测试下载视频: {title}")
            print(f"URL: {video_url[:50]}...")

            # 创建测试下载目录
            test_dir = "test_download"

            success = download_m3u8_video(video_url, test_dir, f"TEST_{title[:30]}", max_quality=True)

            if success:
                print("✅ 视频下载测试成功！")
            else:
                print("❌ 视频下载测试失败")
        else:
            print("⚠️ 没有找到测试数据")
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")

if __name__ == "__main__":
    test_ffmpeg()
    test_m3u8_parsing()

    # 询问是否进行实际下载测试
    download_test = input("\n是否进行实际视频下载测试? (y/n, 默认n): ").strip().lower()
    if download_test == 'y':
        test_single_download()
    else:
        print("跳过视频下载测试")
