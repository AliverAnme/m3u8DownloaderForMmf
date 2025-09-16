import os

class Config:
    """配置常量"""
    # API配置
    API_BASE_URL = "https://api.memefans.ai/v2/posts/"
    DEFAULT_AUTHOR_ID = "BhhLJPlVvjU"
    DEFAULT_PAGE_SIZE = 50
    API_TIMEOUT = 30

    # 请求头配置
    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    # 文件路径配置
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    LOGS_DIR = os.path.join(BASE_DIR, "logs")
    TEMP_DIR = os.path.join(BASE_DIR, "temp")
    
    # 文件名配置
    API_RESPONSE_FILE = os.path.join(DATA_DIR, "api_response.json")
    EXTRACTED_ITEMS_FILE = os.path.join(DATA_DIR, "extracted_items.json")
    DATABASE_FILE = os.path.join(DATA_DIR, "video_downloader.db")
    
    # 下载目录配置
    DEFAULT_DOWNLOADS_DIR = os.path.join(os.path.dirname(BASE_DIR), "downloads")

    # 下载配置
    MAX_RETRIES = 3
    MAX_WORKERS = 5
    MAX_CONCURRENT_DOWNLOADS = 4  # 并行下载片段数量
    DOWNLOAD_DELAY = 2  # 下载间隔秒数
    RETRY_DELAY = 1  # 重试延迟秒数
    FFMPEG_TIMEOUT = 600

    # FFmpeg 参数配置
    FFMPEG_PARAMS = {
        'video_codec': 'libx264',
        'audio_codec': 'aac',
        'preset': 'fast',
        'crf': '23'
    }

    # 音视频处理配置
    AUDIO_STREAM_DETECTION = True  # 启用音频流检测
    SEPARATE_AUDIO_DOWNLOAD = True  # 启用独立音频流下载
    AUTO_MERGE_AUDIO_VIDEO = True  # 自动合并音视频
    EMBED_COVER_IMAGE = True  # 嵌入封面图片
    PREFER_HIGHEST_QUALITY = True  # 优先选择最高质量流

    # 视频处理配置
    TEMP_DIR_PREFIX = "video_download_"
    COVER_FORMATS = ['.jpg', '.png', '.webp']
    OUTPUT_FORMAT = 'mp4'
    
    # 文件名模式配置
    FILENAME_PATTERNS = [
        "{title}_{video_date}.{ext}",
        "{title}.{ext}",
        "{video_date}_{title}.{ext}"
    ]

    # 定时任务配置
    SCHEDULER_CONFIG = {
        'fetch_interval_minutes': 120,
        'upload_interval_minutes': 60,
        'cleanup_time': "03:00",
        'auto_start': False,
        'log_file': os.path.join(LOGS_DIR, "scheduler.log")
    }

    # 云存储配置
    CLOUD_CONFIG_FILE = os.path.join(DATA_DIR, "cloud_config.json")
    CLOUD_UPLOAD_ENABLED = False
    CLOUD_AUTO_UPLOAD = False

    # 服务器部署配置
    SERVER_MODE = False
    DAEMON_MODE = False
    PID_FILE = os.path.join(DATA_DIR, "video_downloader.pid")
    LOG_FILE = os.path.join(LOGS_DIR, "video_downloader.log")
    LOG_LEVEL = "INFO"
    LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5

    # 安全配置
    ENABLE_SSL_VERIFY = False
    MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024  # 5GB 最大文件大小

    # 重复检测配置
    DUPLICATE_CHECK_ENABLED = True
    DUPLICATE_CHECK_FIELDS = ['id', 'title', 'url']

    # 代理配置
    PROXY_ENABLED = False
    PROXY_URL = "http://127.0.0.1:1080"

    def get_proxy_config(self):
        """获取代理配置"""
        if self.PROXY_ENABLED and self.PROXY_URL:
            return {
                'http': self.PROXY_URL,
                'https': self.PROXY_URL
            }
        return {}

    # 其他配置
    LOGGING_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '{levelname} {asctime} {module} {message}',
                'style': '{'
            },
            'simple': {
                'format': '{levelname} {message}',
                'style': '{'
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'verbose',
            },
            'file': {
                'class': 'logging.FileHandler',
                'filename': LOG_FILE,
                'formatter': 'verbose',
            },
        },
        'loggers': {
            '': {
                'handlers': ['console', 'file'],
                'level': 'DEBUG',
                'propagate': True
            },
        }
    }
