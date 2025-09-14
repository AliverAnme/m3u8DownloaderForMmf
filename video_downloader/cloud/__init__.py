"""
云存储模块 - 处理文件上传到各种网盘服务
"""

import os
import hashlib
import json
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime
import requests
import time
import base64
import getpass

from ..core.config import Config


class CloudStorageBase(ABC):
    """云存储基类"""

    @abstractmethod
    def upload_file(self, local_path: str, remote_path: str) -> Optional[str]:
        """上传文件到云存储"""
        pass

    @abstractmethod
    def delete_file(self, remote_path: str) -> bool:
        """删除云存储文件"""
        pass

    @abstractmethod
    def get_file_info(self, remote_path: str) -> Optional[Dict[str, Any]]:
        """获取文件信息"""
        pass


class TencentWeiYunStorage(CloudStorageBase):
    """腾讯微云存储实现"""

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.base_url = "https://webdav.weiyun.com"
        self.session = requests.Session()
        self.session.auth = (username, password)

        # 设置超时和重试策略
        self.session.timeout = 30
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # 腾讯微云特殊请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Cache-Control': 'no-cache'
        })

    def upload_file(self, local_path: str, remote_path: str) -> Optional[str]:
        """上传文件到腾讯微云"""
        try:
            if not os.path.exists(local_path):
                print(f"❌ 本地文件不存在: {local_path}")
                return None

            # 安全检查：验证文件大小
            file_size = os.path.getsize(local_path)
            if file_size > 5 * 1024 * 1024 * 1024:  # 5GB限制
                print(f"❌ 文件过大: {file_size / (1024*1024*1024):.2f}GB，超过5GB限制")
                return None

            # 腾讯微云路径处理
            remote_path = self._sanitize_weiyun_path(remote_path.lstrip('/'))
            url = f"{self.base_url}/{remote_path}"

            print(f"📤 开始上传到腾讯微云: {remote_path}")

            # 创建目录
            self._create_directories(os.path.dirname(remote_path))

            # 使用分块上传大文件
            with open(local_path, 'rb') as f:
                response = self.session.put(url, data=f, timeout=600)

            if response.status_code in [200, 201, 204]:
                print(f"✅ 文件上传成功: {remote_path}")
                return url
            else:
                print(f"❌ 文件上传失败: {response.status_code} - {response.text[:200]}")
                # 尝试获取更详细的错误信息
                if response.status_code == 401:
                    print("❌ 认证失败，请检查用户名和密码")
                elif response.status_code == 403:
                    print("❌ 权限不足，请检查账户权限")
                elif response.status_code == 507:
                    print("❌ 存储空间不足")
                return None

        except requests.exceptions.Timeout:
            print(f"❌ 上传超时，文件可能较大")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ 网络错误: {e}")
            return None
        except Exception as e:
            print(f"❌ 腾讯微云上传异常: {e}")
            return None

    def _sanitize_weiyun_path(self, path: str) -> str:
        """清理腾讯微云路径"""
        # 腾讯微云对路径有特殊要求
        import re
        # 移除危险字符
        path = re.sub(r'[<>:"|?*]', '_', path)
        path = re.sub(r'\.\./', '', path)  # 移除路径遍历
        path = path.replace('\\', '/')  # 统一路径分隔符

        # 腾讯微云路径不能以空格开头或结尾
        path_parts = path.split('/')
        path_parts = [part.strip() for part in path_parts if part.strip()]

        return '/'.join(path_parts)

    def _create_directories(self, dir_path: str):
        """递归创建目录"""
        if not dir_path:
            return

        try:
            dir_path = self._sanitize_weiyun_path(dir_path)
            url = f"{self.base_url}/{dir_path.lstrip('/')}"
            response = self.session.request('MKCOL', url, timeout=30)
            # 201表示创建成功，405表示已存在，403可能是权限问题
            if response.status_code not in [201, 405]:
                print(f"⚠️ 创建目录警告: {dir_path} - {response.status_code}")
        except Exception as e:
            print(f"⚠️ 创建目录异常: {e}")

    def delete_file(self, remote_path: str) -> bool:
        """删除腾讯微云文件"""
        try:
            remote_path = self._sanitize_weiyun_path(remote_path.lstrip('/'))
            url = f"{self.base_url}/{remote_path}"
            response = self.session.delete(url, timeout=30)
            return response.status_code in [200, 204]
        except Exception as e:
            print(f"❌ 删除文件异常: {e}")
            return False

    def get_file_info(self, remote_path: str) -> Optional[Dict[str, Any]]:
        """获取腾讯微云文件信息"""
        try:
            remote_path = self._sanitize_weiyun_path(remote_path.lstrip('/'))
            url = f"{self.base_url}/{remote_path}"

            # 使用PROPFIND获取文件属性
            response = self.session.request('PROPFIND', url, timeout=30)
            if response.status_code == 207:  # Multi-Status
                return {
                    'path': remote_path,
                    'url': url,
                    'exists': True,
                    'last_modified': response.headers.get('Last-Modified'),
                    'content_length': response.headers.get('Content-Length')
                }
            else:
                return None
        except Exception as e:
            print(f"❌ 获取文件信息异常: {e}")
            return None


class WebDAVStorage(CloudStorageBase):
    """WebDAV云存储实现（支持坚果云、NextCloud等）"""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.auth = (username, password)

        # 设置超时和重试策略
        self.session.timeout = 30
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def upload_file(self, local_path: str, remote_path: str) -> Optional[str]:
        """上传文件到WebDAV"""
        try:
            if not os.path.exists(local_path):
                print(f"❌ 本地文件不存在: {local_path}")
                return None

            # 安全检查：验证文件大小
            file_size = os.path.getsize(local_path)
            if file_size > 5 * 1024 * 1024 * 1024:  # 5GB限制
                print(f"❌ 文件过大: {file_size / (1024*1024*1024):.2f}GB，超过5GB限制")
                return None

            # 确保远程路径格式正确并进行安全检查
            remote_path = self._sanitize_path(remote_path.lstrip('/'))
            url = f"{self.base_url}/{remote_path}"

            # 创建目录
            self._create_directories(os.path.dirname(remote_path))

            # 分块上传大文件
            chunk_size = 8192
            with open(local_path, 'rb') as f:
                response = self.session.put(url, data=f, timeout=300)

            if response.status_code in [200, 201, 204]:
                print(f"✅ 文件上传成功: {remote_path}")
                return url
            else:
                print(f"❌ 文件上传失败: {response.status_code} - {response.text[:200]}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"❌ 网络错误: {e}")
            return None
        except Exception as e:
            print(f"❌ WebDAV上传异常: {e}")
            return None

    def _sanitize_path(self, path: str) -> str:
        """清理和验证路径，防止路径遍历攻击"""
        # 移除危险字符和路径遍历
        import re
        path = re.sub(r'[<>:"|?*]', '_', path)  # Windows不允许的字符
        path = re.sub(r'\.\./', '', path)  # 移除路径遍历
        path = path.replace('\\', '/')  # 统一路径分隔符
        return path

    def _create_directories(self, dir_path: str):
        """递归创建目录"""
        if not dir_path:
            return

        try:
            # 安全检查目录路径
            dir_path = self._sanitize_path(dir_path)
            url = f"{self.base_url}/{dir_path.lstrip('/')}"
            response = self.session.request('MKCOL', url, timeout=30)
            # 201表示创建成功，405表示已存在
            if response.status_code not in [201, 405]:
                print(f"⚠️ 创建目录警告: {dir_path} - {response.status_code}")
        except Exception as e:
            print(f"⚠️ 创建目录异常: {e}")

    def delete_file(self, remote_path: str) -> bool:
        """删除WebDAV文件"""
        try:
            remote_path = self._sanitize_path(remote_path.lstrip('/'))
            url = f"{self.base_url}/{remote_path}"
            response = self.session.delete(url, timeout=30)
            return response.status_code in [200, 204]
        except Exception as e:
            print(f"❌ 删除文件异常: {e}")
            return False

    def get_file_info(self, remote_path: str) -> Optional[Dict[str, Any]]:
        """获取WebDAV文件信息"""
        try:
            remote_path = self._sanitize_path(remote_path.lstrip('/'))
            url = f"{self.base_url}/{remote_path}"

            # 使用PROPFIND获取文件属性
            response = self.session.request('PROPFIND', url, timeout=30)
            if response.status_code == 207:  # Multi-Status
                return {
                    'path': remote_path,
                    'url': url,
                    'exists': True,
                    'last_modified': response.headers.get('Last-Modified'),
                    'content_length': response.headers.get('Content-Length')
                }
            else:
                return None
        except Exception as e:
            print(f"❌ 获取文件信息异常: {e}")
            return None


class CloudStorageManager:
    """云存储管理器"""

    def __init__(self, config_file: str = "cloud_config.json"):
        self.config_file = config_file
        self.storage_configs = self._load_config()
        self.active_storages = {}
        self._init_storages()

    def _load_config(self) -> Dict[str, Any]:
        """加载云存储配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                # 解密密码（如果已加密）
                for storage_type, storage_config in config.items():
                    if 'password' in storage_config and storage_config['password'].startswith('enc:'):
                        storage_config['password'] = self._decrypt_password(storage_config['password'])

                return config
            except Exception as e:
                print(f"❌ 加载云存储配置失败: {e}")

        # 返回默认配置模板
        default_config = {
            "webdav": {
                "enabled": False,
                "base_url": "https://dav.jianguoyun.com/dav/",
                "username": "",
                "password": "",
                "upload_path": "video_downloads"
            },
            "weiyun": {
                "enabled": False,
                "username": "",
                "password": "",
                "upload_path": "video_downloads",
                "description": "腾讯微云 - 使用腾讯微云账号和密码"
            }
        }

        # 保存默认配置
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            print(f"📁 已创建默认云存储配置文件: {self.config_file}")
            print("⚠️ 请编辑配置文件并设置正确的用户名和密码")
        except Exception as e:
            print(f"❌ 创建配置文件失败: {e}")

        return default_config

    def _encrypt_password(self, password: str) -> str:
        """加密密码（简单Base64编码，实际应用中应使用更强的加密）"""
        return "enc:" + base64.b64encode(password.encode()).decode()

    def _decrypt_password(self, encrypted_password: str) -> str:
        """解密密码"""
        try:
            return base64.b64decode(encrypted_password[4:]).decode()
        except Exception:
            return encrypted_password  # 解密失败，返回原始值

    def update_password(self, storage_type: str, new_password: str) -> bool:
        """更新并加密存储密码"""
        try:
            if storage_type in self.storage_configs:
                self.storage_configs[storage_type]['password'] = new_password

                # 保存时加密密码
                config_to_save = {}
                for st_type, config in self.storage_configs.items():
                    config_copy = config.copy()
                    if 'password' in config_copy and config_copy['password']:
                        config_copy['password'] = self._encrypt_password(config_copy['password'])
                    config_to_save[st_type] = config_copy

                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(config_to_save, f, indent=2, ensure_ascii=False)

                return True
        except Exception as e:
            print(f"❌ 更新密码失败: {e}")
        return False

    def _init_storages(self):
        """初始化云存储服务"""
        for storage_type, config in self.storage_configs.items():
            if not config.get('enabled', False):
                continue

            # 验证必要配置
            if not config.get('username') or not config.get('password'):
                print(f"⚠️ {storage_type.upper()} 配置不完整，跳过初始化")
                continue

            try:
                if storage_type == 'webdav':
                    storage = WebDAVStorage(
                        config['base_url'],
                        config['username'],
                        config['password']
                    )
                    self.active_storages[storage_type] = {
                        'storage': storage,
                        'upload_path': config.get('upload_path', 'video_downloads')
                    }
                    print(f"✅ {storage_type.upper()} 云存储已初始化")
                elif storage_type == 'weiyun':
                    storage = TencentWeiYunStorage(
                        config['username'],
                        config['password']
                    )
                    self.active_storages[storage_type] = {
                        'storage': storage,
                        'upload_path': config.get('upload_path', 'video_downloads')
                    }
                    print(f"✅ {storage_type.upper()} 云存储已初始化")
            except Exception as e:
                print(f"❌ 初始化 {storage_type} 失败: {e}")

    def upload_video(self, local_path: str, video_title: str, video_id: str) -> List[Dict[str, str]]:
        """上传视频到所有已配置的云存储"""
        upload_results = []

        if not self.active_storages:
            print("⚠️ 没有配置可用的云存储服务")
            return upload_results

        # 安全检查本地文件
        if not os.path.exists(local_path):
            print(f"❌ 本地文件不存在: {local_path}")
            return upload_results

        # 生成安全的文件名
        safe_filename = self._get_safe_filename(video_title, video_id, local_path)

        for storage_type, storage_info in self.active_storages.items():
            try:
                storage = storage_info['storage']
                upload_path = storage_info['upload_path']

                # 构建远程路径
                date_folder = datetime.now().strftime("%Y/%m")
                remote_path = f"{upload_path}/{date_folder}/{safe_filename}"

                print(f"📤 开始上传到 {storage_type.upper()}: {safe_filename}")

                cloud_url = storage.upload_file(local_path, remote_path)

                if cloud_url:
                    result = {
                        'storage_type': storage_type,
                        'cloud_path': remote_path,
                        'cloud_url': cloud_url,
                        'upload_time': datetime.now().isoformat(),
                        'status': 'success'
                    }
                    upload_results.append(result)
                    print(f"✅ {storage_type.upper()} 上传成功")
                else:
                    result = {
                        'storage_type': storage_type,
                        'status': 'failed',
                        'upload_time': datetime.now().isoformat()
                    }
                    upload_results.append(result)
                    print(f"❌ {storage_type.upper()} 上传失败")

            except Exception as e:
                print(f"❌ {storage_type} 上传异常: {e}")
                upload_results.append({
                    'storage_type': storage_type,
                    'status': 'error',
                    'error': str(e)[:200],  # 限制错误信息长度
                    'upload_time': datetime.now().isoformat()
                })

        return upload_results

    def _get_safe_filename(self, title: str, video_id: str, local_path: str) -> str:
        """生成安全的文件名"""
        # 获取文件扩展名
        ext = os.path.splitext(local_path)[1]

        # 清理标题中的特殊字符
        import re
        safe_title = re.sub(r'[^\w\s-]', '', title).strip()
        safe_title = re.sub(r'[-\s]+', '_', safe_title)

        # 限制长度
        if len(safe_title) > 50:
            safe_title = safe_title[:50]

        # 如果标题为空，使用视频ID
        if not safe_title:
            safe_title = f"video_{video_id}"

        # 确保文件名唯一性
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{safe_title}_{video_id}_{timestamp}{ext}"

    def test_connection(self, storage_type: str = None) -> Dict[str, bool]:
        """测试云存储连接"""
        results = {}

        storages_to_test = self.active_storages.items()
        if storage_type and storage_type in self.active_storages:
            storages_to_test = [(storage_type, self.active_storages[storage_type])]

        for st_type, storage_info in storages_to_test:
            try:
                storage = storage_info['storage']

                # 尝试创建测试文件
                test_path = f"{storage_info['upload_path']}/test_connection.txt"

                # 创建临时测试文件
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                    f.write(f"Connection test - {datetime.now().isoformat()}")
                    temp_file = f.name

                try:
                    # 上传测试
                    result = storage.upload_file(temp_file, test_path)
                    if result:
                        # 删除测试文件
                        storage.delete_file(test_path)
                        results[st_type] = True
                        print(f"✅ {st_type.upper()} 连接测试成功")
                    else:
                        results[st_type] = False
                        print(f"❌ {st_type.upper()} 连接测试失败")
                finally:
                    # 清理临时文件
                    os.unlink(temp_file)

            except Exception as e:
                results[st_type] = False
                print(f"❌ {st_type.upper()} 连接异常: {e}")

        return results

    def get_upload_statistics(self) -> Dict[str, Any]:
        """获取上传统计信息"""
        # 这里可以从数据库或日志文件中获取统计信息
        # 当前返回基本信息
        stats = {
            'active_storages': list(self.active_storages.keys()),
            'total_storages': len(self.active_storages),
            'config_file': self.config_file,
            'last_check': datetime.now().isoformat()
        }

        # 测试所有存储的连接状态
        connection_status = self.test_connection()
        stats['connection_status'] = connection_status

        return stats
