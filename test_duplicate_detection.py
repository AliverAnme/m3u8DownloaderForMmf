#!/usr/bin/env python3
"""
重复检测功能演示脚本
展示视频下载器如何检测和跳过已下载的视频
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from video_downloader.database.manager import DatabaseManager
from video_downloader.database.models import VideoRecord, DownloadStatus
from video_downloader.core.enhanced_app import EnhancedVideoDownloaderApp


def demo_duplicate_detection():
    """演示重复检测功能"""
    
    print("🎯 重复检测功能演示")
    print("=" * 50)
    
    # 创建数据库管理器
    db_manager = DatabaseManager("demo_video_downloader.db")
    
    # 模拟添加一些测试视频记录
    test_videos = [
        {
            'id': 'test_video_001',
            'title': '测试视频1 - 已下载',
            'url': 'https://example.com/test1.m3u8',
            'description': '这是一个测试视频',
            'cover': 'https://example.com/cover1.jpg'
        },
        {
            'id': 'test_video_002', 
            'title': '测试视频2 - 下载失败',
            'url': 'https://example.com/test2.m3u8',
            'description': '这是另一个测试视频',
            'cover': 'https://example.com/cover2.jpg'
        },
        {
            'id': 'test_video_003',
            'title': '测试视频3 - 新视频',
            'url': 'https://example.com/test3.m3u8', 
            'description': '这是新的测试视频',
            'cover': 'https://example.com/cover3.jpg'
        }
    ]
    
    print("\n📝 步骤1: 添加测试视频到数据库...")
    
    # 添加第一个视频为已完成状态
    video1 = VideoRecord(
        id=test_videos[0]['id'],
        title=test_videos[0]['title'],
        url=test_videos[0]['url'],
        description=test_videos[0]['description'],
        cover=test_videos[0]['cover'],
        download_status=DownloadStatus.PENDING
    )
    db_manager.add_video(video1)
    db_manager.update_video_status(
        test_videos[0]['id'], 
        DownloadStatus.COMPLETED,
        "downloads/test_video_001.mp4",
        1024*1024*100  # 100MB
    )
    
    # 添加第二个视频为失败状态
    video2 = VideoRecord(
        id=test_videos[1]['id'],
        title=test_videos[1]['title'],
        url=test_videos[1]['url'],
        description=test_videos[1]['description'],
        cover=test_videos[1]['cover'],
        download_status=DownloadStatus.FAILED
    )
    db_manager.add_video(video2)
    
    print("✅ 测试数据添加完成")
    
    print("\n🔍 步骤2: 检测重复下载...")
    
    # 模拟从API获取的新视频列表（包含已存在和新的视频）
    api_videos = test_videos  # 包含3个视频
    
    new_videos = []
    duplicate_videos = []
    failed_videos = []
    
    for video in api_videos:
        video_id = video['id']
        existing_video = db_manager.get_video(video_id)
        
        if existing_video:
            if existing_video.download_status == DownloadStatus.COMPLETED:
                duplicate_videos.append(video)
                print(f"⚠️  跳过已下载视频: {video['title']}")
            elif existing_video.download_status == DownloadStatus.UPLOADED:
                duplicate_videos.append(video)
                print(f"☁️  跳过已上传视频: {video['title']}")
            elif existing_video.download_status == DownloadStatus.FAILED:
                failed_videos.append(video)
                print(f"🔄 发现失败视频，可重新下载: {video['title']}")
            else:
                print(f"⏳ 视频正在处理中: {video['title']} (状态: {existing_video.download_status.value})")
        else:
            new_videos.append(video)
            print(f"🆕 发现新视频: {video['title']}")
    
    print(f"\n📊 检测结果:")
    print(f"   🆕 新视频: {len(new_videos)} 个")
    print(f"   ⚠️  重复视频: {len(duplicate_videos)} 个")
    print(f"   🔄 可重试视频: {len(failed_videos)} 个")
    
    print(f"\n💡 重复检测功能说明:")
    print(f"   ✅ 已完成的视频会被自动跳过")
    print(f"   ☁️  已上传的视频会被自动跳过") 
    print(f"   🔄 失败的视频可以选择重新下载")
    print(f"   🆕 新视频会被添加到下载队列")
    
    # 显示数据库统计
    stats = db_manager.get_statistics()
    print(f"\n📈 当前数据库统计:")
    for status_name, count in stats.items():
        if status_name != 'total_size':
            print(f"   {status_name}: {count}")
    
    print(f"\n🎉 演示完成！重复检测功能已正常工作。")
    
    # 清理演示数据库
    cleanup = input("\n是否清理演示数据库? (y/n): ").strip().lower()
    if cleanup == 'y':
        try:
            os.remove("demo_video_downloader.db")
            print("🧹 演示数据库已清理")
        except:
            pass


def show_actual_database_status():
    """显示实际数据库状态"""
    print("\n" + "="*60)
    print("📊 实际项目数据库状态")
    print("="*60)
    
    try:
        db_manager = DatabaseManager("video_downloader.db")
        stats = db_manager.get_statistics()
        
        if stats.get('total', 0) == 0:
            print("📝 数据库为空，尚未下载任何视频")
        else:
            print("当前数据库中的视频状态:")
            for status_name, count in stats.items():
                if status_name == 'total_size' and count > 0:
                    size_gb = count / (1024 * 1024 * 1024)
                    print(f"   💾 总大小: {size_gb:.2f} GB")
                elif status_name != 'total_size':
                    print(f"   {status_name}: {count}")
        
        # 显示最近的几个视频记录
        recent_videos = db_manager.get_all_videos(5)
        if recent_videos:
            print(f"\n📺 最近的 {len(recent_videos)} 个视频:")
            for i, video in enumerate(recent_videos, 1):
                status_emoji = {
                    DownloadStatus.PENDING: "⏳",
                    DownloadStatus.DOWNLOADING: "⬇️",
                    DownloadStatus.COMPLETED: "✅", 
                    DownloadStatus.FAILED: "❌",
                    DownloadStatus.UPLOADED: "☁️"
                }.get(video.download_status, "❓")
                
                print(f"   [{i}] {status_emoji} {video.title}")
                
    except Exception as e:
        print(f"❌ 无法访问数据库: {e}")


def main():
    """主函数"""
    print("🎬 视频下载器重复检测功能测试")
    print("选择要执行的操作:")
    print("1. 运行重复检测演示")
    print("2. 查看实际数据库状态")
    print("3. 启动主程序")
    
    choice = input("\n请选择 (1-3): ").strip()
    
    if choice == "1":
        demo_duplicate_detection()
    elif choice == "2":
        show_actual_database_status()
    elif choice == "3":
        print("🚀 启动主程序...")
        app = EnhancedVideoDownloaderApp(server_mode=False)
        app.run()
    else:
        print("❌ 无效选择")


if __name__ == "__main__":
    main()
