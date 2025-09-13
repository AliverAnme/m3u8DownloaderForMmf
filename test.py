import requests
import json
import os
import urllib3
import re
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List
import m3u8
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def fetch_posts_from_api(size: int = 50, verify_ssl: bool = False) -> Dict[str, Any]:
    """
    从API接口获取posts数据并保存到本地

    Args:
        size (int): 每页返回的数据条数，默认为50
        verify_ssl (bool): 是否验证SSL证书，默认为False

    Returns:
        Dict[str, Any]: API返回的JSON数据
    """
    # API接口URL
    base_url = "https://api.memefans.ai/v2/posts/"

    # 固定参数
    params = {
        "author_id": "BhhLJPlVvjU",
        "page": 1,
        "size": size
    }

    # 设置请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    try:
        print(f"正在请求API: {base_url}")
        print(f"参数: {params}")
        print(f"SSL验证: {'启用' if verify_ssl else '禁用'}")

        # 发送GET请求，禁用SSL验证并设置超时
        response = requests.get(
            base_url,
            params=params,
            headers=headers,
            verify=verify_ssl,  # 禁用SSL证书验证
            timeout=30  # 设置30秒超时
        )
        response.raise_for_status()  # 检查HTTP错误

        # 解析JSON数据
        data = response.json()

        # 保存到本地文件
        output_file = "api_response.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"数据已成功保存到 {output_file}")
        print(f"获取到 {len(data.get('items', []))} 条记录")

        return data

    except requests.exceptions.SSLError as e:
        print(f"SSL错误: {e}")
        print("尝试禁用SSL验证重新请求...")
        if verify_ssl:
            # 如果之前启用了SSL验证，现在禁用重试
            return fetch_posts_from_api(size, verify_ssl=False)
        else:
            print("SSL验证已禁用，但仍然出现SSL错误")
            return {}
    except requests.exceptions.RequestException as e:
        print(f"API请求失败: {e}")
        print(f"错误类型: {type(e).__name__}")
        return {}
    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}")
        print("响应内容可能不是有效的JSON格式")
        return {}
    except Exception as e:
        print(f"发生未知错误: {e}")
        print(f"错误类型: {type(e).__name__}")
        return {}


def read_json_file(file_path: str) -> Dict[str, Any]:
    """
    读取本地JSON文件

    Args:
        file_path (str): JSON文件路径

    Returns:
        Dict[str, Any]: JSON数据
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"文件 {file_path} 不存在")
        return {}
    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}")
        return {}
    except Exception as e:
        print(f"读取文件时发生错误: {e}")
        return {}


def extract_title_from_description(description: str) -> str:
    """
    从description中提取标题内容

    Args:
        description (str): 完整的描述文本

    Returns:
        str: 提取的标题
    """
    if not description:
        return ""

    # 方法1: 提取【】开头到第一个 # 或者特定关键词之前的内容
    # 匹配模式：【xxxx】后面的内容直到遇到 # 或者特定关键词
    pattern1 = r'【[^】]+】([^#]+?)(?:\s*#|\s*$)'
    match1 = re.search(pattern1, description)
    if match1:
        title = match1.group(0).strip()
        # 移除末尾的空格和特殊字符
        title = re.sub(r'\s*#.*$', '', title).strip()
        return title

    # 方法2: 如果没有【】格式，提取第一个#之前的内容
    pattern2 = r'^([^#]+?)(?:\s*#|$)'
    match2 = re.search(pattern2, description)
    if match2:
        title = match2.group(1).strip()
        return title

    # 方法3: 如果都没有匹配，返回前100个字符
    return description[:100] + "..." if len(description) > 100 else description


def extract_items_data(json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    从JSON数据中提取items下每项的id、url、description、cover字段，并提取标题

    Args:
        json_data (Dict[str, Any]): 完整的JSON数据

    Returns:
        List[Dict[str, Any]]: 提取的字段列表
    """
    extracted_items = []

    if 'items' not in json_data:
        print("JSON数据中没有找到'items'字段")
        return extracted_items

    items = json_data['items']

    for item in items:
        # 提取基本字段
        description = item.get('description', '')

        # 提取标题
        title = extract_title_from_description(description)

        extracted_item = {
            'id': item.get('id', ''),
            'url': item.get('url', ''),
            'title': title,  # 新增标题字段
            'description': description,
            'cover': item.get('cover', '')
        }
        extracted_items.append(extracted_item)

    return extracted_items


def save_extracted_data(extracted_data: List[Dict[str, Any]], output_file: str = "extracted_items.json"):
    """
    保存提取的数据到新的JSON文件

    Args:
        extracted_data (List[Dict[str, Any]]): 提取的数据
        output_file (str): 输出文件名
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(extracted_data, f, ensure_ascii=False, indent=2)
        print(f"提取的数据已保存到 {output_file}")
    except Exception as e:
        print(f"保存文件时发生错误: {e}")


def process_posts_data(data: Dict[str, Any]) -> None:
    """
    处理从API获取的posts数据

    Args:
        data (Dict[str, Any]): API返回的数据
    """
    if not data or 'items' not in data:
        print("数据为空或格式不正确")
        return

    items = data['items']
    total = data.get('total', 0)
    page = data.get('page', 1)
    size = data.get('size', 50)

    print(f"\n数据概览:")
    print(f"总记录数: {total}")
    print(f"当前页: {page}")
    print(f"每页大小: {size}")
    print(f"当前页记录数: {len(items)}")

    print(f"\n前3条记录的标题:")
    for i, item in enumerate(items[:3], 1):
        title = item.get('title', 'No title')
        likes = item.get('likes_count', 0)
        comments = item.get('comments_count', 0)
        print(f"{i}. {title} (👍{likes} 💬{comments})")


def check_ffmpeg() -> bool:
    """检查FFmpeg是否可用"""
    try:
        result = subprocess.run(['ffmpeg', '-version'],
                                capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def parse_m3u8(url: str) -> Optional[object]:
    """解析m3u8文件"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, verify=False, timeout=30)
        response.raise_for_status()

        # 解析m3u8内容
        playlist = m3u8.loads(response.text)
        playlist.base_uri = url.rsplit('/', 1)[0] + '/'

        # 调试信息：显示解析结果
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


def select_best_stream(playlist, max_quality: bool = True) -> Optional[Dict]:
    """选择最佳质量的视频流"""
    try:
        if not playlist.playlists:
            # 如果没有多个质量选项，检查是否直接包含片段
            if playlist.segments:
                # 这是一个包含片段的单一流
                return {
                    'uri': None,  # 使用原始URL
                    'bandwidth': 'unknown',
                    'resolution': 'unknown',
                    'codecs': 'unknown',
                    'is_direct': True
                }
            else:
                print("❌ 既没有播放列表也没有片段")
                return None

        # 按带宽排序选择最佳质量
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

        # 按带宽排序
        streams.sort(key=lambda x: x['bandwidth'], reverse=max_quality)

        return streams[0] if streams else None

    except Exception as e:
        print(f"❌ 选择视频流失败: {e}")
        return None


def download_single_segment(url: str, output_file: Path, headers: dict, max_retries: int = 3) -> bool:
    """下载单个视频片段"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, verify=False, timeout=30)
            response.raise_for_status()

            with open(output_file, 'wb') as f:
                f.write(response.content)

            return True

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)  # 重试前等待1秒
                continue
            else:
                return False

    return False


def download_segments(m3u8_url: str, output_file: Path, max_workers: int = 5) -> bool:
    """下载视频片段并合并"""
    try:
        # 解析具体的m3u8文件获取片段列表
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

        # 创建片段下载目录
        segments_dir = output_file.parent / "segments"
        segments_dir.mkdir(exist_ok=True)

        # 并发下载片段
        segment_files = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}

            for i, segment in enumerate(playlist.segments):
                segment_url = segment.uri if segment.uri.startswith('http') else base_url + segment.uri
                segment_file = segments_dir / f"segment_{i:04d}.ts"

                future = executor.submit(download_single_segment, segment_url, segment_file, headers)
                futures[future] = (i, segment_file)

            # 收集下载结果
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

        # 按顺序排序并合并片段
        segment_files.sort(key=lambda x: x[0])
        print("正在合并视频片段...")

        with open(output_file, 'wb') as outfile:
            for i, segment_file in segment_files:
                if segment_file.exists():
                    with open(segment_file, 'rb') as infile:
                        outfile.write(infile.read())

        # 清理临时文件
        shutil.rmtree(segments_dir, ignore_errors=True)

        print(f"✅ 成功合并 {len(segment_files)} 个片段")
        return True

    except Exception as e:
        print(f"❌ 下载片段失败: {e}")
        return False


def convert_to_mp4(video_file: Path, audio_file: Optional[Path], output_path: str, title: str = None) -> bool:
    """使用FFmpeg将视频转换为MP4格式"""
    try:
        # 构建输出文件名
        if title:
            # 清理文件名中的非法字符
            safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
            safe_title = safe_title.replace('\n', ' ').strip()
            output_file = f"{safe_title}.mp4"
        else:
            output_file = f"video_{int(time.time())}.mp4"

        final_output = os.path.join(output_path, output_file)

        # 确保输出目录存在
        os.makedirs(output_path, exist_ok=True)

        # 构建FFmpeg命令
        cmd = ['ffmpeg', '-y']  # -y 覆盖输出文件

        if audio_file and audio_file.exists():
            # 有独立音频流
            print("使用独立音频流进行合并")
            cmd.extend([
                '-i', str(video_file),
                '-i', str(audio_file),
                '-c:v', 'libx264',  # 视频编码器
                '-c:a', 'aac',      # 音频编码器
                '-preset', 'fast',   # 编码速度
                '-crf', '23',        # 质量控制
                '-map', '0:v:0',     # 映射视频流
                '-map', '1:a:0',     # 映射音频流
                '-shortest',         # 以较短的流为准
            ])
        else:
            # 只有视频文件或视频包含音频
            print("处理包含音频的视频流或纯视频流")
            cmd.extend([
                '-i', str(video_file),
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-preset', 'fast',
                '-crf', '23',
            ])

        cmd.append(final_output)

        print(f"执行FFmpeg命令...")
        # 不显示完整命令以避免过长输出

        # 执行转换 - 修复编码问题
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=False,  # 使用二进制模式避免编码问题
            timeout=600,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0  # Windows下隐藏窗口
        )

        if result.returncode == 0:
            print(f"✅ 视频转换成功: {final_output}")

            # 检查输出文件大小
            if os.path.exists(final_output):
                file_size = os.path.getsize(final_output) / (1024 * 1024)  # MB
                print(f"输出文件大小: {file_size:.2f} MB")

            return True
        else:
            print(f"❌ FFmpeg转换失败:")
            # 安全地解码错误输出
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


def download_m3u8_video(url: str, output_path: str, title: str = None, max_quality: bool = True) -> bool:
    """
    下载m3u8格式视频并自动合并音视频流

    Args:
        url (str): m3u8视频链接
        output_path (str): 输出文件路径
        title (str): 视频标题，用于文件命名
        max_quality (bool): 是否选择最高画质，默认True

    Returns:
        bool: 下载是否成功
    """
    try:
        print(f"开始下载视频: {title or 'Unknown'}")
        print(f"M3U8 URL: {url}")

        # 检查必要的工具
        if not check_ffmpeg():
            print("❌ FFmpeg未安装或不在PATH中，无法合并视频")
            return False

        # 创建临时工作目录
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 1. 解析m3u8文件
            print("步骤1: 解析M3U8文件...")
            playlist = parse_m3u8(url)
            if not playlist:
                return False

            # 2. 选择最优质量的视频流
            print("步骤2: 选择视频流...")
            best_stream = select_best_stream(playlist, max_quality)
            if not best_stream:
                print("❌ 未找到可用的视频流")
                return False

            print(f"选择的流: 分辨率={best_stream.get('resolution', 'Unknown')}, 带宽={best_stream.get('bandwidth', 'Unknown')}")

            # 3. 下载视频流
            print("步骤3: 下载视频流...")
            video_file = temp_path / "video.ts"

            if best_stream.get('is_direct'):
                # 直接从原始URL下载
                if not download_segments(url, video_file):
                    return False
            else:
                # 从指定的流URI下载
                if not download_segments(best_stream['uri'], video_file):
                    return False

            # 4. 查找并下载音频流
            print("步骤4: 查找音频流...")
            audio_file = None

            # 方法1：从媒体流中查找音频
            if playlist.media:
                for media in playlist.media:
                    if media.type and media.type.upper() == 'AUDIO':
                        print(f"发现音频流: {media.uri}")
                        audio_file = temp_path / "audio.ts"
                        audio_uri = media.uri
                        if not audio_uri.startswith('http'):
                            audio_uri = playlist.base_uri + audio_uri

                        if download_segments(audio_uri, audio_file):
                            print("✅ 音频流下载成功")
                            break
                        else:
                            print("⚠️ 音频流下载失败")
                            audio_file = None

            # 方法2：从播放列表中查找音频流
            if not audio_file and playlist.playlists:
                for p in playlist.playlists:
                    if p.stream_info and hasattr(p.stream_info, 'audio') and p.stream_info.audio:
                        print(f"从播放列表中找到音频引用: {p.stream_info.audio}")
                        # 尝试在媒体流中找到对应的音频
                        for media in playlist.media or []:
                            if media.group_id == p.stream_info.audio:
                                print(f"找到对应音频流: {media.uri}")
                                audio_file = temp_path / "audio.ts"
                                audio_uri = media.uri
                                if not audio_uri.startswith('http'):
                                    audio_uri = playlist.base_uri + audio_uri

                                if download_segments(audio_uri, audio_file):
                                    print("✅ 音频流下载成功")
                                    break
                                else:
                                    print("⚠️ 音频流下载失败")
                                    audio_file = None
                        if audio_file:
                            break

            if not audio_file:
                print("⚠️ 未找到独立音频流，视频可能已包含音频")

            # 5. 使用FFmpeg合并/转换为MP4
            print("步骤5: 转换为MP4格式...")
            success = convert_to_mp4(video_file, audio_file, output_path, title)

            if success:
                print(f"✅ 视频下载完成: {output_path}")
                return True
            else:
                print("❌ 视频转换失败")
                return False

    except Exception as e:
        print(f"❌ 下载过程中发生错误: {e}")
        return False


def download_videos_from_extracted_data(json_file: str = "extracted_items.json",
                                       output_dir: str = "downloads",
                                       max_concurrent: int = 2) -> None:
    """
    从提取的数据中批量下载视频

    Args:
        json_file (str): 包含视频信息的JSON文件
        output_dir (str): 下载目录
        max_concurrent (int): 最大并发下载数
    """
    try:
        # 读取提取的数据
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not data:
            print("❌ 没有找到视频数据")
            return

        print(f"准备下载 {len(data)} 个视频到 {output_dir} 目录")

        # 创建下载目录
        os.makedirs(output_dir, exist_ok=True)

        # 统计信息
        success_count = 0
        failed_count = 0

        # 逐个下载（可以根据需要改为并发）
        for i, item in enumerate(data, 1):
            video_url = item.get('url', '')
            title = item.get('title', f"Video_{item.get('id', i)}")
            video_id = item.get('id', i)

            print(f"\n[{i}/{len(data)}] 下载视频: {title}")

            if not video_url:
                print(f"⚠️ 跳过 - 没有视频URL")
                failed_count += 1
                continue

            # 下载视频
            success = download_m3u8_video(video_url, output_dir, title)

            if success:
                success_count += 1
            else:
                failed_count += 1

            # 避免请求过于频繁
            time.sleep(2)

        print(f"\n📊 下载完成统计:")
        print(f"✅ 成功: {success_count}")
        print(f"❌ 失败: {failed_count}")
        print(f"📁 输出目录: {output_dir}")

    except Exception as e:
        print(f"❌ 批量下载过程中发生错误: {e}")


def complete_workflow(size: int = 50) -> List[Dict[str, Any]]:
    """
    完整工作流程：从API获取数据 -> 保存到本地 -> 提取指定字段 -> 保存提取结果

    Args:
        size (int): 每页返回的数据条数，默认为50

    Returns:
        List[Dict[str, Any]]: 提取的字段列表
    """
    print("=== 开始完整工作流程 ===")

    # 步骤1：从API获取数据
    print("\n步骤1: 从API获取数据...")
    api_data = fetch_posts_from_api(size, verify_ssl=False)  # 默认禁用SSL验证

    if not api_data:
        print("❌ 从API获取数据失败，工作流程中断")
        return []

    # 步骤2：显示API数据概览
    print("\n步骤2: 处理API数据...")
    process_posts_data(api_data)

    # 步骤3：提取指定字段
    print("\n步骤3: 提取指定字段 (id、url、title、description、cover)...")
    extracted_items = extract_items_data(api_data)

    if not extracted_items:
        print("❌ 提取字段失败")
        return []

    print(f"✅ 成功提取了 {len(extracted_items)} 条记录")

    # 步骤4：保存提取的数据
    print("\n步骤4: 保存提取的数据...")
    save_extracted_data(extracted_items)

    # 步骤5：显示提取结果预览
    print("\n步骤5: 显示提取结果预览...")
    print("前5条提取的记录:")
    for i, item in enumerate(extracted_items[:5], 1):
        print(f"\n记录 {i}:")
        print(f"  ID: {item['id']}")
        print(f"  标题: {item['title']}")  # 显示提取的标题
        print(f"  URL: {item['url'][:50]}..." if len(item['url']) > 50 else f"  URL: {item['url']}")
        print(f"  封面: {item['cover']}")
        print(f"  完整描述: {item['description'][:150]}..." if len(item['description']) > 150 else f"  完整描述: {item['description']}")

    print("\n=== 完整工作流程执行完成 ===")
    return extracted_items


if __name__ == "__main__":
    # 选择执行模式
    print("请选择执行模式:")
    print("1. 完整工作流程 (API获取 -> 提取字段 -> 保存)")
    print("2. 仅从本地JSON文件提取字段")
    print("3. 仅从API获取数据")
    print("4. 下载单个m3u8视频")
    print("5. 批量下载视频 (从extracted_items.json)")

    mode = input("请输入选择 (1/2/3/4/5, 默认为1): ").strip() or "1"

    if mode == "1":
        # 完整工作流程
        size = input("请输入每页数据条数 (默认50): ").strip()
        size = int(size) if size.isdigit() else 50

        extracted_items = complete_workflow(size)

        if extracted_items:
            print(f"\n🎉 工作流程成功完成！共处理了 {len(extracted_items)} 条记录")

            # 询问是否下载视频
            download_choice = input("\n是否立即下载视频? (y/n, 默认n): ").strip().lower()
            if download_choice == 'y':
                output_dir = input("请输入下载目录 (默认downloads): ").strip() or "downloads"
                download_videos_from_extracted_data("extracted_items.json", output_dir)
        else:
            print("\n❌ 工作流程执行失败")

    elif mode == "2":
        # 仅从本地JSON文件提取字段
        print("\n=== 从JSON文件中提取数据 ===")

        json_file_path = input("请输入JSON文件路径 (默认example.json): ").strip() or "example.json"
        json_data = read_json_file(json_file_path)

        if json_data:
            extracted_items = extract_items_data(json_data)

            if extracted_items:
                print(f"成功提取了 {len(extracted_items)} 条记录")
                save_extracted_data(extracted_items)

                # 显示前5条记录作为示例
                print("\n前5条提取的记录:")
                for i, item in enumerate(extracted_items[:5], 1):
                    print(f"\n记录 {i}:")
                    print(f"  ID: {item['id']}")
                    print(f"  标题: {item['title']}")
                    print(f"  URL: {item['url'][:50]}..." if len(item['url']) > 50 else f"  URL: {item['url']}")
                    print(f"  封面: {item['cover']}")
                    print(f"  完整描述: {item['description'][:150]}..." if len(item['description']) > 150 else f"  完整描述: {item['description']}")

                # 询问是否下载视频
                download_choice = input("\n是否下载视频? (y/n, 默认n): ").strip().lower()
                if download_choice == 'y':
                    output_dir = input("请输入下载目录 (默认downloads): ").strip() or "downloads"
                    download_videos_from_extracted_data("extracted_items.json", output_dir)
            else:
                print("没有提取到任何数据")
        else:
            print("无法读取JSON文件")

    elif mode == "3":
        # 仅从API获取数据
        print("\n=== 从API获取数据 ===")

        size = input("请输入每页数据条数 (默认50): ").strip()
        size = int(size) if size.isdigit() else 50

        # 询问是否启用SSL验证
        ssl_choice = input("是否启用SSL证书验证? (y/n, 默认n): ").strip().lower()
        verify_ssl = ssl_choice == 'y'

        api_data = fetch_posts_from_api(size, verify_ssl=verify_ssl)

        if api_data:
            process_posts_data(api_data)
            print("✅ API数据获取完成")
        else:
            print("❌ API数据获取失败")

    elif mode == "4":
        # 下载单个m3u8视频
        print("\n=== 下载单个m3u8视频 ===")

        video_url = input("请输入m3u8视频URL: ").strip()
        if not video_url:
            print("❌ 未提供视频URL")
        else:
            title = input("请输入视频标题 (可选): ").strip()
            output_dir = input("请输入下载目录 (默认downloads): ").strip() or "downloads"

            quality_choice = input("选择画质 (1=最高画质, 2=最低画质, 默认1): ").strip()
            max_quality = quality_choice != "2"

            success = download_m3u8_video(video_url, output_dir, title, max_quality)

            if success:
                print("✅ 视频下载成功！")
            else:
                print("❌ 视频下载失败")

    elif mode == "5":
        # 批量下载视频
        print("\n=== 批量下载视频 ===")

        json_file = input("请输入JSON文件路径 (默认extracted_items.json): ").strip() or "extracted_items.json"
        output_dir = input("请输入下载目录 (默认downloads): ").strip() or "downloads"

        # 检查文件是否存在
        if not os.path.exists(json_file):
            print(f"❌ 文件 {json_file} 不存在")
        else:
            download_videos_from_extracted_data(json_file, output_dir)

    else:
        print("❌ 无效的选择，程序退出")
