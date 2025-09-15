"""
命令行应用控制器 - 整合所有功能模块
"""

import os
import importlib
from typing import List

from ..api.client import APIClient
from ..database.manager import DatabaseManager
from ..database.models import VideoRecord
from ..download.manager import DownloadManager
from ..core.config import Config


class CLIVideoDownloaderApp:
    """命令行视频下载器应用"""

    def __init__(self):
        """初始化应用"""
        self.config = Config()

        # 确保必要的目录存在
        os.makedirs(self.config.DATA_DIR, exist_ok=True)
        os.makedirs(self.config.LOGS_DIR, exist_ok=True)
        os.makedirs(self.config.TEMP_DIR, exist_ok=True)
        os.makedirs(self.config.DEFAULT_DOWNLOADS_DIR, exist_ok=True)

        # 动态导入UI模块以确保获取最新版本
        ui_module = importlib.import_module('video_downloader.ui.interface')
        importlib.reload(ui_module)
        UserInterface = getattr(ui_module, 'UserInterface')

        self.ui = UserInterface()
        self.api_client = APIClient()
        self.db_manager = DatabaseManager(self.config.DATABASE_FILE)
        self.download_manager = DownloadManager()

        # 确保下载目录存在
        os.makedirs(self.config.DEFAULT_DOWNLOADS_DIR, exist_ok=True)

    def run(self):
        """运行主程序"""
        try:
            # 显示启动信息
            self.ui.show_startup_banner()
            self.show_startup_info()

            # 主循环
            while True:
                choice = self.ui.show_main_menu()

                if choice == '1':
                    self.handle_api_parsing()
                elif choice == '2':
                    self.handle_download_menu()
                elif choice == '3':
                    self.handle_view_database()
                elif choice == '4':
                    self.handle_sync_directory()
                elif choice == '5':
                    break

                self.ui.wait_for_enter()

            # 退出程序
            self.ui.show_exit_message()

        except KeyboardInterrupt:
            print("\n\n👋 用户中断程序，正在安全退出...")
        except Exception as e:
            self.ui.show_error(f"程序运行时发生错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 清理资源
            self.cleanup()

    def show_startup_info(self):
        """显示启动信息"""
        try:
            stats = self.db_manager.get_statistics()
            self.ui.display_statistics(stats)

            # 检查ffmpeg
            if self.download_manager.check_ffmpeg():
                self.ui.show_success("ffmpeg 检查通过")
            else:
                self.ui.show_warning("ffmpeg 未找到，下载功能可能无法正常使用")

        except Exception as e:
            self.ui.show_error(f"获取启动信息失败: {e}")

    def handle_enhanced_json_parsing(self):
        """处理增强JSON解析操作"""
        try:
            self.ui.show_info("🔍 启动增强JSON解析功能...")

            # 选择数据源
            source_choice = self.ui.show_enhanced_parsing_menu()

            if source_choice == '1':
                # 从API获取数据并使用增强解析
                size = self.ui.get_api_size_input(self.config.DEFAULT_PAGE_SIZE)
                self.ui.show_info(f"📡 获取API数据 ({size} 条) 并使用增强解析...")

                # 获取API数据
                api_data = self.api_client.fetch_api_data(size)
                if not api_data:
                    self.ui.show_warning("❌ 无法获取API数据")
                    return

                # 使用增强解析器处理
                video_records = self.api_client.parse_api_response_enhanced(api_data)

            elif source_choice == '2':
                # 从本地JSON文件解析
                file_path = self.ui.get_json_file_path_input()
                if not file_path or not os.path.exists(file_path):
                    self.ui.show_warning("❌ 文件不存在或路径无效")
                    return

                self.ui.show_info(f"📖 使用增强解析器读取文件: {file_path}")

                # 使用数据处理器的增强解析功能
                from ..utils.data_processor import DataProcessor
                processor = DataProcessor()
                json_data = processor.read_json_file_enhanced(file_path)

                if not json_data or 'items' not in json_data:
                    self.ui.show_warning("❌ 文件中没有找到有效的items数据")
                    return

                # 转换为VideoRecord
                video_records = []
                items = json_data['items']
                for i, item in enumerate(items):
                    try:
                        if isinstance(item, dict) and any(key in item for key in ['description', 'title', 'content']):
                            description = item.get('description', '') or item.get('content', '') or item.get('title', '')
                            if description:
                                standardized_data = {
                                    'description': str(description),
                                    'cover': item.get('cover', ''),
                                    'url': item.get('url', ''),
                                    'id': item.get('id', ''),
                                    'title': item.get('title', '')
                                }
                                video_record = VideoRecord.from_api_data(standardized_data)
                                if video_record and video_record.title:
                                    video_records.append(video_record)
                    except Exception as e:
                        print(f"⚠️ 跳过第 {i+1} 项: {e}")

            elif source_choice == '3':
                # 测试字符串对象解析
                self._test_string_object_parsing()
                return
            else:
                return

            if not video_records:
                self.ui.show_warning("❌ 增强解析未获取到任何有效视频数据")
                return

            # 处理解析结果
            self.ui.show_success(f"✅ 增强解析成功，获得 {len(video_records)} 条视频记录")
            self._process_video_records(video_records)

        except Exception as e:
            self.ui.show_error(f"❌ 增强JSON解析失败: {e}")
            import traceback
            traceback.print_exc()

    def _test_string_object_parsing(self):
        """测试字符串对象解析功能"""
        self.ui.show_info("🧪 测试字符串对象解析功能...")

        # 创建测试数据
        test_data = {
            "items": [
                # 正常的字典格式
                {
                    "id": "test001",
                    "title": "正常的视频标题",
                    "description": "【测试视频】这是一个正常的视频描述 #测试 #视频",
                    "url": "https://example.com/video1.m3u8",
                    "cover": "https://example.com/cover1.jpg"
                },
                # 字符串格式的JSON
                '{"id": "test002", "description": "【JSON字符串】这是JSON字符串格式的数据 #测试", "url": "https://example.com/video2.m3u8"}',
                # 对象表示字符串
                '<Video object at 0x7f8b8c0d4f40>',
                # 对象参数格式
                'Video(id="test003", description="【对象格式】对象表示的视频数据 #测试", url="https://example.com/video3.m3u8")',
                # 纯文本描述
                "这是一段纯文本描述，包含了一些视频信息，但不是标准格式",
                # 无效数据
                None,
                "",
                "null",
                # 混合格式
                ["nested_data", {"description": "嵌套在列表中的数据"}]
            ]
        }

        try:
            # 使用增强解析器处理测试数据
            video_records = self.api_client.parse_api_response_enhanced(test_data)

            self.ui.show_success(f"✅ 测试完成！成功解析 {len(video_records)} 条记录")

            # 显示解析结果
            if video_records:
                print("\n📋 解析结果预览:")
                for i, record in enumerate(video_records[:3], 1):
                    print(f"{i}. {record.title}")
                    print(f"   描述: {record.description[:50]}...")
                    print(f"   URL: {record.video_url}")
                    print()

        except Exception as e:
            self.ui.show_error(f"❌ 测试失败: {e}")

    def handle_api_parsing(self):
        """处理API解析操作"""
        while True:
            choice = self.ui.show_api_menu()

            if choice == '1':
                self.handle_basic_api_parsing()
            elif choice == '2':
                self.handle_api_parsing_with_retry()
            elif choice == '3':
                self.handle_multi_page_api_parsing()
            elif choice == '4':
                self.handle_enhanced_json_parsing()  # 新增选项
            elif choice == '5':
                break

            if choice != '5':
                self.ui.wait_for_enter()

    def handle_basic_api_parsing(self):
        """处理基础API解析操作"""
        try:
            # 获取API size参数
            size = self.ui.get_api_size_input(self.config.DEFAULT_PAGE_SIZE)

            self.ui.show_info(f"开始执行基础API解析，请求 {size} 条数据...")

            # 获取API数据并解析
            video_records = self.api_client.fetch_and_parse_videos(size)

            if not video_records:
                self.ui.show_warning("未获取到任何视频数据")
                return

            self._process_video_records(video_records)

        except Exception as e:
            self.ui.show_error(f"基础API解析失败: {e}")
            import traceback
            traceback.print_exc()

    def handle_api_parsing_with_retry(self):
        """处理带重试机制的API解析操作"""
        try:
            # 获取参数
            size = self.ui.get_api_size_input(self.config.DEFAULT_PAGE_SIZE)
            max_retries = self.ui.get_retry_count_input()
            retry_delay = self.ui.get_retry_delay_input()

            # 询问是否使用增强解析
            use_enhanced = self.ui.confirm_action("是否使用增强JSON解析？(推荐，支持更多数据格式)")

            self.ui.show_info(f"开始执行带重试的API解析...")
            self.ui.show_info(f"请求数据条数: {size}")
            self.ui.show_info(f"最大重试次数: {max_retries}")
            self.ui.show_info(f"重试延迟: {retry_delay} 秒")
            self.ui.show_info(f"增强解析: {'启用' if use_enhanced else '禁用'}")

            # 使用增强版本的重试机制
            video_records = self.api_client.fetch_and_parse_videos_with_retry_enhanced(
                size=size,
                max_retries=max_retries,
                retry_delay=retry_delay,
                use_enhanced_parsing=use_enhanced
            )

            if not video_records:
                self.ui.show_warning("重试后仍未获取到任何视频数据")
                return

            self._process_video_records(video_records)

        except Exception as e:
            self.ui.show_error(f"带重试的API解析失败: {e}")
            import traceback
            traceback.print_exc()

    def handle_multi_page_api_parsing(self):
        """处理多页API解析操作"""
        try:
            # 获取参数
            pages_input = self.ui.get_pages_input()
            size = self.ui.get_api_size_input(self.config.DEFAULT_PAGE_SIZE)
            max_retries = self.ui.get_retry_count_input()
            page_delay = self.ui.get_page_delay_input()

            # 询问是否使用增强解析
            use_enhanced = self.ui.confirm_action("是否使用增强JSON解析？(推荐，支持更多数据格式)")

            # 解析页码
            pages = self._parse_pages_input(pages_input)
            if not pages:
                self.ui.show_warning("页码输入格式错误")
                return

            self.ui.show_info(f"开始执行多页API解析...")
            self.ui.show_info(f"页码: {pages}")
            self.ui.show_info(f"每页数据条数: {size}")
            self.ui.show_info(f"每页重试次数: {max_retries}")
            self.ui.show_info(f"页面间延迟: {page_delay} 秒")
            self.ui.show_info(f"增强解析: {'启用' if use_enhanced else '禁用'}")

            # 使用增强版本的多页重试机制
            video_records = self.api_client.fetch_multiple_pages_with_retry_enhanced(
                pages=pages,
                size=size,
                max_retries=max_retries,
                page_delay=page_delay,
                use_enhanced_parsing=use_enhanced
            )

            if not video_records:
                self.ui.show_warning("多页请求后仍未获取到任何视频数据")
                return

            self._process_video_records(video_records)

        except Exception as e:
            self.ui.show_error(f"多页API解析失败: {e}")
            import traceback
            traceback.print_exc()

    def _parse_pages_input(self, pages_input: str) -> List[int]:
        """解析页码输入"""
        try:
            pages = []
            parts = pages_input.split(',')

            for part in parts:
                part = part.strip()
                if '-' in part:
                    # 范围格式：1-5
                    start, end = map(int, part.split('-'))
                    pages.extend(range(start, end + 1))
                else:
                    # 单个页码
                    pages.append(int(part))

            return sorted(list(set(pages)))  # 去重并排序
        except:
            return []

    def _process_video_records(self, video_records: List[VideoRecord]):
        """处理视频记录的通用方法"""
        try:
            # 检查重复数据
            unique_keys = set()
            unique_records = []
            duplicate_count = 0

            for video in video_records:
                key = f"{video.title}_{video.video_date}"
                if key not in unique_keys:
                    unique_keys.add(key)
                    unique_records.append(video)
                else:
                    duplicate_count += 1
                    print(f"⚠️ 发现重复数据：{video.title} ({video.video_date})")

            # 写入数据库
            success_count = 0
            failed_count = 0
            updated_count = 0

            for video in unique_records:
                # 检查记录是否已存在
                existing_videos = self.db_manager.get_videos_by_date(video.video_date)
                is_existing = any(v.title == video.title and v.video_date == video.video_date for v in existing_videos)

                if self.db_manager.insert_or_update_video(video):
                    if is_existing:
                        updated_count += 1
                    else:
                        success_count += 1
                else:
                    failed_count += 1

            # 显示详细的统计信息
            total_processed = len(video_records)
            total_unique = len(unique_records)

            print(f"\n📊 详细统计信息:")
            print(f"🔍 API返回记录数: {total_processed}")
            print(f"📋 唯一记录数: {total_unique}")
            if duplicate_count > 0:
                print(f"🔄 重复记录数: {duplicate_count}")
            print(f"✅ 新增记录数: {success_count}")
            print(f"🔄 更新记录数: {updated_count}")
            if failed_count > 0:
                print(f"❌ 失败记录数: {failed_count}")

            self.ui.show_success(f"API解析完成，共处理 {total_processed} 条数据，" +
                               f"其中 {total_unique} 条唯一记录，新增 {success_count} 条，更新 {updated_count} 条")

        except Exception as e:
            self.ui.show_error(f"API解析失败: {e}")
            import traceback
            traceback.print_exc()

    def handle_download_menu(self):
        """处理下载菜单"""
        while True:
            choice = self.ui.show_download_menu()

            if choice == '1':
                self.handle_download_by_date_all()
            elif choice == '2':
                self.handle_download_all_pending()
            elif choice == '3':
                self.handle_download_by_search()
            elif choice == '4':
                self.handle_download_by_date_pending()
            elif choice == '5':
                self.handle_download_by_index()
            elif choice == '6':
                break

            if choice != '6':
                self.ui.wait_for_enter()

    def handle_download_by_date_all(self):
        """按日期全量下载"""
        try:
            video_date = self.ui.get_video_date_input("请输入要下载的视频日期")

            # 获取该日期的所有视频
            videos = self.db_manager.get_videos_by_date(video_date)

            if not videos:
                self.ui.show_warning(f"未找到日期为 {video_date} 的视频")
                return

            self.ui.display_video_list(videos, f"日期 {video_date} 的视频")

            if not self.ui.confirm_action(f"确认下载日期 {video_date} 的所有 {len(videos)} 个视频？"):
                return

            # 执行下载
            stats = self.download_manager.download_videos_by_date(
                videos, self.config.DEFAULT_DOWNLOADS_DIR, force=True
            )

            # 更新数据库状态
            for video in videos:
                if not video.is_primer:  # 只更新非付费视频的状态
                    self.db_manager.update_download_status(video.title, video.video_date, True)

            self.ui.show_download_result(stats)

        except Exception as e:
            self.ui.show_error(f"按日期下载失败: {e}")

    def handle_download_all_pending(self):
        """全局补全下载"""
        try:
            # 获取所有未下载的视频
            videos = self.db_manager.get_undownloaded_videos()

            if not videos:
                self.ui.show_info("所有视频都已下载完成")
                return

            # 过滤掉付费视频
            free_videos = [v for v in videos if not v.is_primer]

            if not free_videos:
                self.ui.show_info("所有免费视频都已下载完成")
                return

            self.ui.display_video_list(free_videos, "待下载的免费视频")

            if not self.ui.confirm_action(f"确认下载所有 {len(free_videos)} 个免费视频？"):
                return

            # 执行下载
            stats = self.download_manager.download_videos_by_date(
                free_videos, self.config.DEFAULT_DOWNLOADS_DIR, force=False
            )

            # 更新数据库状态
            for video in free_videos:
                self.db_manager.update_download_status(video.title, video.video_date, True)

            self.ui.show_download_result(stats)

        except Exception as e:
            self.ui.show_error(f"全局补全下载失败: {e}")

    def handle_download_by_search(self):
        """指定视频下载"""
        try:
            search_term = self.ui.get_search_input()

            # 根据输入判断是搜索标题还是日期
            if search_term.isdigit() and len(search_term) == 4:
                # 按日期搜索
                videos = self.db_manager.get_videos_by_date(search_term)
            else:
                # 按标题搜索
                videos = self.db_manager.get_videos_by_title(search_term)

            if not videos:
                self.ui.show_warning(f"未找到包含 '{search_term}' 的视频")
                return

            self.ui.display_video_list(videos, f"搜索结果")

            if not self.ui.confirm_action(f"确认下载这 {len(videos)} 个视频？"):
                return

            # 执行下载
            stats = self.download_manager.download_videos_by_date(
                videos, self.config.DEFAULT_DOWNLOADS_DIR, force=False
            )

            # 更新数据库状态
            for video in videos:
                if not video.is_primer:
                    self.db_manager.update_download_status(video.title, video.video_date, True)

            self.ui.show_download_result(stats)

        except Exception as e:
            self.ui.show_error(f"指定视频下载失败: {e}")

    def handle_download_by_date_pending(self):
        """按日期补全下载"""
        try:
            video_date = self.ui.get_video_date_input("请输入要补全下载的视频日期")

            # 获取该日期未下载的视频
            videos = self.db_manager.get_undownloaded_videos(video_date)

            if not videos:
                self.ui.show_info(f"日期 {video_date} 的视频都已下载完成")
                return

            # 过滤掉付费视频
            free_videos = [v for v in videos if not v.is_primer]

            if not free_videos:
                self.ui.show_info(f"日期 {video_date} 的免费视频都已下载完成")
                return

            self.ui.display_video_list(free_videos, f"日期 {video_date} 待下载的免费视频")

            if not self.ui.confirm_action(f"确认下载日期 {video_date} 的 {len(free_videos)} 个免费视频？"):
                return

            # 执行下载
            stats = self.download_manager.download_videos_by_date(
                free_videos, self.config.DEFAULT_DOWNLOADS_DIR, force=False
            )

            # 更新数据库状态
            for video in free_videos:
                self.db_manager.update_download_status(video.title, video.video_date, True)

            self.ui.show_download_result(stats)

        except Exception as e:
            self.ui.show_error(f"按日期补全下载失败: {e}")

    def handle_download_by_index(self):
        """指定序号下载"""
        try:
            # 获取所有视频列表
            videos = self.db_manager.get_all_videos()

            if not videos:
                self.ui.show_info("数据库中暂无视频记录")
                return

            # 显示视频列表
            self.ui.display_video_list(videos, "所有视频列表")

            # 获取用户选择的序号
            selected_indices = self.ui.get_index_selection(videos)

            if not selected_indices:
                self.ui.show_info("未选择任何视频")
                return

            # 根据序号获取对应的视频记录
            selected_videos = []
            for idx in selected_indices:
                if 1 <= idx <= len(videos):
                    selected_videos.append(videos[idx-1])

            if not selected_videos:
                self.ui.show_warning("没有有效的视频选择")
                return

            # 显示即将下载的视频
            print(f"\n🎯 准备下载 {len(selected_videos)} 个视频:")
            for i, video in enumerate(selected_videos, 1):
                status = "💰付费" if video.is_primer else "🆓免费"
                download_status = "✅已下载" if video.download else "⏳待下载"
                print(f"  {i}. {video.title} ({status}, {download_status})")

            # 执行下载
            stats = self.download_manager.download_videos_by_date(
                selected_videos, self.config.DEFAULT_DOWNLOADS_DIR, force=False
            )

            # 更新数据库状态
            for video in selected_videos:
                if not video.is_primer:  # 只更新非付费视频的状态
                    self.db_manager.update_download_status(video.title, video.video_date, True)

            self.ui.show_download_result(stats)

        except Exception as e:
            self.ui.show_error(f"指定序号下载失败: {e}")

    def handle_view_database(self):
        """查看数据库所有视频信息"""
        try:
            videos = self.db_manager.get_all_videos()

            if not videos:
                self.ui.show_info("数据库中暂无视频记录")
                return

            self.ui.display_video_list(videos, "数据库中的所有视频")

            # 显示统计信息
            stats = self.db_manager.get_statistics()
            self.ui.display_statistics(stats)

        except Exception as e:
            self.ui.show_error(f"查看数据库失败: {e}")

    def handle_sync_directory(self):
        """同步本地目录与数据库状态"""
        try:
            self.ui.show_info(f"开始同步本地目录: {self.config.DEFAULT_DOWNLOADS_DIR}")

            updated_count = self.db_manager.sync_with_local_directory(
                self.config.DEFAULT_DOWNLOADS_DIR
            )

            if updated_count > 0:
                self.ui.show_success(f"同步完成，更新了 {updated_count} 条记录的下载状态")
            else:
                self.ui.show_info("同步完成，无需更新")

            # 显示更新后的统计信息
            stats = self.db_manager.get_statistics()
            self.ui.display_statistics(stats)

        except Exception as e:
            self.ui.show_error(f"同步目录失败: {e}")

    def cleanup(self):
        """清理资源"""
        try:
            # 清理下载管理器的临时文件
            self.download_manager.cleanup_temp_files()
        except Exception as e:
            print(f"清理资源时发生错误: {e}")
