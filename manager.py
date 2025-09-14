#!/usr/bin/env python3
"""
视频下载器管理工具
提供状态监控、日志查看、数据库管理等功能
"""

import os
import sys
import json
import sqlite3
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from video_downloader.database.manager import DatabaseManager
from video_downloader.database.models import DownloadStatus
from video_downloader.cloud import CloudStorageManager


class VideoDownloaderManager:
    """视频下载器管理工具"""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.cloud_manager = CloudStorageManager()

    def show_status(self):
        """显示系统状态"""
        print("🔍 系统状态检查")
        print("=" * 50)

        # 检查进程状态
        pid_file = "video_downloader.pid"
        if os.path.exists(pid_file):
            try:
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())
                # 检查进程是否存在
                try:
                    os.kill(pid, 0)
                    print(f"✅ 服务运行中 (PID: {pid})")
                except OSError:
                    print("❌ 服务未运行 (PID文件存在但进程不存在)")
                    os.remove(pid_file)
            except:
                print("❌ 无法读取PID文件")
        else:
            print("⚠️ 服务未运行 (无PID文件)")

        # 数据库统计
        stats = self.db_manager.get_statistics()
        print(f"\n📊 数据库统计:")
        print(f"   总视频数: {stats.get('total', 0)}")
        print(f"   待下载: {stats.get('pending', 0)}")
        print(f"   已完成: {stats.get('completed', 0)}")
        print(f"   已上传: {stats.get('uploaded', 0)}")
        print(f"   失败数: {stats.get('failed', 0)}")
        total_size = stats.get('total_size', 0)
        print(f"   总大小: {total_size / (1024*1024*1024):.2f} GB")

        # 云存储状态
        cloud_stats = self.cloud_manager.get_upload_statistics()
        print(f"\n☁️ 云存储状态:")
        for storage, status in cloud_stats.get('connection_status', {}).items():
            status_text = "✅ 正常" if status else "❌ 异常"
            print(f"   {storage.upper()}: {status_text}")

        # 磁盘空间
        downloads_dir = "downloads"
        if os.path.exists(downloads_dir):
            total_size = sum(
                os.path.getsize(os.path.join(downloads_dir, f))
                for f in os.listdir(downloads_dir)
                if os.path.isfile(os.path.join(downloads_dir, f))
            )
            print(f"\n💾 下载目录:")
            print(f"   路径: {os.path.abspath(downloads_dir)}")
            print(f"   大小: {total_size / (1024*1024*1024):.2f} GB")

    def show_recent_logs(self, lines=50):
        """显示最近的日志"""
        log_files = ["video_downloader.log", "scheduler.log"]

        for log_file in log_files:
            if os.path.exists(log_file):
                print(f"\n📝 {log_file} (最近 {lines} 行):")
                print("-" * 50)
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        all_lines = f.readlines()
                        recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                        for line in recent_lines:
                            print(line.rstrip())
                except Exception as e:
                    print(f"❌ 读取日志失败: {e}")
            else:
                print(f"\n📝 {log_file}: 文件不存在")

    def list_videos(self, status=None, limit=20):
        """列出视频"""
        if status:
            try:
                status_enum = DownloadStatus(status)
                videos = self.db_manager.get_videos_by_status(status_enum)
                title = f"{status} 状态的视频"
            except ValueError:
                print(f"❌ 无效的状态: {status}")
                return
        else:
            videos = self.db_manager.get_all_videos(limit)
            title = "所有视频"

        if not videos:
            print(f"📺 {title}: 无数据")
            return

        print(f"\n📺 {title} (显示前 {min(len(videos), limit)} 个):")
        print("=" * 80)

        for i, video in enumerate(videos[:limit], 1):
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
            print(f"     创建时间: {video.created_at}")
            if video.file_path:
                print(f"     文件: {video.file_path}")
            print()

    def cleanup_database(self):
        """清理数据库"""
        print("🧹 开始清理数据库...")

        # 清理失败记录
        failed_count = self.db_manager.cleanup_failed_downloads()
        print(f"✅ 清理了 {failed_count} 个失败记录")

        # 检查文件是否存在
        completed_videos = self.db_manager.get_videos_by_status(DownloadStatus.COMPLETED)
        missing_files = []

        for video in completed_videos:
            if video.file_path and not os.path.exists(video.file_path):
                missing_files.append(video.id)

        if missing_files:
            print(f"⚠️ 发现 {len(missing_files)} 个文件丢失的记录")
            choice = input("是否将这些记录状态重置为待下载? (y/n): ").strip().lower()
            if choice == 'y':
                for video_id in missing_files:
                    self.db_manager.update_video_status(video_id, DownloadStatus.PENDING)
                print(f"✅ 已重置 {len(missing_files)} 个记录的状态")

    def test_cloud_storage(self):
        """测试云存储连接"""
        print("☁️ 测试云存储连接...")
        results = self.cloud_manager.test_connection()

        for storage_type, success in results.items():
            if success:
                print(f"✅ {storage_type.upper()}: 连接成功")
            else:
                print(f"❌ {storage_type.upper()}: 连接失败")

    def export_data(self, output_file="video_data_export.json"):
        """导出数据"""
        try:
            videos = self.db_manager.get_all_videos()
            export_data = {
                'export_time': datetime.now().isoformat(),
                'total_count': len(videos),
                'videos': [video.to_dict() for video in videos]
            }

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            print(f"✅ 数据已导出到: {output_file}")
            print(f"   包含 {len(videos)} 个视频记录")

        except Exception as e:
            print(f"❌ 导出失败: {e}")

    def show_help(self):
        """显示帮助信息"""
        print("📖 视频下载器管理工具")
        print("=" * 50)
        print("命令列表:")
        print("  status          - 显示系统状态")
        print("  logs [lines]    - 显示最近日志 (默认50行)")
        print("  list [status]   - 列出视频 (可选状态: pending/completed/failed/uploaded)")
        print("  cleanup         - 清理数据库")
        print("  test-cloud      - 测试云存储连接")
        print("  export [file]   - 导出数据")
        print("  help            - 显示此帮助")
        print()
        print("示例:")
        print("  python manager.py status")
        print("  python manager.py logs 100")
        print("  python manager.py list pending")
        print("  python manager.py export my_backup.json")


def main():
    """主函数"""
    manager = VideoDownloaderManager()

    if len(sys.argv) < 2:
        manager.show_help()
        return

    command = sys.argv[1].lower()

    try:
        if command == "status":
            manager.show_status()
        elif command == "logs":
            lines = int(sys.argv[2]) if len(sys.argv) > 2 else 50
            manager.show_recent_logs(lines)
        elif command == "list":
            status = sys.argv[2] if len(sys.argv) > 2 else None
            manager.list_videos(status)
        elif command == "cleanup":
            manager.cleanup_database()
        elif command == "test-cloud":
            manager.test_cloud_storage()
        elif command == "export":
            output_file = sys.argv[2] if len(sys.argv) > 2 else "video_data_export.json"
            manager.export_data(output_file)
        elif command == "help":
            manager.show_help()
        else:
            print(f"❌ 未知命令: {command}")
            manager.show_help()
    except Exception as e:
        print(f"❌ 执行命令失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
