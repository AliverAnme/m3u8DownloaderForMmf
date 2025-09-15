"""
下载管理器模块
处理视频下载、ffmpeg合并和封面嵌入
"""

import os
import subprocess
import tempfile
import time
import re
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import m3u8

from ..core.config import Config
from ..database.models import VideoRecord


class DownloadManager:

    def __init__(self):
        self.config = Config()
        self.temp_dir = tempfile.mkdtemp(prefix="video_download_")

    def sanitize_filename(self, filename: str) -> str:
        """
        清理文件名，去除不合法字符和标签

        Args:
            filename (str): 原始文件名

        Returns:
            str: 清理后的安全文件名
        """
        if not filename:
            return "unnamed"

        # 去除换行符和回车符
        filename = filename.replace('\n', '').replace('\r', '')

        # 去除多余的空白符（包括制表符等）
        filename = re.sub(r'\s+', ' ', filename)

        # 去除所有#标签（包括#逆愛等）
        filename = re.sub(r'#[^\s]*', '', filename)

        # 去除Windows文件名不允许的字符
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)

        # 去除首尾空白和点号
        filename = filename.strip().strip('.')

        # 去除连续的空格
        filename = re.sub(r'\s{2,}', ' ', filename)

        # 如果清理后为空，使用默认名称
        if not filename:
            return "unnamed"

        # 限制长度，避免文件名过长
        if len(filename) > 100:
            filename = filename[:100]

        return filename

    def check_ffmpeg(self) -> bool:
        """检查ffmpeg是否可用"""
        try:
            result = subprocess.run(['ffmpeg', '-version'],
                                    capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def download_cover_image(self, cover_url: str, temp_dir: str) -> Optional[str]:
        """下载封面图片到临时目录"""
        if not cover_url:
            return None

        try:
            print(f"📸 正在下载封面图片...")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(cover_url, headers=headers, timeout=30)
            response.raise_for_status()

            # 获取文件扩展名
            ext = '.jpg'
            if 'content-type' in response.headers:
                content_type = response.headers['content-type']
                if 'png' in content_type:
                    ext = '.png'
                elif 'webp' in content_type:
                    ext = '.webp'

            cover_path = os.path.join(temp_dir, f"cover{ext}")
            with open(cover_path, 'wb') as f:
                f.write(response.content)

            print(f"✅ 封面图片下载完成: {cover_path}")
            return cover_path

        except Exception as e:
            print(f"❌ 下载封面图片失败: {e}")
            return None

    def download_m3u8_streams(self, url: str, temp_dir: str) -> Tuple[Optional[str], Optional[str]]:
        """下载m3u8视频流和音频流"""
        if not url:
            print("⚠️ URL为空，跳过下载")
            return None, None

        try:
            print(f"🎬 正在解析m3u8流: {url}")

            # 解析m3u8
            playlist = self.parse_m3u8(url)
            if not playlist:
                return None, None

            # 下载视频和音频流
            video_path = self.download_stream(playlist, temp_dir, "video")
            audio_path = self.download_stream(playlist, temp_dir, "audio")

            return video_path, audio_path

        except Exception as e:
            print(f"❌ 下载m3u8流失败: {e}")
            return None, None

    def parse_m3u8(self, url: str) -> Optional[Any]:
        """解析m3u8文件"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, verify=False, timeout=30)
            response.raise_for_status()

            playlist = m3u8.loads(response.text)
            playlist.base_uri = url.rsplit('/', 1)[0] + '/'

            return playlist

        except Exception as e:
            print(f"❌ 解析M3U8文件失败: {e}")
            return None

    def download_stream(self, playlist, temp_dir: str, stream_type: str) -> Optional[str]:
        """下载视频或音频流"""
        try:
            output_file = os.path.join(temp_dir, f"{stream_type}.ts")

            # 使用ffmpeg下载m3u8流
            cmd = [
                'ffmpeg',
                '-i', playlist.base_uri if hasattr(playlist, 'base_uri') else str(playlist),
                '-c', 'copy',
                '-y',  # 覆盖现有文件
                output_file
            ]

            print(f"📥 正在下载{stream_type}流...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0 and os.path.exists(output_file):
                print(f"✅ {stream_type}流下载完成")
                return output_file
            else:
                print(f"❌ {stream_type}流下载失败: {result.stderr}")
                return None

        except Exception as e:
            print(f"❌ 下载{stream_type}流异常: {e}")
            return None

    def merge_video_with_cover(self, video_path: str, audio_path: str, cover_path: str, output_path: str) -> bool:
        """使用ffmpeg合并音视频并嵌入封面"""
        try:
            print(f"🔧 正在合并音视频并嵌入封面...")

            # 构建ffmpeg命令
            cmd = ['ffmpeg', '-y']  # -y 覆盖现有文件

            # 添加输入文件
            if video_path:
                cmd.extend(['-i', video_path])
            if audio_path:
                cmd.extend(['-i', audio_path])
            if cover_path:
                cmd.extend(['-i', cover_path])

            # 设置映射和编码参数
            if video_path and audio_path and cover_path:
                # 视频 + 音频 + 封面
                cmd.extend([
                    '-map', '0:v',  # 视频流
                    '-map', '1:a',  # 音频流
                    '-map', '2:v',  # 封面图片
                    '-c:v', 'libx264',  # 视频编码
                    '-c:a', 'aac',      # 音频编码
                    '-disposition:v:1', 'attached_pic',  # 将封面设为附加图片
                ])
            elif video_path and cover_path:
                # 仅视频 + 封面
                cmd.extend([
                    '-map', '0:v',
                    '-map', '1:v',
                    '-c:v', 'libx264',
                    '-disposition:v:1', 'attached_pic',
                ])
            elif video_path and audio_path:
                # 仅视频 + 音频
                cmd.extend([
                    '-map', '0:v',
                    '-map', '1:a',
                    '-c:v', 'libx264',
                    '-c:a', 'aac',
                ])
            else:
                print("❌ 没有足够的输入文件进行合并")
                return False

            # 添加输出文件
            cmd.append(output_path)

            print(f"🎯 执行命令: {' '.join(cmd)}")

            # 执行命令
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            if result.returncode == 0 and os.path.exists(output_path):
                print(f"✅ 视频合并完成: {output_path}")
                return True
            else:
                print(f"❌ 视频合并失败:")
                print(f"stdout: {result.stdout}")
                print(f"stderr: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ 视频合并异常: {e}")
            return False

    def download_video(self, video: VideoRecord, download_dir: str) -> bool:
        """下载单个视频"""
        if not video.url:
            print(f"⚠️ 跳过付费视频: {video.title}")
            return False

        try:
            print(f"\n🎬 开始下载: {video.title} ({video.video_date})")

            # 清理标题作为安全的文件名
            safe_title = self.sanitize_filename(video.title)
            safe_date = self.sanitize_filename(video.video_date)

            # 创建视频专用目录
            video_dir = os.path.join(download_dir, f"{safe_title}_{safe_date}")
            os.makedirs(video_dir, exist_ok=True)

            # 创建临时目录
            temp_dir = tempfile.mkdtemp(prefix=f"download_{safe_date}_")

            try:
                # 1. 下载封面图片
                cover_path = self.download_cover_image(video.cover, temp_dir)

                # 2. 下载m3u8视频流和音频流
                video_path, audio_path = self.download_m3u8_streams(video.url, temp_dir)

                if not video_path and not audio_path:
                    print(f"❌ 无法下载任何媒体流")
                    return False

                # 3. 合并音视频并嵌入封面
                output_filename = f"{safe_title}_{safe_date}.mp4"
                output_path = os.path.join(video_dir, output_filename)

                success = self.merge_video_with_cover(
                    video_path, audio_path, cover_path, output_path
                )

                if success:
                    print(f"🎉 下载完成: {output_path}")
                    return True
                else:
                    print(f"❌ 视频处理失败")
                    return False

            finally:
                # 清理临时文件
                try:
                    shutil.rmtree(temp_dir)
                    print(f"🧹 临时文件已清理")
                except:
                    pass

        except Exception as e:
            print(f"❌ 下载视频失败: {e}")
            return False

    def download_videos_by_date(self, videos: List[VideoRecord], download_dir: str, force: bool = False) -> Dict[str, int]:
        """按日期下载视频"""
        stats = {'success': 0, 'failed': 0, 'skipped': 0}

        print(f"\n📁 开始批量下载，目标目录: {download_dir}")
        print(f"🎯 待下载视频数量: {len(videos)}")

        for i, video in enumerate(videos, 1):
            print(f"\n📺 [{i}/{len(videos)}] 处理: {video.title}")

            # 检查是否需要跳过
            if not force and video.download:
                print(f"⏭️ 已下载，跳过")
                stats['skipped'] += 1
                continue

            # 下载视频
            if self.download_video(video, download_dir):
                stats['success'] += 1
            else:
                stats['failed'] += 1

        print(f"\n📊 下载统计:")
        print(f"✅ 成功: {stats['success']}")
        print(f"❌ 失败: {stats['failed']}")
        print(f"⏭️ 跳过: {stats['skipped']}")

        return stats

    def cleanup_temp_files(self):
        """清理临时文件"""
        try:
            if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                print("🧹 临时目录已清理")
        except Exception as e:
            print(f"⚠️ 清理临时目录失败: {e}")

    def __del__(self):
        """析构函数，清理临时文件"""
        self.cleanup_temp_files()
