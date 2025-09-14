#!/usr/bin/env python3
"""
快速启动脚本 - 带重复检测功能的视频下载器
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from video_downloader.core.enhanced_app import EnhancedVideoDownloaderApp
from video_downloader.database.manager import DatabaseManager


def quick_start():
    """快速启动带重复检测的视频下载器"""

    print("🎬 视频下载器 - 重复检测版本")
    print("=" * 50)

    try:
        # 初始化数据库管理器
        db_manager = DatabaseManager()

        # 显示当前数据库状态
        stats = db_manager.get_statistics()
        total_videos = stats.get('total', 0)
        completed_videos = stats.get('completed', 0)
        uploaded_videos = stats.get('uploaded', 0)

        print(f"📊 数据库状态: 总共 {total_videos} 个视频")
        if total_videos > 0:
            print(f"   ✅ 已完成: {completed_videos}")
            print(f"   ☁️ 已上传: {uploaded_videos}")
            print(f"   💡 重复检测: 已启用")
        else:
            print("   📝 数据库为空，首次运行")

        print("\n🚀 启动功能:")
        print("   ✓ 自动检测重复视频")
        print("   ✓ 跳过已下载内容")
        print("   ✓ 支持云存储上传")
        print("   ✓ 数据库状态管理")

        print("\n" + "="*50)

        # 启动增强版应用
        app = EnhancedVideoDownloaderApp(server_mode=False)
        app.run()

    except KeyboardInterrupt:
        print("\n\n👋 程序已退出")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        print("💡 提示: 请确保所有依赖包已正确安装")


if __name__ == "__main__":
    quick_start()
