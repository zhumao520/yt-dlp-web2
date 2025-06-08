#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用Cookies格式转换工具
支持各种平台的cookies格式转换
"""

import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

class CookiesConverter:
    """Cookies格式转换器"""
    
    def __init__(self):
        self.platform_configs = {
            'youtube': {
                'domains': ['youtube.com', 'youtu.be'],
                'key_cookies': ['VISITOR_INFO1_LIVE', 'YSC', 'CONSENT'],
                'description': 'YouTube视频平台'
            },
            'bilibili': {
                'domains': ['bilibili.com', 'b23.tv'],
                'key_cookies': ['SESSDATA', 'bili_jct', 'DedeUserID'],
                'description': 'Bilibili视频平台'
            },
            'twitter': {
                'domains': ['twitter.com', 'x.com'],
                'key_cookies': ['auth_token', 'ct0', 'guest_id'],
                'description': 'Twitter/X社交平台'
            },
            'instagram': {
                'domains': ['instagram.com'],
                'key_cookies': ['sessionid', 'csrftoken', 'ds_user_id'],
                'description': 'Instagram图片社交平台'
            },
            'tiktok': {
                'domains': ['tiktok.com'],
                'key_cookies': ['sessionid', 'sid_tt', 'uid_tt'],
                'description': 'TikTok短视频平台'
            }
        }
    
    def detect_format(self, content: str) -> str:
        """检测cookies格式"""
        content = content.strip()
        
        # JSON格式
        if (content.startswith('[') and content.endswith(']')) or \
           (content.startswith('{') and content.endswith('}')):
            try:
                json.loads(content)
                return 'json'
            except:
                return 'json_invalid'
        
        # Netscape格式
        if '# Netscape HTTP Cookie File' in content or \
           (content.count('\t') > content.count('=') and '\n' in content):
            return 'netscape'
        
        # 键值对格式
        if '=' in content and (';' in content or '\n' in content):
            return 'keyvalue'
        
        # 浏览器复制格式 (name: value)
        if ':' in content and '\n' in content:
            return 'browser_copy'
        
        return 'unknown'
    
    def parse_json(self, content: str) -> list:
        """解析JSON格式cookies"""
        try:
            data = json.loads(content)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return [data]
            return []
        except Exception as e:
            print(f"❌ JSON解析失败: {e}")
            return []
    
    def parse_netscape(self, content: str) -> list:
        """解析Netscape格式cookies"""
        cookies = []
        for line_num, line in enumerate(content.split('\n'), 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split('\t')
            if len(parts) >= 7:
                try:
                    expiration = int(parts[4]) if parts[4] != '0' else 0
                except ValueError:
                    expiration = 0
                
                cookies.append({
                    'domain': parts[0],
                    'flag': parts[1] == 'TRUE',
                    'path': parts[2],
                    'secure': parts[3] == 'TRUE',
                    'expiration': expiration,
                    'name': parts[5],
                    'value': parts[6] if len(parts) > 6 else ''
                })
            else:
                print(f"⚠️ 跳过第{line_num}行：格式不正确")
        
        return cookies
    
    def parse_keyvalue(self, content: str) -> list:
        """解析键值对格式cookies"""
        cookies = []
        # 支持分号或换行分隔
        pairs = re.split(r'[;\n]', content)
        
        for pair in pairs:
            pair = pair.strip()
            if '=' in pair:
                name, value = pair.split('=', 1)
                cookies.append({
                    'name': name.strip(),
                    'value': value.strip(),
                    'domain': '',
                    'path': '/',
                    'secure': False,
                    'expiration': 0
                })
        
        return cookies
    
    def parse_browser_copy(self, content: str) -> list:
        """解析浏览器复制格式cookies"""
        cookies = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    name = parts[0].strip()
                    value = parts[1].strip()
                    cookies.append({
                        'name': name,
                        'value': value,
                        'domain': '',
                        'path': '/',
                        'secure': False,
                        'expiration': 0
                    })
        
        return cookies
    
    def to_netscape(self, cookies: list) -> str:
        """转换为Netscape格式"""
        lines = ['# Netscape HTTP Cookie File', '# Generated by Cookies Converter', '']
        
        for cookie in cookies:
            domain = cookie.get('domain', '')
            if not domain:
                continue
            
            # 域名规范化
            if domain.startswith('.'):
                domain_specified = 'TRUE'
            else:
                domain_specified = 'FALSE'
                if cookie.get('flag', False):
                    domain_specified = 'TRUE'
            
            path = cookie.get('path', '/')
            secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
            
            # 处理过期时间
            expiration = cookie.get('expiration', 0)
            if expiration == 0:
                expiration = cookie.get('expirationDate', 0)
            if expiration == 0:
                expiration = cookie.get('expires', 0)
            
            try:
                expiration = int(float(expiration))
            except (ValueError, TypeError):
                expiration = 0
            
            name = cookie.get('name', '')
            value = cookie.get('value', '')
            
            if name:
                line = f"{domain}\t{domain_specified}\t{path}\t{secure}\t{expiration}\t{name}\t{value}"
                lines.append(line)
        
        return '\n'.join(lines)
    
    def to_json(self, cookies: list) -> str:
        """转换为JSON格式"""
        return json.dumps(cookies, indent=2, ensure_ascii=False)
    
    def detect_platform(self, cookies: list) -> str:
        """检测cookies所属平台"""
        cookie_names = {cookie.get('name', '') for cookie in cookies}
        
        for platform, config in self.platform_configs.items():
            key_cookies = set(config['key_cookies'])
            if key_cookies.intersection(cookie_names):
                return platform
        
        # 根据域名检测
        domains = {cookie.get('domain', '').replace('.', '') for cookie in cookies}
        for platform, config in self.platform_configs.items():
            for domain in config['domains']:
                if domain.replace('.', '') in domains:
                    return platform
        
        return 'unknown'
    
    def validate_cookies(self, cookies: list, platform: str = None) -> dict:
        """验证cookies有效性"""
        if not cookies:
            return {'valid': False, 'error': 'cookies为空'}
        
        result = {
            'valid': True,
            'total': len(cookies),
            'expired': 0,
            'missing_key_cookies': [],
            'platform': platform or self.detect_platform(cookies)
        }
        
        current_time = int(time.time())
        
        # 检查过期
        for cookie in cookies:
            expiration = cookie.get('expiration', 0)
            if expiration > 0 and expiration < current_time:
                result['expired'] += 1
        
        # 检查关键cookies
        if result['platform'] in self.platform_configs:
            config = self.platform_configs[result['platform']]
            cookie_names = {cookie.get('name', '') for cookie in cookies}
            for key_cookie in config['key_cookies']:
                if key_cookie not in cookie_names:
                    result['missing_key_cookies'].append(key_cookie)
        
        return result
    
    def convert(self, input_content: str, output_format: str = 'netscape', platform: str = None) -> dict:
        """转换cookies格式"""
        try:
            # 检测输入格式
            input_format = self.detect_format(input_content)
            print(f"🔍 检测到输入格式: {input_format}")
            
            # 解析cookies
            if input_format == 'json':
                cookies = self.parse_json(input_content)
            elif input_format == 'netscape':
                cookies = self.parse_netscape(input_content)
            elif input_format == 'keyvalue':
                cookies = self.parse_keyvalue(input_content)
            elif input_format == 'browser_copy':
                cookies = self.parse_browser_copy(input_content)
            else:
                return {'success': False, 'error': f'不支持的输入格式: {input_format}'}
            
            if not cookies:
                return {'success': False, 'error': '无法解析cookies或cookies为空'}
            
            # 验证cookies
            validation = self.validate_cookies(cookies, platform)
            
            # 转换输出格式
            if output_format == 'netscape':
                output_content = self.to_netscape(cookies)
            elif output_format == 'json':
                output_content = self.to_json(cookies)
            else:
                return {'success': False, 'error': f'不支持的输出格式: {output_format}'}
            
            return {
                'success': True,
                'input_format': input_format,
                'output_format': output_format,
                'content': output_content,
                'validation': validation
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("🍪 Cookies格式转换工具")
        print("\n使用方法:")
        print("  python cookies_converter.py <input_file> [output_format] [platform]")
        print("\n参数说明:")
        print("  input_file: 输入的cookies文件")
        print("  output_format: 输出格式 (netscape/json，默认netscape)")
        print("  platform: 目标平台 (youtube/bilibili/twitter等，可选)")
        print("\n示例:")
        print("  python cookies_converter.py cookies.json")
        print("  python cookies_converter.py cookies.txt json youtube")
        return
    
    input_file = sys.argv[1]
    output_format = sys.argv[2] if len(sys.argv) > 2 else 'netscape'
    platform = sys.argv[3] if len(sys.argv) > 3 else None
    
    if not Path(input_file).exists():
        print(f"❌ 文件不存在: {input_file}")
        return
    
    # 读取输入文件
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return
    
    # 转换
    converter = CookiesConverter()
    result = converter.convert(content, output_format, platform)
    
    if result['success']:
        validation = result['validation']
        print(f"✅ 转换成功!")
        print(f"📊 统计信息:")
        print(f"   - 输入格式: {result['input_format']}")
        print(f"   - 输出格式: {result['output_format']}")
        print(f"   - 检测平台: {validation['platform']}")
        print(f"   - Cookies数量: {validation['total']}")
        print(f"   - 过期数量: {validation['expired']}")
        
        if validation['missing_key_cookies']:
            print(f"   - 缺少关键cookies: {', '.join(validation['missing_key_cookies'])}")
        
        # 保存输出文件
        output_file = f"{Path(input_file).stem}_converted.{'txt' if output_format == 'netscape' else 'json'}"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result['content'])
        
        print(f"💾 输出文件: {output_file}")
    else:
        print(f"❌ 转换失败: {result['error']}")

if __name__ == "__main__":
    main()
