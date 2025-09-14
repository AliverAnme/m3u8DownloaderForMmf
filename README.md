# 增强版视频下载器 v2.0

一个功能完整的m3u8视频下载工具，支持定时运行、数据库管理、重复检测和网盘推送功能。

## 🚀 新增功能

### ✨ 主要特性
- **定时运行**: 支持定时获取新视频和自动下载
- **数据库管理**: 本地SQLite数据库存储视频信息
- **重复检测**: 自动检测并跳过已下载的视频
- **网盘推送**: 支持WebDAV协议的网盘服务（坚果云、NextCloud等）
- **服务器部署**: 支持无人值守的服务器模式运行
- **守护进程**: Linux/Unix系统支持守护进程模式

### 🎯 核心功能
- API数据获取和处理
- 视频列表展示和选择
- m3u8视频下载和转换
- 交互式用户界面
- 云存储自动上传
- 系统状态监控

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
pip install requests m3u8 moviepy pillow schedule python-daemon
```

2. **创建必要目录**
```bash
mkdir -p downloads logs
```

3. **配置云存储** (可选)
编辑 `cloud_config.json` 文件配置网盘信息

## 🎮 使用方法

### 交互模式
```bash
python enhanced_main.py
```

### 服务器模式
```bash
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

使用 `manager.py` 进行系统管理：

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

## ⚙️ 配置文件

### 云存储配置 (cloud_config.json)
```json
{
  "webdav": {
    "enabled": true,
    "base_url": "https://dav.jianguoyun.com/dav/",
    "username": "your_username",
    "password": "your_password",
    "upload_path": "video_downloads"
  }
}
```

### 支持的网盘服务
- 坚果云 (JianGuoYun)
- NextCloud
- ownCloud
- **腾讯微云 (Tencent WeiYun)** - 新增支持
- 其他支持WebDAV的服务

## 🎯 腾讯微云配置

### 快速配置腾讯微云
```bash
# 运行腾讯微云配置工具
python setup_weiyun.py
```

### 手动配置腾讯微云
编辑 `cloud_config.json` 文件：
```json
{
  "weiyun": {
    "enabled": true,
    "username": "your_phone_or_email",
    "password": "your_password",
    "upload_path": "video_downloads",
    "description": "腾讯微云 - 使用腾讯微云账号和密码"
  }
}
```

### 腾讯微云使用说明
1. **账号要求**: 
   - 支持手机号或邮箱登录
   - 建议开通腾讯微云会员以获得更好的WebDAV支持
   - 可以使用应用专用密码提高安全性

2. **上传特性**:
   - 自动按年月分类存储 (如: video_downloads/2024/12/)
   - 支持大文件上传 (最大5GB)
   - 自动重试和错误恢复
   - 详细的上传进度显示

3. **安全保障**:
   - 密码加密存储
   - 安全路径验证
   - 文件大小检查
   - 网络超时保护
```

## 🏗️ 系统架构

```
video_downloader/
├── api/           # API客户端
├── cloud/         # 云存储模块
├── core/          # 核心应用逻辑
├── database/      # 数据库管理
├── download/      # 下载管理器
├── scheduler/     # 定时任务调度
├── ui/            # 用户界面
└── utils/         # 工具函数
```

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

系统默认包含以下定时任务：

1. **获取新视频**: 每2小时从API获取新视频数据
2. **上传已完成视频**: 每1小时检查并上传已下载的视频
3. **日常清理**: 每天凌晨3点清理失败的下载记录

可通过配置文件或命令行参数调整执行频率。

## 🐧 Linux系统服务

### 安装系统服务
```bash
# 复制服务文件
sudo cp video-downloader.service /etc/systemd/system/

# 启用并启动服务
sudo systemctl enable video-downloader
sudo systemctl start video-downloader

# 查看服务状态
sudo systemctl status video-downloader

# 查看服务日志
sudo journalctl -u video-downloader -f
```

### 服务管理命令
```bash
sudo systemctl start video-downloader    # 启动服务
sudo systemctl stop video-downloader     # 停止服务
sudo systemctl restart video-downloader  # 重启服务
sudo systemctl reload video-downloader   # 重载配置
```

## 🪟 Windows系统服务

### 安装Windows服务
```cmd
# 以管理员身份运行
install_service.bat
```

### 服务管理
```cmd
sc start VideoDownloader     # 启动服务
sc stop VideoDownloader      # 停止服务
sc delete VideoDownloader    # 删除服务
```

## 📝 日志文件

- `video_downloader.log`: 主应用日志
- `scheduler.log`: 定时任务日志
- `video_downloader.pid`: 进程ID文件（服务器模式）

## 🔍 监控和维护

### 系统状态检查
```bash
python manager.py status
```

### 日志监控
```bash
# 实时查看日志
tail -f video_downloader.log

# 查看最近100行日志
python manager.py logs 100
```

### 数据库维护
```bash
# 清理失败记录
python manager.py cleanup

# 导出数据备份
python manager.py export backup_$(date +%Y%m%d).json
```

## 🛠️ 故障排除

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

本项目采用MIT许可证 - 详见 [LICENSE](LICENSE) 文件

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目。

## 📧 联系方式

- 作者: 冰冻芋头

---

**注意**: 请遵守相关法律法规，仅下载您有权访问的内容。
