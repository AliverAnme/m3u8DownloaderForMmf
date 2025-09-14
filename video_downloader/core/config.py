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

    # FFmpeg 参数配置 - 改为字典格式
    FFMPEG_PARAMS = {
        'video_codec': 'libx264',
        'audio_codec': 'aac',
        'preset': 'fast',
        'crf': '23'
    }

    # 数据库配置
    DATABASE_FILE = "video_downloader.db"

    # 定时任务配置
    SCHEDULER_CONFIG = {
        'fetch_interval_minutes': 120,  # 2小时获取一次新数据
        'upload_interval_minutes': 60,  # 1小时检查一次上传
        'cleanup_time': "03:00",        # 凌晨3点清理
        'auto_start': False,            # 默认不自动启动调度器
        'log_file': "scheduler.log"
    }

    # 云存储配置
    CLOUD_CONFIG_FILE = "cloud_config.json"
    CLOUD_UPLOAD_ENABLED = False  # 默认关闭云存储
    CLOUD_AUTO_UPLOAD = False     # 默认不自动上传

    # 服务器部署配置
    SERVER_MODE = False  # 服务器模式，无交互界面
    DAEMON_MODE = False  # 守护进程模式
    PID_FILE = "video_downloader.pid"
    LOG_FILE = "video_downloader.log"
    LOG_LEVEL = "INFO"
    LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5

    # 请求头
    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Cache-Control': 'no-cache'
    }

    # 安全配置
    ENABLE_SSL_VERIFY = False
    MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024  # 5GB 最大文件大小

    # 重复检测配置
    DUPLICATE_CHECK_ENABLED = True
    DUPLICATE_CHECK_FIELDS = ['id', 'title', 'url']

    # 代理配置
    PROXY_ENABLED = False
    PROXY_URL = "http://127.0.0.1:1080"

    # 其他配置
    MAX_CONCURRENT_DOWNLOADS = 3
    RETRY_DELAY = 5  # 重试间隔秒数
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
                'filename': 'app.log',
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
