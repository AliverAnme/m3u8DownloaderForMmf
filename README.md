# 视频下载器

一个功能完整的 m3u8 视频下载工具，支持定时运行、数据库管理、重复检测和网盘推送功能。瞎写的请不必在意readme，使用poetry导入包之后运行即可，虽然有个包缺失的报错（video—download那个），要求有ffmpeg

## 🚀 功能
- 定时自动下载新视频
- 本地数据库管理视频信息
- 自动检测并跳过重复下载
- 支持网盘自动上传

## 🏁 快速开始

1. 克隆项目并进入目录
2. 安装依赖（推荐使用 Poetry）
   - 项目依赖管理文件：`pyproject.toml`、`poetry.lock`
3. 配置云存储（可选）
4. 运行主程序或管理工具

详细步骤见下方“安装部署”与“使用方法”。

## 📦 安装

### 手动安装

1. **安装依赖**
```bash
# 使用Poetry (推荐)
poetry install

# 或使用pip
pip install -r requirements.txt  # 如无 requirements.txt，可参考 pyproject.toml
```

2. **创建必要目录(并不必要其实)**
```bash
mkdir downloads logs data
```

3. **配置云存储** (可选)
编辑 `cloud_config.json` 文件配置网盘信息

## 🎮 使用方法

### 交互模式

```bash
python cli_main.py
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
- `cli_main.py`：命令行入口


## 📊 数据库结构

视频记录包含以下字段：
- `title`: 视频标题
- `url`: 视频下载链接
- `description`: 视频描述
- `cover`: 封面图片URL
- `created_at`: 创建时间
- `updated_at`: 更新时间

## 🔄 定时任务

> 所有定时任务均可通过配置文件灵活调整。

系统默认包含以下定时任务：

 **获取新视频**: 每5分钟从API获取新视频数据

可通过配置文件调整执行频率。

## 📝 数据说明

- `data/video_downloader.db`：数据库文件
- `downloads/`：视频文件存储目录

## 🛠️ 故障排除

> 如遇问题，自行修复。

### 常见问题
 **视频下载失败**
 看看官方服务器是不是抽风了就行

## 📄 许可证

本项目采用 MIT 许可证，详见 [LICENSE](LICENSE)。

## 🤝 贡献指南

欢迎任何形式的贡献！提交 Issue 前请确保代码风格一致并通过基本测试。

## 📧 联系方式

- 作者: 冰冻芋头
- 邮箱: 请在 Issue 中留言

---

**免责声明**: 本工具仅供学习和交流，请勿用于非法用途。请遵守相关法律法规，仅下载您有权访问的内容。
