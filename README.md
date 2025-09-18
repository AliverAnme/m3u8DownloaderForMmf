# 增强版视频下载器 v2.0

一个功能完整的 m3u8 视频下载工具，支持定时运行、数据库管理、重复检测和网盘推送功能。瞎写的请不必在意readme，使用poetry导入包之后运行即可，虽然有个包缺失的报错（video—download那个），要求有ffmpeg

## 🚀 新增功能
- 定时自动下载新视频
- 本地数据库管理视频信息
- 自动检测并跳过重复下载
- 支持多种网盘（WebDAV/腾讯微云等）自动上传
- 服务器/守护进程模式，适合无人值守部署
- 系统状态与日志监控工具

## 🏁 快速开始

1. 克隆项目并进入目录
2. 安装依赖（推荐使用 Poetry）
   - 项目依赖管理文件：`pyproject.toml`、`poetry.lock`
3. 配置云存储（可选）
4. 运行主程序或管理工具

详细步骤见下方“安装部署”与“使用方法”。

## 📦 安装部署

### 自动部署

**Linux/Mac:**
```bash
chmod +x deploy.sh
./deploy.sh
```

**Windows:**
```cmd
deploy.bat
```

### 手动安装

1. **安装依赖**
```bash
# 使用Poetry (推荐)
poetry install

# 或使用pip
pip install -r requirements.txt  # 如无 requirements.txt，可参考 pyproject.toml
pip install requests m3u8 moviepy pillow schedule python-daemon
```

2. **创建必要目录**
```bash
mkdir downloads logs data
```

3. **配置云存储** (可选)
编辑 `cloud_config.json` 文件配置网盘信息

## 🎮 使用方法

### 交互模式
```bash
python video_downloader/core/main.py
```
或
```bash
python cli_main.py
```

### 增强模式/服务器模式
```bash
python video_downloader/core/enhanced_app.py --server
```
或
```bash
python enhanced_main.py --server
```

# 前台运行
python enhanced_main.py --server

# 后台运行（Linux/Unix）
python enhanced_main.py --server --daemon

# 自定义配置
python enhanced_main.py --server --interval 60 --log-level DEBUG
```

### 命令行参数
- `--server`: 服务器模式（无交互界面）
- `--daemon`: 守护进程模式（仅限Linux/Unix）
- `--config`: 指定数据库文件路径
- `--log-level`: 设置日志级别（DEBUG/INFO/WARNING/ERROR）
- `--interval`: 设置获取新视频的间隔时间（分钟）

## 🔧 管理工具

使用 `video_downloader/database/manager.py` 或 `manager.py` 进行系统管理：

```bash
# 查看系统状态
python manager.py status

# 查看最近日志
python manager.py logs

# 列出所有视频
python manager.py list

# 列出特定状态的视频
python manager.py list pending
python manager.py list completed

# 清理数据库
python manager.py cleanup

# 测试云存储连接
python manager.py test-cloud

# 导出数据
python manager.py export backup.json
```

## 📁 目录结构说明

- `video_downloader/`：主程序模块
  - `api/`：API客户端
  - `cloud/`：云存储模块
  - `core/`：核心应用逻辑（main.py、enhanced_app.py、cli_app.py、config.py）
  - `database/`：数据库管理（models.py、manager.py）
  - `download/`：下载管理器
  - `scheduler/`：定时任务调度
  - `security/`：安全相关
  - `ui/`：用户界面
  - `utils/`：工具函数
- `downloads/`：视频下载目录
- `logs/`：日志文件目录
- `data/`：数据库及临时数据
- `cli_main.py`：命令行入口
- `enhanced_main.py`：增强/服务器模式入口

## 📊 数据库结构

视频记录包含以下字段：
- `id`: 视频唯一标识
- `title`: 视频标题
- `url`: 视频下载链接
- `description`: 视频描述
- `cover`: 封面图片URL
- `file_path`: 本地文件路径
- `file_size`: 文件大小
- `download_status`: 下载状态（pending/downloading/completed/failed/uploaded）
- `download_time`: 下载完成时间
- `upload_time`: 上传完成时间
- `cloud_path`: 云存储路径
- `created_at`: 创建时间
- `updated_at`: 更新时间

## 🔄 定时任务

> 所有定时任务均可通过配置文件或命令行参数灵活调整。

系统默认包含以下定时任务：

1. **获取新视频**: 每2小时从API获取新视频数据
2. **上传已完成视频**: 每1小时检查并上传已下载的视频
3. **日常清理**: 每天凌晨3点清理失败的下载记录

可通过配置文件或命令行参数调整执行频率。

## 📝 日志与数据说明

- `logs/video_downloader.log`：主应用日志
- `logs/scheduler.log`：定时任务日志
- `data/video_downloader.db`：数据库文件
- `downloads/`：视频文件存储目录

## 🛠️ 故障排除

> 如遇问题，建议先查看日志文件并使用调试模式运行。

### 常见问题

1. **数据库锁定错误**
   - 确保只有一个程序实例在运行
   - 检查数据库文件权限

2. **网盘上传失败**
   - 检查网络连接
   - 验证WebDAV配置信息
   - 使用测试命令：`python manager.py test-cloud`

3. **视频下载失败**
   - 检查网络连接和代理设置
   - 确认视频URL有效性
   - 检查磁盘空间

4. **定时任务不执行**
   - 检查调度器是否启动
   - 查看调度器日志文件

### 调试模式
```bash
python enhanced_main.py --server --log-level DEBUG
```

## 📄 许可证

本项目采用 MIT 许可证，详见 [LICENSE](LICENSE)。

## 🤝 贡献指南

欢迎任何形式的贡献！请先阅读 [CONTRIBUTING.md]，提交 Issue 或 Pull Request 前请确保代码风格一致并通过基本测试。

## 📧 联系方式

- 作者: 冰冻芋头
- 邮箱: 请在 Issue 中留言

---

**免责声明**: 本工具仅供学习和交流，请勿用于非法用途。请遵守相关法律法规，仅下载您有权访问的内容。
