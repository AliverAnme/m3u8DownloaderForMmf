#!/usr/bin/env python3

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from video_downloader import VideoDownloaderApp


def main():
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
