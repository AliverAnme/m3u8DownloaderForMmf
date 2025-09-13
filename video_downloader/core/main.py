"""
主应用程序模块
整合所有功能模块，提供完整的工作流程
"""

import os
from typing import List, Dict, Any

from ..api.client import APIClient
from ..utils.data_processor import DataProcessor
from ..download.manager import DownloadManager
from ..ui.interface import UserInterface
from ..core.config import Config


class VideoDownloaderApp:
    """视频下载器主应用类"""

    def __init__(self):
        self.config = Config()
        self.api_client = APIClient()
        self.data_processor = DataProcessor()
        self.download_manager = DownloadManager()
        self.ui = UserInterface()

    def complete_workflow(self, size: int = 50) -> List[Dict[str, Any]]:
        """
        完整工作流程：从API获取数据 -> 保存到本地 -> 提取指定字段 -> 保存提取结果

        Args:
            size (int): 每页返回的数据条数，默认为50

        Returns:
            List[Dict[str, Any]]: 提取的字段列表
        """
        print("=== 开始完整工作流程 ===")

        # 步骤1：从API获取数据
        print("\n步骤1: 从API获取数据...")
        api_data = self.api_client.fetch_posts_from_api(size, verify_ssl=False)

        if not api_data:
            print("❌ 从API获取数据失败，工作流程中断")
            return []

        # 步骤2：显示API数据概览
        print("\n步骤2: 处理API数据...")
        self.api_client.process_posts_data(api_data)

        # 步骤3：提取指定字段
        print("\n步骤3: 提取指定字段 (id、url、title、description、cover)...")
        extracted_items = self.data_processor.extract_items_data(api_data)

        if not extracted_items:
            print("❌ 提取字段失败")
            return []

        print(f"✅ 成功提取了 {len(extracted_items)} 条记录")

        # 步骤4：保存提取的数据
        print("\n步骤4: 保存提取的数据...")
        self.data_processor.save_extracted_data(extracted_items)

        # 步骤5：显示提取结果预览
        print("\n步骤5: 显示提取结果预览...")
        print("前5条提取的记录:")
        for i, item in enumerate(extracted_items[:5], 1):
            print(f"\n记录 {i}:")
            print(f"  ID: {item['id']}")
            print(f"  标题: {item['title']}")
            print(f"  URL: {item['url'][:50]}..." if len(item['url']) > 50 else f"  URL: {item['url']}")
            print(f"  封面: {item['cover']}")
            print(f"  完整描述: {item['description'][:150]}..." if len(item['description']) > 150 else f"  完整描述: {item['description']}")

        print("\n=== 完整工作流程执行完成 ===")
        return extracted_items

    def handle_mode_1(self):
        """处理模式1：完整工作流程"""
        size = input("请输入每页数据条数 (默认50): ").strip()
        size = int(size) if size.isdigit() else 50

        extracted_items = self.complete_workflow(size)

        if extracted_items:
            print(f"\n🎉 工作流程成功完成！共处理了 {len(extracted_items)} 条记录")

            download_choice = self.ui.get_download_mode_choice()

            if download_choice == "1":
                output_dir = input("请输入下载目录 (默认downloads): ").strip() or "downloads"
                all_indices = list(range(1, len(extracted_items) + 1))
                self.download_manager.download_videos_from_list(extracted_items, all_indices, output_dir)
            elif download_choice == "2":
                output_dir = input("请输入下载目录 (默认downloads): ").strip() or "downloads"
                self.ui.interactive_video_selection(self.config.EXTRACTED_ITEMS_FILE, output_dir)
            else:
                print("跳过下载，程序结束")
        else:
            print("\n❌ 工作流程执行失败")

    def handle_mode_2(self):
        """处理模式2：仅从本地JSON文件提取字段"""
        print("\n=== 从JSON文件中提取数据 ===")

        json_file_path = input("请输入JSON文件路径 (默认example.json): ").strip() or "example.json"
        json_data = self.data_processor.read_json_file(json_file_path)

        if json_data:
            extracted_items = self.data_processor.extract_items_data(json_data)

            if extracted_items:
                print(f"成功提取了 {len(extracted_items)} 条记录")
                self.data_processor.save_extracted_data(extracted_items)

                # 显示前5条记录作为示例
                print("\n前5条提取的记录:")
                for i, item in enumerate(extracted_items[:5], 1):
                    print(f"\n记录 {i}:")
                    print(f"  ID: {item['id']}")
                    print(f"  标题: {item['title']}")
                    print(f"  URL: {item['url'][:50]}..." if len(item['url']) > 50 else f"  URL: {item['url']}")
                    print(f"  封面: {item['cover']}")
                    print(f"  完整描述: {item['description'][:150]}..." if len(item['description']) > 150 else f"  完整描述: {item['description']}")

                download_choice = input("\n是否下载视频? (y/n, 默认n): ").strip().lower()
                if download_choice == 'y':
                    output_dir = input("请输入下载目录 (默认downloads): ").strip() or "downloads"
                    all_indices = list(range(1, len(extracted_items) + 1))
                    self.download_manager.download_videos_from_list(extracted_items, all_indices, output_dir)
            else:
                print("没有提取到任何数据")
        else:
            print("无法读取JSON文件")

    def handle_mode_3(self):
        """处理模式3：仅从API获取数据"""
        print("\n=== 从API获取数据 ===")

        size = input("请输入每页数据条数 (默认50): ").strip()
        size = int(size) if size.isdigit() else 50

        ssl_choice = input("是否启用SSL证书验证? (y/n, 默认n): ").strip().lower()
        verify_ssl = ssl_choice == 'y'

        api_data = self.api_client.fetch_posts_from_api(size, verify_ssl=verify_ssl)

        if api_data:
            # 显示API数据概览
            self.api_client.process_posts_data(api_data)
            print("✅ API数据获取完成")

            # 询问用户是否要进一步处理数据
            process_choice = input("\n请选择后续操作:\n1. 提取视频数据并显示列表\n2. 仅保存原始API数据\n3. 退出\n请输入选择 (1/2/3, 默认1): ").strip() or "1"

            if process_choice == "1":
                # 提取视频数据
                extracted_items = self.data_processor.extract_items_data(api_data)

                if extracted_items:
                    print(f"✅ 成功提取了 {len(extracted_items)} 条记录")
                    self.data_processor.save_extracted_data(extracted_items)

                    # 显示视频列表
                    print(f"\n📺 提取的视频列表:")
                    print("=" * 80)
                    for i, item in enumerate(extracted_items[:10], 1):  # 显示前10个
                        title = item.get('title', f"Video_{item.get('id', i)}")
                        video_id = item.get('id', 'Unknown')
                        url = item.get('url', '')
                        print(f"[{i:2d}] {title}")
                        print(f"     ID: {video_id}")
                        print(f"     URL: {'✅ 有效' if url else '❌ 无效'}")
                        print()

                    if len(extracted_items) > 10:
                        print(f"... 还有 {len(extracted_items) - 10} 个视频")
                    print("=" * 80)

                    # 下载选择
                    download_choice = self.ui.get_download_mode_choice()

                    if download_choice == "1":
                        output_dir = input("请输入下载目录 (默认downloads): ").strip() or "downloads"
                        all_indices = list(range(1, len(extracted_items) + 1))
                        self.download_manager.download_videos_from_list(extracted_items, all_indices, output_dir)
                    elif download_choice == "2":
                        output_dir = input("请输入下载目录 (默认downloads): ").strip() or "downloads"
                        self.ui.interactive_video_selection(self.config.EXTRACTED_ITEMS_FILE, output_dir)
                    else:
                        print("跳过下载，数据已保存到文件")
                else:
                    print("❌ 提取数据失败")
            elif process_choice == "2":
                print("✅ 原始API数据已保存")
            else:
                print("退出模式3")
        else:
            print("❌ API数据获取失败")

    def handle_mode_4(self):
        """处理模式4：下载单个m3u8视频"""
        print("\n=== 下载单个m3u8视频 ===")

        video_url = input("请输入m3u8视频URL: ").strip()
        if not video_url:
            print("❌ 未提供视频URL")
        else:
            title = input("请输入视频标题 (可选): ").strip()
            cover_url = input("请输入封面图片URL (可选): ").strip()
            output_dir = input("请输入下载目录 (默认downloads): ").strip() or "downloads"

            quality_choice = input("选择画质 (1=最高画质, 2=最低画质, 默认1): ").strip()
            max_quality = quality_choice != "2"

            success = self.download_manager.download_m3u8_video(video_url, output_dir, title, max_quality, cover_url)

            if success:
                print("✅ 视频下载成功！")
            else:
                print("❌ 视频下载失败")

    def handle_mode_5(self):
        """处理模式5：批量下载视频"""
        print("\n=== 批量下载视频 ===")

        json_file = input("请输入JSON文件路径 (默认extracted_items.json): ").strip() or "extracted_items.json"
        output_dir = input("请输入下载目录 (默认downloads): ").strip() or "downloads"

        if not os.path.exists(json_file):
            print(f"❌ 文件 {json_file} 不存在")
        else:
            video_data = self.data_processor.read_json_file(json_file).get('items', [])
            if isinstance(video_data, list) and video_data:
                all_indices = list(range(1, len(video_data) + 1))
                self.download_manager.download_videos_from_list(video_data, all_indices, output_dir)
            else:
                print("❌ JSON文件格式不正确或没有视频数据")

    def handle_mode_6(self):
        """处理模式6：交互式选择视频下载"""
        print("\n=== 交互式选择视频下载 ===")

        json_file = input("请输入JSON文件路径 (默认extracted_items.json): ").strip() or "extracted_items.json"
        output_dir = input("请输入下载目录 (默认downloads): ").strip() or "downloads"

        self.ui.interactive_video_selection(json_file, output_dir)

    def run(self):
        """运行主应用程序"""
        mode = self.ui.show_menu()

        mode_handlers = {
            "1": self.handle_mode_1,
            "2": self.handle_mode_2,
            "3": self.handle_mode_3,
            "4": self.handle_mode_4,
            "5": self.handle_mode_5,
            "6": self.handle_mode_6
        }

        handler = mode_handlers.get(mode)
        if handler:
            handler()
        else:
            print("❌ 无效的选择，程序退出")
