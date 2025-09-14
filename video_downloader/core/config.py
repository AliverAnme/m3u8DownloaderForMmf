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

    # 数据库配置
    DATABASE_FILE = "video_downloader.db"

    # 定时任务配置
    SCHEDULER_CONFIG = {
        'fetch_interval_minutes': 120,  # 2小时获取一次新数据
        'upload_interval_minutes': 60,  # 1小时检查一次上传
        'cleanup_time': "03:00",        # 凌晨3点清理
        'auto_start': True,             # 自动启动调度器
        'log_file': "scheduler.log"
    }

    # 云存储配置
    CLOUD_CONFIG_FILE = "cloud_config.json"
    CLOUD_UPLOAD_ENABLED = True
    CLOUD_AUTO_UPLOAD = True  # 下载完成后自动上传

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
        'Upgrade-Insecure-Requests': '1'
    }

    # FFmpeg配置
    FFMPEG_PARAMS = {
        'preset': 'fast',
        'crf': '23',
        'video_codec': 'libx264',
        'audio_codec': 'aac'
    }
