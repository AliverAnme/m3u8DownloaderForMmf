"""
坚果云WebDAV客户端
处理本地视频文件上传到坚果云
"""

import os
import requests
import base64
from typing import Optional, Dict, Any
from urllib.parse import urljoin, quote

class JianguoyunClient:
    """坚果云WebDAV客户端"""

    def __init__(self, username: str, password: str, base_url: str = "https://dav.jianguoyun.com/dav/"):
        """
        初始化坚果云客户端

        Args:
            username: 坚果云用户名（邮箱）
            password: 坚果云应用密码（非登录密码）
            base_url: WebDAV服务器地址
        """
        self.username = username
        self.password = password
        self.base_url = base_url

        # 设置Basic认证
        auth_string = f"{username}:{password}"
        auth_bytes = auth_string.encode('utf-8')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')

        self.headers = {
            'Authorization': f'Basic {auth_b64}',
            'User-Agent': 'VideoDownloader/1.0'
        }

        self.session = requests.Session()
        self.session.headers.update(self.headers)
        # 禁用SSL验证以避免证书问题
        self.session.verify = False

    def create_directory(self, remote_path: str) -> bool:
        """
        创建远程目录

        Args:
            remote_path: 远程目录路径

        Returns:
            bool: 创建是否成功
        """
        try:
            url = urljoin(self.base_url, quote(remote_path.strip('/'), safe='/'))
            response = self.session.request('MKCOL', url)

            # 201表示创建成功，405表示目录已存在
            if response.status_code in [201, 405]:
                return True
            else:
                print(f"❌ 创建目录失败: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"❌ 创建目录异常: {e}")
            return False

    def upload_file(self, local_file_path: str, remote_file_path: str,
                   progress_callback=None) -> bool:
        """
        上传文件到坚果云

        Args:
            local_file_path: 本地文件路径
            remote_file_path: 远程文件路径
            progress_callback: 进度回调函数

        Returns:
            bool: 上传是否成功
        """
        try:
            if not os.path.exists(local_file_path):
                print(f"❌ 本地文件不存在: {local_file_path}")
                return False

            file_size = os.path.getsize(local_file_path)
            print(f"📤 开始上传文件: {os.path.basename(local_file_path)} ({file_size / 1024 / 1024:.2f} MB)")

            # 确保远程目录存在
            remote_dir = os.path.dirname(remote_file_path)
            if remote_dir:
                self.create_directory(remote_dir)

            url = urljoin(self.base_url, quote(remote_file_path.strip('/'), safe='/'))

            with open(local_file_path, 'rb') as f:
                response = self.session.put(url, data=f)

            if response.status_code in [201, 204]:
                print(f"✅ 文件上传成功: {remote_file_path}")
                return True
            else:
                print(f"❌ 文件上传失败: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"❌ 上传文件异常: {e}")
            return False

    def check_file_exists(self, remote_file_path: str) -> bool:
        """
        检查远程文件是否存在

        Args:
            remote_file_path: 远程文件路径

        Returns:
            bool: 文件是否存在
        """
        try:
            url = urljoin(self.base_url, quote(remote_file_path.strip('/'), safe='/'))
            response = self.session.head(url)
            return response.status_code == 200
        except Exception:
            return False

    def get_file_info(self, remote_file_path: str) -> Optional[Dict[str, Any]]:
        """
        获取远程文件信息

        Args:
            remote_file_path: 远程文件路径

        Returns:
            dict: 文件信息，包含大小、修改时间等
        """
        try:
            url = urljoin(self.base_url, quote(remote_file_path.strip('/'), safe='/'))
            response = self.session.request('PROPFIND', url,
                                          headers={'Depth': '0'})

            if response.status_code == 207:
                # 解析WebDAV响应（简化版）
                content_length = response.headers.get('Content-Length', '0')
                last_modified = response.headers.get('Last-Modified', '')

                return {
                    'size': int(content_length) if content_length.isdigit() else 0,
                    'last_modified': last_modified,
                    'exists': True
                }
            else:
                return {'exists': False}

        except Exception as e:
            print(f"❌ 获取文件信息异常: {e}")
            return {'exists': False}

    def delete_file(self, remote_file_path: str) -> bool:
        """
        删除远程文件

        Args:
            remote_file_path: 远程文件路径

        Returns:
            bool: 删除是否成功
        """
        try:
            url = urljoin(self.base_url, quote(remote_file_path.strip('/'), safe='/'))
            response = self.session.delete(url)

            if response.status_code in [204, 404]:
                print(f"✅ 文件删除成功: {remote_file_path}")
                return True
            else:
                print(f"❌ 文件删除失败: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"❌ 删除文件异常: {e}")
            return False
