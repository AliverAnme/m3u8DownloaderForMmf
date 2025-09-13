"""
用户界面模块
处理交互式选择、输入解析和用户交互
"""

import re
from typing import List, Dict, Any

from ..utils.data_processor import DataProcessor
from ..download.manager import DownloadManager
from ..core.config import Config


class UserInterface:
    """用户界面类"""

    def __init__(self):
        self.config = Config()
        self.data_processor = DataProcessor()
        self.download_manager = DownloadManager()

    def parse_selection(self, selection_input: str, max_count: int) -> List[int]:
        """
        解析用户的选择输入

        Args:
            selection_input (str): 用户输入的选择字符串
            max_count (int): 最大视频数量

        Returns:
            List[int]: 解析后的索引列表
        """
        selections = []

        try:
            # 分割输入（支持逗号、空格分隔）
            parts = re.split(r'[,，\s]+', selection_input.strip())

            for part in parts:
                if not part:
                    continue

                # 处理范围选择（如 1-5）
                if '-' in part:
                    try:
                        start, end = map(int, part.split('-', 1))
                        if 1 <= start <= max_count and 1 <= end <= max_count and start <= end:
                            selections.extend(range(start, end + 1))
                        else:
                            print(f"⚠️ 范围 {part} 超出有效范围 (1-{max_count})")
                    except ValueError:
                        print(f"⚠️ 无效的范围格式: {part}")
                # 处理单个数字
                else:
                    try:
                        num = int(part)
                        if 1 <= num <= max_count:
                            selections.append(num)
                        else:
                            print(f"⚠️ 数字 {num} 超出有效范围 (1-{max_count})")
                    except ValueError:
                        print(f"⚠️ 无效的数字: {part}")

        except Exception as e:
            print(f"⚠️ 解析选择时发生错误: {e}")

        # 去重并排序
        selections = sorted(list(set(selections)))
        return selections

    def interactive_video_selection(self, json_file: str = None,
                                   output_dir: str = None) -> None:
        """
        交互式视频选择和下载

        Args:
            json_file (str): 包含视频信息的JSON文件
            output_dir (str): 下载目录
        """
        if json_file is None:
            json_file = self.config.EXTRACTED_ITEMS_FILE
        if output_dir is None:
            output_dir = self.config.DEFAULT_DOWNLOADS_DIR

        # 显示视频列表
        video_data = self.data_processor.display_video_list(json_file)

        if not video_data:
            return

        print(f"\n📋 选择说明:")
        print(f"• 单个视频: 输入数字，如 3")
        print(f"• 多个视频: 用逗号分隔，如 1,3,5")
        print(f"• 范围选择: 用横线连接，如 1-5")
        print(f"• 混合选择: 如 1,3-5,8")
        print(f"• 全部下载: 输入 all 或 *")
        print(f"• 取消下载: 输入 q 或 quit")

        selected_indices = []  # 初始化变量

        while True:
            selection_input = input(f"\n请选择要下载的视频 (1-{len(video_data)}): ").strip()

            if not selection_input:
                print("⚠️ 请输入有效的选择")
                continue

            # 检查特殊命令
            if selection_input.lower() in ['q', 'quit', '退出']:
                print("👋 取消下载，退出")
                return

            if selection_input.lower() in ['all', '*', '全部']:
                selected_indices = list(range(1, len(video_data) + 1))
                print(f"📥 选择全部 {len(selected_indices)} 个视频")
                break

            # 解析选择
            selected_indices = self.parse_selection(selection_input, len(video_data))

            if not selected_indices:
                print("⚠️ 没有有效的选择，请重新输入")
                continue

            # 确认选择
            print(f"\n📋 您选择了以下 {len(selected_indices)} 个视频:")
            for idx in selected_indices:
                title = video_data[idx-1].get('title', f"Video_{idx}")
                print(f"  [{idx:2d}] {title}")

            confirm = input(f"\n确认下载这些视频? (y/n, 默认y): ").strip().lower()
            if confirm in ['', 'y', 'yes', '是', '确认']:
                break
            else:
                print("重新选择...")
                continue

        # 执行下载
        self.download_manager.download_videos_from_list(video_data, selected_indices, output_dir)

    def show_menu(self) -> str:
        """显示主菜单并获取用户选择"""
        print("请选择执行模式:")
        print("1. 完整工作流程 (API获取 -> 提取字段 -> 保存)")
        print("2. 仅从本地JSON文件提取字段")
        print("3. 仅从API获取数据")
        print("4. 下载单个m3u8视频")
        print("5. 批量下载视频 (从extracted_items.json)")
        print("6. 交互式选择视频下载")

        return input("请输入选择 (1/2/3/4/5/6, 默认为1): ").strip() or "1"

    def get_download_mode_choice(self) -> str:
        """获取下载方式选择"""
        print("\n请选择下载方式:")
        print("1. 批量下载所有视频")
        print("2. 交互式选择下载")
        print("3. 跳过下载")

        return input("请输入选择 (1/2/3, 默认3): ").strip() or "3"
