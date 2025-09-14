#!/usr/bin/env python3
"""
腾讯微云配置工具 - 帮助用户配置和测试腾讯微云连接
"""

import os
import sys
import json
import getpass
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from video_downloader.cloud import CloudStorageManager, TencentWeiYunStorage


class WeiYunConfigTool:
    """腾讯微云配置工具"""

    def __init__(self):
        self.config_file = "cloud_config.json"
        self.cloud_manager = CloudStorageManager(self.config_file)

    def show_welcome(self):
        """显示欢迎信息"""
        print("🎯 腾讯微云配置工具")
        print("=" * 50)
        print("此工具将帮助您配置腾讯微云，以便自动上传下载的视频。")
        print()
        print("📋 配置步骤:")
        print("1. 输入腾讯微云账号（手机号或邮箱）")
        print("2. 输入腾讯微云密码")
        print("3. 测试连接")
        print("4. 设置上传路径")
        print()
        print("⚠️ 重要提示:")
        print("- 请确保您的腾讯微云账号支持WebDAV访问")
        print("- 建议使用应用专用密码而不是主密码")
        print("- 密码将被加密存储在本地配置文件中")
        print()

    def get_user_credentials(self):
        """获取用户凭证"""
        print("🔐 请输入腾讯微云账号信息:")
        print("-" * 30)

        username = input("📧 用户名（手机号或邮箱）: ").strip()
        if not username:
            print("❌ 用户名不能为空")
            return None, None

        password = getpass.getpass("🔑 密码: ").strip()
        if not password:
            print("❌ 密码不能为空")
            return None, None

        return username, password

    def test_connection(self, username: str, password: str) -> bool:
        """测试腾讯微云连接"""
        print("\n🔍 正在测试腾讯微云连接...")

        try:
            # 创建腾讯微云存储实例
            weiyun = TencentWeiYunStorage(username, password)

            # 创建测试文件
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                f.write(f"腾讯微云连接测试 - {datetime.now().isoformat()}")
                test_file = f.name

            try:
                # 尝试上传测试文件
                test_path = "video_downloads/connection_test.txt"
                result = weiyun.upload_file(test_file, test_path)

                if result:
                    print("✅ 连接测试成功！")
                    # 清理测试文件
                    weiyun.delete_file(test_path)
                    return True
                else:
                    print("❌ 连接测试失败")
                    return False
            finally:
                # 删除临时文件
                os.unlink(test_file)

        except Exception as e:
            print(f"❌ 连接测试异常: {e}")
            return False

    def save_configuration(self, username: str, password: str, upload_path: str = "video_downloads"):
        """保存配置"""
        print(f"\n💾 正在保存配置到 {self.config_file}...")

        try:
            # 加载现有配置
            config = {}
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

            # 更新腾讯微云配置
            config['weiyun'] = {
                "enabled": True,
                "username": username,
                "password": password,  # 将由CloudStorageManager自动加密
                "upload_path": upload_path,
                "description": "腾讯微云 - 使用腾讯微云账号和密码"
            }

            # 保存配置
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            # 使用CloudStorageManager加密密码
            self.cloud_manager.update_password('weiyun', password)

            print("✅ 配置保存成功！")
            return True

        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
            return False

    def show_final_instructions(self):
        """显示最终说明"""
        print("\n🎉 腾讯微云配置完成！")
        print("=" * 50)
        print("📁 配置文件位置:", os.path.abspath(self.config_file))
        print()
        print("🚀 现在您可以:")
        print("1. 运行主程序开始下载和上传视频")
        print("   python enhanced_main.py")
        print()
        print("2. 测试云存储连接")
        print("   python manager.py test-cloud")
        print()
        print("3. 查看上传统计")
        print("   python manager.py status")
        print()
        print("⚙️ 配置说明:")
        print("- 视频将自动上传到腾讯微云的 video_downloads 文件夹")
        print("- 文件按年月自动分类 (如: video_downloads/2024/12/)")
        print("- 可以在配置文件中修改上传路径")
        print()
        print("🔒 安全提示:")
        print("- 您的密码已经过加密存储")
        print("- 如需修改密码，请重新运行此工具")
        print()

    def run(self):
        """运行配置工具"""
        self.show_welcome()

        # 获取用户凭证
        username, password = self.get_user_credentials()
        if not username or not password:
            print("❌ 配置取消")
            return

        # 测试连接
        if not self.test_connection(username, password):
            print("\n❌ 无法连接到腾讯微云，请检查:")
            print("- 用户名和密码是否正确")
            print("- 网络连接是否正常")
            print("- 腾讯微云是否支持WebDAV（可能需要开通会员）")

            retry = input("\n是否重试? (y/n): ").strip().lower()
            if retry == 'y':
                return self.run()
            else:
                return

        # 设置上传路径
        print("\n📁 设置上传路径:")
        default_path = "video_downloads"
        upload_path = input(f"上传路径 (默认: {default_path}): ").strip()
        if not upload_path:
            upload_path = default_path

        # 保存配置
        if self.save_configuration(username, password, upload_path):
            self.show_final_instructions()
        else:
            print("❌ 配置失败，请重试")


def main():
    """主函数"""
    try:
        tool = WeiYunConfigTool()
        tool.run()
    except KeyboardInterrupt:
        print("\n\n👋 配置已取消")
    except Exception as e:
        print(f"\n❌ 配置工具运行异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
