#!/usr/bin/env python3
"""
测试SSL修复的简单脚本
"""
import requests
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_ssl_fix():
    """测试SSL修复"""
    url = "https://api.memefans.ai/v2/posts/"
    params = {
        "author_id": "BhhLJPlVvjU",
        "page": 1,
        "size": 5
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    print("测试1: 禁用SSL验证的请求...")
    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            verify=False,  # 禁用SSL验证
            timeout=10
        )
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 成功获取数据，items数量: {len(data.get('items', []))}")
            return True
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            return False

    except requests.exceptions.SSLError as e:
        print(f"❌ SSL错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

if __name__ == "__main__":
    success = test_ssl_fix()
    print(f"\n测试结果: {'成功' if success else '失败'}")
