# 视频下载器

一个功能完整的m3u8视频下载工具。

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

## 功能模块说明

### 1. API模块 (`api/`)
- **APIClient**: 处理API数据获取、SSL验证、错误处理
- 负责从远程API获取视频信息并保存到本地

### 2. 核心模块 (`core/`)
- **Config**: 集中管理所有配置常量和参数
- **VideoDownloaderApp**: 主应用控制器，整合所有功能模块

### 3. 下载模块 (`download/`)
- **DownloadManager**: 处理m3u8视频下载、FFmpeg转换、封面下载

### 4. 工具模块 (`utils/`)
- **DataProcessor**: 数据提取、标题解析、JSON文件处理
- 负责数据格式转换和存储

### 5. 用户界面模块 (`ui/`)
- **UserInterface**: 交互式选择、输入解析、菜单显示

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

1. **完整工作流程**: API获取 → 数据提取 → 视频下载
2. **交互式选择**: 支持单个、多个、范围选择视频
3. **批量下载**: 支持所有视频的批量下载
4. **单个下载**: 支持指定URL的单个视频下载
5. **数据处理**: 自动提取标题、处理封面图片
6. **格式转换**: 自动合并音视频流，输出MP4格式

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
