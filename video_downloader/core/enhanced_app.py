"""
增强版视频下载器 - 支持定时运行、数据库管理、重复检测和网盘推送
"""

import os
import sys
import signal
import logging
from typing import List, Optional
import json

from ..api.client import APIClient
from ..utils.data_processor import DataProcessor
from ..download.manager import DownloadManager
from ..ui.interface import UserInterface
from ..core.config import Config
from ..database.manager import DatabaseManager
from ..database.models import VideoRecord, DownloadStatus
from ..scheduler import TaskScheduler
from ..cloud import CloudStorageManager


class EnhancedVideoDownloaderApp:
    """增强版视频下载器应用"""
    
    def __init__(self, server_mode: bool = False):
        self.config = Config()
        self.server_mode = server_mode
        
        # 初始化组件
        self.api_client = APIClient()
        self.data_processor = DataProcessor()
        self.download_manager = DownloadManager()
        self.ui = UserInterface()
        self.db_manager = DatabaseManager(self.config.DATABASE_FILE)
        self.scheduler = TaskScheduler()
        self.cloud_manager = CloudStorageManager(self.config.CLOUD_CONFIG_FILE)

        # 设置日志
        self.logger = self._setup_logger()
        
        # 注册信号处理器
        self._register_signal_handlers()
        
        # 启动时初始化
        self._initialize()
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger('video_downloader')
        logger.setLevel(getattr(logging, self.config.LOG_LEVEL))
        
        if not logger.handlers:
            # 文件日志处理器
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                self.config.LOG_FILE,
                maxBytes=self.config.LOG_MAX_SIZE,
                backupCount=self.config.LOG_BACKUP_COUNT,
                encoding='utf-8'
            )
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
            
            # 控制台日志处理器（非服务器模式）
            if not self.server_mode:
                console_handler = logging.StreamHandler()
                console_formatter = logging.Formatter('%(levelname)s - %(message)s')
                console_handler.setFormatter(console_formatter)
                logger.addHandler(console_handler)
        
        return logger
    
    def _register_signal_handlers(self):
        """注册信号处理器"""
        def signal_handler(signum, frame):
            self.logger.info(f"收到信号 {signum}，正在安全关闭...")
            self.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _initialize(self):
        """初始化应用"""
        self.logger.info("正在初始化视频下载器...")
        
        # 创建必要的目录
        os.makedirs(self.config.DEFAULT_DOWNLOADS_DIR, exist_ok=True)
        
        # 测试云存储连接
        if self.config.CLOUD_UPLOAD_ENABLED:
            connection_status = self.cloud_manager.test_connection()
            for storage, status in connection_status.items():
                if status:
                    self.logger.info(f"✅ {storage.upper()} 云存储连接正常")
                else:
                    self.logger.warning(f"⚠️ {storage.upper()} 云存储连接失败")
        
        # 设置定时任务
        if self.config.SCHEDULER_CONFIG['auto_start']:
            self._setup_scheduled_tasks()
        
        self.logger.info("应用初始化完成")
    
    def _setup_scheduled_tasks(self):
        """设置定时任务"""
        try:
            # 定时获取新视频数据
            self.scheduler.add_interval_task(
                "fetch_new_videos",
                self.scheduled_fetch_videos,
                self.config.SCHEDULER_CONFIG['fetch_interval_minutes']
            )
            
            # 定时上传已下载的视频
            if self.config.CLOUD_UPLOAD_ENABLED:
                self.scheduler.add_interval_task(
                    "upload_completed_videos",
                    self.scheduled_upload_videos,
                    self.config.SCHEDULER_CONFIG['upload_interval_minutes']
                )
            
            # 每日清理任务
            self.scheduler.add_daily_task(
                "daily_cleanup",
                self.scheduled_cleanup,
                self.config.SCHEDULER_CONFIG['cleanup_time']
            )
            
            # 启动调度器
            self.scheduler.start()
            self.logger.info("定时任务调度器已启动")
            
        except Exception as e:
            self.logger.error(f"设置定时任务失败: {e}")
    
    def scheduled_fetch_videos(self) -> bool:
        """定时获取新视频任务"""
        try:
            self.logger.info("开始定时获取新视频...")
            
            # 从API获取数据
            api_data = self.api_client.fetch_posts_from_api(
                self.config.DEFAULT_PAGE_SIZE, 
                verify_ssl=False
            )
            
            if not api_data:
                self.logger.warning("未能从API获取数据")
                return False
            
            # 提取视频数据
            extracted_items = self.data_processor.extract_items_data(api_data)
            if not extracted_items:
                self.logger.warning("未能提取视频数据")
                return False
            
            # 检查重复并保存到数据库
            new_videos = 0
            for item in extracted_items:
                video_id = item.get('id')
                if not video_id:
                    continue
                
                # 检查是否已存在
                if not self.db_manager.get_video(video_id):
                    video_record = VideoRecord(
                        id=video_id,
                        title=item.get('title', ''),
                        url=item.get('url', ''),
                        description=item.get('description', ''),
                        cover=item.get('cover', ''),
                        download_status=DownloadStatus.PENDING
                    )
                    
                    if self.db_manager.add_video(video_record):
                        new_videos += 1
            
            self.logger.info(f"发现 {new_videos} 个新视频")
            
            # 如果在服务器模式，自动下载新视频
            if self.server_mode and new_videos > 0:
                self.auto_download_pending_videos()
            
            return True
            
        except Exception as e:
            self.logger.error(f"定时获取视频失败: {e}")
            return False
    
    def scheduled_upload_videos(self) -> bool:
        """定时上传已完成下载的视频"""
        try:
            self.logger.info("开始检查待上传视频...")
            
            # 获取已下载但未上传的视频
            completed_videos = self.db_manager.get_videos_by_status(DownloadStatus.COMPLETED)
            
            uploaded_count = 0
            for video in completed_videos:
                if video.file_path and os.path.exists(video.file_path):
                    upload_results = self.cloud_manager.upload_video(
                        video.file_path, 
                        video.title, 
                        video.id
                    )
                    
                    # 检查是否有成功的上传
                    successful_uploads = [r for r in upload_results if r.get('status') == 'success']
                    if successful_uploads:
                        # 更新数据库状态
                        cloud_paths = [r['cloud_path'] for r in successful_uploads]
                        self.db_manager.update_upload_info(video.id, json.dumps(cloud_paths))
                        uploaded_count += 1
                        self.logger.info(f"视频上传成功: {video.title}")
            
            if uploaded_count > 0:
                self.logger.info(f"成功上传 {uploaded_count} 个视频")
            
            return True
            
        except Exception as e:
            self.logger.error(f"定时上传失败: {e}")
            return False
    
    def scheduled_cleanup(self) -> bool:
        """定时清理任务"""
        try:
            self.logger.info("开始执行清理任务...")
            
            # 清理失败的下载记录
            failed_count = self.db_manager.cleanup_failed_downloads()
            if failed_count > 0:
                self.logger.info(f"清理了 {failed_count} 个失败的下载记录")
            
            # 获取统计信息
            stats = self.db_manager.get_statistics()
            self.logger.info(f"数据库统计: {stats}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"清理任务失败: {e}")
            return False
    
    def auto_download_pending_videos(self) -> int:
        """自动下载待下载的视频"""
        try:
            pending_videos = self.db_manager.get_videos_by_status(DownloadStatus.PENDING)
            
            if not pending_videos:
                return 0
            
            self.logger.info(f"开始自动下载 {len(pending_videos)} 个待下载视频...")
            
            downloaded_count = 0
            for video in pending_videos:
                try:
                    # 更新状态为下载中
                    self.db_manager.update_video_status(video.id, DownloadStatus.DOWNLOADING)
                    
                    # 执行下载
                    success = self.download_manager.download_m3u8_video(
                        video.url,
                        self.config.DEFAULT_DOWNLOADS_DIR,
                        video.title,
                        max_quality=True,
                        cover_url=video.cover
                    )
                    
                    if success:
                        # 查找下载的文件
                        download_path = self._find_downloaded_file(video.title, video.id)
                        if download_path:
                            file_size = os.path.getsize(download_path)
                            self.db_manager.update_video_status(
                                video.id, 
                                DownloadStatus.COMPLETED,
                                download_path,
                                file_size
                            )
                            downloaded_count += 1
                            
                            # 自动上传到云存储
                            if self.config.CLOUD_AUTO_UPLOAD:
                                self.upload_video_to_cloud(video.id)
                        else:
                            self.db_manager.update_video_status(video.id, DownloadStatus.FAILED)
                    else:
                        self.db_manager.update_video_status(video.id, DownloadStatus.FAILED)
                        
                except Exception as e:
                    self.logger.error(f"下载视频 {video.id} 失败: {e}")
                    self.db_manager.update_video_status(video.id, DownloadStatus.FAILED)
            
            self.logger.info(f"自动下载完成，成功下载 {downloaded_count} 个视频")
            return downloaded_count
            
        except Exception as e:
            self.logger.error(f"自动下载失败: {e}")
            return 0
    
    def upload_video_to_cloud(self, video_id: str) -> bool:
        """上传指定视频到云存储"""
        try:
            video = self.db_manager.get_video(video_id)
            if not video or not video.file_path or not os.path.exists(video.file_path):
                return False
            
            upload_results = self.cloud_manager.upload_video(
                video.file_path, 
                video.title, 
                video.id
            )
            
            successful_uploads = [r for r in upload_results if r.get('status') == 'success']
            if successful_uploads:
                cloud_paths = [r['cloud_path'] for r in successful_uploads]
                self.db_manager.update_upload_info(video.id, json.dumps(cloud_paths))
                self.logger.info(f"视频上传成功: {video.title}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"上传视频失败: {e}")
            return False
    
    def _find_downloaded_file(self, title: str, video_id: str) -> Optional[str]:
        """查找下载的文件路径"""
        try:
            download_dir = self.config.DEFAULT_DOWNLOADS_DIR

            # 安全检查：确保下载目录存在且可访问
            if not os.path.exists(download_dir):
                self.logger.warning(f"下载目录不存在: {download_dir}")
                return None

            if not os.access(download_dir, os.R_OK):
                self.logger.error(f"无法访问下载目录: {download_dir}")
                return None

            # 首先尝试直接匹配完整的文件名
            import glob
            video_extensions = ['*.mp4', '*.mkv', '*.avi', '*.mov', '*.wmv', '*.flv']

            for ext in video_extensions:
                pattern = os.path.join(download_dir, ext)
                files = glob.glob(pattern)

                for file_path in files:
                    filename = os.path.basename(file_path)
                    filename_without_ext = os.path.splitext(filename)[0]

                    # 检查文件名是否包含标题的主要部分
                    if title and len(title) > 10:
                        # 提取标题的关键部分进行匹配
                        title_keywords = []
                        if '】' in title:
                            # 提取中括号后的内容
                            after_bracket = title.split('】', 1)[1] if '】' in title else title
                            title_keywords.append(after_bracket[:20])  # 取前20个字符

                        # 添加原始标题的前20个字符
                        title_keywords.append(title[:20])

                        for keyword in title_keywords:
                            if keyword.strip() and keyword.strip() in filename_without_ext:
                                abs_file = os.path.abspath(file_path)
                                abs_download_dir = os.path.abspath(download_dir)
                                if abs_file.startswith(abs_download_dir) and os.path.isfile(abs_file):
                                    self.logger.info(f"找到下载文件: {abs_file}")
                                    return abs_file

                    # 按视频ID匹配
                    if video_id and video_id in filename_without_ext:
                        abs_file = os.path.abspath(file_path)
                        abs_download_dir = os.path.abspath(download_dir)
                        if abs_file.startswith(abs_download_dir) and os.path.isfile(abs_file):
                            self.logger.info(f"找到下载文件: {abs_file}")
                            return abs_file

            # 如果直接匹配失败，尝试模糊匹配
            # 清理文件名以避免路径遍历，但保留更多字符
            import re
            safe_title = re.sub(r'[<>:"/\\|?*]', '', title) if title else ''
            safe_video_id = re.sub(r'[^\w-]', '', video_id) if video_id else ''

            # 可能的文件名模式
            patterns = []
            if safe_title and len(safe_title) > 5:
                # 使用更宽松的匹配模式
                safe_title_short = safe_title[:30]  # 取前30个字符
                patterns.extend([
                    f"*{safe_title_short}*.mp4",
                    f"*{safe_title_short}*.mkv",
                    f"*{safe_title_short}*.avi"
                ])

            if safe_video_id:
                patterns.extend([
                    f"*{safe_video_id}*.mp4",
                    f"*{safe_video_id}*.mkv",
                    f"*{safe_video_id}*.avi"
                ])

            for pattern in patterns:
                try:
                    # 使用绝对路径进行搜索
                    search_pattern = os.path.join(download_dir, pattern)
                    files = glob.glob(search_pattern)

                    for file_path in files:
                        # 安全检查：确保文件在下载目录内
                        abs_file = os.path.abspath(file_path)
                        abs_download_dir = os.path.abspath(download_dir)

                        if abs_file.startswith(abs_download_dir) and os.path.isfile(abs_file):
                            self.logger.info(f"找到下载文件: {abs_file}")
                            return abs_file

                except Exception as e:
                    self.logger.warning(f"搜索文件模式 {pattern} 时出错: {e}")
                    continue

            self.logger.warning(f"未找到视频文件: title={title}, id={video_id}")

            # 最后的尝试：列出下载目录中的所有视频文件
            self.logger.info("尝试列出下载目录中的所有视频文件:")
            for ext in video_extensions:
                pattern = os.path.join(download_dir, ext)
                files = glob.glob(pattern)
                for file_path in files:
                    filename = os.path.basename(file_path)
                    file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                    self.logger.info(f"  - {filename} ({file_size:.1f} MB)")

            return None

        except Exception as e:
            self.logger.error(f"查找下载文件时发生异常: {e}")
            return None

    def run_server_mode(self):
        """运行服务器模式"""
        self.logger.info("启动服务器模式...")
        
        # 写入PID文件
        with open(self.config.PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
        
        try:
            # 立即执行一次获取任务
            self.scheduled_fetch_videos()
            
            # 保持运行
            import time
            while True:
                time.sleep(60)  # 每分钟检查一次
                
        except KeyboardInterrupt:
            self.logger.info("收到中断信号，正在关闭...")
        finally:
            self.shutdown()
    
    def run_interactive_mode(self):
        """运行交互模式"""
        while True:
            try:
                # 显示增强菜单
                mode = self._show_enhanced_menu()

                mode_handlers = {
                    "1": self.handle_mode_1,
                    "2": self.handle_mode_2,
                    "3": self.handle_mode_3,
                    "4": self.handle_mode_4,
                    "5": self.handle_mode_5,
                    "6": self.handle_mode_6,
                    "7": self.handle_database_operations,
                    "8": self.handle_cloud_operations,
                    "9": self.handle_scheduler_operations,
                    "10": self.show_statistics
                }

                if mode.lower() in ['q', 'quit', 'exit']:
                    print("👋 退出程序")
                    break

                handler = mode_handlers.get(mode)
                if handler:
                    handler()
                else:
                    print("❌ 无效的选择，请重新选择")

            except KeyboardInterrupt:
                print("\n\n👋 用户中断程序，正在退出...")
                break
            except Exception as e:
                self.logger.error(f"交互模式运行异常: {e}")
                print(f"❌ 程序运行异常: {e}")
                print("程序将继续运行，请重新选择功能")
                import traceback
                traceback.print_exc()

    def _show_enhanced_menu(self) -> str:
        """显示增强版菜单"""
        print("\n" + "="*60)
        print("🎬 增强版视频下载器 v2.0")
        print("="*60)
        print("📊 基本功能:")
        print("  1. 完整工作流程 (API -> 提取 -> 显示 -> 下载)")
        print("  2. 从本地JSON文件提取并下载")
        print("  3. 仅从API获取数据")
        print("  4. 下载单个m3u8视频")
        print("  5. 批量下载视频")
        print("  6. 交互式选择下载")
        print("\n🚀 新增功能:")
        print("  7. 数据库管理")
        print("  8. 云存储管理")
        print("  9. 定时任务管理")
        print(" 10. 统计信息")
        print("\n💡 输入 q/quit/exit 退出程序")
        print("="*60)
        
        choice = input("请选择功能 (1-10): ").strip()
        return choice
    
    def handle_database_operations(self):
        """处理数据库操作"""
        print("\n=== 数据库管理 ===")
        print("1. 查看所有视频")
        print("2. 查看待下载视频")
        print("3. 查看已完成视频")
        print("4. 搜索视频")
        print("5. 清理失败记录")
        print("6. 检测本地文件状态")
        print("7. 文件与数据库同步")
        print("8. 下载缺失的视频文件")
        print("9. 视频文件分类管理")
        print("10. 文件夹统计信息")

        choice = input("请选择操作 (1-10): ").strip()

        if choice == "1":
            videos = self.db_manager.get_all_videos()
            self._display_video_list(videos)
        elif choice == "2":
            videos = self.db_manager.get_videos_by_status(DownloadStatus.PENDING)
            self._display_video_list(videos, "待下载")
        elif choice == "3":
            videos = self.db_manager.get_videos_by_status(DownloadStatus.COMPLETED)
            self._display_video_list(videos, "已完成")
        elif choice == "4":
            keyword = input("请输入搜索关键词: ").strip()
            # 这里可以扩展搜索功能
            print("搜索功能待实现")
        elif choice == "5":
            count = self.db_manager.cleanup_failed_downloads()
            print(f"✅ 清理了 {count} 个失败记录")
        elif choice == "6":
            self.handle_local_file_detection()
        elif choice == "7":
            self.handle_file_database_sync()
        elif choice == "8":
            self.handle_download_missing_videos()
        elif choice == "9":
            self.handle_video_classification()
        elif choice == "10":
            self.handle_folder_statistics()

    def handle_local_file_detection(self):
        """处理本地文件检测"""
        print("\n=== 本地文件检测 ===")
        print("🔍 正在分析文件与数据库记录的对应关系...")

        # 实现文件检测逻辑
        sync_stats = self.db_manager.sync_database_with_local_files(self.config.DEFAULT_DOWNLOADS_DIR)

        if sync_stats:
            print(f"📊 同步完成:")
            print(f"  ✅ 更新为已完成: {sync_stats['updated_to_completed']}")
            print(f"  ⏳ 重置为待下载: {sync_stats['updated_to_missing']}")
            print(f"  📝 创建新记录: {sync_stats['created_from_files']}")
            print(f"  🔗 文件匹配: {sync_stats['files_matched']}")

        input("按 Enter 键继续...")

    def handle_file_database_sync(self):
        """处理文件与数据库同步"""
        print("\n=== 文件与数据库同步 ===")
        # 实现同步逻辑
        print("同步功能待实现")
        input("按 Enter 键继续...")

    def handle_download_missing_videos(self):
        """处理下载缺失视频文件"""
        print("\n=== 下载缺失的视频文件 ===")

        # 首先同步数据库状态
        print("🔄 正在同步数据库状态...")
        sync_stats = self.db_manager.sync_database_with_local_files(self.config.DEFAULT_DOWNLOADS_DIR)

        if sync_stats:
            print(f"📊 同步完成:")
            print(f"  ✅ 更新为已完成: {sync_stats['updated_to_completed']}")
            print(f"  ⏳ 重置为待下载: {sync_stats['updated_to_missing']}")
            print(f"  📝 创建新记录: {sync_stats['created_from_files']}")
            print(f"  🔗 文件匹配: {sync_stats['files_matched']}")

        # 获取缺失文件的视频
        missing_videos = self.db_manager.get_videos_missing_files()

        if not missing_videos:
            print("✅ 所有视频文件都已存在，无需下载")
            input("按 Enter 键返回...")
            return

        print(f"\n🔍 发现 {len(missing_videos)} 个缺失文件的视频:")
        print("=" * 80)

        # 显示缺失的视频列表
        for i, video in enumerate(missing_videos[:20], 1):
            status_emoji = {
                DownloadStatus.PENDING: "⏳",
                DownloadStatus.COMPLETED: "💔",  # 标记为完成但文件不存在
                DownloadStatus.FAILED: "❌"
            }.get(video.download_status, "❓")

            print(f"[{i:2d}] {status_emoji} {video.title}")
            print(f"     ID: {video.id}")
            print(f"     状态: {video.download_status.value}")
            if video.url:
                print(f"     URL: {video.url[:50]}...")
            print()

        if len(missing_videos) > 20:
            print(f"... 还有 {len(missing_videos) - 20} 个缺失视频")

        print("\n📥 下载选项:")
        print("1. 下载所有缺失的视频")
        print("2. 选择性下载视频")
        print("3. 仅下载有URL的视频")
        print("0. 返回上级菜单")

        choice = input("请选择 (0-3): ").strip()

        if choice == "1":
            self._download_all_missing_videos(missing_videos)
        elif choice == "2":
            self._interactive_download_missing_videos(missing_videos)
        elif choice == "3":
            videos_with_url = [v for v in missing_videos if v.url]
            if videos_with_url:
                self._download_all_missing_videos(videos_with_url)
            else:
                print("❌ 没有找到有URL的缺失视频")
                input("按 Enter 键继续...")

    def _download_all_missing_videos(self, missing_videos: List[VideoRecord]):
        """下载所有缺失的视频"""
        videos_with_url = [v for v in missing_videos if v.url]
        videos_without_url = [v for v in missing_videos if not v.url]

        print(f"\n📥 准备下载 {len(videos_with_url)} 个有URL的视频")
        if videos_without_url:
            print(f"⚠️ 跳过 {len(videos_without_url)} 个无URL的本地文件记录")

        if not videos_with_url:
            print("❌ 没有可下载的视频")
            input("按 Enter 键继续...")
            return

        confirm = input(f"确认下载这 {len(videos_with_url)} 个视频? (y/n): ").strip().lower()
        if confirm != 'y':
            return

        downloaded_count = 0
        failed_count = 0

        for i, video in enumerate(videos_with_url, 1):
            print(f"\n[{i}/{len(videos_with_url)}] 下载: {video.title}")

            try:
                # 更新状态为下载中
                self.db_manager.update_video_status(video.id, DownloadStatus.DOWNLOADING)

                # 执行下载
                success = self.download_manager.download_m3u8_video(
                    video.url,
                    self.config.DEFAULT_DOWNLOADS_DIR,
                    video.title,
                    max_quality=True,
                    cover_url=video.cover
                )

                if success:
                    # 查找下载的文件
                    download_path = self._find_downloaded_file(video.title, video.id)
                    if download_path:
                        file_size = os.path.getsize(download_path)
                        self.db_manager.update_video_status(
                            video.id,
                            DownloadStatus.COMPLETED,
                            download_path,
                            file_size
                        )
                        downloaded_count += 1
                        print(f"✅ 下载成功")
                    else:
                        self.db_manager.update_video_status(video.id, DownloadStatus.FAILED)
                        failed_count += 1
                        print(f"❌ 下载失败: 文件未找到")
                else:
                    self.db_manager.update_video_status(video.id, DownloadStatus.FAILED)
                    failed_count += 1
                    print(f"❌ 下载失败")

            except Exception as e:
                self.db_manager.update_video_status(video.id, DownloadStatus.FAILED)
                failed_count += 1
                print(f"❌ 下载异常: {e}")

        print(f"\n📊 下载完成:")
        print(f"  ✅ 成功: {downloaded_count}")
        print(f"  ❌ 失败: {failed_count}")
        print(f"  📊 总计: {len(videos_with_url)}")

        input("按 Enter 键继续...")

    def _interactive_download_missing_videos(self, missing_videos: List[VideoRecord]):
        """交互式选择下载缺失视频"""
        videos_with_url = [v for v in missing_videos if v.url]

        if not videos_with_url:
            print("❌ 没有可下载的视频（缺失URL）")
            input("按 Enter 键继续...")
            return

        print(f"\n📋 可下载的视频列表 (共 {len(videos_with_url)} 个):")
        print("=" * 80)

        for i, video in enumerate(videos_with_url, 1):
            print(f"[{i:2d}] {video.title}")
            print(f"     ID: {video.id}")
            print()

        print("💡 选择说明:")
        print("• 单个视频: 输入数字，如 3")
        print("• 多个视频: 用逗号分隔，如 1,3,5")
        print("• 范围选择: 用横线连接，如 1-5")
        print("• 全部下载: 输入 all")
        print("• 取消: 输入 q")

        while True:
            selection = input(f"\n请选择要下载的视频 (1-{len(videos_with_url)}): ").strip()

            if not selection or selection.lower() == 'q':
                return

            if selection.lower() == 'all':
                selected_videos = videos_with_url
                break

            try:
                # 解析选择
                selected_indices = self._parse_video_selection(selection, len(videos_with_url))
                if selected_indices:
                    selected_videos = [videos_with_url[i-1] for i in selected_indices]
                    break
                else:
                    print("❌ 无效的选择，请重新输入")
            except:
                print("❌ 输入格式错误，请重新输入")

        # 确认并下载
        print(f"\n📋 您选择了 {len(selected_videos)} 个视频:")
        for i, video in enumerate(selected_videos[:5], 1):
            print(f"  [{i}] {video.title}")
        if len(selected_videos) > 5:
            print(f"  ... 还有 {len(selected_videos) - 5} 个视频")

        confirm = input(f"\n确认下载这些视频? (y/n): ").strip().lower()
        if confirm == 'y':
            self._download_all_missing_videos(selected_videos)

    def _parse_video_selection(self, selection: str, max_count: int) -> List[int]:
        """解析视频选择输入"""
        import re
        selections = []

        try:
            parts = re.split(r'[,，\s]+', selection.strip())

            for part in parts:
                if not part:
                    continue

                if '-' in part:
                    # 范围选择
                    start, end = map(int, part.split('-', 1))
                    if 1 <= start <= max_count and 1 <= end <= max_count and start <= end:
                        selections.extend(range(start, end + 1))
                else:
                    # 单个数字
                    num = int(part)
                    if 1 <= num <= max_count:
                        selections.append(num)

            return sorted(list(set(selections)))
        except:
            return []

    def handle_video_classification(self):
        """处理视频分类管理"""
        print("\n=== 视频文件分类管理 ===")
        print("分类功能待实现")
        input("按 Enter 键继续...")

    def handle_folder_statistics(self):
        """处理文件夹统计信息"""
        print("\n📊 文件夹统计信息")
        print("统计功能待实现")
        input("按 Enter 键继续...")

    def handle_cloud_operations(self):
        """处理云存储操作"""
        print("\n=== 云存储管理 ===")
        print("云存储功能待实现")
        input("按 Enter 键继续...")

    def handle_scheduler_operations(self):
        """处理定时任务操作"""
        print("\n=== 定时任务管理 ===")
        print("定时任务功能待实现")
        input("按 Enter 键继续...")

    def show_statistics(self):
        """显示统计信息"""
        print("\n=== 统计信息 ===")
        stats = self.db_manager.get_statistics()
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        input("按 Enter 键继续...")

    def handle_mode_1(self):
        """处理模式1：完整工作流程"""
        print("\n=== 完整工作流程 ===")
        # 实现完整工作流程
        input("按 Enter 键继续...")

    def handle_mode_2(self):
        """处理模式2：从本地JSON文件提取并下载"""
        print("\n=== 从本地JSON文件提取并下载 ===")
        # 实现从本地文件提取
        input("按 Enter 键继续...")

    def handle_mode_3(self):
        """处理模式3：仅从API获取数据"""
        print("\n=== 仅从API获取数据 ===")
        # 实现API获取数据
        input("按 Enter 键继续...")

    def handle_mode_4(self):
        """处理模式4：下载单个m3u8视频"""
        print("\n=== 下载单个m3u8视频 ===")
        # 实现单个视频下载
        input("按 Enter 键继续...")

    def handle_mode_5(self):
        """处理模式5：批量下载视频"""
        print("\n=== 批量下载视频 ===")
        # 实现批量下载
        input("按 Enter 键继续...")

    def handle_mode_6(self):
        """处理模式6：交互式选择下载"""
        print("\n=== 交互式选择下载 ===")
        # 实现交互式选择下载
        input("按 Enter 键继续...")

    def _display_video_list(self, videos: List[VideoRecord], title: str = "视频列表"):
        """显示视频列表"""
        if not videos:
            print(f"📺 {title}: 暂无视频")
            return

        print(f"\n📺 {title} (共 {len(videos)} 个):")
        print("=" * 80)

        for i, video in enumerate(videos[:20], 1):
            status_emoji = {
                DownloadStatus.PENDING: "⏳",
                DownloadStatus.COMPLETED: "✅",
                DownloadStatus.FAILED: "❌",
                DownloadStatus.DOWNLOADING: "⬇️"
            }.get(video.download_status, "❓")

            print(f"[{i:2d}] {status_emoji} {video.title}")
            print(f"     ID: {video.id}")
            if video.file_path:
                print(f"     文件: {video.file_path}")
            print()

        if len(videos) > 20:
            print(f"... 还有 {len(videos) - 20} 个视频")

        is_duplicates = input("是否查看重复视频的详情? (y/n): ").strip().lower() == 'y'
        if is_duplicates:
            # 显示重复视频详情逻辑
            pass

        input("按 Enter 键返回主菜单...")

    def shutdown(self):
        """安全关闭应用"""
        try:
            if hasattr(self, 'scheduler') and self.scheduler:
                self.scheduler.stop()

            if hasattr(self, 'db_manager') and self.db_manager:
                self.db_manager.close()

            # 清理PID文件
            if hasattr(self, 'config') and os.path.exists(self.config.PID_FILE):
                os.remove(self.config.PID_FILE)

            self.logger.info("应用已安全关闭")
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"关闭应用时出错: {e}")

    def run(self):
        """主运行方法 - 根据模式选择运行方式"""
        if self.server_mode:
            self.run_server_mode()
        else:
            self.run_interactive_mode()
