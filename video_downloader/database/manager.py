"""
数据库管理器 - 处理本地数据库操作
"""

import sqlite3
import json
import os
import threading
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
            conn.row_factory = sqlite3.Row  # 使查询结果可以通过列名访问
            
            # 启用WAL模式以提高并发性能
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA synchronous=NORMAL')
            conn.execute('PRAGMA temp_store=MEMORY')
            conn.execute('PRAGMA mmap_size=268435456')  # 256MB
            
            yield conn
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def add_video(self, video: VideoRecord) -> bool:
        """添加视频记录"""
        with self._lock:
            try:
                # 数据验证
                if not self._validate_video_record(video):
                    return False
                
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # 检查是否已存在
                    cursor.execute('SELECT id FROM videos WHERE id = ?', (video.id,))
                    if cursor.fetchone():
                        print(f"⚠️ 视频 {video.id} 已存在，跳过添加")
                        return False
                    
                    cursor.execute('''
                        INSERT INTO videos 
                        (id, title, url, description, cover, file_path, file_size, 
                         download_status, download_time, upload_time, cloud_path, 
                         created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        video.id, video.title, video.url, video.description, video.cover,
                        video.file_path, video.file_size, video.download_status.value,
                        video.download_time.isoformat() if video.download_time else None,
                        video.upload_time.isoformat() if video.upload_time else None,
                        video.cloud_path,
                        video.created_at.isoformat() if video.created_at else None,
                        video.updated_at.isoformat() if video.updated_at else None
                    ))
                    
                    # 记录操作历史
                    self._add_history_record(cursor, video.id, 'CREATE', 'SUCCESS')
                    
                    conn.commit()
                    return True
                    
            except sqlite3.Error as e:
                print(f"❌ 添加视频记录失败: {e}")
                return False
    
    def _validate_video_record(self, video: VideoRecord) -> bool:
        """验证视频记录数据"""
        if not video.id or not video.id.strip():
            print("❌ 视频ID不能为空")
            return False
        
        if not video.title or not video.title.strip():
            print("❌ 视频标题不能为空")
            return False
        
        if not video.url or not video.url.strip():
            print("❌ 视频URL不能为空")
            return False
        
        # 验证URL格式
        if not (video.url.startswith('http://') or video.url.startswith('https://')):
            print("❌ 视频URL格式无效")
            return False
        
        # 验证文件大小
        if video.file_size is not None and video.file_size < 0:
            print("❌ 文件大小不能为负数")
            return False
        
        return True
    
    def _add_history_record(self, cursor, video_id: str, action: str, status: str, error_message: str = None):
        """添加操作历史记录"""
        try:
            cursor.execute('''
                INSERT INTO download_history (video_id, action, status, error_message, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (video_id, action, status, error_message, datetime.now().isoformat()))
        except sqlite3.Error:
            # 历史记录失败不应该影响主操作
            pass
    
    def get_video(self, video_id: str) -> Optional[VideoRecord]:
        """获取视频记录"""
        with self._lock:
            try:
                if not video_id or not video_id.strip():
                    return None
                
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT * FROM videos WHERE id = ?', (video_id,))
                    row = cursor.fetchone()
                    if row:
                        return VideoRecord.from_dict(dict(row))
                    return None
                    
            except sqlite3.Error as e:
                print(f"❌ 获取视频记录失败: {e}")
                return None
    
    def update_video_status(self, video_id: str, status: DownloadStatus, 
                           file_path: str = None, file_size: int = None) -> bool:
        """更新视频下载状态"""
        with self._lock:
            try:
                if not video_id or not video_id.strip():
                    return False
                
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # 检查记录是否存在
                    cursor.execute('SELECT id FROM videos WHERE id = ?', (video_id,))
                    if not cursor.fetchone():
                        print(f"❌ 视频记录 {video_id} 不存在")
                        return False
                    
                    update_fields = ['download_status = ?', 'updated_at = ?']
                    values = [status.value, datetime.now().isoformat()]
                    
                    if file_path:
                        # 验证文件路径
                        if os.path.exists(file_path):
                            update_fields.append('file_path = ?')
                            values.append(file_path)
                        else:
                            print(f"⚠️ 文件路径不存在: {file_path}")
                    
                    if file_size is not None and file_size >= 0:
                        update_fields.append('file_size = ?')
                        values.append(file_size)
                    
                    if status == DownloadStatus.COMPLETED:
                        update_fields.append('download_time = ?')
                        values.append(datetime.now().isoformat())
                    
                    values.append(video_id)
                    
                    sql = f'UPDATE videos SET {", ".join(update_fields)} WHERE id = ?'
                    cursor.execute(sql, values)
                    
                    # 记录操作历史
                    self._add_history_record(cursor, video_id, 'UPDATE_STATUS', 'SUCCESS')
                    
                    conn.commit()
                    return cursor.rowcount > 0
                    
            except sqlite3.Error as e:
                print(f"❌ 更新视频状态失败: {e}")
                return False
    
    def update_upload_info(self, video_id: str, cloud_path: str) -> bool:
        """更新视频上传信息"""
        with self._lock:
            try:
                if not video_id or not video_id.strip():
                    return False
                
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE videos SET 
                        download_status = ?, cloud_path = ?, upload_time = ?, updated_at = ?
                        WHERE id = ?
                    ''', (
                        DownloadStatus.UPLOADED.value, cloud_path, 
                        datetime.now().isoformat(), datetime.now().isoformat(), video_id
                    ))
                    
                    # 记录操作历史
                    self._add_history_record(cursor, video_id, 'UPLOAD', 'SUCCESS')
                    
                    conn.commit()
                    return cursor.rowcount > 0
                    
            except sqlite3.Error as e:
                print(f"❌ 更新上传信息失败: {e}")
                return False
    
    def is_video_downloaded(self, video_id: str) -> bool:
        """检查视频是否已下载"""
        if not video_id or not video_id.strip():
            return False
        
        video = self.get_video(video_id)
        return video and video.download_status in [DownloadStatus.COMPLETED, DownloadStatus.UPLOADED]
    
    def get_videos_by_status(self, status: DownloadStatus, limit: int = None) -> List[VideoRecord]:
        """根据状态获取视频列表"""
        with self._lock:
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    sql = 'SELECT * FROM videos WHERE download_status = ? ORDER BY created_at DESC'
                    params = [status.value]
                    
                    if limit and limit > 0:
                        sql += ' LIMIT ?'
                        params.append(limit)
                    
                    cursor.execute(sql, params)
                    rows = cursor.fetchall()
                    return [VideoRecord.from_dict(dict(row)) for row in rows]
                    
            except sqlite3.Error as e:
                print(f"❌ 获取视频列表失败: {e}")
                return []
    
    def get_all_videos(self, limit: int = None, offset: int = 0) -> List[VideoRecord]:
        """获取所有视频记录"""
        with self._lock:
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    sql = 'SELECT * FROM videos ORDER BY created_at DESC'
                    params = []
                    
                    if limit and limit > 0:
                        sql += ' LIMIT ? OFFSET ?'
                        params.extend([limit, offset])
                    
                    cursor.execute(sql, params)
                    rows = cursor.fetchall()
                    return [VideoRecord.from_dict(dict(row)) for row in rows]
                    
            except sqlite3.Error as e:
                print(f"❌ 获取所有视频失败: {e}")
                return []
    
    def search_videos(self, keyword: str, limit: int = 50) -> List[VideoRecord]:
        """搜索视频"""
        with self._lock:
            try:
                if not keyword or not keyword.strip():
                    return []
                
                keyword = f"%{keyword.strip()}%"
                
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT * FROM videos 
                        WHERE title LIKE ? OR description LIKE ? 
                        ORDER BY created_at DESC 
                        LIMIT ?
                    ''', (keyword, keyword, limit))
                    
                    rows = cursor.fetchall()
                    return [VideoRecord.from_dict(dict(row)) for row in rows]
                    
            except sqlite3.Error as e:
                print(f"❌ 搜索视频失败: {e}")
                return []
    
    def get_statistics(self) -> Dict[str, int]:
        """获取下载统计信息"""
        with self._lock:
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    stats = {}
                    
                    # 使用视图获取统计信息
                    cursor.execute('SELECT * FROM video_summary')
                    summary_rows = cursor.fetchall()
                    
                    # 初始化所有状态的计数
                    for status in DownloadStatus:
                        stats[status.value] = 0
                    
                    # 更新实际计数
                    total_size = 0
                    total_count = 0
                    for row in summary_rows:
                        status = row['download_status']
                        count = row['count']
                        size = row['total_size']
                        
                        stats[status] = count
                        total_count += count
                        total_size += size
                    
                    stats['total'] = total_count
                    stats['total_size'] = total_size
                    
                    return stats
                    
            except sqlite3.Error as e:
                print(f"❌ 获取统计信息失败: {e}")
                return {}
    
    def cleanup_failed_downloads(self, days_old: int = 7) -> int:
        """清理失败的下载记录"""
        with self._lock:
            try:
                cutoff_date = datetime.now() - timedelta(days=days_old)
                
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        DELETE FROM videos 
                        WHERE download_status = ? AND datetime(created_at) < ?
                    ''', (DownloadStatus.FAILED.value, cutoff_date.isoformat()))
                    
                    deleted_count = cursor.rowcount
                    conn.commit()
                    return deleted_count
                    
            except sqlite3.Error as e:
                print(f"❌ 清理失败记录失败: {e}")
                return 0
    
    def backup_database(self, backup_path: str) -> bool:
        """备份数据库"""
        with self._lock:
            try:
                with self.get_connection() as conn:
                    backup = sqlite3.connect(backup_path)
                    conn.backup(backup)
                    backup.close()
                    return True
            except sqlite3.Error as e:
                print(f"❌ 数据库备份失败: {e}")
                return False
    
    def vacuum_database(self) -> bool:
        """压缩数据库"""
        with self._lock:
            try:
                with self.get_connection() as conn:
                    conn.execute('VACUUM')
                    return True
            except sqlite3.Error as e:
                print(f"❌ 数据库压缩失败: {e}")
                return False
