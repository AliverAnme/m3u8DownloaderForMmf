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

from .models import VideoRecord, DownloadStatus


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
                    
                    # 创建视频表
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS videos (
                            id TEXT PRIMARY KEY,
                            title TEXT NOT NULL,
                            url TEXT NOT NULL,
                            description TEXT,
                            cover TEXT,
                            file_path TEXT,
                            file_size INTEGER,
                            download_status TEXT DEFAULT 'pending' CHECK (download_status IN ('pending', 'downloading', 'completed', 'failed', 'uploaded')),
                            download_time TEXT,
                            upload_time TEXT,
                            cloud_path TEXT,
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL,
                            CONSTRAINT valid_file_size CHECK (file_size IS NULL OR file_size >= 0),
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
                            video_id TEXT NOT NULL,
                            action TEXT NOT NULL,
                            status TEXT NOT NULL,
                            error_message TEXT,
                            timestamp TEXT NOT NULL,
                            FOREIGN KEY (video_id) REFERENCES videos (id) ON DELETE CASCADE
                        )
                    ''')
                    
                    # 创建索引以提高查询性能
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_download_status ON videos(download_status)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON videos(created_at)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_video_id_history ON download_history(video_id)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp_history ON download_history(timestamp)')
                    
                    # 创建视图以便于查询
                    cursor.execute('''
                        CREATE VIEW IF NOT EXISTS video_summary AS
                        SELECT 
                            download_status,
                            COUNT(*) as count,
                            COALESCE(SUM(file_size), 0) as total_size
                        FROM videos 
                        GROUP BY download_status
                    ''')
                    
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
                timeout=30.0,  # 30秒超时
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row  # 使查询结果可以按列名访问
            yield conn
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def add_video(self, video: VideoRecord) -> bool:
        """添加视频记录"""
        with self._lock:
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    now = datetime.now().isoformat()

                    cursor.execute('''
                        INSERT OR REPLACE INTO videos 
                        (id, title, url, description, cover, download_status, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        video.id, video.title, video.url, video.description,
                        video.cover, video.download_status.value, now, now
                    ))

                    conn.commit()
                    return True
                    
            except sqlite3.Error as e:
                print(f"❌ 添加视频记录失败: {e}")
                return False
    
    def get_video(self, video_id: str) -> Optional[VideoRecord]:
        """获取指定视频记录"""
        with self._lock:
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT * FROM videos WHERE id = ?', (video_id,))
                    row = cursor.fetchone()

                    if row:
                        return self._row_to_video_record(row)
                    return None
                    
            except sqlite3.Error as e:
                print(f"❌ 获取视频记录失败: {e}")
                return None
    
    def get_all_videos(self, limit: int = None) -> List[VideoRecord]:
        """获取所有视频记录"""
        with self._lock:
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    if limit:
                        cursor.execute('SELECT * FROM videos ORDER BY created_at DESC LIMIT ?', (limit,))
                    else:
                        cursor.execute('SELECT * FROM videos ORDER BY created_at DESC')

                    rows = cursor.fetchall()
                    return [self._row_to_video_record(row) for row in rows]

            except sqlite3.Error as e:
                print(f"❌ 获取视频列表失败: {e}")
                return []
    
    def get_videos_by_status(self, status: DownloadStatus) -> List[VideoRecord]:
        """根据状态获取视频记录"""
        with self._lock:
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        'SELECT * FROM videos WHERE download_status = ? ORDER BY created_at DESC',
                        (status.value,)
                    )
                    rows = cursor.fetchall()
                    return [self._row_to_video_record(row) for row in rows]

            except sqlite3.Error as e:
                print(f"❌ 根据状态获取视频失败: {e}")
                return []
    
    def get_videos_missing_files(self) -> List[VideoRecord]:
        """获取文件缺失的视频（数据库中存在但本地文件不存在）"""
        with self._lock:
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT * FROM videos 
                        WHERE download_status = 'completed' 
                        AND (file_path IS NULL OR file_path = '')
                        OR download_status = 'pending'
                        ORDER BY created_at DESC
                    ''')

                    rows = cursor.fetchall()
                    missing_videos = []

                    for row in rows:
                        video = self._row_to_video_record(row)
                        # 检查文件是否真的不存在
                        if not video.file_path or not os.path.exists(video.file_path):
                            missing_videos.append(video)

                    return missing_videos

            except sqlite3.Error as e:
                print(f"❌ 获取缺失文件的视频失败: {e}")
                return []

    def sync_database_with_local_files(self, download_dir: str) -> Dict[str, int]:
        """同步数据库与本地文件状态"""
        if not os.path.exists(download_dir):
            return {
                'updated_to_completed': 0,
                'updated_to_missing': 0,
                'created_from_files': 0,
                'files_matched': 0
            }

        with self._lock:
            try:
                stats = {
                    'updated_to_completed': 0,
                    'updated_to_missing': 0,
                    'created_from_files': 0,
                    'files_matched': 0
                }

                # 获取所有视频记录
                all_videos = self.get_all_videos()

                # 获取下载目录中的所有视频文件
                video_extensions = ['*.mp4', '*.mkv', '*.avi', '*.mov', '*.wmv', '*.flv']
                local_files = []

                for ext in video_extensions:
                    pattern = os.path.join(download_dir, '**', ext)
                    local_files.extend(glob.glob(pattern, recursive=True))

                # 为数据库中的视频检查本地文件
                for video in all_videos:
                    found_file = None

                    # 首先检查数据库中记录的文件路径
                    if video.file_path and os.path.exists(video.file_path):
                        found_file = video.file_path
                    else:
                        # 通过标题和ID匹配文件
                        found_file = self._find_matching_file(video, local_files)

                    if found_file:
                        # 文件存在，更新为已完成状态
                        if video.download_status != DownloadStatus.COMPLETED:
                            file_size = os.path.getsize(found_file)
                            self.update_video_status(
                                video.id,
                                DownloadStatus.COMPLETED,
                                found_file,
                                file_size
                            )
                            stats['updated_to_completed'] += 1
                        stats['files_matched'] += 1
                    else:
                        # 文件不存在，重置为待下载状态
                        if video.download_status == DownloadStatus.COMPLETED:
                            self.update_video_status(video.id, DownloadStatus.PENDING)
                            stats['updated_to_missing'] += 1

                # 为本地文件创建数据库记录（如果不存在）
                existing_files = {v.file_path for v in all_videos if v.file_path}
                for file_path in local_files:
                    if file_path not in existing_files:
                        # 从文件名提取信息
                        filename = os.path.basename(file_path)
                        title = os.path.splitext(filename)[0]

                        # 创建新的视频记录
                        video_id = self._generate_id_from_filename(filename)
                        new_video = VideoRecord(
                            id=video_id,
                            title=title,
                            url='',  # 本地文件没有URL
                            description='从本地文件同步',
                            cover='',
                            download_status=DownloadStatus.COMPLETED
                        )

                        if self.add_video(new_video):
                            file_size = os.path.getsize(file_path)
                            self.update_video_status(
                                video_id,
                                DownloadStatus.COMPLETED,
                                file_path,
                                file_size
                            )
                            stats['created_from_files'] += 1

                return stats

            except Exception as e:
                print(f"❌ 同步数据库与本地文件失败: {e}")
                return {
                    'updated_to_completed': 0,
                    'updated_to_missing': 0,
                    'created_from_files': 0,
                    'files_matched': 0
                }

    def _find_matching_file(self, video: VideoRecord, local_files: List[str]) -> Optional[str]:
        """为视频记录找到匹配的本地文件"""
        # 清理标题和ID用于匹配
        safe_title = re.sub(r'[^\w\s-]', '', video.title)[:50] if video.title else ''
        safe_id = re.sub(r'[^\w-]', '', video.id)[:20] if video.id else ''

        for file_path in local_files:
            filename = os.path.basename(file_path).lower()

            # 按标题匹配
            if safe_title and safe_title.lower() in filename:
                return file_path

            # 按ID匹配
            if safe_id and safe_id.lower() in filename:
                return file_path

        return None

    def _generate_id_from_filename(self, filename: str) -> str:
        """从文件名生成视频ID"""
        import hashlib
        # 使用文件名的MD5哈希作为ID
        return hashlib.md5(filename.encode()).hexdigest()[:16]

    def update_video_status(self, video_id: str, status: DownloadStatus,
                           file_path: str = None, file_size: int = None) -> bool:
        """更新视频状态"""
        with self._lock:
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    now = datetime.now().isoformat()

                    if status == DownloadStatus.COMPLETED and file_path:
                        cursor.execute('''
                            UPDATE videos 
                            SET download_status = ?, file_path = ?, file_size = ?, 
                                download_time = ?, updated_at = ?
                            WHERE id = ?
                        ''', (status.value, file_path, file_size, now, now, video_id))
                    else:
                        cursor.execute('''
                            UPDATE videos 
                            SET download_status = ?, updated_at = ?
                            WHERE id = ?
                        ''', (status.value, now, video_id))

                    conn.commit()
                    return cursor.rowcount > 0

            except sqlite3.Error as e:
                print(f"❌ 更新视频状态失败: {e}")
                return False

    def update_upload_info(self, video_id: str, cloud_path: str) -> bool:
        """更新上传信息"""
        with self._lock:
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    now = datetime.now().isoformat()

                    cursor.execute('''
                        UPDATE videos 
                        SET download_status = ?, cloud_path = ?, upload_time = ?, updated_at = ?
                        WHERE id = ?
                    ''', (DownloadStatus.UPLOADED.value, cloud_path, now, now, video_id))

                    conn.commit()
                    return cursor.rowcount > 0

            except sqlite3.Error as e:
                print(f"❌ 更新上传信息失败: {e}")
                return False

    def cleanup_failed_downloads(self, days_ago: int = 7) -> int:
        """清理失败的下载记录"""
        with self._lock:
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cutoff_date = (datetime.now() - timedelta(days=days_ago)).isoformat()

                    cursor.execute('''
                        DELETE FROM videos 
                        WHERE download_status = 'failed' AND updated_at < ?
                    ''', (cutoff_date,))

                    conn.commit()
                    return cursor.rowcount

            except sqlite3.Error as e:
                print(f"❌ 清理失败记录失败: {e}")
                return 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()

                    # 获取各状态的统计
                    cursor.execute('SELECT download_status, COUNT(*), COALESCE(SUM(file_size), 0) FROM videos GROUP BY download_status')
                    status_stats = cursor.fetchall()

                    # 获取总数
                    cursor.execute('SELECT COUNT(*), COALESCE(SUM(file_size), 0) FROM videos')
                    total_count, total_size = cursor.fetchone()

                    stats = {
                        'total': total_count or 0,
                        'total_size': total_size or 0,
                        'pending': 0,
                        'downloading': 0,
                        'completed': 0,
                        'failed': 0,
                        'uploaded': 0
                    }

                    for status, count, size in status_stats:
                        if status in stats:
                            stats[status] = count
                            stats[f'{status}_size'] = size

                    return stats

            except sqlite3.Error as e:
                print(f"❌ 获取统计信息失败: {e}")
                return {}

    def _row_to_video_record(self, row: sqlite3.Row) -> VideoRecord:
        """将数据库行转换为VideoRecord对象"""
        return VideoRecord(
            id=row['id'],
            title=row['title'],
            url=row['url'],
            description=row['description'],
            cover=row['cover'],
            file_path=row['file_path'],
            file_size=row['file_size'],
            download_status=DownloadStatus(row['download_status']),
            download_time=row['download_time'],
            upload_time=row['upload_time'],
            cloud_path=row['cloud_path'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

    def add_download_history(self, video_id: str, action: str, status: str, error_message: str = None):
        """添加下载历史记录"""
        with self._lock:
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    now = datetime.now().isoformat()

                    cursor.execute('''
                        INSERT INTO download_history 
                        (video_id, action, status, error_message, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (video_id, action, status, error_message, now))

                    conn.commit()

            except sqlite3.Error as e:
                print(f"❌ 添加下载历史失败: {e}")

    def close(self):
        """关闭数据库连接"""
        # 由于使用了上下文管理器，这里不需要特别的清理操作
        pass
