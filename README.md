# 视频下载器

一个针对Mmf的m3u8视频下载工具。

## 项目结构

```
video_downloader/
├── __init__.py                 # 主模块初始化
├── api/                        # API相关功能
│   ├── __init__.py
│   └── client.py              # API客户端，处理数据获取
├── core/                       # 核心模块
│   ├── __init__.py
│   ├── config.py              # 配置管理
│   └── main.py                # 主应用程序控制器
├── download/                   # 下载功能
│   ├── __init__.py
│   └── manager.py             # 下载管理器，处理m3u8下载
├── utils/                      # 工具模块
│   ├── __init__.py
│   └── data_processor.py      # 数据处理和文件操作
└── ui/                         # 用户界面
    ├── __init__.py
    └── interface.py           # 交互式界面和选择处理
```

## 使用方法

### 快速开始
```bash
python main.py
```

### 模块化使用示例
```python
from video_downloader import VideoDownloaderApp

app = VideoDownloaderApp()
app.run()
```

### 单独使用模块
```python
from video_downloader.api import APIClient
from video_downloader.download import DownloadManager

# 使用API客户端
api_client = APIClient()
data = api_client.fetch_posts_from_api(size=10)

# 使用下载管理器
download_manager = DownloadManager()
success = download_manager.download_m3u8_video(url, output_dir, title)
```

## 主要功能

下载来自Mmf的视频

## 依赖项
使用poetry进行包管理
- requests
- m3u8
- urllib3
- pathlib
- concurrent.futures
- FFmpeg (外部依赖)

## 许可证

本项目采用MIT许可证。
