#!/usr/bin/env python3
"""
增强版视频下载器主入口
支持服务器模式部署和定时运行
"""

import sys
import os
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from video_downloader.core.enhanced_app import EnhancedVideoDownloaderApp
from video_downloader.core.config import Config


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="增强版视频下载器 - 支持定时运行、数据库管理和网盘推送"
    )

    parser.add_argument(
        '--server',
        action='store_true',
        help='运行在服务器模式（无交互界面，支持定时任务）'
    )

    parser.add_argument(
        '--daemon',
        action='store_true',
        help='以守护进程模式运行（仅限Linux/Unix）'
    )

    parser.add_argument(
        '--config',
        default='video_downloader.db',
        help='指定数据库文件路径（默认: video_downloader.db）'
    )

    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='设置日志级别（默认: INFO）'
    )

    parser.add_argument(
        '--interval',
        type=int,
        default=120,
        help='设置获取新视频的间隔时间（分钟，默认: 120）'
    )

    return parser.parse_args()


def setup_daemon():
    """设置守护进程（仅限Unix系统）"""
    try:
        import daemon
        import lockfile

        # 创建daemon上下文
        context = daemon.DaemonContext(
            pidfile=lockfile.FileLock('/var/run/video_downloader.pid'),
            working_directory='.',
            umask=0o002,
        )

        return context
    except ImportError:
        print("❌ 守护进程模式需要安装python-daemon包: pip install python-daemon")
        sys.exit(1)


def main():
    """主函数"""
    args = parse_arguments()

    try:
        # 更新配置
        if hasattr(Config, 'DATABASE_FILE'):
            Config.DATABASE_FILE = args.config
        if hasattr(Config, 'LOG_LEVEL'):
            Config.LOG_LEVEL = args.log_level
        if hasattr(Config, 'SCHEDULER_CONFIG'):
            Config.SCHEDULER_CONFIG['fetch_interval_minutes'] = args.interval

        # 创建应用实例
        app = EnhancedVideoDownloaderApp(server_mode=args.server)

        if args.daemon and os.name != 'nt':  # 非Windows系统
            print("🚀 启动守护进程模式...")
            context = setup_daemon()
            with context:
                app.run()
        else:
            if args.server:
                print("🚀 启动服务器模式...")
                print(f"📊 数据库文件: {args.config}")
                print(f"📝 日志级别: {args.log_level}")
                print(f"⏰ 获取间隔: {args.interval} 分钟")
                print("按 Ctrl+C 停止服务")
            else:
                print("🎬 启动交互模式...")

            app.run()

    except KeyboardInterrupt:
        print("\n\n👋 用户中断程序，正在安全退出...")
    except Exception as e:
        print(f"❌ 程序运行时发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
