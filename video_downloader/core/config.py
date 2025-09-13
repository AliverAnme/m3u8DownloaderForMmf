
class Config:
    """配置常量"""
    # API配置
    API_BASE_URL = "https://api.memefans.ai/v2/posts/"
    DEFAULT_AUTHOR_ID = "BhhLJPlVvjU"
    DEFAULT_PAGE_SIZE = 50
    API_TIMEOUT = 30

    # 文件名配置
    API_RESPONSE_FILE = "api_response.json"
    EXTRACTED_ITEMS_FILE = "extracted_items.json"
    DEFAULT_DOWNLOADS_DIR = "downloads"

    # 下载配置
    MAX_RETRIES = 3
    MAX_WORKERS = 5
    DOWNLOAD_DELAY = 2  # 下载间隔秒数
    FFMPEG_TIMEOUT = 600

    # 请求头
    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    # FFmpeg配置
    FFMPEG_PARAMS = {
        'preset': 'fast',
        'crf': '23',
        'video_codec': 'libx264',
        'audio_codec': 'aac'
    }
