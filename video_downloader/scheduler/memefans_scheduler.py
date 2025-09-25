"""
Memefans API定时调度器 - 支持API降级机制
当feed API多次失败后，自动切换到posts API
"""

import logging
import os
from typing import List, Dict, Any
from datetime import datetime

from ..api.memefans_client import MemefansAPIClient
from ..api.client import APIClient
from ..core.config import Config
from ..database.models import VideoRecord


class MemefansScheduler:
    """Memefans API定时调度器，支持API降级机制"""

    def __init__(self, db_manager, download_manager, cloud_manager):
        self.config = Config()
        self.db_manager = db_manager
        self.download_manager = download_manager
        self.cloud_manager = cloud_manager
        self.logger = logging.getLogger('memefans_scheduler')

        # 初始化API客户端
        self.memefans_client = MemefansAPIClient()  # feed API
        self.posts_client = APIClient()  # posts API

        # 执行统计（移除API状态记忆）
        self.total_executions = 0
        self.feed_api_executions = 0
        self.posts_api_executions = 0
        self.last_execution_time = None
        self.last_api_used = None

    def execute_scheduled_task(self) -> bool:
        """执行定时调度任务的主要方法 - 每轮都重新开始，先尝试Feed API，失败后降级到Posts API"""
        try:
            self.total_executions += 1
            self.last_execution_time = datetime.now()

            self.logger.info(f"🔄 开始第 {self.total_executions} 次Memefans定时调度")
            self.logger.info("📡 每轮都先尝试Feed API...")

            # 第一阶段：尝试Feed API（最多重试3次）
            self.logger.info("🟡 阶段1: 尝试Feed API（最多重试3次）")
            success = self._execute_with_feed_api_retry()

            if success:
                self.last_api_used = "feed"
                self.logger.info("✅ Feed API执行成功，本轮完成")
                return True

            # 第二阶段：Feed API失败，降级到Posts API（最多重试3次）
            self.logger.warning("🔴 Feed API重试失败，降级到Posts API")
            self.logger.info("🟡 阶段2: 尝试Posts API（最多重试3次）")
            success = self._execute_with_posts_api_retry()

            if success:
                self.last_api_used = "posts (fallback)"
                self.logger.info("✅ Posts API降级执行成功，本轮完成")
                return True
            else:
                self.last_api_used = "both failed"
                self.logger.error("❌ Feed API和Posts API都失败，本轮执行失败")
                return False

        except Exception as e:
            self.logger.error(f"❌ 定时调度执行异常: {e}")
            return False

    def _execute_with_feed_api_retry(self) -> bool:
        """使用Feed API执行任务，内置重试机制（最多3次）"""
        max_retries = 3

        for attempt in range(max_retries):
            try:
                self.feed_api_executions += 1
                attempt_info = f"第{attempt + 1}/{max_retries}次"
                self.logger.info(f"📡 Feed API {attempt_info} 尝试...")

                # 使用feed API获取数据（每次尝试内部也有重试）
                api_data = self.memefans_client.fetch_data_with_retry(
                    page=1,
                    size=self.config.DEFAULT_PAGE_SIZE,
                    max_retries=1  # 减少内部重试，由外层控制
                )

                if not api_data:
                    self.logger.warning(f"❌ Feed API {attempt_info} 获取数据失败")
                    if attempt < max_retries - 1:
                        self.logger.info("⏳ 1秒后进行下次尝试...")
                        import time
                        time.sleep(1)
                    continue

                # 解析数据
                video_records = self.memefans_client.parse_items_to_video_records(api_data)

                if not video_records:
                    self.logger.warning(f"⚠️ Feed API {attempt_info} 未解析到有效数据")
                    if attempt < max_retries - 1:
                        self.logger.info("⏳ 1秒后进行下次尝试...")
                        import time
                        time.sleep(1)
                    continue

                # 处理数据
                if self._process_video_data(video_records, f"Feed API ({attempt_info})"):
                    self.logger.info(f"✅ Feed API {attempt_info} 执行成功")
                    return True
                else:
                    self.logger.warning(f"❌ Feed API {attempt_info} 数据处理失败")
                    if attempt < max_retries - 1:
                        self.logger.info("⏳ 1秒后进行下次尝试...")
                        import time
                        time.sleep(1)

            except Exception as e:
                self.logger.error(f"❌ Feed API {attempt_info} 执行异常: {e}")
                if attempt < max_retries - 1:
                    self.logger.info("⏳ 1秒后进行下次尝试...")
                    import time
                    time.sleep(1)

        self.logger.error(f"💥 Feed API重试{max_retries}次全部失败")
        return False

    def _execute_with_posts_api_retry(self) -> bool:
        """使用Posts API执行任务，内置重试机制（最多3次）"""
        max_retries = 3

        for attempt in range(max_retries):
            try:
                self.posts_api_executions += 1
                attempt_info = f"第{attempt + 1}/{max_retries}次"
                self.logger.info(f"📡 Posts API {attempt_info} 尝试...")

                # 使用posts API获取数据（每次尝试内部也有重试）
                api_data = self.posts_client.fetch_api_data_with_retry(
                    size=self.config.DEFAULT_PAGE_SIZE,
                    verify_ssl=False,
                    max_retries=1,  # 减少内部重试，由外层控制
                    retry_delay=1.0,
                    backoff_factor=2.0
                )

                if not api_data:
                    self.logger.warning(f"❌ Posts API {attempt_info} 获取数据失败")
                    if attempt < max_retries - 1:
                        self.logger.info("⏳ 1秒后进行下次尝试...")
                        import time
                        time.sleep(1)
                    continue

                # 解析数据
                video_records = self.posts_client.parse_items_to_video_records(api_data)

                if not video_records:
                    self.logger.warning(f"⚠️ Posts API {attempt_info} 未解析到有效数据")
                    if attempt < max_retries - 1:
                        self.logger.info("⏳ 1秒后进行下次尝试...")
                        import time
                        time.sleep(1)
                    continue

                # 处理数据
                if self._process_video_data(video_records, f"Posts API ({attempt_info})"):
                    self.logger.info(f"✅ Posts API {attempt_info} 执行成功")
                    return True
                else:
                    self.logger.warning(f"❌ Posts API {attempt_info} 数据处理失败")
                    if attempt < max_retries - 1:
                        self.logger.info("⏳ 1秒后进行下次尝试...")
                        import time
                        time.sleep(1)

            except Exception as e:
                self.logger.error(f"❌ Posts API {attempt_info} 执行异常: {e}")
                if attempt < max_retries - 1:
                    self.logger.info("⏳ 1秒后进行下次尝试...")
                    import time
                    time.sleep(1)

        self.logger.error(f"💥 Posts API重试{max_retries}次全部失败")
        return False

    def _process_video_data(self, video_records: List[VideoRecord], api_source: str) -> bool:
        """处理视频数据：存储、下载、上传"""
        try:
            self.logger.info(f"🔍 {api_source}解析到 {len(video_records)} 个视频记录")

            # 第1步：存储到数据库
            self.logger.info("💾 存储视频记录到数据库...")
            self._store_video_records(video_records)

            # 第2步：智能下载（跳过已存在的文件）
            self.logger.info("📥 开始智能下载...")
            new_downloads = self._smart_download_videos(video_records)

            # 第3步：自动上传新下载的视频
            if new_downloads and self.cloud_manager.jianguoyun_client:
                self.logger.info(f"☁️ 自动上传 {len(new_downloads)} 个新下载的视频...")
                self._upload_new_videos(new_downloads)
            elif new_downloads:
                self.logger.info("⚠️ 坚果云未配置，跳过上传步骤")

            self.logger.info(f"✅ {api_source}数据处理完成，新下载 {len(new_downloads)} 个视频")
            return True

        except Exception as e:
            self.logger.error(f"❌ 处理{api_source}数据异常: {e}")
            return False

    def _store_video_records(self, video_records: List[VideoRecord]):
        """存储视频记录到数据库"""
        try:
            success_count = 0
            for video in video_records:
                if self.db_manager.insert_or_update_video(video):
                    success_count += 1
            self.logger.info(f"💾 成功存储 {success_count}/{len(video_records)} 条视频记录")
        except Exception as e:
            self.logger.error(f"❌ 存储视频记录失败: {e}")

    def _smart_download_videos(self, video_records: List[VideoRecord]) -> List[VideoRecord]:
        """智能下载视频（跳过已存在和付费视频）"""
        try:
            # 过滤免费视频
            free_videos = [v for v in video_records if not v.is_primer]
            self.logger.info(f"📋 过滤后有 {len(free_videos)} 个免费视频")

            if not free_videos:
                return []

            # 过滤需要下载的视频
            videos_to_download = self._filter_videos_for_download(free_videos)

            if not videos_to_download:
                self.logger.info("📁 所有视频文件都已存在，跳过下载")
                return []

            self.logger.info(f"🎯 需要下载 {len(videos_to_download)} 个新视频")

            # 执行下载
            self.download_manager.download_videos_by_date(
                videos_to_download,
                self.config.DEFAULT_DOWNLOADS_DIR,
                force=False
            )

            # 检查下载结果
            new_downloads = []
            for video in videos_to_download:
                file_name = f"{video.title}_{video.video_date}.mp4"
                local_path = os.path.join(self.config.DEFAULT_DOWNLOADS_DIR, file_name)
                if os.path.exists(local_path):
                    self.db_manager.update_download_status(video.title, video.video_date, True)
                    new_downloads.append(video)
                    self.logger.info(f"✅ 下载成功：{video.title}")

            return new_downloads

        except Exception as e:
            self.logger.error(f"❌ 智能下载异常: {e}")
            return []

    def _filter_videos_for_download(self, videos: List[VideoRecord]) -> List[VideoRecord]:
        """过滤需要下载的视频"""
        import os
        videos_to_download = []

        for video in videos:
            file_name = f"{video.title}_{video.video_date}.mp4"
            local_path = os.path.join(self.config.DEFAULT_DOWNLOADS_DIR, file_name)

            if os.path.exists(local_path):
                self.logger.debug(f"📁 文件已存在，跳过: {video.title}")
                self.db_manager.update_download_status(video.title, video.video_date, True)
            else:
                videos_to_download.append(video)
                self.logger.debug(f"🆕 需要下载: {video.title}")

        return videos_to_download

    def _upload_new_videos(self, new_downloads: List[VideoRecord]):
        """上传新下载的视频"""
        try:
            upload_success_count = 0
            for video in new_downloads:
                try:
                    file_name = f"{video.title}_{video.video_date}.mp4"
                    local_path = os.path.join(self.config.DEFAULT_DOWNLOADS_DIR, file_name)

                    if os.path.exists(local_path):
                        # 尝试上传
                        success = self.cloud_manager.jianguoyun_client.upload_file(
                            local_path, file_name
                        )
                        if success:
                            upload_success_count += 1
                            self.logger.info(f"📤 上传成功：{video.title}")
                        else:
                            self.logger.warning(f"❌ 上传失败：{video.title}")
                except Exception as e:
                    self.logger.error(f"❌ 上传视频异常 {video.title}: {e}")

            self.logger.info(f"📤 上传结果: {upload_success_count}/{len(new_downloads)} 成功")

        except Exception as e:
            self.logger.error(f"❌ 批量上传异常: {e}")

    def get_status_info(self) -> Dict[str, Any]:
        """获取调度器状态信息"""
        return {
            'total_executions': self.total_executions,
            'feed_api_executions': self.feed_api_executions,
            'posts_api_executions': self.posts_api_executions,
            'strategy': 'per_round_fallback',  # 每轮都重新开始的降级策略
            'last_execution_time': self.last_execution_time.isoformat() if self.last_execution_time else None,
            'last_api_used': self.last_api_used
        }
