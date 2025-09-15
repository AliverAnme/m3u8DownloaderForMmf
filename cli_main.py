#!/usr/bin/env python3
"""
命令行界面版视频下载器 - 主入口文件
"""

import sys
import os

# 将项目根目录添加到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from video_downloader.core.cli_app import CLIVideoDownloaderApp


def main():
    """
    主函数 - 运行命令行界面版视频下载器
    """
    try:
        print("🚀 启动命令行视频下载器")

        # 创建并运行CLI应用
        app = CLIVideoDownloaderApp()
        app.run()

    except KeyboardInterrupt:
        print("\n\n👋 用户中断程序，正在安全退出...")
    except Exception as e:
        print(f"❌ 程序运行时发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
