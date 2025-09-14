#!/usr/bin/env python3

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from video_downloader.core.enhanced_app import EnhancedVideoDownloaderApp
from video_downloader.database.manager import DatabaseManager
from video_downloader.database.models import VideoRecord, DownloadStatus


def main():
    """
    主函数 - 运行带重复检测功能的视频下载器
    """
    try:
        print("🚀 启动增强版视频下载器（带重复检测功能）")
        print("=" * 60)

        # 创建增强版应用实例（交互模式）
        app = EnhancedVideoDownloaderApp(server_mode=False)

        # 显示数据库统计信息
        show_database_stats(app.db_manager)

        # 运行应用
        app.run()

    except KeyboardInterrupt:
        print("\n\n👋 用户中断程序，正在安全退出...")
    except Exception as e:
        print(f"❌ 程序运行时发生错误: {e}")
        import traceback
        traceback.print_exc()


def show_database_stats(db_manager: DatabaseManager):
    """显示数据库统计信息"""
    try:
        stats = db_manager.get_statistics()

        print("\n📊 当前数据库状态:")
        print("-" * 30)
        print(f"📺 总视频数: {stats.get('total', 0)}")
        print(f"⏳ 待下载: {stats.get('pending', 0)}")
        print(f"⬇️ 下载中: {stats.get('downloading', 0)}")
        print(f"✅ 已完成: {stats.get('completed', 0)}")
        print(f"☁️ 已上传: {stats.get('uploaded', 0)}")
        print(f"❌ 失败: {stats.get('failed', 0)}")

        total_size = stats.get('total_size', 0)
        if total_size > 0:
            size_gb = total_size / (1024 * 1024 * 1024)
            print(f"💾 总大小: {size_gb:.2f} GB")

        print("-" * 30)
        print("💡 提示: 程序会自动检测并跳过已下载的视频")
        print()

    except Exception as e:
        print(f"⚠️ 获取数据库统计失败: {e}")


if __name__ == "__main__":
    main()
