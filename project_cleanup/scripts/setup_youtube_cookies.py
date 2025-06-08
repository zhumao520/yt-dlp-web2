#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube Cookies 设置助手
帮助用户快速设置YouTube cookies以解决下载问题
"""

import json
import os
import sys
import time
from pathlib import Path

def create_youtube_cookies_template():
    """创建YouTube cookies模板"""
    template = [
        {
            "name": "VISITOR_INFO1_LIVE",
            "value": "YOUR_VISITOR_INFO_HERE",
            "domain": ".youtube.com",
            "path": "/",
            "secure": True,
            "httpOnly": False,
            "sameSite": "None",
            "expirationDate": 1735689600
        },
        {
            "name": "YSC",
            "value": "YOUR_YSC_VALUE_HERE",
            "domain": ".youtube.com",
            "path": "/",
            "secure": True,
            "httpOnly": True,
            "sameSite": "None",
            "expirationDate": 0
        },
        {
            "name": "PREF",
            "value": "tz=Asia.Shanghai&f4=4000000&f5=30000",
            "domain": ".youtube.com",
            "path": "/",
            "secure": False,
            "httpOnly": False,
            "sameSite": "Lax",
            "expirationDate": 1735689600
        },
        {
            "name": "CONSENT",
            "value": "YES+cb.20210328-17-p0.en+FX+667",
            "domain": ".youtube.com",
            "path": "/",
            "secure": False,
            "httpOnly": False,
            "sameSite": "Lax",
            "expirationDate": 1735689600
        }
    ]
    return template

def setup_cookies():
    """设置cookies"""
    print("🍪 YouTube Cookies 设置助手")
    print("=" * 50)
    
    # 确保cookies目录存在
    cookies_dir = Path("data/cookies")
    cookies_dir.mkdir(parents=True, exist_ok=True)
    
    cookies_file = cookies_dir / "youtube.json"
    
    print(f"📁 Cookies文件路径: {cookies_file}")
    
    if cookies_file.exists():
        print("⚠️  YouTube cookies文件已存在")
        choice = input("是否覆盖现有文件? (y/N): ").strip().lower()
        if choice != 'y':
            print("❌ 操作已取消")
            return False
    
    # 创建模板
    template = create_youtube_cookies_template()
    
    print("\n📝 创建YouTube cookies模板...")
    with open(cookies_file, 'w', encoding='utf-8') as f:
        json.dump(template, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 模板已创建: {cookies_file}")
    
    print("\n" + "=" * 50)
    print("📖 接下来的步骤 (yt-dlp官方推荐方法):")
    print("⭐ 重要：使用隐私浏览窗口避免cookies轮换")
    print("1. 打开新的隐私浏览/无痕窗口")
    print("2. 在该窗口登录 https://youtube.com")
    print("3. 在同一个标签页中，导航到 https://www.youtube.com/robots.txt")
    print("4. 使用浏览器扩展导出 youtube.com 的cookies")
    print("5. 立即关闭隐私浏览窗口")
    print("6. 将导出的cookies内容替换模板文件")
    print("7. 或者访问Web管理界面的Cookies页面上传")
    print("\n💡 推荐的浏览器扩展:")
    print("• EditThisCookie (Chrome/Edge) - 推荐")
    print("• Cookie-Editor (Firefox)")
    print("• Get cookies.txt LOCALLY (Chrome)")
    print("\n⚠️ 重要提醒:")
    print("• 导出的cookies在30分钟内最有效")
    print("• YouTube会频繁轮换cookies，请按步骤操作")
    print("• 使用账户下载可能导致账户被封，建议使用备用账户")
    
    return True

def check_cookies():
    """检查cookies是否有效"""
    cookies_file = Path("data/cookies/youtube.json")

    if not cookies_file.exists():
        print("❌ YouTube cookies文件不存在")
        return False

    try:
        with open(cookies_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 检查是否是正确的格式
        if 'cookies' in data:
            cookies = data['cookies']
            print(f"✅ 找到cookies管理器格式文件，包含 {len(cookies)} 个cookies")
        else:
            cookies = data if isinstance(data, list) else [data]
            print(f"✅ 找到原始格式文件，包含 {len(cookies)} 个cookies")

        # 检查关键cookies
        key_cookies = ['VISITOR_INFO1_LIVE', 'YSC', 'CONSENT']
        found_keys = []
        template_values = []

        for cookie in cookies:
            name = cookie.get('name', '')
            value = cookie.get('value', '')

            if name in key_cookies:
                found_keys.append(name)

            # 检查是否是示例数据
            if any(x in value for x in ['PLEASE_REPLACE_WITH_REAL_VALUE', 'example_', 'YOUR_']):
                template_values.append(name)

        if found_keys:
            print(f"🔑 关键cookies: {', '.join(found_keys)}")
        else:
            print("⚠️  未找到关键cookies，可能需要更新")

        if template_values:
            print(f"⚠️  检测到示例数据: {', '.join(template_values)}")
            print("   请替换为从浏览器导出的真实cookies")
            return False

        # 检查过期时间
        current_time = int(time.time())
        expired_count = 0

        for cookie in cookies:
            expiration = cookie.get('expiration', 0)
            if expiration == 0:
                expiration = cookie.get('expirationDate', 0)

            if expiration > 0 and expiration < current_time:
                expired_count += 1

        if expired_count > 0:
            print(f"⚠️  有 {expired_count} 个cookies已过期")

        return len(template_values) == 0

    except Exception as e:
        print(f"❌ 检查cookies失败: {e}")
        return False

def main():
    """主函数"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "check":
            success = check_cookies()
            sys.exit(0 if success else 1)
        elif command == "setup":
            success = setup_cookies()
            sys.exit(0 if success else 1)
    
    print("🍪 YouTube Cookies 助手")
    print("使用方法:")
    print("  python setup_youtube_cookies.py setup  - 创建cookies模板")
    print("  python setup_youtube_cookies.py check  - 检查cookies状态")

if __name__ == "__main__":
    main()
