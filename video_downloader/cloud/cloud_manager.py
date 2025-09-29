"""
云存储管理器
处理视频文件上传到各种云存储服务
"""

import os
import json
from typing import Dict, Any, List
from ..core.config import Config
from .jianguoyun_client import JianguoyunClient


class CloudStorageManager:
    """云存储管理器"""

    def __init__(self):
        self.config = Config()
        self.jianguoyun_client = None
        self._load_cloud_config()

    def _load_cloud_config(self):
        """加载云存储配置"""
        try:
            if os.path.exists(self.config.CLOUD_CONFIG_FILE):
                with open(self.config.CLOUD_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    cloud_config = json.load(f)

                # 更新坚果云配置
                jianguoyun_config = cloud_config.get('jianguoyun', {})
                if jianguoyun_config.get('enabled', False):
                    username = jianguoyun_config.get('username', '')
                    password = jianguoyun_config.get('password', '')
                    if username and password:
                        self.jianguoyun_client = JianguoyunClient(username, password)
                        print("✅ 坚果云客户端初始化成功")
                    else:
                        print("❌ 坚果云配置不完整")
        except Exception as e:
            print(f"❌ 加载云存储配置失败: {e}")

    def setup_jianguoyun(self, username: str, password: str) -> bool:
        """
        设置坚果云WebDAV连接

        Args:
            username: 坚果云用户名（邮箱）
            password: 坚果云应用密码

        Returns:
            bool: 设置是否成功
        """
        try:
            self.jianguoyun_client = JianguoyunClient(username, password)

            # 测试连接
            test_result = self.jianguoyun_client.create_directory('test_connection')
            if test_result:
                # 保存配置
                self._save_jianguoyun_config(username, password, True)
                print("✅ 坚果云连接设置成功")
                return True
            else:
                print("❌ 坚果云连接测试失败")
                return False

        except Exception as e:
            print(f"❌ 设置坚果云连接失败: {e}")
            return False

    def _save_jianguoyun_config(self, username: str, password: str, enabled: bool):
        """保存坚果云配置"""
        try:
            cloud_config = {}
            if os.path.exists(self.config.CLOUD_CONFIG_FILE):
                with open(self.config.CLOUD_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    cloud_config = json.load(f)

            cloud_config['jianguoyun'] = {
                'enabled': enabled,
                'username': username,
                'password': password,
                'base_url': 'https://dav.jianguoyun.com/dav/',
                'remote_dir': '/视频备份/'
            }

            os.makedirs(os.path.dirname(self.config.CLOUD_CONFIG_FILE), exist_ok=True)
            with open(self.config.CLOUD_CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(cloud_config, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"❌ 保存坚果云配置失败: {e}")

    def upload_video_to_jianguoyun(self, local_file_path: str,
                                  remote_subdir: str = '') -> bool:
        """
        上传视频文件到坚果云

        Args:
            local_file_path: 本地视频文件路径
            remote_subdir: 远程子目录（可选）

        Returns:
            bool: 上传是否成功
        """
        if not self.jianguoyun_client:
            print("❌ 坚果云客户端未初始化")
            return False

        if not os.path.exists(local_file_path):
            print(f"❌ 本地文件不存在: {local_file_path}")
            return False

        try:
            # 获取文件信息
            file_name = os.path.basename(local_file_path)
            file_size_mb = os.path.getsize(local_file_path) / 1024 / 1024

            # 检查文件大小限制
            max_size = self.config.JIANGUOYUN_CONFIG['max_file_size_mb']
            if file_size_mb > max_size:
                print(f"❌ 文件太大: {file_size_mb:.2f}MB > {max_size}MB")
                return False

            # 构建远程路径
            base_dir = self.config.JIANGUOYUN_CONFIG['remote_dir']
            if remote_subdir:
                remote_path = f"{base_dir.rstrip('/')}/{remote_subdir.strip('/')}/{file_name}"
            else:
                remote_path = f"{base_dir.rstrip('/')}/{file_name}"

            # 检查是否已存在
            if not self.config.JIANGUOYUN_CONFIG['overwrite_existing']:
                if self.jianguoyun_client.check_file_exists(remote_path):
                    print(f"⚠️ 远程文件已存在，跳过上传: {remote_path}")
                    return True

            # 上传文件
            success = self.jianguoyun_client.upload_file(local_file_path, remote_path)

            if success:
                print(f"✅ 视频上传成功: {file_name} -> {remote_path}")

                # 如果配置了上传后删除本地文件
                if self.config.JIANGUOYUN_CONFIG['delete_local_after_upload']:
                    try:
                        os.remove(local_file_path)
                        print(f"🗑️ 已删除本地文件: {local_file_path}")
                    except Exception as e:
                        print(f"⚠️ 删除本地文件失败: {e}")

                return True
            else:
                print(f"❌ 视频上传失败: {file_name}")
                return False

        except Exception as e:
            print(f"❌ 上传视频异常: {e}")
            return False

    def upload_videos_batch(self, video_files: List[str],
                           remote_subdir: str = '') -> Dict[str, bool]:
        """
        批量上传视频文件

        Args:
            video_files: 本地视频文件路径列表
            remote_subdir: 远程子目录（可选）

        Returns:
            dict: 上传结果字典 {文件路径: 是否成功}
        """
        results = {}
        total_files = len(video_files)

        print(f"🚀 开始批量上传 {total_files} 个视频文件...")

        for index, file_path in enumerate(video_files, 1):
            print(f"📍 上传进度: {index}/{total_files}")
            results[file_path] = self.upload_video_to_jianguoyun(file_path, remote_subdir)

        success_count = sum(1 for success in results.values() if success)
        print(f"🎉 批量上传完成: {success_count}/{total_files} 成功")

        return results

    def scan_and_upload_downloads(self, downloads_dir: str = None) -> Dict[str, bool]:
        """
        扫描下载目录并上传所有视频文件

        Args:
            downloads_dir: 下载目录路径，默认使用配置中的目录

        Returns:
            dict: 上传结果字典
        """
        if downloads_dir is None:
            downloads_dir = self.config.DEFAULT_DOWNLOADS_DIR

        if not os.path.exists(downloads_dir):
            print(f"❌ 下载目录不存在: {downloads_dir}")
            return {}

        # 扫描视频文件
        video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm']
        video_files = []

        for file_name in os.listdir(downloads_dir):
            file_path = os.path.join(downloads_dir, file_name)
            if os.path.isfile(file_path):
                _, ext = os.path.splitext(file_name)
                if ext.lower() in video_extensions:
                    video_files.append(file_path)

        if not video_files:
            print(f"📁 下载目录中没有找到视频文件: {downloads_dir}")
            return {}

        print(f"📹 找到 {len(video_files)} 个视频文件")
        return self.upload_videos_batch(video_files)

    def get_upload_status(self) -> Dict[str, Any]:
        """
        获取上传状态信息

        Returns:
            dict: 状态信息
        """
        status = {
            'jianguoyun_enabled': self.jianguoyun_client is not None,
            'config_loaded': os.path.exists(self.config.CLOUD_CONFIG_FILE)
        }

        if self.jianguoyun_client:
            # 可以添加更多状态检查
            status['jianguoyun_connected'] = True

        return status

    def disable_jianguoyun(self):
        """禁用坚果云上传功能"""
        self.jianguoyun_client = None
        self._save_jianguoyun_config('', '', False)
        print("❌ 坚果云上传功能已禁用")
