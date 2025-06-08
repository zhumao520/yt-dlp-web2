#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通过Web API更新yt-dlp
"""

import requests
import sys

def update_ytdlp(base_url='http://localhost:8080'):
    """通过Web API更新yt-dlp"""
    try:
        print("🔄 更新yt-dlp...")

        response = requests.post(f"{base_url}/api/system/ytdlp/update", timeout=120)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✅ {data.get('message', '更新成功')}")
                return True
            else:
                print(f"❌ 更新失败: {data.get('error', '未知错误')}")
                return False
        else:
            print(f"❌ API请求失败: HTTP {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ 更新异常: {e}")
        return False

if __name__ == '__main__':
    url = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8080'
    success = update_ytdlp(url)
    sys.exit(0 if success else 1)
