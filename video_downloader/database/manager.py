"""
数据库管理器 - 处理本地数据库操作
"""

import sqlite3
import json
import os
import threading
import glob
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from .models import VideoRecord


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = "video_downloader.db"):
        self.db_path = db_path
        self._lock = threading.RLock()  # 线程安全锁
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        with self._lock:
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # 启用外键约束
                    cursor.execute('PRAGMA foreign_keys = ON')
                    
                    # 创建视频表（按照新的字段设计）
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS videos (
                            title TEXT NOT NULL,
                            video_date TEXT NOT NULL,
                            cover TEXT,
                            url TEXT,
                            description TEXT,
                            download BOOLEAN DEFAULT 0,
                            is_primer BOOLEAN DEFAULT 0,
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL,
                            PRIMARY KEY (title, video_date),
                            CONSTRAINT valid_dates CHECK (
                                datetime(created_at) IS NOT NULL AND 
                                datetime(updated_at) IS NOT NULL
                            )
                        )
                    ''')
                    
                    # 创建下载历史表
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS download_history (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            title TEXT NOT NULL,
                            video_date TEXT NOT NULL,
                            action TEXT NOT NULL,
                            status TEXT NOT NULL,
                            error_message TEXT,
                            timestamp TEXT NOT NULL,
                            FOREIGN KEY (title, video_date) REFERENCES videos (title, video_date) ON DELETE CASCADE
                        )
                    ''')
                    
                    # 创建索引以提高查询性能
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_download ON videos(download)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_video_date ON videos(video_date)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_title ON videos(title)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_is_primer ON videos(is_primer)')

                    conn.commit()
                    
            except sqlite3.Error as e:
                print(f"❌ 数据库初始化失败: {e}")
                raise
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = None
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row
            yield conn
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def insert_or_update_video(self, video: VideoRecord) -> bool:
        """插入或更新视频记录"""
        with self._lock:
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()

                    # 检查记录是否存在
                    cursor.execute(
                        'SELECT title FROM videos WHERE title = ? AND video_date = ?',
                        (video.title, video.video_date)
                    )

                    if cursor.fetchone():
                        # 更新现有记录
                        cursor.execute('''
                            UPDATE videos SET
                                cover = ?,
                                url = ?,
                                description = ?,
                                is_primer = ?,
                                updated_at = ?
                            WHERE title = ? AND video_date = ?
                        ''', (
                            video.cover,
                            video.url,
                            video.description,
                            video.is_primer,
                            datetime.now().isoformat(),
                            video.title,
                            video.video_date
                        ))
                    else:
                        # 插入新记录
                        cursor.execute('''
                            INSERT INTO videos (
                                title, video_date, cover, url, description,
                                download, is_primer, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            video.title,
                            video.video_date,
                            video.cover,
                            video.url,
                            video.description,
                            video.download,
                            video.is_primer,
                            video.created_at.isoformat(),
                            video.updated_at.isoformat()
                        ))

                    conn.commit()
                    return True
                    
            except sqlite3.Error as e:
                print(f"❌ 插入/更新视频记录失败: {e}")
                return False
    
    def get_videos_by_date(self, video_date: str) -> List[VideoRecord]:
        """根据日期获取视频列表"""
        with self._lock:
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        'SELECT * FROM videos WHERE video_date = ? ORDER BY title',
                        (video_date,)
                    )

                    return [self._row_to_video_record(row) for row in cursor.fetchall()]

            except sqlite3.Error as e:
                print(f"❌ 获取视频列表失败: {e}")
                return []
    
    def get_videos_by_title(self, title: str) -> List[VideoRecord]:
        """根据标题获取视频列表"""
        with self._lock:
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        'SELECT * FROM videos WHERE title LIKE ? ORDER BY video_date',
                        (f'%{title}%',)
                    )

                    return [self._row_to_video_record(row) for row in cursor.fetchall()]

            except sqlite3.Error as e:
                print(f"❌ 获取视频列表失败: {e}")
                return []
    
    def get_undownloaded_videos(self, video_date: str = None) -> List[VideoRecord]:
        """获取未下载的视频列表"""
        with self._lock:
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()

                    if video_date:
                        cursor.execute(
                            'SELECT * FROM videos WHERE download = 0 AND video_date = ? ORDER BY title',
                            (video_date,)
                        )
                    else:
                        cursor.execute(
                            'SELECT * FROM videos WHERE download = 0 ORDER BY video_date, title'
                        )

                    return [self._row_to_video_record(row) for row in cursor.fetchall()]

            except sqlite3.Error as e:
                print(f"❌ 获取未下载视频列表失败: {e}")
                return []

    def update_download_status(self, title: str, video_date: str, download: bool) -> bool:
        """更新下载状态"""
        with self._lock:
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE videos SET
                            download = ?,
                            updated_at = ?
                        WHERE title = ? AND video_date = ?
                    ''', (
                        download,
                        datetime.now().isoformat(),
                        title,
                        video_date
                    ))

                    conn.commit()
                    return cursor.rowcount > 0

            except sqlite3.Error as e:
                print(f"❌ 更新下载状态失败: {e}")
                return False

    def get_all_videos(self) -> List[VideoRecord]:
        """获取所有视频记录"""
        with self._lock:
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT * FROM videos ORDER BY video_date DESC, title')

                    return [self._row_to_video_record(row) for row in cursor.fetchall()]

            except sqlite3.Error as e:
                print(f"❌ 获取所有视频记录失败: {e}")
                return []

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()

                    # 获取总数
                    cursor.execute('SELECT COUNT(*) FROM videos')
                    total = cursor.fetchone()[0]

                    # 获取已下载数
                    cursor.execute('SELECT COUNT(*) FROM videos WHERE download = 1')
                    downloaded = cursor.fetchone()[0]

                    # 获取未下载数
                    cursor.execute('SELECT COUNT(*) FROM videos WHERE download = 0')
                    pending = cursor.fetchone()[0]

                    # 获取付费视频数
                    cursor.execute('SELECT COUNT(*) FROM videos WHERE is_primer = 1')
                    primer = cursor.fetchone()[0]

                    return {
                        'total': total,
                        'downloaded': downloaded,
                        'pending': pending,
                        'primer': primer
                    }

            except sqlite3.Error as e:
                print(f"❌ 获取统计信息失败: {e}")
                return {}

    def sync_with_local_directory(self, download_dir: str) -> int:
        """同步本地目录与数据库状态"""
        if not os.path.exists(download_dir):
            print(f"⚠️ 下载目录不存在: {download_dir}")
            return 0

        updated_count = 0

        with self._lock:
            try:
                # 获取所有视频记录
                videos = self.get_all_videos()

                for video in videos:
                    # 构造可能的文件名模式
                    file_patterns = [
                        f"{video.title}*.mp4",
                        f"*{video.video_date}*.mp4",
                        f"{video.get_unique_key()}*.mp4"
                    ]

                    found = False
                    for pattern in file_patterns:
                        files = glob.glob(os.path.join(download_dir, pattern))
                        if files:
                            found = True
                            break

                    # 更新下载状态
                    if found != video.download:
                        if self.update_download_status(video.title, video.video_date, found):
                            updated_count += 1

                print(f"✅ 同步完成，更新了 {updated_count} 条记录")
                return updated_count

            except Exception as e:
                print(f"❌ 同步目录失败: {e}")
                return 0

    def _row_to_video_record(self, row) -> VideoRecord:
        """将数据库行转换为VideoRecord对象"""
        return VideoRecord(
            title=row['title'],
            video_date=row['video_date'],
            cover=row['cover'],
            url=row['url'],
            description=row['description'],
            download=bool(row['download']),
            is_primer=bool(row['is_primer']),
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
        )
