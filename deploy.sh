#!/bin/bash
# 视频下载器部署脚本

set -e

echo "🚀 开始部署增强版视频下载器..."

# 检查Python版本
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1-2)
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ 需要Python 3.8或更高版本，当前版本: $python_version"
    exit 1
fi

echo "✅ Python版本检查通过: $python_version"

# 安装依赖
echo "📦 安装依赖包..."
if command -v poetry &> /dev/null; then
    echo "使用Poetry安装依赖..."
    poetry install
else
    echo "使用pip安装依赖..."
    pip install requests m3u8 moviepy pillow schedule python-daemon
fi

# 创建必要的目录
echo "📁 创建必要目录..."
mkdir -p downloads
mkdir -p logs

# 创建systemd服务文件（Linux）
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "🔧 创建systemd服务文件..."

    cat > video-downloader.service << EOF
[Unit]
Description=Enhanced Video Downloader Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
ExecStart=$(which python3) enhanced_main.py --server
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    echo "📋 systemd服务文件已创建: video-downloader.service"
    echo "   安装命令: sudo cp video-downloader.service /etc/systemd/system/"
    echo "   启动命令: sudo systemctl enable video-downloader && sudo systemctl start video-downloader"
fi

# 创建默认云存储配置
echo "☁️ 创建默认云存储配置..."
cat > cloud_config.json << EOF
{
  "webdav": {
    "enabled": false,
    "base_url": "https://dav.jianguoyun.com/dav/",
    "username": "your_username",
    "password": "your_password",
    "upload_path": "video_downloads"
  }
}
EOF

echo "✅ 默认云存储配置已创建: cloud_config.json"
echo "   请编辑此文件以配置您的网盘信息"

# 设置权限
echo "🔐 设置执行权限..."
chmod +x enhanced_main.py

echo ""
echo "🎉 部署完成！"
echo ""
echo "📖 使用方法:"
echo "   交互模式: python3 enhanced_main.py"
echo "   服务器模式: python3 enhanced_main.py --server"
echo "   守护进程模式: python3 enhanced_main.py --server --daemon"
echo ""
echo "⚙️ 配置文件:"
echo "   云存储配置: cloud_config.json"
echo "   数据库文件: video_downloader.db (自动创建)"
echo ""
echo "📝 日志文件:"
echo "   应用日志: video_downloader.log"
echo "   调度器日志: scheduler.log"
echo ""
