"""
用户界面模块 - 命令行交互界面
"""

import os
from typing import List
from ..database.models import VideoRecord


class UserInterface:
    """命令行用户界面"""

    def __init__(self):
        pass

    def show_main_menu(self) -> str:
        """显示主菜单并获取用户输入"""
        print("\n" + "="*60)
        print("🎬 【视频解析与下载工具】")
        print("="*60)
        print("1. 执行API解析并写入数据库")
        print("2. 本地JSON文件解析（支持UID提取）")
        print("3. Feed文件批量解析（从feed.json提取ID并请求详情）")
        print("4. 下载操作（进入子菜单）")
        print("5. 查看数据库所有视频信息")
        print("6. 同步本地目录与数据库状态")
        print("7. 退出程序")
        print("-"*60)

        while True:
            choice = input("请输入操作编号（1-7）: ").strip()
            if choice in ['1', '2', '3', '4', '5', '6', '7']:
                return choice
            print("❌ 无效输入，请输入1-7之间的数字")

    def show_download_menu(self) -> str:
        """显示下载子菜单并获取用户输入"""
        print("\n" + "="*60)
        print("📥 【下载操作子菜单】")
        print("="*60)
        print("1. 按日期全量下载（输入目标日期）")
        print("2. 全局补全下载（下载所有未保存视频）")
        print("3. 指定视频下载（输入视频标题/日期）")
        print("4. 按日期补全下载（输入目标日期）")
        print("5. 指定序号下载（选择视频序号）")
        print("6. 返回主菜单")
        print("-"*60)

        while True:
            choice = input("请输入操作编号（1-6）: ").strip()
            if choice in ['1', '2', '3', '4', '5', '6']:
                return choice
            print("❌ 无效输入，请输入1-6之间的数字")

    def show_api_menu(self) -> str:
        """显示API操作子菜单并获取用户输入"""
        print("\n" + "="*60)
        print("🔄 【API解析操作子菜单】")
        print("="*60)
        print("1. 基础API解析（单次请求）")
        print("2. 带重试机制的API解析")
        print("3. 多页API解析（支持重试）")
        print("4. 增强JSON解析（支持字符串对象）")
        print("5. 返回主菜单")
        print("-"*60)

        while True:
            choice = input("请输入操作编号（1-5）: ").strip()
            if choice in ['1', '2', '3', '4', '5']:
                return choice
            print("❌ 无效输入，请输入1-5之间的数字")

    def show_enhanced_parsing_menu(self) -> str:
        """显示增强解析菜单并获取用户输入"""
        print("\n" + "="*50)
        print("🔍 【增强JSON解析选项】")
        print("="*50)
        print("1. 从API获取数据并使用增强解析")
        print("2. 从本地JSON文件解析")
        print("3. 测试字符串对象解析功能")
        print("4. 返回上级菜单")
        print("-"*50)

        while True:
            choice = input("请选择数据源（1-4）: ").strip()
            if choice in ['1', '2', '3', '4']:
                return choice
            print("❌ 无效输入，请输入1-4之间的数字")

    def get_video_date_input(self, prompt: str = "请输入视频日期（4位数字，如0714）") -> str:
        """获取视频日期输入"""
        while True:
            date_input = input(f"{prompt}: ").strip()
            if date_input.isdigit() and len(date_input) == 4:
                return date_input
            print("❌ 请输入4位数字的日期格式（如0714）")

    def get_search_input(self, prompt: str = "请输入搜索关键词（标题或日期）") -> str:
        """获取搜索关键词输入"""
        search_input = input(f"{prompt}: ").strip()
        if not search_input:
            print("❌ 输入不能为空")
            return self.get_search_input(prompt)
        return search_input

    def confirm_action(self, message: str) -> bool:
        """确认操作"""
        while True:
            choice = input(f"{message} (y/n): ").strip().lower()
            if choice in ['y', 'yes', '是']:
                return True
            elif choice in ['n', 'no', '否']:
                return False
            print("❌ 请输入 y 或 n")

    def display_video_list(self, videos: List[VideoRecord], title: str = "视频列表"):
        """显示视频列表"""
        if not videos:
            print(f"\n📋 {title}: 暂无数据")
            return

        print(f"\n📋 {title} (共{len(videos)}个):")
        print("-" * 100)
        print(f"{'序号':<4} {'标题':<30} {'日期':<8} {'下载状态':<8} {'付费状态':<8} {'描述':<30}")
        print("-" * 100)

        for i, video in enumerate(videos, 1):
            download_status = "✅已下载" if video.download else "⏳待下载"
            primer_status = "💰付费" if video.is_primer else "🆓免费"
            description = video.description[:27] + "..." if len(video.description) > 30 else video.description

            print(f"{i:<4} {video.title[:27]+'...' if len(video.title) > 30 else video.title:<30} "
                  f"{video.video_date:<8} {download_status:<8} {primer_status:<8} {description:<30}")

        print("-" * 100)

    def display_statistics(self, stats: dict):
        """显示统计信息"""
        print("\n📊 数据库统计信息:")
        print("-" * 40)
        print(f"📺 视频总数: {stats.get('total', 0)}")
        print(f"✅ 已下载: {stats.get('downloaded', 0)}")
        print(f"⏳ 待下载: {stats.get('pending', 0)}")
        print(f"💰 付费视频: {stats.get('primer', 0)}")
        print("-" * 40)

    def show_progress(self, current: int, total: int, item_name: str = "项"):
        """显示进度"""
        percentage = (current / total * 100) if total > 0 else 0
        print(f"📊 进度: {current}/{total} ({percentage:.1f}%) - {item_name}")

    def show_download_result(self, stats: dict):
        """显示下载结果统计"""
        print("\n🎯 下载结果统计:")
        print("-" * 30)
        print(f"✅ 成功: {stats.get('success', 0)}")
        print(f"❌ 失败: {stats.get('failed', 0)}")
        print(f"⏭️ 跳过: {stats.get('skipped', 0)}")
        print("-" * 30)

    def wait_for_enter(self, message: str = "按回车键继续..."):
        """等待用户按回车"""
        input(f"\n{message}")

    def clear_screen(self):
        """清屏"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def show_error(self, message: str):
        """显示错误信息"""
        print(f"❌ 错误: {message}")

    def show_success(self, message: str):
        """显示成功信息"""
        print(f"✅ {message}")

    def show_warning(self, message: str):
        """显示警告信息"""
        print(f"⚠️ 警告: {message}")

    def show_info(self, message: str):
        """显示信息"""
        print(f"ℹ️ {message}")

    def show_startup_banner(self):
        """显示启动横幅"""
        print("\n" + "="*60)
        print("🎬 视频解析与下载工具")
        print("📝 支持API解析、数据库管理、视频下载")
        print("🔧 基于ffmpeg的音视频合并和封面嵌入")
        print("="*60)

    def show_exit_message(self):
        """显示退出信息"""
        print("\n👋 感谢使用视频解析与下载工具！")
        print("🔧 程序已安全退出")

    def get_index_selection(self, videos: List[VideoRecord]) -> List[int]:
        """获取用户选择的视频序号"""
        if not videos:
            return []

        print("\n📋 选择说明:")
        print("• 单个视频: 输入数字，如 3")
        print("• 多个视频: 用逗号分隔，如 1,3,5")
        print("• 范围选择: 用横线连接，如 1-5")
        print("• 混合选择: 如 1,3-5,8")
        print("• 全部下载: 输入 all 或 *")
        print("• 取消选择: 输入 q 或 quit")

        while True:
            selection_input = input(f"\n请选择要下载的视频序号 (1-{len(videos)}): ").strip()

            if not selection_input:
                print("⚠️ 请输入有效的选择")
                continue

            # 检查特殊命令
            if selection_input.lower() in ['q', 'quit', '退出']:
                return []

            if selection_input.lower() in ['all', '*', '全部']:
                return list(range(1, len(videos) + 1))

            # 解析选择
            selected_indices = self._parse_selection(selection_input, len(videos))

            if not selected_indices:
                print("⚠️ 没有有效的选择，请重新输入")
                continue

            # 显示选择的视频
            print(f"\n📋 您选择了以下 {len(selected_indices)} 个视频:")
            for idx in selected_indices:
                video = videos[idx-1]
                status = "💰付费" if video.is_primer else "🆓免费"
                print(f"  [{idx:2d}] {video.title[:50]}... ({status})")

            if self.confirm_action(f"确认下载这些视频？"):
                return selected_indices
            else:
                print("重新选择...")
                continue

    def _parse_selection(self, selection_input: str, max_count: int) -> List[int]:
        """解析用户的选择输入"""
        import re
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

    def get_api_size_input(self, default_size: int = 50) -> int:
        """获取API请求的size参数"""
        while True:
            size_input = input(f"请输入API请求数据条数 (默认{default_size}, 范围1-200): ").strip()

            if not size_input:
                return default_size

            try:
                size = int(size_input)
                if 1 <= size <= 200:
                    return size
                else:
                    print("❌ 请输入1-200之间的数字")
            except ValueError:
                print("❌ 请输入有效的数字")

    def get_retry_count_input(self) -> int:
        """获取重试次数输入"""
        while True:
            try:
                retry_input = input("请输入最大重试次数（默认3次，范围1-10）: ").strip()
                if not retry_input:
                    return 3  # 默认值
                retry_count = int(retry_input)
                if 1 <= retry_count <= 10:
                    return retry_count
                else:
                    print("❌ 重试次数必须在1-10之间")
            except ValueError:
                print("❌ 请输入有效的数字")

    def get_retry_delay_input(self) -> float:
        """获取重试延迟时间输入"""
        while True:
            try:
                delay_input = input("请输入重试延迟时间（默认1.0秒，范围0.1-10.0）: ").strip()
                if not delay_input:
                    return 1.0  # 默认值
                delay = float(delay_input)
                if 0.1 <= delay <= 10.0:
                    return delay
                else:
                    print("❌ 延迟时间必须在0.1-10.0秒之间")
            except ValueError:
                print("❌ 请输入有效的数字")

    def get_pages_input(self) -> str:
        """获取页码输入"""
        print("\n📄 页码输入格式说明:")
        print("  - 单个页码: 1")
        print("  - 多个页码: 1,3,5")
        print("  - 页码范围: 1-5")
        print("  - 混合格式: 1,3-5,8")

        while True:
            pages_input = input("请输入要获取的页码: ").strip()
            if pages_input:
                return pages_input
            print("❌ 页码输入不能为空")

    def get_page_delay_input(self) -> float:
        """获取页面间延迟时间输入"""
        while True:
            try:
                delay_input = input("请输入页面间延迟时间（默认0.5秒，范围0.1-5.0）: ").strip()
                if not delay_input:
                    return 0.5  # 默认值
                delay = float(delay_input)
                if 0.1 <= delay <= 5.0:
                    return delay
                else:
                    print("❌ 页面间延迟时间必须在0.1-5.0秒之间")
            except ValueError:
                print("❌ 请输入有效的数字")

    def get_json_file_path_input(self) -> str:
        """获取JSON文件路径输入"""
        print("\n💡 提示：可以输入绝对路径或相对路径")
        print("   示例：video_downloader/data/api_response.json")

        while True:
            file_path = input("请输入JSON文件路径: ").strip()
            if not file_path:
                print("❌ 文件路径不能为空")
                continue

            # 处理相对路径
            if not os.path.isabs(file_path):
                # 相对于项目根目录
                current_dir = os.getcwd()
                file_path = os.path.join(current_dir, file_path)

            if os.path.exists(file_path):
                return file_path
            else:
                print(f"❌ 文件不存在: {file_path}")
                retry = input("是否重新输入？(y/n): ").strip().lower()
                if retry not in ['y', 'yes', '是']:
                    return ""  # 返回空字符串而不是None

    def get_feed_file_path_input(self) -> str:
        """获取Feed文件路径输入"""
        print("\n💡 提示：请输入feed.json文件的路径")
        print("   示例：feed.json 或 /path/to/feed.json")

        while True:
            file_path = input("请输入Feed文件路径: ").strip()
            if not file_path:
                print("❌ 文件路径不能为空")
                continue

            # 处理相对路径
            if not os.path.isabs(file_path):
                # 相对于项目根目录
                current_dir = os.getcwd()
                file_path = os.path.join(current_dir, file_path)

            if os.path.exists(file_path):
                return file_path
            else:
                print(f"❌ 文件不存在: {file_path}")
                retry = input("是否重新输入？(y/n): ").strip().lower()
                if retry not in ['y', 'yes', '是']:
                    return ""

    def get_request_delay_input(self) -> float:
        """获取请求延迟时间输入"""
        while True:
            try:
                delay_input = input("请求间隔时间（默认2.0秒，范围0.5-10.0）: ").strip()
                if not delay_input:
                    return 2.0  # 默认值
                delay = float(delay_input)
                if 0.5 <= delay <= 10.0:
                    return delay
                else:
                    print("❌ 请求间隔时间必须在0.5-10.0秒之间")
            except ValueError:
                print("❌ 请输入有效的数字")
