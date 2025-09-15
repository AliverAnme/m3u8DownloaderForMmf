#!/usr/bin/env python3
"""
命令行界面版视频下载器 - 主入口文件
"""

import sys
import os
import importlib

# 将项目根目录添加到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 清除可能的模块缓存
def clear_module_cache():
    """清除video_downloader相关的模块缓存"""
    modules_to_remove = []
    for module_name in sys.modules:
        if module_name.startswith('video_downloader'):
            modules_to_remove.append(module_name)

    for module_name in modules_to_remove:
        del sys.modules[module_name]

# 清除缓存并重新导入
clear_module_cache()

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
