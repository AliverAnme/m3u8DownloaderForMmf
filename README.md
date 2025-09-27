<h1 align="center">Video Downloader</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/Code%20Style-Black-black.svg" alt="Code Style: Black">
</p>

<p align="center">
  一个功能强大的命令行视频下载工具，专为 m3u8 视频流设计。支持 API 抓取、定时任务、数据库管理、重复内容检测和云存储同步。
</p>

---

## ✨ 功能特性

- **多源获取**: 从 Web API、本地 JSON 文件中解析视频源。
- **强大的下载器**:
  - 使用`ffmpeg` 合并 m3u8 视频流。
  - 支持多线程并行下载，提升下载速度。
  - 自动处理音视频分离与合并。
  - 内置下载失败自动重试机制。
- **数据库管理**:
  - 使用 SQLite 持久化存储视频元数据。
  - 智能检测重复内容，避免重复下载。
- **定时任务**:
  - 内置灵活的调度器，可定时自动抓取和下载新视频。
- **云同步**:
  - 支持将下载完成的视频自动上传到指定的云存储服务（坚果云 WebDAV）。
- **灵活配置**:
  - 所有核心参数（如 API 地址、下载路径、并发数、定时任务频率等）均可通过 `config.py` 文件进行配置。
- **健壮的数据解析**:
  - 内置增强型解析器，能够处理非标准或格式略有错误的 JSON 数据，最大限度地提取有效信息。
- **交互式命令行**:
  - 提供一个清晰、易用的菜单驱动命令行界面（CLI），方便用户执行各种操作。

## 📦 安装指南

### 1. 环境准备

- **Python**: 确保您的系统已安装 Python 3.8 或更高版本。
- **FFmpeg**: 本工具依赖 `ffmpeg` 进行视频流的下载和合并。请确保 `ffmpeg` 已安装并在系统的 `PATH` 环境变量中。

### 2. 安装步骤

1.  **克隆项目**
    ```bash
    git clone <your-repository-url>
    cd video-downloader
    ```

2.  **安装依赖 (推荐使用 Poetry)**
    项目使用 [Poetry](https://python-poetry.org/) 进行依赖管理。
    ```bash
    poetry install
    ```
    或者，如果您想使用 `pip`，可以先从 `pyproject.toml` 导出 `requirements.txt` 文件：
    ```bash
    poetry export -f requirements.txt --output requirements.txt
    pip install -r requirements.txt
    ```

3.  **配置 (可选)**
    - **云存储**: 如果需要使用云同步功能，请在 `video_downloader/data/` 目录下创建 `cloud_config.json` 文件，并填入您的云存储配置。
    - **核心配置**: 您可以根据需要调整 `video_downloader/core/config.py` 文件中的参数。

## 🚀 快速开始

直接运行 `cli_main.py` 即可启动交互式命令行程序。

```bash
python cli_main.py
```

程序启动后，您会看到一个功能菜单，可以根据提示选择操作：

1.  **从 API 解析**: 抓取最新的视频信息并存入数据库。
2.  **下载视频**: 进入下载菜单，选择并下载数据库中尚未下载的视频。
3.  **查看数据库**: 浏览所有已记录的视频信息。
4.  **启动定时任务**: 启动内置的调度器，让程序在后台自动运行。
5.  **云端上传**: 将本地已下载的视频同步到云存储。

## 📁 项目结构

```
cli_main.py              # 命令行应用主入口
pyproject.toml           # 项目依赖和配置 (Poetry)
video_downloader/
├── api/                 # API 客户端模块
├── cloud/               # 云存储同步模块
├── core/                # 核心应用逻辑 (CLI App, 配置)
├── database/            # 数据库模型与管理
├── download/            # 下载管理器
├── scheduler/           # 定时任务调度器
├── ui/                  # 命令行用户界面
└── utils/               # 工具函数 (如增强型JSON解析器)
downloads/               # 默认视频下载目录
data/                    # 数据文件目录 (数据库、配置文件等)
```

## ⚙️ 配置

项目的主要配置项位于 `video_downloader/core/config.py` 文件中。您可以在此文件中修改：
- API 的 URL 和参数。
- 下载目录、日志目录等文件路径。
- 并行下载数量、重试次数等下载参数。
- 定时任务的执行频率。
- 云存储功能的开关。

## 🗃️ 数据库模型

项目的核心数据模型为 `VideoRecord`，定义在 `video_downloader/database/models.py` 中，包含以下主要字段：

| 字段          | 类型     | 描述                                         |
|---------------|----------|----------------------------------------------|
| `title`       | `str`    | 清洗后的视频标题                             |
| `video_date`  | `str`    | 从标题中提取的视频日期（通常是年份）         |
| `cover`       | `str`    | 封面图片的 URL                               |
| `url`         | `str`    | m3u8 视频流的 URL                            |
| `description` | `str`    | API 返回的原始描述信息                       |
| `uid`         | `str`    | 视频的唯一标识符 (UID)                       |
| `download`    | `bool`   | 下载状态 (`True` 表示已下载)                 |
| `is_primer`   | `bool`   | 是否为付费内容的标记                         |

## 🤝 贡献指南

欢迎对本项目做出贡献！如果您有任何改进建议或功能需求，请随时提交 Issue 或 Pull Request。

1.  Fork 本仓库。
2.  创建您的特性分支 (`git checkout -b feature/AmazingFeature`)。
3.  提交您的更改 (`git commit -m 'Add some AmazingFeature'`)。
4.  将您的分支推送到远程仓库 (`git push origin feature/AmazingFeature`)。
5.  创建一个新的 Pull Request。

## 📄 许可证

本项目采用 MIT 许可证。详情请参阅 [LICENSE](LICENSE) 文件。

## 联系方式

📮邮箱：m3u8DownloaderForMmf@hotmail.com

---

**免责声明**: 本工具仅供学习和技术交流，请勿用于任何非法用途。使用者应自行承担因使用本工具而产生的所有风险和责任。请尊重版权，仅下载您有权访问的内容。
