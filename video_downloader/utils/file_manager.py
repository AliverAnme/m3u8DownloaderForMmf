"""
视频文件管理器 - 处理视频文件的分类和组织
"""

import os
import re
import shutil
from typing import Dict

from ..database.manager import DatabaseManager


class VideoFileManager:
    """视频文件管理器"""

    def __init__(self, db_manager: DatabaseManager, base_download_dir: str):
        self.db_manager = db_manager
        self.base_download_dir = base_download_dir

    def organize_videos_by_series(self, series_pattern: str = r'(\d+)',
                                 create_folders: bool = True) -> Dict[str, any]:
        """根据序号将视频分类到相应文件夹"""
        try:
            # 获取按序号分组的视频
            series_groups = self.db_manager.get_videos_by_series_number(series_pattern)

            results = {
                'organized_count': 0,
                'failed_count': 0,
                'created_folders': [],
                'moved_files': [],
                'errors': []
            }

            for series_number, videos in series_groups.items():
                # 创建序号文件夹
                if series_number == '其他':
                    folder_name = '其他视频'
                else:
                    folder_name = f"系列_{series_number.zfill(3)}"  # 补零便于排序

                series_folder = os.path.join(self.base_download_dir, folder_name)

                if create_folders and not os.path.exists(series_folder):
                    try:
                        os.makedirs(series_folder, exist_ok=True)
                        results['created_folders'].append(series_folder)
                    except Exception as e:
                        results['errors'].append(f"创建文件夹失败 {series_folder}: {e}")
                        continue

                # 移动视频文件
                for video in videos:
                    if video.file_path and os.path.exists(video.file_path):
                        try:
                            filename = os.path.basename(video.file_path)
                            new_path = os.path.join(series_folder, filename)

                            # 如果文件已经在正确位置，跳过
                            if os.path.abspath(video.file_path) == os.path.abspath(new_path):
                                continue

                            # 处理文件名冲突
                            if os.path.exists(new_path):
                                base, ext = os.path.splitext(filename)
                                counter = 1
                                while os.path.exists(new_path):
                                    new_filename = f"{base}_{counter}{ext}"
                                    new_path = os.path.join(series_folder, new_filename)
                                    counter += 1

                            # 移动文件
                            shutil.move(video.file_path, new_path)

                            # 更新数据库中的文件路径
                            if self.db_manager.update_video_file_path_and_folder(video.id, new_path):
                                results['moved_files'].append({
                                    'video_id': video.id,
                                    'title': video.title,
                                    'old_path': video.file_path,
                                    'new_path': new_path,
                                    'series': series_number
                                })
                                results['organized_count'] += 1
                            else:
                                results['errors'].append(f"更新数据库失败: {video.title}")
                                # 如果数据库更新失败，将文件移回原位置
                                try:
                                    shutil.move(new_path, video.file_path)
                                except:
                                    pass
                                results['failed_count'] += 1

                        except Exception as e:
                            results['errors'].append(f"移动文件失败 {video.title}: {e}")
                            results['failed_count'] += 1

            return results

        except Exception as e:
            return {
                'organized_count': 0,
                'failed_count': 0,
                'created_folders': [],
                'moved_files': [],
                'errors': [f"组织视频失败: {e}"]
            }

    def create_series_structure(self, pattern_config: Dict[str, str] = None) -> Dict[str, any]:
        """根据配置创建系列文件夹结构"""
        if pattern_config is None:
            # 默认模式配置
            pattern_config = {
                r'0704': '0704系列',
                r'0709': '0709系列',
                r'0710': '0710系列',
                r'0713': '0713系列',
                r'0714': '0714系列',
                r'郭姜\d+': '郭姜系列',
                r'池.*畏': '池畏系列',
                r'加更': '加更内容'
            }

        try:
            all_videos = self.db_manager.get_all_videos()

            results = {
                'organized_count': 0,
                'created_folders': [],
                'moved_files': [],
                'unmatched_videos': [],
                'errors': []
            }

            # 为每个模式创建文件夹
            pattern_folders = {}
            for pattern, folder_name in pattern_config.items():
                folder_path = os.path.join(self.base_download_dir, folder_name)
                pattern_folders[pattern] = folder_path

                if not os.path.exists(folder_path):
                    try:
                        os.makedirs(folder_path, exist_ok=True)
                        results['created_folders'].append(folder_path)
                    except Exception as e:
                        results['errors'].append(f"创建文件夹失败 {folder_path}: {e}")

            # 分类视频
            for video in all_videos:
                if not video.file_path or not os.path.exists(video.file_path):
                    continue

                matched = False
                for pattern, folder_path in pattern_folders.items():
                    if re.search(pattern, video.title, re.IGNORECASE):
                        try:
                            filename = os.path.basename(video.file_path)
                            new_path = os.path.join(folder_path, filename)

                            # 如果已在正确位置，跳过
                            if os.path.abspath(video.file_path) == os.path.abspath(new_path):
                                matched = True
                                break

                            # 处理文件名冲突
                            if os.path.exists(new_path):
                                base, ext = os.path.splitext(filename)
                                counter = 1
                                while os.path.exists(new_path):
                                    new_filename = f"{base}_{counter}{ext}"
                                    new_path = os.path.join(folder_path, new_filename)
                                    counter += 1

                            # 移动文件
                            shutil.move(video.file_path, new_path)

                            # 更新数据库
                            if self.db_manager.update_video_file_path_and_folder(video.id, new_path):
                                results['moved_files'].append({
                                    'video_id': video.id,
                                    'title': video.title,
                                    'old_path': video.file_path,
                                    'new_path': new_path,
                                    'pattern': pattern
                                })
                                results['organized_count'] += 1
                                matched = True
                                break
                            else:
                                # 数据库更新失败，恢复文件
                                try:
                                    shutil.move(new_path, video.file_path)
                                except:
                                    pass
                                results['errors'].append(f"数据库更新失败: {video.title}")

                        except Exception as e:
                            results['errors'].append(f"移动文件失败 {video.title}: {e}")
                            break

                if not matched:
                    results['unmatched_videos'].append({
                        'video_id': video.id,
                        'title': video.title,
                        'file_path': video.file_path
                    })

            return results

        except Exception as e:
            return {
                'organized_count': 0,
                'created_folders': [],
                'moved_files': [],
                'unmatched_videos': [],
                'errors': [f"创建系列结构失败: {e}"]
            }

    def get_folder_statistics(self) -> Dict[str, any]:
        """获取文件夹统计信息"""
        try:
            stats = {
                'total_folders': 0,
                'total_files': 0,
                'folder_details': {},
                'total_size': 0
            }

            if not os.path.exists(self.base_download_dir):
                return stats

            for item in os.listdir(self.base_download_dir):
                item_path = os.path.join(self.base_download_dir, item)

                if os.path.isdir(item_path):
                    stats['total_folders'] += 1

                    # 统计文件夹内容
                    folder_stats = {
                        'file_count': 0,
                        'total_size': 0,
                        'video_files': []
                    }

                    for file_item in os.listdir(item_path):
                        file_path = os.path.join(item_path, file_item)
                        if os.path.isfile(file_path):
                            file_size = os.path.getsize(file_path)
                            if any(file_item.lower().endswith(ext) for ext in ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv']):
                                folder_stats['file_count'] += 1
                                folder_stats['total_size'] += file_size
                                folder_stats['video_files'].append({
                                    'name': file_item,
                                    'size': file_size,
                                    'size_mb': file_size / (1024 * 1024)
                                })

                    stats['folder_details'][item] = folder_stats
                    stats['total_files'] += folder_stats['file_count']
                    stats['total_size'] += folder_stats['total_size']

                elif os.path.isfile(item_path):
                    # 根目录下的文件
                    if any(item.lower().endswith(ext) for ext in ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv']):
                        file_size = os.path.getsize(item_path)
                        stats['total_files'] += 1
                        stats['total_size'] += file_size

                        if '根目录' not in stats['folder_details']:
                            stats['folder_details']['根目录'] = {
                                'file_count': 0,
                                'total_size': 0,
                                'video_files': []
                            }

                        stats['folder_details']['根目录']['file_count'] += 1
                        stats['folder_details']['根目录']['total_size'] += file_size
                        stats['folder_details']['根目录']['video_files'].append({
                            'name': item,
                            'size': file_size,
                            'size_mb': file_size / (1024 * 1024)
                        })

            return stats

        except Exception as e:
            return {
                'total_folders': 0,
                'total_files': 0,
                'folder_details': {},
                'total_size': 0,
                'error': str(e)
            }

    def cleanup_empty_folders(self) -> Dict[str, any]:
        """清理空文件夹"""
        try:
            results = {
                'removed_folders': [],
                'kept_folders': [],
                'errors': []
            }

            if not os.path.exists(self.base_download_dir):
                return results

            for item in os.listdir(self.base_download_dir):
                item_path = os.path.join(self.base_download_dir, item)

                if os.path.isdir(item_path):
                    try:
                        # 检查文件夹是否为空
                        if not os.listdir(item_path):
                            os.rmdir(item_path)
                            results['removed_folders'].append(item)
                        else:
                            results['kept_folders'].append(item)
                    except Exception as e:
                        results['errors'].append(f"处理文件夹 {item} 失败: {e}")

            return results

        except Exception as e:
            return {
                'removed_folders': [],
                'kept_folders': [],
                'errors': [f"清理空文件夹失败: {e}"]
            }
