#!/usr/bin/env python3
"""
视频下载器主程序入口
使用模块化架构的新版本
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from video_downloader import VideoDownloaderApp


def main():
    """主函数"""
    try:
        app = VideoDownloaderApp()
        app.run()
    except KeyboardInterrupt:
        print("\n\n👋 用户中断程序，退出")
    except Exception as e:
        print(f"❌ 程序运行时发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
