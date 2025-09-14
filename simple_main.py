#!/usr/bin/env python3
"""
简化版视频下载器 - 专注于重复检测功能，不依赖复杂的调度器
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from video_downloader.api.client import APIClient
from video_downloader.utils.data_processor import DataProcessor
from video_downloader.download.manager import DownloadManager
from video_downloader.ui.interface import UserInterface
from video_downloader.core.config import Config
from video_downloader.database.manager import DatabaseManager
from video_downloader.database.models import VideoRecord, DownloadStatus


class SimpleVideoDownloaderApp:
    """简化版视频下载器应用 - 专注于重复检测"""

    def __init__(self):
        self.config = Config()

        # 初始化基础组件
        self.api_client = APIClient()
        self.data_processor = DataProcessor()
        self.download_manager = DownloadManager()
        self.ui = UserInterface()
        self.db_manager = DatabaseManager(getattr(self.config, 'DATABASE_FILE', 'video_downloader.db'))

        # 创建必要的目录
        os.makedirs(self.config.DEFAULT_DOWNLOADS_DIR, exist_ok=True)

    def show_menu(self) -> str:
        """显示菜单"""
        print("\n" + "="*60)
        print("🎬 视频下载器 - 重复检测版本")
        print("="*60)
        print("📊 功能选项:")
        print("  1. 完整工作流程 (API -> 检测重复 -> 下载)")
        print("  2. 从本地JSON文件提取并下载")
        print("  3. 仅从API获取数据")
        print("  4. 下载单个m3u8视频")
        print("  5. 批量下载视频")
        print("  6. 交互式选择下载")
        print("  7. 数据库管理")
        print("  8. 查看统计信息")
        print("="*60)

        choice = input("请选择功能 (1-8): ").strip()
        return choice

    def handle_mode_1(self):
        """处理模式1：完整工作流程（带重复检测）"""
        size = input("请输入每页数据条数 (默认50): ").strip()
        size = int(size) if size.isdigit() else 50

        print("=== 开始完整工作流程（重复检测版本） ===")

        # 获取API数据
        print("\n步骤1: 从API获取数据...")
        api_data = self.api_client.fetch_posts_from_api(size, verify_ssl=False)
        if not api_data:
            print("❌ 从API获取数据失败")
            return

        # 提取视频数据
        print("\n步骤2: 提取视频数据...")
        extracted_items = self.data_processor.extract_items_data(api_data)
        if not extracted_items:
            print("❌ 提取数据失败")
            return

        # 重复检测和分类
        print("\n步骤3: 检测重复视频...")
        new_videos = []
        duplicate_videos = []
        failed_videos = []

        for item in extracted_items:
            video_id = item.get('id')
            if not video_id:
                continue

            existing_video = self.db_manager.get_video(video_id)
            if existing_video:
                if existing_video.download_status in [DownloadStatus.COMPLETED, DownloadStatus.UPLOADED]:
                    duplicate_videos.append(item)
                    print(f"⚠️  跳过已下载: {item.get('title', 'Unknown')}")
                elif existing_video.download_status == DownloadStatus.FAILED:
                    failed_videos.append(item)
                    print(f"🔄 可重试视频: {item.get('title', 'Unknown')}")
                else:
                    print(f"⏳ 处理中视频: {item.get('title', 'Unknown')} (状态: {existing_video.download_status.value})")
            else:
                # 添加新视频到数据库
                video_record = VideoRecord(
                    id=video_id,
                    title=item.get('title', ''),
                    url=item.get('url', ''),
                    description=item.get('description', ''),
                    cover=item.get('cover', ''),
                    download_status=DownloadStatus.PENDING
                )

                if self.db_manager.add_video(video_record):
                    new_videos.append(item)
                    print(f"🆕 发现新视频: {item.get('title', 'Unknown')}")

        print(f"\n📊 检测结果:")
        print(f"   🆕 新视频: {len(new_videos)} 个")
        print(f"   ⚠️  重复视频: {len(duplicate_videos)} 个")
        print(f"   🔄 可重试视频: {len(failed_videos)} 个")

        # 下载选择
        if new_videos or failed_videos:
            download_videos = []

            if new_videos:
                choice = input(f"\n是否下载 {len(new_videos)} 个新视频? (y/n): ").strip().lower()
                if choice == 'y':
                    download_videos.extend(new_videos)

            if failed_videos:
                choice = input(f"\n是否重新下载 {len(failed_videos)} 个失败视频? (y/n): ").strip().lower()
                if choice == 'y':
                    download_videos.extend(failed_videos)

            if download_videos:
                self._download_videos(download_videos)
        else:
            print("\n💡 没有需要下载的视频")

    def _download_videos(self, videos):
        """下载视频列表"""
        print(f"\n开始下载 {len(videos)} 个视频...")

        for i, video in enumerate(videos, 1):
            video_id = video.get('id')
            title = video.get('title', 'Unknown')

            print(f"\n[{i}/{len(videos)}] 下载: {title}")

            # 更新状态为下载中
            self.db_manager.update_video_status(video_id, DownloadStatus.DOWNLOADING)

            # 执行下载
            success = self.download_manager.download_m3u8_video(
                video.get('url'),
                self.config.DEFAULT_DOWNLOADS_DIR,
                title,
                max_quality=True,
                cover_url=video.get('cover')
            )

            if success:
                # 查找下载的文件
                download_path = self._find_downloaded_file(title, video_id)
                if download_path:
                    file_size = os.path.getsize(download_path)
                    self.db_manager.update_video_status(
                        video_id,
                        DownloadStatus.COMPLETED,
                        download_path,
                        file_size
                    )
                    print(f"✅ 下载成功: {title}")
                else:
                    self.db_manager.update_video_status(video_id, DownloadStatus.FAILED)
                    print(f"❌ 文件未找到: {title}")
            else:
                self.db_manager.update_video_status(video_id, DownloadStatus.FAILED)
                print(f"❌ 下载失败: {title}")

    def _find_downloaded_file(self, title: str, video_id: str) -> str:
        """查找下载的文件路径"""
        download_dir = self.config.DEFAULT_DOWNLOADS_DIR

        if not os.path.exists(download_dir):
            return None

        import glob
        import re

        # 清理文件名
        safe_title = re.sub(r'[^\w\s-]', '', title)[:50] if title else ''
        safe_video_id = re.sub(r'[^\w-]', '', video_id)[:20] if video_id else ''

        # 搜索模式
        patterns = []
        if safe_title:
            patterns.extend([f"{safe_title}*.mp4", f"{safe_title}*.mkv"])
        if safe_video_id:
            patterns.extend([f"*{safe_video_id}*.mp4", f"*{safe_video_id}*.mkv"])

        for pattern in patterns:
            files = glob.glob(os.path.join(download_dir, pattern))
            if files:
                return files[0]

        return None

    def handle_database_operations(self):
        """处理数据库操作"""
        print("\n=== 数据库管理 ===")
        print("1. 查看所有视频")
        print("2. 查看待下载视频")
        print("3. 查看已完成视频")
        print("4. 清理失败记录")

        choice = input("请选择操作 (1-4): ").strip()

        if choice == "1":
            videos = self.db_manager.get_all_videos(50)
            self._display_video_list(videos)
        elif choice == "2":
            videos = self.db_manager.get_videos_by_status(DownloadStatus.PENDING)
            self._display_video_list(videos, "待下载")
        elif choice == "3":
            videos = self.db_manager.get_videos_by_status(DownloadStatus.COMPLETED)
            self._display_video_list(videos, "已完成")
        elif choice == "4":
            count = self.db_manager.cleanup_failed_downloads()
            print(f"✅ 清理了 {count} 个失败记录")

    def _display_video_list(self, videos, title: str = "视频列表"):
        """显示视频列表"""
        if not videos:
            print(f"📺 {title}: 无数据")
            return

        print(f"\n📺 {title} (共 {len(videos)} 个):")
        print("="*80)

        for i, video in enumerate(videos[:20], 1):
            status_emoji = {
                DownloadStatus.PENDING: "⏳",
                DownloadStatus.DOWNLOADING: "⬇️",
                DownloadStatus.COMPLETED: "✅",
                DownloadStatus.FAILED: "❌",
                DownloadStatus.UPLOADED: "☁️"
            }.get(video.download_status, "❓")

            print(f"[{i:2d}] {status_emoji} {video.title}")
            print(f"     ID: {video.id}")
            print(f"     状态: {video.download_status.value}")
            if video.file_path:
                print(f"     文件: {video.file_path}")
            print()

        if len(videos) > 20:
            print(f"... 还有 {len(videos) - 20} 个视频")

    def show_statistics(self):
        """显示统计信息"""
        print("\n=== 数据库统计 ===")

        stats = self.db_manager.get_statistics()
        for key, value in stats.items():
            if key == 'total_size':
                value = f"{value / (1024*1024):.2f} MB" if value > 0 else "0 MB"
            print(f"  {key}: {value}")

    def handle_original_modes(self, mode: str):
        """处理原有的模式（兼容性）"""
        from video_downloader.core.main import VideoDownloaderApp
        original_app = VideoDownloaderApp()

        if mode == "2":
            original_app.handle_mode_2()
        elif mode == "3":
            original_app.handle_mode_3()
        elif mode == "4":
            original_app.handle_mode_4()
        elif mode == "5":
            original_app.handle_mode_5()
        elif mode == "6":
            original_app.handle_mode_6()

    def run(self):
        """运行应用"""
        mode = self.show_menu()

        if mode == "1":
            self.handle_mode_1()
        elif mode in ["2", "3", "4", "5", "6"]:
            self.handle_original_modes(mode)
        elif mode == "7":
            self.handle_database_operations()
        elif mode == "8":
            self.show_statistics()
        else:
            print("❌ 无效的选择")


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


def main():
    """主函数"""
    try:
        print("🚀 启动视频下载器（重复检测版本）")
        print("=" * 60)

        # 创建简化版应用实例
        app = SimpleVideoDownloaderApp()

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


if __name__ == "__main__":
    main()
