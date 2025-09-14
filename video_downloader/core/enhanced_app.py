"""
增强版视频下载器 - 支持定时运行、数据库管理、重复检测和网盘推送
"""

import os
import sys
import signal
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import json

from ..api.client import APIClient
from ..utils.data_processor import DataProcessor
from ..download.manager import DownloadManager
from ..ui.interface import UserInterface
from ..core.config import Config
from ..database.manager import DatabaseManager
from ..database.models import VideoRecord, DownloadStatus
from ..scheduler import TaskScheduler, SchedulerConfig
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

            # 清理文件名以避免路径遍历
            import re
            safe_title = re.sub(r'[^\w\s-]', '', title)[:50] if title else ''
            safe_video_id = re.sub(r'[^\w-]', '', video_id)[:20] if video_id else ''

            # 可能的文件名模式
            patterns = []
            if safe_title:
                patterns.extend([
                    f"{safe_title}*.mp4",
                    f"{safe_title}*.mkv",
                    f"{safe_title}*.avi"
                ])
            if safe_video_id:
                patterns.extend([
                    f"*{safe_video_id}*.mp4",
                    f"*{safe_video_id}*.mkv",
                    f"*{safe_video_id}*.avi"
                ])

            import glob
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
            
            handler = mode_handlers.get(mode)
            if handler:
                handler()
            else:
                print("❌ 无效的选择，程序退出")
                
        except Exception as e:
            self.logger.error(f"交互模式运行异常: {e}")
            print(f"❌ 程序运行异常: {e}")
    
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
        
        choice = input("请选择操作 (1-5): ").strip()
        
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
            keyword = input("请输入搜索关键词: ").strip()
            # 这里可以扩展搜索功能
            print("搜索功能待实现")
        elif choice == "5":
            count = self.db_manager.cleanup_failed_downloads()
            print(f"✅ 清理了 {count} 个失败记录")
    
    def handle_cloud_operations(self):
        """处理云存储操作"""
        print("\n=== 云存储管理 ===")
        print("1. 测试连接")
        print("2. 查看配置")
        print("3. 上传待上传视频")
        print("4. 上传统计")
        
        choice = input("请选择操作 (1-4): ").strip()
        
        if choice == "1":
            results = self.cloud_manager.test_connection()
            for storage, status in results.items():
                status_text = "✅ 连接正常" if status else "❌ 连接失败"
                print(f"{storage.upper()}: {status_text}")
        elif choice == "2":
            stats = self.cloud_manager.get_upload_statistics()
            print(json.dumps(stats, indent=2, ensure_ascii=False))
        elif choice == "3":
            self.scheduled_upload_videos()
        elif choice == "4":
            stats = self.cloud_manager.get_upload_statistics()
            print(f"活跃存储: {', '.join(stats['active_storages'])}")
    
    def handle_scheduler_operations(self):
        """处理定时任务操作"""
        print("\n=== 定时任务管理 ===")
        print("1. 查看任务状态")
        print("2. 手动执行获取任务")
        print("3. 手动执行上传任务")
        print("4. 手动执行清理任务")
        print("5. 启动/停止调度器")
        
        choice = input("请选择操作 (1-5): ").strip()
        
        if choice == "1":
            tasks = self.scheduler.get_task_info()
            for task in tasks:
                print(f"任务: {task['name']}")
                print(f"  类型: {task.get('type', 'unknown')}")
                print(f"  下次运行: {task.get('next_run', '未知')}")
                print()
        elif choice == "2":
            self.scheduler.run_task_once("fetch_new_videos")
        elif choice == "3":
            self.scheduler.run_task_once("upload_completed_videos")
        elif choice == "4":
            self.scheduler.run_task_once("daily_cleanup")
        elif choice == "5":
            if self.scheduler.is_running:
                self.scheduler.stop()
                print("✅ 调度器已停止")
            else:
                self.scheduler.start()
                print("✅ 调度器已启动")
    
    def show_statistics(self):
        """显示统计信息"""
        print("\n=== 系统统计 ===")
        
        # 数据库统计
        db_stats = self.db_manager.get_statistics()
        print("📊 数据库统计:")
        for key, value in db_stats.items():
            if key == 'total_size':
                value = f"{value / (1024*1024):.2f} MB" if value > 0 else "0 MB"
            print(f"  {key}: {value}")
        
        # 云存储统计
        cloud_stats = self.cloud_manager.get_upload_statistics()
        print("\n☁️ 云存储统计:")
        print(f"  活跃存储: {len(cloud_stats['active_storages'])}")
        for storage, status in cloud_stats.get('connection_status', {}).items():
            status_text = "正常" if status else "异常"
            print(f"  {storage}: {status_text}")
        
        # 任务统计
        tasks = self.scheduler.get_task_info()
        print(f"\n⏰ 定时任务: {len(tasks)} 个")
        print(f"  调度器状态: {'运行中' if self.scheduler.is_running else '已停止'}")
    
    def _display_video_list(self, videos: List[VideoRecord], title: str = "视频列表"):
        """显示视频列表"""
        if not videos:
            print(f"📺 {title}: 无数据")
            return
        
        print(f"\n📺 {title} (共 {len(videos)} 个):")
        print("="*80)
        
        for i, video in enumerate(videos[:20], 1):  # 最多显示20个
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
    
    # 保留原有的处理方法
    def handle_mode_1(self):
        """处理模式1：完整工作流程（增强版）"""
        size = input("请输入每页数据条数 (默认50): ").strip()
        size = int(size) if size.isdigit() else 50

        print("=== 开始完整工作流程 ===")
        
        # 获取API数据
        api_data = self.api_client.fetch_posts_from_api(size, verify_ssl=False)
        if not api_data:
            print("❌ 从API获取数据失败")
            return

        # 提取视频数据
        extracted_items = self.data_processor.extract_items_data(api_data)
        if not extracted_items:
            print("❌ 提取数据失败")
            return

        # 保存到数据库并检查重复
        new_videos = []
        duplicate_videos = []
        
        for item in extracted_items:
            video_id = item.get('id')
            if not video_id:
                continue
            
            existing_video = self.db_manager.get_video(video_id)
            if existing_video:
                duplicate_videos.append(item)
            else:
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

        print(f"✅ 发现 {len(new_videos)} 个新视频")
        print(f"⚠️ 跳过 {len(duplicate_videos)} 个重复视频")

        if new_videos:
            # 显示新视频列表
            print(f"\n📺 新视频列表:")
            print("=" * 80)
            for i, item in enumerate(new_videos[:10], 1):
                title = item.get('title', f"Video_{item.get('id')}")
                print(f"[{i:2d}] {title}")
                print(f"     ID: {item.get('id')}")
                print()

            # 下载选择
            download_choice = input("\n是否下载新视频? (1=全部下载, 2=选择下载, n=跳过): ").strip().lower()
            
            if download_choice == "1":
                for item in new_videos:
                    video_id = item.get('id')
                    if video_id:
                        self.download_and_upload_video(video_id)
            elif download_choice == "2":
                # 交互式选择
                self.interactive_select_and_download(new_videos)
        else:
            print("没有新视频需要下载")
    
    def download_and_upload_video(self, video_id: str) -> bool:
        """下载并上传视频"""
        try:
            video = self.db_manager.get_video(video_id)
            if not video:
                return False
            
            # 更新状态为下载中
            self.db_manager.update_video_status(video_id, DownloadStatus.DOWNLOADING)
            
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
                        video_id, 
                        DownloadStatus.COMPLETED,
                        download_path,
                        file_size
                    )
                    
                    # 自动上传到云存储
                    if self.config.CLOUD_AUTO_UPLOAD:
                        self.upload_video_to_cloud(video_id)
                    
                    print(f"✅ 视频下载成功: {video.title}")
                    return True
                else:
                    self.db_manager.update_video_status(video_id, DownloadStatus.FAILED)
            else:
                self.db_manager.update_video_status(video_id, DownloadStatus.FAILED)
            
            return False
            
        except Exception as e:
            self.logger.error(f"下载视频失败: {e}")
            self.db_manager.update_video_status(video_id, DownloadStatus.FAILED)
            return False
    
    def interactive_select_and_download(self, videos: List[Dict[str, Any]]):
        """交互式选择并下载视频"""
        print("\n请选择要下载的视频 (输入序号，用逗号分隔，如: 1,3,5):")
        
        try:
            selection = input("选择: ").strip()
            if not selection:
                return
            
            indices = [int(x.strip()) - 1 for x in selection.split(',')]
            selected_videos = [videos[i] for i in indices if 0 <= i < len(videos)]
            
            for video in selected_videos:
                video_id = video.get('id')
                if video_id:
                    self.download_and_upload_video(video_id)
                    
        except (ValueError, IndexError) as e:
            print(f"❌ 输入格式错误: {e}")
    
    # 保留其他原有方法的引用，但可以在这些方法中集成数据库操作
    def handle_mode_2(self):
        """处理模式2：从本地JSON文件提取字段（保持兼容）"""
        # 调用原有的处理逻辑，这里可以保持不变或稍作修改
        from ..core.main import VideoDownloaderApp
        original_app = VideoDownloaderApp()
        original_app.handle_mode_2()
    
    def handle_mode_3(self):
        """处理模式3：仅从API获取数据（保持兼容）"""
        from ..core.main import VideoDownloaderApp
        original_app = VideoDownloaderApp()
        original_app.handle_mode_3()
    
    def handle_mode_4(self):
        """处理模式4：下载单个m3u8视频（保持兼容）"""
        from ..core.main import VideoDownloaderApp
        original_app = VideoDownloaderApp()
        original_app.handle_mode_4()
    
    def handle_mode_5(self):
        """处理模式5：批量下载视频（保持兼容）"""
        from ..core.main import VideoDownloaderApp
        original_app = VideoDownloaderApp()
        original_app.handle_mode_5()
    
    def handle_mode_6(self):
        """处理模式6：交互式选择视频下载（保持兼容）"""
        from ..core.main import VideoDownloaderApp
        original_app = VideoDownloaderApp()
        original_app.handle_mode_6()
    
    def shutdown(self):
        """安全关闭应用"""
        self.logger.info("正在关闭应用...")
        
        # 停止调度器
        if self.scheduler.is_running:
            self.scheduler.stop()
        
        # 删除PID文件
        if os.path.exists(self.config.PID_FILE):
            os.remove(self.config.PID_FILE)
        
        self.logger.info("应用已安全关闭")
    
    def run(self):
        """主运行方法"""
        if self.server_mode:
            self.run_server_mode()
        else:
            self.run_interactive_mode()
