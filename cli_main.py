#!/usr/bin/env python3
"""
命令行界面版视频下载器 - 主入口文件
"""

import sys
import os
# import importlib

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

    # 强制清除__pycache__
    import shutil
    pycache_dirs = [
        'video_downloader/__pycache__',
        'video_downloader/api/__pycache__',
        'video_downloader/core/__pycache__',
        'video_downloader/database/__pycache__',
        'video_downloader/download/__pycache__',
        'video_downloader/ui/__pycache__',
        'video_downloader/utils/__pycache__',
        'video_downloader/cloud/__pycache__'
    ]

    for pycache_dir in pycache_dirs:
        if os.path.exists(pycache_dir):
            try:
                shutil.rmtree(pycache_dir)
                print(f"🗑️ 清除缓存目录: {pycache_dir}")
            except Exception as e:
                print(f"⚠️ 清除缓存失败 {pycache_dir}: {e}")

# 清除缓存并重新导入
clear_module_cache()

# 强制重新导入
# import importlib
if 'video_downloader.api.memefans_client' in sys.modules:
    del sys.modules['video_downloader.api.memefans_client']

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
