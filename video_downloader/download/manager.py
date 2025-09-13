"""
下载管理器模块
处理m3u8视频下载、转换和相关工具检查
"""

import os
import subprocess
import tempfile
import time
import re
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import m3u8

from ..core.config import Config


class DownloadManager:
    """下载管理器类"""

    def __init__(self):
        self.config = Config()

    def check_ffmpeg(self) -> bool:
        """检查FFmpeg是否可用"""
        try:
            result = subprocess.run(['ffmpeg', '-version'],
                                    capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

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

            print(f"解析结果：")
            print(f"  - 主播放列表数量: {len(playlist.playlists) if playlist.playlists else 0}")
            print(f"  - 媒体流数量: {len(playlist.media) if playlist.media else 0}")
            print(f"  - 片段数量: {len(playlist.segments) if playlist.segments else 0}")

            if playlist.media:
                for media in playlist.media:
                    print(f"  - 媒体类型: {media.type}, URI: {media.uri}")

            return playlist

        except Exception as e:
            print(f"❌ 解析M3U8文件失败: {e}")
            return None

    def select_best_stream(self, playlist, max_quality: bool = True) -> Optional[Dict]:
        """选择最佳质量的视频流"""
        try:
            if not playlist.playlists:
                if playlist.segments:
                    return {
                        'uri': None,
                        'bandwidth': 'unknown',
                        'resolution': 'unknown',
                        'codecs': 'unknown',
                        'is_direct': True
                    }
                else:
                    print("❌ 既没有播放列表也没有片段")
                    return None

            streams = []
            for p in playlist.playlists:
                stream_info = {
                    'uri': playlist.base_uri + p.uri if not p.uri.startswith('http') else p.uri,
                    'bandwidth': p.stream_info.bandwidth if p.stream_info else 0,
                    'resolution': p.stream_info.resolution if p.stream_info else None,
                    'codecs': p.stream_info.codecs if p.stream_info else None,
                    'is_direct': False
                }
                streams.append(stream_info)

            streams.sort(key=lambda x: x['bandwidth'], reverse=max_quality)
            return streams[0] if streams else None

        except Exception as e:
            print(f"❌ 选择视频流失败: {e}")
            return None

    def download_single_segment(self, url: str, output_file: Path, headers: dict,
                               max_retries: int = None) -> bool:
        """下载单个视频片段"""
        if max_retries is None:
            max_retries = self.config.MAX_RETRIES

        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers, verify=False, timeout=30)
                response.raise_for_status()

                with open(output_file, 'wb') as f:
                    f.write(response.content)

                return True

            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                else:
                    return False

        return False

    def download_segments(self, m3u8_url: str, output_file: Path,
                         max_workers: int = None) -> bool:
        """下载视频片段并合并"""
        if max_workers is None:
            max_workers = self.config.MAX_WORKERS

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(m3u8_url, headers=headers, verify=False, timeout=30)
            response.raise_for_status()

            playlist = m3u8.loads(response.text)
            base_url = m3u8_url.rsplit('/', 1)[0] + '/'

            if not playlist.segments:
                print("❌ 未找到视频片段")
                return False

            print(f"找到 {len(playlist.segments)} 个视频片段")

            segments_dir = output_file.parent / "segments"
            segments_dir.mkdir(exist_ok=True)

            segment_files = []
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {}

                for i, segment in enumerate(playlist.segments):
                    segment_url = segment.uri if segment.uri.startswith('http') else base_url + segment.uri
                    segment_file = segments_dir / f"segment_{i:04d}.ts"

                    future = executor.submit(self.download_single_segment,
                                           segment_url, segment_file, headers)
                    futures[future] = (i, segment_file)

                completed = 0
                for future in as_completed(futures):
                    i, segment_file = futures[future]
                    try:
                        success = future.result()
                        if success:
                            segment_files.append((i, segment_file))
                            completed += 1
                            if completed % 10 == 0 or completed == len(playlist.segments):
                                print(f"已下载 {completed}/{len(playlist.segments)} 个片段")
                        else:
                            print(f"⚠️ 片段 {i} 下载失败")
                    except Exception as e:
                        print(f"⚠️ 片段 {i} 下载异常: {e}")

            if not segment_files:
                print("❌ 没有成功下载任何片段")
                return False

            segment_files.sort(key=lambda x: x[0])
            print("正在合并视频片段...")

            with open(output_file, 'wb') as outfile:
                for i, segment_file in segment_files:
                    if segment_file.exists():
                        with open(segment_file, 'rb') as infile:
                            outfile.write(infile.read())

            shutil.rmtree(segments_dir, ignore_errors=True)
            print(f"✅ 成功合并 {len(segment_files)} 个片段")
            return True

        except Exception as e:
            print(f"❌ 下载片段失败: {e}")
            return False

    def download_cover_image(self, cover_url: str, output_dir: Path) -> Optional[Path]:
        """下载封面图片"""
        if not cover_url:
            return None

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(cover_url, headers=headers, verify=False, timeout=30)
            response.raise_for_status()

            content_type = response.headers.get('content-type', '')
            if 'jpeg' in content_type or 'jpg' in content_type:
                ext = '.jpg'
            elif 'png' in content_type:
                ext = '.png'
            elif 'webp' in content_type:
                ext = '.webp'
            else:
                ext = os.path.splitext(cover_url.split('?')[0])[-1] or '.jpg'

            cover_file = output_dir / f"cover{ext}"

            with open(cover_file, 'wb') as f:
                f.write(response.content)

            print(f"✅ 封面图片下载成功: {cover_file}")
            return cover_file

        except Exception as e:
            print(f"⚠️ 封面图片下载失败: {e}")
            return None

    def convert_to_mp4(self, video_file: Path, audio_file: Optional[Path],
                      output_path: str, title: str = None,
                      cover_file: Optional[Path] = None) -> bool:
        """使用FFmpeg将视频转换为MP4格式"""
        try:
            if title:
                safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
                safe_title = safe_title.replace('\n', ' ').strip()
                output_file = f"{safe_title}.mp4"
            else:
                output_file = f"video_{int(time.time())}.mp4"

            final_output = os.path.join(output_path, output_file)
            os.makedirs(output_path, exist_ok=True)

            cmd = ['ffmpeg', '-y']

            if audio_file and audio_file.exists():
                print("使用独立音频流进行合并")
                cmd.extend(['-i', str(video_file), '-i', str(audio_file)])

                if cover_file and cover_file.exists():
                    cmd.extend(['-i', str(cover_file)])
                    cmd.extend([
                        '-map', '0:v:0', '-map', '1:a:0', '-map', '2:v:0',
                        '-c:v:0', self.config.FFMPEG_PARAMS['video_codec'],
                        '-c:a:0', self.config.FFMPEG_PARAMS['audio_codec'],
                        '-c:v:1', 'mjpeg',
                        '-disposition:v:1', 'attached_pic',
                        '-preset', self.config.FFMPEG_PARAMS['preset'],
                        '-crf', self.config.FFMPEG_PARAMS['crf'],
                        '-movflags', '+faststart'
                    ])
                else:
                    cmd.extend([
                        '-map', '0:v:0', '-map', '1:a:0',
                        '-c:v', self.config.FFMPEG_PARAMS['video_codec'],
                        '-c:a', self.config.FFMPEG_PARAMS['audio_codec'],
                        '-preset', self.config.FFMPEG_PARAMS['preset'],
                        '-crf', self.config.FFMPEG_PARAMS['crf'],
                        '-movflags', '+faststart'
                    ])
            else:
                cmd.extend(['-i', str(video_file)])
                if cover_file and cover_file.exists():
                    cmd.extend(['-i', str(cover_file)])
                    cmd.extend([
                        '-map', '0:v:0', '-map', '0:a:0', '-map', '1:v:0',
                        '-c:v:0', self.config.FFMPEG_PARAMS['video_codec'],
                        '-c:a:0', self.config.FFMPEG_PARAMS['audio_codec'],
                        '-c:v:1', 'mjpeg',
                        '-disposition:v:1', 'attached_pic',
                        '-preset', self.config.FFMPEG_PARAMS['preset'],
                        '-crf', self.config.FFMPEG_PARAMS['crf'],
                        '-movflags', '+faststart'
                    ])
                else:
                    cmd.extend([
                        '-c:v', self.config.FFMPEG_PARAMS['video_codec'],
                        '-c:a', self.config.FFMPEG_PARAMS['audio_codec'],
                        '-preset', self.config.FFMPEG_PARAMS['preset'],
                        '-crf', self.config.FFMPEG_PARAMS['crf'],
                        '-movflags', '+faststart'
                    ])

            cmd.append(final_output)

            print(f"执行FFmpeg命令...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=False,
                timeout=self.config.FFMPEG_TIMEOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            if result.returncode == 0:
                print(f"✅ 视频转换成功: {final_output}")
                if os.path.exists(final_output):
                    file_size = os.path.getsize(final_output) / (1024 * 1024)
                    print(f"输出文件大小: {file_size:.2f} MB")
                return True
            else:
                print(f"❌ FFmpeg转换失败")
                try:
                    error_output = result.stderr.decode('utf-8', errors='ignore')
                    print(f"错误输出: {error_output}")
                except:
                    print("无法解码错误输出")
                return False

        except subprocess.TimeoutExpired:
            print("❌ FFmpeg转换超时")
            return False
        except Exception as e:
            print(f"❌ 视频转换过程中发生错误: {e}")
            return False

    def download_m3u8_video(self, url: str, output_path: str, title: str = None,
                           max_quality: bool = True, cover_url: str = None) -> bool:
        """下载m3u8格式视频并自动合并音视频流"""
        try:
            print(f"开始下载视频: {title or 'Unknown'}")
            print(f"M3U8 URL: {url}")
            if cover_url:
                print(f"封面URL: {cover_url}")

            if not self.check_ffmpeg():
                print("❌ FFmpeg未安装或不在PATH中，无法合并视频")
                return False

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                print("步骤1: 解析M3U8文件...")
                playlist = self.parse_m3u8(url)
                if not playlist:
                    return False

                print("步骤2: 选择视频流...")
                best_stream = self.select_best_stream(playlist, max_quality)
                if not best_stream:
                    print("❌ 未找到可用的视频流")
                    return False

                print(f"选择的流: 分辨率={best_stream.get('resolution', 'Unknown')}, 带宽={best_stream.get('bandwidth', 'Unknown')}")

                print("步骤3: 下载视频流...")
                video_file = temp_path / "video.ts"

                if best_stream.get('is_direct'):
                    if not self.download_segments(url, video_file):
                        return False
                else:
                    if not self.download_segments(best_stream['uri'], video_file):
                        return False

                print("步骤4: 查找音频流...")
                audio_file = None

                if playlist.media:
                    for media in playlist.media:
                        if media.type and media.type.upper() == 'AUDIO':
                            print(f"发现音频流: {media.uri}")
                            audio_file = temp_path / "audio.ts"
                            audio_uri = media.uri
                            if not audio_uri.startswith('http'):
                                audio_uri = playlist.base_uri + audio_uri

                            if self.download_segments(audio_uri, audio_file):
                                print("✅ 音频流下载成功")
                                break
                            else:
                                print("⚠️ 音频流下载失败")
                                audio_file = None

                if not audio_file and playlist.playlists:
                    for p in playlist.playlists:
                        if p.stream_info and hasattr(p.stream_info, 'audio') and p.stream_info.audio:
                            print(f"从播放列表中找到音频引用: {p.stream_info.audio}")
                            for media in playlist.media or []:
                                if media.group_id == p.stream_info.audio:
                                    print(f"找到对应音频流: {media.uri}")
                                    audio_file = temp_path / "audio.ts"
                                    audio_uri = media.uri
                                    if not audio_uri.startswith('http'):
                                        audio_uri = playlist.base_uri + audio_uri

                                    if self.download_segments(audio_uri, audio_file):
                                        print("✅ 音频流下载成功")
                                        break
                                    else:
                                        print("⚠️ 音频流下载失败")
                                        audio_file = None
                            if audio_file:
                                break

                if not audio_file:
                    print("⚠️ 未找到独立音频流，视频可能已包含音频")

                print("步骤5: 下载封面图片...")
                cover_file = None
                if cover_url:
                    cover_file = self.download_cover_image(cover_url, temp_path)

                print("步骤6: 转换为MP4格式...")
                success = self.convert_to_mp4(video_file, audio_file, output_path, title, cover_file)

                if success:
                    print(f"✅ 视频下载完成: {output_path}")
                    return True
                else:
                    print("❌ 视频转换失败")
                    return False

        except Exception as e:
            print(f"❌ 下载过程中发生错误: {e}")
            return False

    def download_videos_from_list(self, video_data: List[Dict[str, Any]],
                                 selected_indices: List[int],
                                 output_dir: str = None) -> None:
        """下载选中的视频"""
        if output_dir is None:
            output_dir = self.config.DEFAULT_DOWNLOADS_DIR

        if not selected_indices:
            print("❌ 没有选择任何视频")
            return

        print(f"\n📥 准备下载 {len(selected_indices)} 个视频到 {output_dir} 目录")
        os.makedirs(output_dir, exist_ok=True)

        success_count = 0
        failed_count = 0

        for i, index in enumerate(selected_indices, 1):
            try:
                video_index = index - 1

                if video_index >= len(video_data):
                    print(f"⚠️ 索引 {index} 超出范围，跳过")
                    failed_count += 1
                    continue

                item = video_data[video_index]
                video_url = item.get('url', '')
                title = item.get('title', f"Video_{item.get('id', index)}")
                cover_url = item.get('cover', '')

                print(f"\n[{i}/{len(selected_indices)}] 下载视频 #{index}: {title}")

                if not video_url:
                    print(f"⚠️ 跳过 - 没有视频URL")
                    failed_count += 1
                    continue

                success = self.download_m3u8_video(video_url, output_dir, title, True, cover_url)

                if success:
                    success_count += 1
                    print(f"✅ 视频 #{index} 下载成功")
                else:
                    failed_count += 1
                    print(f"❌ 视频 #{index} 下载失败")

                if i < len(selected_indices):
                    time.sleep(self.config.DOWNLOAD_DELAY)

            except Exception as e:
                print(f"❌ 下载视频 #{index} 时发生错误: {e}")
                failed_count += 1

        print(f"\n📊 下载完成统计:")
        print(f"✅ 成功: {success_count}")
        print(f"❌ 失败: {failed_count}")
        print(f"📁 输出目录: {output_dir}")
