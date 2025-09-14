@echo off
REM 视频下载器Windows部署脚本

echo 🚀 开始部署增强版视频下载器...

REM 检查Python版本
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到Python，请先安装Python 3.8或更高版本
    pause
    exit /b 1
)

echo ✅ Python检查通过

REM 安装依赖
echo 📦 安装依赖包...
pip install requests m3u8 moviepy pillow schedule python-daemon

REM 创建必要的目录
echo 📁 创建必要目录...
if not exist "downloads" mkdir downloads
if not exist "logs" mkdir logs

REM 创建默认云存储配置
echo ☁️ 创建默认云存储配置...
echo {> cloud_config.json
echo   "webdav": {>> cloud_config.json
echo     "enabled": false,>> cloud_config.json
echo     "base_url": "https://dav.jianguoyun.com/dav/",>> cloud_config.json
echo     "username": "your_username",>> cloud_config.json
echo     "password": "your_password",>> cloud_config.json
echo     "upload_path": "video_downloads">> cloud_config.json
echo   }>> cloud_config.json
echo }>> cloud_config.json

echo ✅ 默认云存储配置已创建: cloud_config.json

REM 创建Windows服务安装脚本
echo 🔧 创建Windows服务脚本...
echo @echo off > install_service.bat
echo REM 安装Windows服务需要管理员权限 >> install_service.bat
echo sc create VideoDownloader binPath= "%CD%\enhanced_main.py --server" start= auto >> install_service.bat
echo sc description VideoDownloader "Enhanced Video Downloader Service" >> install_service.bat
echo echo 服务已创建，使用以下命令管理: >> install_service.bat
echo echo   启动: sc start VideoDownloader >> install_service.bat
echo echo   停止: sc stop VideoDownloader >> install_service.bat
echo echo   删除: sc delete VideoDownloader >> install_service.bat

echo @echo off > uninstall_service.bat
echo sc stop VideoDownloader >> uninstall_service.bat
echo sc delete VideoDownloader >> uninstall_service.bat
echo echo 服务已删除 >> uninstall_service.bat

echo.
echo 🎉 部署完成！
echo.
echo 📖 使用方法:
echo    交互模式: python enhanced_main.py
echo    服务器模式: python enhanced_main.py --server
echo.
echo ⚙️ 配置文件:
echo    云存储配置: cloud_config.json
echo    数据库文件: video_downloader.db (自动创建)
echo.
echo 📝 日志文件:
echo    应用日志: video_downloader.log
echo    调度器日志: scheduler.log
echo.
echo 🔧 Windows服务:
echo    安装服务: 以管理员身份运行 install_service.bat
echo    卸载服务: 以管理员身份运行 uninstall_service.bat
echo.
pause
