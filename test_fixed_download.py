#!/usr/bin/env python3
"""
测试修复后的m3u8视频下载功能
"""
import sys
import os
import json

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_fixed_download():
    """测试修复后的下载功能"""
    try:
        from test import download_m3u8_video, check_ffmpeg

        print("=== 测试修复后的功能 ===")

        # 检查FFmpeg
        if not check_ffmpeg():
            print("❌ FFmpeg不可用，无法进行测试")
            return

        print("✅ FFmpeg可用")

        # 读取测试数据
        with open('extracted_items.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not data:
            print("❌ 没有测试数据")
            return

        test_item = data[0]
        print(f"\n测试视频: {test_item['title'][:50]}...")
        print(f"URL: {test_item['url'][:50]}...")

        # 进行测试下载
        test_dir = "test_fixed_download"
        test_title = f"FIXED_TEST_{test_item['title'][:30]}"

        print(f"\n开始下载到目录: {test_dir}")
        success = download_m3u8_video(test_item['url'], test_dir, test_title, True)

        if success:
            print("\n✅ 修复后的下载功能测试成功！")

            # 检查输出文件
            import os
            if os.path.exists(test_dir):
                files = os.listdir(test_dir)
                print(f"输出文件: {files}")
        else:
            print("\n❌ 修复后的下载功能测试失败")

    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_fixed_download()
