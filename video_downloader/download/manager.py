"""
下载管理器模块
处理视频下载、ffmpeg合并和封面嵌入
"""

import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, Any, List, Tuple

import m3u8
import requests

from ..core.config import Config
from ..database.models import VideoRecord
from ..core.logger import info, error


class DownloadManager:

    def __init__(self):
        self.config = Config()
        self.temp_dir = tempfile.mkdtemp(prefix="video_download_")
        # 创建会话，支持代理配置
        self.session = requests.Session()
        self.setup_session()

    def setup_session(self):
        """设置会话配置"""
        if self.config.PROXY_ENABLED:
            try:
                proxies = self.config.get_proxy_config()
                self.session.proxies.update(proxies)
                info(f"🌐 已启用代理: {proxies}")
            except Exception as e:
                error(f"⚠️ 代理配置失败，使用直连: {e}")
                self.session.trust_env = False
                self.session.proxies = {}
        else:
            self.session.trust_env = False
            self.session.proxies = {}

    @staticmethod
    def sanitize_filename(filename: str) -> str:
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

    @staticmethod
    def check_ffmpeg() -> bool:
        """检查ffmpeg是否可用"""
        try:
            result = subprocess.run(['ffmpeg', '-version'],
                                    capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def verify_m3u8_url(self, url: str) -> bool:
        """验证M3U8 URL是否可访问"""
        if not url:
            return False

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': url
            }

            # 发送HEAD请求检查URL是否可访问
            response = self.session.head(url, headers=headers, timeout=15, allow_redirects=True)

            # 如果HEAD请求失败，尝试GET请求获取前几个字节
            if response.status_code != 200:
                response = self.session.get(url, headers=headers, timeout=15, stream=True)
                # 只读取前1024字节来验证
                content = response.raw.read(1024)
                response.close()

                # 检查内容是否像M3U8文件
                if response.status_code == 200:
                    content_str = content.decode('utf-8', errors='ignore')
                    return '#EXTM3U' in content_str or '.m3u8' in url.lower()

            return response.status_code == 200

        except Exception as e:
            error(f"⚠️ 验证M3U8 URL失败: {e}")
            return False

    def download_cover_image(self, cover_url: str, temp_dir: str) -> Optional[str]:
        """下载封面图片到临时目录"""
        if not cover_url:
            return None

        try:
            info(f"📸 正在下载封面图片...")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': cover_url
            }

            response = self.session.get(cover_url, headers=headers, timeout=30)
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

            info(f"✅ 封面图片下载完成: {cover_path}")
            return cover_path

        except Exception as e:
            error(f"❌ 下载封面图片失败: {e}")
            return None

    def parse_m3u8_playlist(self, m3u8_url: str) -> Optional[Dict]:
        """解析M3U8播放列表，检测音视频流"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': m3u8_url
            }

            response = self.session.get(m3u8_url, headers=headers, timeout=30)
            response.raise_for_status()

            playlist = m3u8.loads(response.text)

            # 检查是否是主播放列表（包含多个质量的流）
            if playlist.is_variant:
                info(f"📺 发现多质量流，正在分析...")

                # 分析音视频流
                video_streams = []
                audio_streams = []
                mixed_streams = []

                # 收集所有的媒体组信息
                audio_groups = {}
                video_groups = {}
                subtitle_groups = {}

                # 首先解析媒体组
                if hasattr(playlist, 'media') and playlist.media:
                    for media in playlist.media:
                        media_info = {
                            'url': urllib.parse.urljoin(m3u8_url, media.uri) if media.uri else None,
                            'name': media.name or f"Track {media.group_id}",
                            'language': getattr(media, 'language', 'und'),
                            'default': getattr(media, 'default', False),
                            'autoselect': getattr(media, 'autoselect', False),
                            'group_id': media.group_id,
                            'characteristics': getattr(media, 'characteristics', None)
                        }

                        if media.type == 'AUDIO':
                            audio_groups[media.group_id] = media_info
                            info(f"🎵 发现音频组: {media.group_id} - {media_info['name']} ({media_info['language']}) URL: {media_info['url']}")
                        elif media.type == 'VIDEO':
                            video_groups[media.group_id] = media_info
                            info(f"🎬 发现视频组: {media.group_id} - {media_info['name']}")
                        elif media.type == 'SUBTITLES':
                            subtitle_groups[media.group_id] = media_info
                            info(f"📝 发现字幕组: {media.group_id} - {media_info['name']} ({media_info['language']}) ")

                # 分析播放列表中的流
                for stream in playlist.playlists:
                    stream_info = stream.stream_info
                    stream_data = {
                        'url': urllib.parse.urljoin(m3u8_url, stream.uri),
                        'bandwidth': stream_info.bandwidth or 0,
                        'resolution': getattr(stream_info, 'resolution', None),
                        'codecs': getattr(stream_info, 'codecs', None),
                        'frame_rate': getattr(stream_info, 'frame_rate', None),
                        'audio_group': getattr(stream_info, 'audio', None),
                        'video_group': getattr(stream_info, 'video', None),
                        'subtitle_group': getattr(stream_info, 'subtitles', None)
                    }

                    # 检查编码信息来判断流类型
                    codecs = stream_data.get('codecs', '') or ''
                    has_video_codec = any(codec in codecs.lower() for codec in ['avc1', 'hvc1', 'h264', 'h265', 'vp9', 'av01'])
                    has_audio_codec = any(codec in codecs.lower() for codec in ['mp4a', 'aac', 'mp3', 'opus'])

                    # 更精确的流分类
                    if stream_data.get('resolution') and has_video_codec:
                        # 有分辨率且有视频编码 - 视频流（可能引用音频组）
                        video_streams.append(stream_data)
                        info(f"📹 视频流: {stream_data['bandwidth']}bps, 分辨率: {stream_data.get('resolution', 'Unknown')}, 音频组: {stream_data['audio_group']}, 编码: {codecs}")
                    elif not stream_data.get('resolution') and has_audio_codec and not has_video_codec:
                        # 无分辨率且只有音频编码 - 纯音频流
                        audio_streams.append(stream_data)
                        info(f"🎵 纯音频流: {stream_data['bandwidth']}bps, 编码: {codecs}")
                    else:
                        # 混合流（包含音视频）
                        mixed_streams.append(stream_data)
                        resolution_str = f", 分辨率: {stream_data.get('resolution', 'Unknown')}" if stream_data.get('resolution') else ""
                        info(f"🎬 混合流: {stream_data['bandwidth']}bps{resolution_str}, 编码: {codecs}")

                # 决定使用哪种下载策略 - 优先检查视频流+音频组的组合
                if video_streams and audio_groups:
                    # 独立音视频流模式
                    info(f"🎵 检测到独立音视频流模式: {len(video_streams)} 个视频流, {len(audio_groups)} 个音频组")

                    # 选择最高质量的视频流
                    best_video = max(video_streams, key=lambda x: (x['bandwidth'],
                                                                  x.get('resolution', [0, 0])[0] if x.get('resolution') else 0))

                    # 选择对应的音频流
                    selected_audio = None
                    audio_group_id = best_video.get('audio_group')

                    if audio_group_id and audio_group_id in audio_groups:
                        selected_audio = audio_groups[audio_group_id]
                        info(f"🎯 匹配到音频组: {audio_group_id}")
                    else:
                        # 如果没有指定音频组，选择默认或第一个
                        for group_id, audio_info in audio_groups.items():
                            if audio_info.get('default', False) or selected_audio is None:
                                selected_audio = audio_info
                            info(f"🎯 使用默认音频组: {group_id}")
                            break

                    if selected_audio and selected_audio['url']:
                        info(f"🎯 选择视频流: 码率 {best_video['bandwidth']}, 分辨率 {best_video.get('resolution', 'Unknown')}")
                        info(f"🎵 选择音频流: {selected_audio['name']} ({selected_audio['language']}) - URL: {selected_audio['url']}")

                        # 递归解析视频和音频流
                        video_info = self.parse_m3u8_playlist(best_video['url'])
                        audio_info = self.parse_m3u8_playlist(selected_audio['url'])

                        if video_info and audio_info:
                            return {
                                'has_separate_audio': True,
                                'video_stream': video_info,
                                'audio_stream': audio_info,
                                'video_url': best_video['url'],
                                'audio_url': selected_audio['url']
                            }
                        else:
                            error(f"⚠️ 无法解析独立音视频流，回退到混合流")

                # 如果独立音视频流失败，尝试混合流
                all_streams = mixed_streams + video_streams
                if all_streams:
                    # 选择最高质量的混合流或视频流
                    best_stream = max(all_streams, key=lambda x: (x['bandwidth'],
                                                                 x.get('resolution', [0, 0])[0] if x.get('resolution') else 0))
                    info(f"🎯 选择混合流: 码率 {best_stream['bandwidth']}, 分辨率 {best_stream.get('resolution', 'Unknown')}")
                    return self.parse_m3u8_playlist(best_stream['url'])

                # 最后回退选择
                if playlist.playlists:
                    best_playlist = max(playlist.playlists, key=lambda x: x.stream_info.bandwidth or 0)
                    best_url = urllib.parse.urljoin(m3u8_url, best_playlist.uri)
                    info(f"🎯 回退选择流: {best_url} (码率: {best_playlist.stream_info.bandwidth})")
                    return self.parse_m3u8_playlist(best_url)

            else:
                # 直接的媒体播放列表
                base_url = m3u8_url.rsplit('/', 1)[0] + '/'
                segments = []

                for segment in playlist.segments:
                    segment_url = urllib.parse.urljoin(base_url, segment.uri)
                    segments.append({
                        'url': segment_url,
                        'duration': segment.duration,
                        'byterange': getattr(segment, 'byterange', None)
                    })

                total_duration = sum(seg.get('duration', 0) for seg in segments)
                info(f"📊 媒体播放列表: {len(segments)} 个片段, 总时长: {total_duration:.1f}秒")

                return {
                    'has_separate_audio': False,
                    'segments': segments,
                    'base_url': base_url,
                    'total_segments': len(segments),
                    'total_duration': total_duration
                }

        except Exception as e:
            error(f"❌ 解析M3U8播放列表失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def download_segment(self, segment_info: Dict, segment_index: int, temp_dir: str) -> Optional[str]:
        """下载单个视频片段"""
        try:
            segment_url = segment_info['url']
            segment_filename = f"segment_{segment_index:05d}.ts"
            segment_path = os.path.join(temp_dir, segment_filename)

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': segment_url
            }

            for retry in range(self.config.MAX_RETRIES):
                try:
                    response = self.session.get(segment_url, headers=headers, timeout=30, stream=True)
                    response.raise_for_status()

                    with open(segment_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)

                    return segment_path

                except Exception as e:
                    if retry < self.config.MAX_RETRIES - 1:
                        error(f"⚠️ 片段 {segment_index} 下载失败，重试 {retry + 1}/{self.config.MAX_RETRIES}: {e}")
                        time.sleep(self.config.RETRY_DELAY)
                    else:
                        error(f"❌ 片段 {segment_index} 下载最终失败: {e}")
                        return None

        except Exception as e:
            error(f"❌ 下载片段 {segment_index} 异常: {e}")
            return None

    def download_m3u8_with_python(self, playlist_info: Dict, temp_dir: str, stream_type: str = "mixed") -> Optional[str]:
        """使用Python下载M3U8流，支持音视频分离"""
        try:
            # 检查是否有分离的音视频流
            if playlist_info.get('has_separate_audio', False):
                info(f"🎵 检测到独立音视频流")
                return None  # 对于分离流，使用ffmpeg处理更可靠

            segments = playlist_info['segments']
            total_segments = playlist_info['total_segments']

            info(f"📊 发现 {total_segments} 个{stream_type}片段")

            # 创建片段下载目录
            segments_dir = os.path.join(temp_dir, f"{stream_type}_segments")
            os.makedirs(segments_dir, exist_ok=True)

            downloaded_segments = []

            # 使用线程池并行下载片段
            with ThreadPoolExecutor(max_workers=self.config.MAX_CONCURRENT_DOWNLOADS) as executor:
                # 提交所有下载任务
                future_to_index = {
                    executor.submit(self.download_segment, segment, i, segments_dir): i
                    for i, segment in enumerate(segments)
                }

                # 收集结果
                for future in as_completed(future_to_index):
                    segment_index = future_to_index[future]
                    try:
                        segment_path = future.result()
                        if segment_path:
                            downloaded_segments.append((segment_index, segment_path))
                            info(f"✅ {stream_type}片段 {segment_index + 1}/{total_segments} 下载完成")
                        else:
                            error(f"❌ {stream_type}片段 {segment_index + 1} 下载失败")
                    except Exception as e:
                        error(f"❌ {stream_type}片段 {segment_index + 1} 下载异常: {e}")

            # 按索引排序片段
            downloaded_segments.sort(key=lambda x: x[0])

            if not downloaded_segments:
                error(f"❌ 没有成功下载任何{stream_type}片段")
                return None

            info(f"✅ 成功下载 {len(downloaded_segments)}/{total_segments} 个{stream_type}片段")

            # 合并片段
            return self.merge_ts_segments(downloaded_segments, temp_dir, stream_type)

        except Exception as e:
            error(f"❌ Python下载{stream_type}M3U8失败: {e}")
            return None

    def merge_ts_segments(self, segments: List[Tuple[int, str]], temp_dir: str, stream_type: str = "mixed") -> Optional[str]:
        """合并TS片段为单个视频文件"""
        try:
            info(f"🔧 正在合并 {len(segments)} 个{stream_type}片段...")

            # 创建片段列表文件
            segments_list_file = os.path.join(temp_dir, f"{stream_type}_segments_list.txt")
            with open(segments_list_file, 'w', encoding='utf-8') as f:
                for _, segment_path in segments:
                    # 使用相对路径避免路径问题
                    relative_path = os.path.relpath(segment_path, temp_dir)
                    f.write(f"file '{relative_path}'\n")

            # 输出文件
            if stream_type == "audio":
                merged_file = os.path.join(temp_dir, "merged_audio.aac")
                # 对音频流，直接复制不重新编码
                codec_args = ['-c', 'copy']
            else:
                merged_file = os.path.join(temp_dir, "merged_video.mp4")
                codec_args = ['-c', 'copy']

            # 使用ffmpeg合并片段
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', segments_list_file,
            ] + codec_args + [
                '-avoid_negative_ts', 'make_zero',
                merged_file
            ]

            info(f"🎯 执行{stream_type}合并命令: {' '.join(cmd)}")

            # 修复编码问题
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8',
                                  errors='ignore', timeout=self.config.FFMPEG_TIMEOUT, cwd=temp_dir)

            if result.returncode == 0 and os.path.exists(merged_file):
                file_size = os.path.getsize(merged_file)
                info(f"✅ {stream_type}片段合并完成，文件大小: {file_size / 1024 / 1024:.2f} MB")
                return merged_file
            else:
                error(f"❌ {stream_type}片段合并失败:")
                error(f"返回码: {result.returncode}")
                if result.stderr:
                    error(f"错误信息: {result.stderr}")
                return None

        except Exception as e:
            error(f"❌ 合并{stream_type}片段异常: {e}")
            return None

    def download_m3u8_streams(self, url: str, temp_dir: str) -> Tuple[Optional[str], Optional[str]]:
        """下载m3u8视频流，支持音视频分离下载"""
        if not url:
            info("⚠️ URL为空，跳过下载")
            return None, None

        try:
            info(f"🎬 正在解析M3U8流: {url}")

            # 首先验证URL是否可访问
            if not self.verify_m3u8_url(url):
                error(f"❌ M3U8 URL无法访问: {url}")
                return None, None

            # 解析M3U8播放列表
            playlist_info = self.parse_m3u8_playlist(url)
            if not playlist_info:
                error("❌ 无法解析M3U8播放列表")
                return None, None

            # 检查是否有分离的音视频流
            if playlist_info.get('has_separate_audio', False):
                info("🎵 检测到独立的音视频流，开始分别下载...")

                video_stream_info = playlist_info['video_stream']
                audio_stream_info = playlist_info['audio_stream']
                video_url = playlist_info.get('video_url')
                audio_url = playlist_info.get('audio_url')

                # 并行下载视频和音频流
                video_path = None
                audio_path = None

                # 下载视频流
                if video_stream_info:
                    info("📹 下载视频流...")
                    # 优先使用Python方式下载片段
                    video_path = self.download_m3u8_with_python(video_stream_info, temp_dir, "video")

                    # 如果失败，使用ffmpeg直接下载
                    if not video_path and video_url:
                        info("🔄 Python下载视频流失败，使用ffmpeg...")
                        video_path = self.download_single_stream(video_url, temp_dir, "video")

                # 下载音频流
                if audio_stream_info:
                    info("🎵 下载音频流...")
                    # 优先使用Python方式下载片段
                    audio_path = self.download_m3u8_with_python(audio_stream_info, temp_dir, "audio")

                    # 如果失败，使用ffmpeg直接下载
                    if not audio_path and audio_url:
                        info("🔄 Python下载音频流失败，使用ffmpeg...")
                        audio_path = self.download_single_stream(audio_url, temp_dir, "audio")

                # 检查下载结果
                if video_path and audio_path:
                    info("✅ 音视频流下载完成")
                    return video_path, audio_path
                elif video_path:
                    info("⚠️ 仅视频流下载成功，音频流下载失败")
                    return video_path, None
                else:
                    error("❌ 音视频流下载均失败")
                    # 如果独立流下载失败，尝试下载原始URL作为混合流
                    info("🔄 尝试下载原始URL作为混合流...")
                    mixed_path = self.download_single_stream(url, temp_dir, "mixed")
                    return mixed_path, None
            else:
                # 混合流，使用原有逻辑
                info("🎬 检测到混合音视频流")
                video_path = self.download_m3u8_with_python(playlist_info, temp_dir, "mixed")

                # 如果Python下载失败，回退到ffmpeg
                if not video_path:
                    info("🔄 Python下载失败，回退到ffmpeg下载...")
                    video_path = self.download_single_stream(url, temp_dir, "mixed")

                return video_path, None

        except Exception as e:
            error(f"❌ 下载M3U8流失败: {e}")
            import traceback
            traceback.print_exc()
            return None, None

    # @staticmethod
    # def reconstruct_stream_url(base_url: str, stream_info: Dict) -> Optional[str]:
    #     """从基础URL和流信息重构完整的流URL"""
    #     try:
    #         # 如果流信息中有完整URL，直接使用
    #         if 'url' in stream_info:
    #             return stream_info['url']
    #
    #         # 否则尝试从segments中获取base_url
    #         if 'base_url' in stream_info:
    #             return stream_info['base_url']
    #
    #         # 如果都没有，返回None
    #         return None
    #
    #     except Exception as e:
    #         print(f"❌ 重构流URL失败: {e}")
    #         return None

    def download_single_stream(self, url: str, temp_dir: str, stream_type: str) -> Optional[str]:
        """使用ffmpeg下载单个流文件"""
        try:
            # 根据流类型选择合适的输出格式
            if stream_type == "audio":
                output_file = os.path.join(temp_dir, f"{stream_type}.aac")
            else:
                output_file = os.path.join(temp_dir, f"{stream_type}.mp4")

            # 使用ffmpeg下载m3u8流，添加更多参数提高成功率
            cmd = [
                'ffmpeg', '-y',
                '-user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                '-headers', 'Referer: ' + url,
                '-reconnect', '1',
                '-reconnect_streamed', '1',
                '-reconnect_delay_max', '5',
                '-i', url,
                '-c', 'copy',
                '-avoid_negative_ts', 'make_zero'
            ]

            # 对音频流添加特殊处理
            if stream_type == "audio":
                cmd.extend(['-vn'])  # 禁用视频流
            else:
                cmd.extend(['-bsf:a', 'aac_adtstoasc'])  # 修复AAC音频

            cmd.append(output_file)

            info(f"📥 正在使用ffmpeg下载{stream_type}流...")
            info(f"🎯 执行命令: {' '.join(cmd)}")

            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8',
                                  errors='ignore', timeout=self.config.FFMPEG_TIMEOUT)

            if result.returncode == 0 and os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                info(f"✅ {stream_type}流下载完成，文件大小: {file_size / 1024 / 1024:.2f} MB")

                # 验证下载的文件是否有效
                if self.verify_stream_file(output_file, stream_type):
                    return output_file
                else:
                    error(f"⚠️ {stream_type}流文件验证失败")
                    return None
            else:
                error(f"❌ {stream_type}流下载失败:")
                error(f"返回码: {result.returncode}")
                if result.stderr:
                    error(f"错误信息: {result.stderr}")
                if result.stdout:
                    error(f"输出信息: {result.stdout}")
                return None

        except Exception as e:
            error(f"❌ 下载{stream_type}流异常: {e}")
            return None

    @staticmethod
    def verify_stream_file(file_path: str, stream_type: str) -> bool:
        """验证下载的流文件是否有效"""
        try:
            if stream_type == "audio":
                # 验证音频文件
                cmd = ['ffprobe', '-v', 'quiet', '-select_streams', 'a', '-show_entries', 'stream=codec_name,duration', '-of', 'csv=p=0', file_path]
            else:
                # 验证视频文件
                cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'stream=codec_name,duration', '-of', 'csv=p=0', file_path]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0 and result.stdout.strip():
                info(f"✅ {stream_type}流文件验证成功")
                return True
            else:
                error(f"❌ {stream_type}流文件验证失败")
                return False
        except Exception as e:
            error(f"⚠️ {stream_type}流文件验证异常: {e}")
            return False

    def download_video(self, video: VideoRecord, download_dir: str) -> bool:
        """下载单个视频"""
        if not video:
            return False

        if not video.url:
            info(f"⚠️ 跳过付费视频: {video.title}")
            return False

        try:
            info(f"\n🎬 开始下载: {video.title} ({video.video_date})")

            # 清理标题作为安全的文件名
            safe_title = self.sanitize_filename(video.title)
            safe_date = self.sanitize_filename(video.video_date)

            # 创建临时工作目录，使用标题和日期的组合作为唯一标识符
            temp_work_dir = os.path.join(self.temp_dir, f"video_{safe_title}_{safe_date}_{int(time.time())}")
            os.makedirs(temp_work_dir, exist_ok=True)

            try:
                # 1. 下载封面图片
                cover_path = self.download_cover_image(video.cover, temp_work_dir)

                # 2. 下载视频流
                video_path, audio_path = self.download_m3u8_streams(video.url, temp_work_dir)

                if not video_path:
                    error(f"❌ 视频下载失败: {video.title}")
                    return False

                # 3. 合并视频和封面 - 保存到按日期分类的子文件夹中
                date_folder = os.path.join(download_dir, safe_date)
                os.makedirs(date_folder, exist_ok=True)

                output_filename = f"{safe_title}_{safe_date}.{self.config.OUTPUT_FORMAT}"
                output_path = os.path.join(date_folder, output_filename)

                success = self.merge_video_with_cover(video_path, audio_path, cover_path, output_path)

                if success:
                    info(f"✅ 视频下载完成: {output_path}")
                    return True
                else:
                    error(f"❌ 视频处理失败: {video.title}")
                    return False

            finally:
                # 清理临时文件
                try:
                    shutil.rmtree(temp_work_dir)
                except Exception as e:
                    error(f"⚠️ 清理临时文件失败: {e}")

        except Exception as e:
            error(f"❌ 下载视频异常: {video.title} - {e}")
            return False

    def download_videos_by_date(self, videos: List[VideoRecord], download_dir: str, force: bool = False) -> Dict[str, Any]:
        """
        批量下载视频列表

        Args:
            videos: 要下载的视频列表
            download_dir: 下载目录
            force: 是否强制下载（覆盖已存在的文件）

        Returns:
            Dict: 下载统计信息
        """
        if not videos:
            info("⚠️ 没有视频需要下载")
            return {
                'total': 0,
                'success': 0,
                'failed': 0,
                'skipped': 0,
                'failed_videos': []
            }

        info(f"\n🎬 开始批量下载 {len(videos)} 个视频...")

        stats = {
            'total': len(videos),
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'failed_videos': []
        }

        for i, video in enumerate(videos, 1):
            try:
                info(f"\n📊 进度: {i}/{len(videos)}")

                # 检查是否跳过付费视频
                if video.is_primer:
                    info(f"⚠️ 跳过付费视频: {video.title}")
                    stats['skipped'] += 1
                    continue

                # 检查文件是否已存在
                if not force:
                    safe_title = self.sanitize_filename(video.title)
                    safe_date = self.sanitize_filename(video.video_date)

                    # 构建按日期分类的路径
                    date_folder = os.path.join(download_dir, safe_date)
                    output_filename = f"{safe_title}_{safe_date}.{self.config.OUTPUT_FORMAT}"
                    output_path = os.path.join(date_folder, output_filename)

                    if os.path.exists(output_path):
                        info(f"📁 文件已存在，跳过: {video.title}")
                        stats['skipped'] += 1
                        continue

                # 执行下载
                success = self.download_video(video, download_dir)

                if success:
                    stats['success'] += 1
                    info(f"✅ 下载成功: {video.title}")
                else:
                    stats['failed'] += 1
                    stats['failed_videos'].append({
                        'title': video.title,
                        'date': video.video_date,
                        'url': video.url
                    })
                    error(f"❌ 下载失败: {video.title}")

                # 添加下载间隔
                if i < len(videos):
                    info(f"⏳ 等待 {self.config.DOWNLOAD_DELAY} 秒...")
                    time.sleep(self.config.DOWNLOAD_DELAY)

            except Exception as e:
                stats['failed'] += 1
                stats['failed_videos'].append({
                    'title': video.title,
                    'date': video.video_date,
                    'url': video.url,
                    'error': str(e)
                })
                error(f"❌ 下载异常: {video.title} - {e}")

        # 显示最终统计
        info(f"\n📊 批量下载完成:")
        info(f"   总计: {stats['total']} 个")
        info(f"   成功: {stats['success']} 个")
        info(f"   失败: {stats['failed']} 个")
        info(f"   跳过: {stats['skipped']} 个")

        if stats['failed_videos']:
            error(f"\n❌ 失败的视频:")
            for failed in stats['failed_videos']:
                error_msg = failed.get('error', '下载失败')
                error(f"   - {failed['title']} ({failed['date']}): {error_msg}")

        return stats

    def download_videos_list(self, videos: List[VideoRecord], download_dir: str) -> Dict[str, Any]:
        """
        下载视频列表（兼容性方法）

        Args:
            videos: 要下载的视频列表
            download_dir: 下载目录

        Returns:
            Dict: 下载统计信息
        """
        return self.download_videos_by_date(videos, download_dir, force=False)

    def cleanup(self):
        """清理临时目录"""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                info(f"🧹 临时目录已清理: {self.temp_dir}")
        except Exception as e:
            error(f"⚠️ 清理临时目录失败: {e}")

    def __del__(self):
        """析构函数，自动清理临时目录"""
        self.cleanup()

    def merge_video_with_cover(self, video_path: str, audio_path: str, cover_path: str, output_path: str) -> bool:
        """使用ffmpeg合并音视频并嵌入封面"""
        try:
            info(f"🔧 正在处理视频并嵌入封面...")

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
                # 视频 + 独立音频 + 封面
                info("🎵 合并独立音视频流并嵌入封面")
                cmd.extend([
                    '-map', '0:v',  # 映射视频流
                    '-map', '1:a',  # 映射音频流
                    '-map', '2:v',  # 映射封面图片
                    '-c:v:0', 'copy',  # 主视频流直接复制
                    '-c:a', 'copy',  # 音频直接复制
                    '-c:v:1', 'copy',  # 封面图片保持原格式
                    '-disposition:v:1', 'attached_pic',  # 将封面设为附加图片
                    '-movflags', '+faststart',
                ])
            elif video_path and cover_path:
                # 视频 + 封面（需要确保音频不丢失）
                info("🎬 嵌入封面到混合音视频流")
                # 先检查视频文件是否包含音频流
                has_audio = self.check_audio_in_file(video_path)
                if has_audio:
                    cmd.extend([
                        '-map', '0:v',    # 映射视频流
                        '-map', '0:a',    # 明确映射音频流
                        '-map', '1:v',    # 映射封面图片
                        '-c:v:0', 'copy', # 主视频流直接复制
                        '-c:a', 'copy',   # 音频流直接复制
                        '-c:v:1', 'copy', # 封面图片保持原格式
                        '-disposition:v:1', 'attached_pic',
                        '-movflags', '+faststart',
                    ])
                else:
                    info("⚠️ 原视频文件不包含音频流")
                    cmd.extend([
                        '-map', '0:v',    # 映射视频流
                        '-map', '1:v',    # 映射封面图片
                        '-c:v:0', 'copy', # 主视频流直接复制
                        '-c:v:1', 'copy', # 封面图片保持原格式
                        '-disposition:v:1', 'attached_pic',
                        '-movflags', '+faststart',
                    ])
            elif video_path and audio_path:
                # 视频 + 独立音频（无封面）
                info("🎵 合并独立音视频流")
                cmd.extend([
                    '-map', '0:v',  # 映射视频流
                    '-map', '1:a',  # 映射音频流
                    '-c:v', 'copy', # 视频直接复制
                    '-c:a', 'copy', # 音频直接复制
                    '-movflags', '+faststart',
                ])
            elif video_path:
                # 仅视频文件
                info("🎬 处理单一视频文件")
                has_audio = self.check_audio_in_file(video_path)
                if has_audio:
                    cmd.extend([
                        '-map', '0',      # 映射所有流
                        '-c', 'copy',     # 所有流直接复制
                        '-movflags', '+faststart',
                    ])
                else:
                    cmd.extend([
                        '-map', '0:v',    # 仅映射视频流
                        '-c:v', 'copy',   # 视频流直接复制
                        '-movflags', '+faststart',
                    ])
            else:
                error("❌ 没有视频文件进行处理")
                return False

            # 添加输出文件
            cmd.append(output_path)

            info(f"🎯 执行命令: {' '.join(cmd)}")

            # 执行ffmpeg命令
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8',
                                  errors='ignore', timeout=self.config.FFMPEG_TIMEOUT)

            if result.returncode == 0 and os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                info(f"✅ 视频处理完成: {output_path}")
                info(f"📁 文件大小: {file_size / 1024 / 1024:.2f} MB")

                # 验证音频流是否存在
                self.verify_audio_in_output(output_path)
                return True
            else:
                error(f"❌ 视频处理失败:")
                error(f"返回码: {result.returncode}")
                if result.stderr:
                    error(f"错误信息: {result.stderr}")
                if result.stdout:
                    error(f"输出信息: {result.stdout}")

                # 如果失败，尝试简化处理
                if cover_path:
                    info("🔄 尝试简化处理（不嵌入封面）...")
                    return self.process_video_without_cover(video_path, audio_path, output_path)

                return False

        except Exception as e:
            error(f"❌ 视频处理异常: {e}")
            return False

    @staticmethod
    def check_audio_in_file(file_path: str) -> bool:
        """检查文件是否包含音频流"""
        try:
            cmd = ['ffprobe', '-v', 'quiet', '-select_streams', 'a', '-show_entries', 'stream=index', '-of', 'csv=p=0', file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            has_audio = result.returncode == 0 and result.stdout.strip()
            if has_audio:
                info(f"✅ 检测到音频流: {file_path}")
            else:
                info(f"⚠️ 未检测到音频流: {file_path}")
            return bool(has_audio)
        except Exception as e:
            error(f"⚠️ 音频检测异常: {e}")
            return False

    def process_video_without_cover(self, video_path: str, audio_path: str, output_path: str) -> bool:
        """处理视频但不嵌入封面"""
        try:
            cmd = ['ffmpeg', '-y']

            if video_path:
                cmd.extend(['-i', video_path])
            if audio_path:
                cmd.extend(['-i', audio_path])

            if video_path and audio_path:
                info("🎵 合并音视频流（无封面）")
                cmd.extend([
                    '-map', '0:v',
                    '-map', '1:a',
                    '-c:v', 'copy',
                    '-c:a', 'copy',
                    '-movflags', '+faststart',
                ])
            elif video_path:
                info("🎬 处理视频文件（无封面）")
                cmd.extend([
                    '-map', '0',
                    '-c', 'copy',
                    '-movflags', '+faststart',
                ])
            else:
                return False

            cmd.append(output_path)

            info(f"🎯 执行命令（无封面）: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8',
                                  errors='ignore', timeout=self.config.FFMPEG_TIMEOUT)

            if result.returncode == 0 and os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                info(f"✅ 视频处理完成（无封面）: {output_path}")
                info(f"📁 文件大小: {file_size / 1024 / 1024:.2f} MB")
                self.verify_audio_in_output(output_path)
                return True
            else:
                error(f"❌ 视频处理失败（无封面）:")
                error(f"返回码: {result.returncode}")
                if result.stderr:
                    error(f"错误信息: {result.stderr}")
                return False

        except Exception as e:
            error(f"❌ 视频处理异常（无封面）: {e}")
            return False

    @staticmethod
    def verify_audio_in_output(video_path: str) -> bool:
        """验证输出视频是否包含音频流"""
        try:
            cmd = ['ffprobe', '-v', 'quiet', '-select_streams', 'a', '-show_entries', 'stream=codec_name', '-of', 'csv=p=0', video_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0 and result.stdout.strip():
                info(f"✅ 音频流验证成功: {result.stdout.strip()}")
                return True
            else:
                info(f"⚠️ 未检测到音频流，可能是静音视频")
                return False
        except Exception as e:
            error(f"⚠️ 音频验证失败: {e}")
            return False
