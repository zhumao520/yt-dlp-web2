# -*- coding: utf-8 -*-
"""
Cookies管理器 - 统一处理各种格式的Cookies
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Union
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class CookiesManager:
    """Cookies管理器"""
    
    def __init__(self):
        self.cookies_dir = None
        self._load_config()
    
    def _load_config(self):
        """加载配置"""
        try:
            from ...core.config import get_config
            self.cookies_dir = Path(get_config('app.data_dir', '/app/data')) / 'cookies'
            self.cookies_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"✅ Cookies目录: {self.cookies_dir}")
        except Exception as e:
            logger.error(f"❌ 加载Cookies配置失败: {e}")
    
    def save_cookies(self, website: str, cookies_data: str, format_type: str = 'auto') -> Dict:
        """保存Cookies"""
        try:
            # 检测格式
            if format_type == 'auto':
                format_type = self._detect_format(cookies_data)
            
            # 验证Cookies
            parsed_cookies = self._parse_cookies(cookies_data, format_type)
            if not parsed_cookies:
                return {'success': False, 'error': 'Cookies格式无效'}
            
            # 标准化网站名称
            website = self._normalize_website_name(website)
            
            # 保存到文件
            cookies_file = self.cookies_dir / f"{website}.json"
            
            # 准备保存数据
            save_data = {
                'website': website,
                'format': format_type,
                'cookies': parsed_cookies,
                'created_at': self._get_current_timestamp(),
                'updated_at': self._get_current_timestamp(),
                'count': len(parsed_cookies)
            }
            
            # 写入文件
            with open(cookies_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Cookies保存成功: {website} ({len(parsed_cookies)}个)")
            
            return {
                'success': True,
                'message': f'成功保存 {len(parsed_cookies)} 个Cookies',
                'website': website,
                'count': len(parsed_cookies),
                'format': format_type
            }
            
        except Exception as e:
            logger.error(f"❌ 保存Cookies失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_cookies(self, website: str) -> Dict:
        """获取指定网站的Cookies"""
        try:
            website = self._normalize_website_name(website)
            cookies_file = self.cookies_dir / f"{website}.json"
            
            if not cookies_file.exists():
                return {'success': False, 'error': 'Cookies不存在'}
            
            with open(cookies_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return {
                'success': True,
                'data': data
            }
            
        except Exception as e:
            logger.error(f"❌ 获取Cookies失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def list_cookies(self) -> Dict:
        """列出所有Cookies"""
        try:
            cookies_list = []
            
            for cookies_file in self.cookies_dir.glob("*.json"):
                try:
                    with open(cookies_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    cookies_list.append({
                        'website': data.get('website', cookies_file.stem),
                        'count': data.get('count', 0),
                        'format': data.get('format', 'unknown'),
                        'created_at': data.get('created_at'),
                        'updated_at': data.get('updated_at'),
                        'file_size': cookies_file.stat().st_size
                    })
                    
                except Exception as e:
                    logger.warning(f"⚠️ 读取Cookies文件失败: {cookies_file} - {e}")
            
            # 按更新时间排序
            cookies_list.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
            
            return {
                'success': True,
                'cookies': cookies_list,
                'total': len(cookies_list)
            }
            
        except Exception as e:
            logger.error(f"❌ 列出Cookies失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def delete_cookies(self, website: str) -> Dict:
        """删除指定网站的Cookies"""
        try:
            website = self._normalize_website_name(website)
            cookies_file = self.cookies_dir / f"{website}.json"
            
            if not cookies_file.exists():
                return {'success': False, 'error': 'Cookies不存在'}
            
            cookies_file.unlink()
            logger.info(f"✅ Cookies删除成功: {website}")
            
            return {
                'success': True,
                'message': f'成功删除 {website} 的Cookies'
            }
            
        except Exception as e:
            logger.error(f"❌ 删除Cookies失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def export_cookies(self, website: str, format_type: str = 'netscape') -> Dict:
        """导出Cookies为指定格式"""
        try:
            cookies_data = self.get_cookies(website)
            if not cookies_data['success']:
                return cookies_data
            
            cookies = cookies_data['data']['cookies']
            
            if format_type == 'netscape':
                content = self._export_netscape(cookies)
            elif format_type == 'json':
                content = json.dumps(cookies, indent=2, ensure_ascii=False)
            else:
                return {'success': False, 'error': f'不支持的导出格式: {format_type}'}
            
            return {
                'success': True,
                'content': content,
                'format': format_type,
                'filename': f"{website}_cookies.{'txt' if format_type == 'netscape' else 'json'}"
            }
            
        except Exception as e:
            logger.error(f"❌ 导出Cookies失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_cookies_for_ytdlp(self, url: str) -> Optional[str]:
        """为yt-dlp获取对应网站的Cookies文件路径"""
        try:
            domain = self._extract_domain(url)
            if not domain:
                return None

            logger.info(f"🔍 为URL查找cookies: {url} -> 域名: {domain}")

            # 定义域名映射关系
            domain_mappings = {
                'youtube.com': ['youtube'],
                'youtu.be': ['youtube'],
                'bilibili.com': ['bilibili'],
                'twitter.com': ['twitter'],
                'x.com': ['twitter'],
                'instagram.com': ['instagram'],
                'tiktok.com': ['tiktok']
            }

            # 查找匹配的网站名
            possible_websites = []
            for site_domain, website_names in domain_mappings.items():
                if domain == site_domain or domain.endswith('.' + site_domain):
                    possible_websites.extend(website_names)

            # 如果没有预定义映射，使用域名本身
            if not possible_websites:
                # 移除www前缀和顶级域名
                clean_domain = domain.replace('www.', '')
                if '.' in clean_domain:
                    possible_websites.append(clean_domain.split('.')[0])
                else:
                    possible_websites.append(clean_domain)

            logger.info(f"🎯 可能的网站名: {possible_websites}")

            # 查找匹配的Cookies文件
            for website in possible_websites:
                cookies_file = self.cookies_dir / f"{website}.json"
                if cookies_file.exists():
                    logger.info(f"✅ 找到cookies文件: {cookies_file}")

                    # 转换为Netscape格式并保存临时文件
                    temp_file = self.cookies_dir / f"{website}_temp.txt"
                    export_result = self.export_cookies(website, 'netscape')

                    if export_result['success']:
                        with open(temp_file, 'w', encoding='utf-8') as f:
                            f.write(export_result['content'])
                        logger.info(f"✅ 生成临时cookies文件: {temp_file}")
                        return str(temp_file)
                    else:
                        logger.warning(f"⚠️ 导出cookies失败: {export_result.get('error')}")

            logger.warning(f"⚠️ 未找到匹配的cookies文件，域名: {domain}")
            return None

        except Exception as e:
            logger.error(f"❌ 获取yt-dlp Cookies失败: {e}")
            return None
    
    def _detect_format(self, cookies_data: str) -> str:
        """检测Cookies格式 - 增强版"""
        cookies_data = cookies_data.strip()

        if not cookies_data:
            return 'empty'

        # JSON格式检测 (更严格)
        if (cookies_data.startswith('[') and cookies_data.endswith(']')) or \
           (cookies_data.startswith('{') and cookies_data.endswith('}')):
            try:
                data = json.loads(cookies_data)
                # 验证JSON结构
                if isinstance(data, list):
                    if all(isinstance(item, dict) and 'name' in item for item in data):
                        return 'json_array'
                    return 'json_invalid'
                elif isinstance(data, dict):
                    if 'name' in data or 'cookies' in data:
                        return 'json_object'
                    return 'json_invalid'
                return 'json_unknown'
            except json.JSONDecodeError:
                return 'json_invalid'

        # Netscape格式检测 (更精确)
        if '# Netscape HTTP Cookie File' in cookies_data:
            return 'netscape_standard'

        # 检查是否为制表符分隔的格式
        lines = cookies_data.split('\n')
        tab_lines = [line for line in lines if '\t' in line and not line.strip().startswith('#')]
        if tab_lines:
            # 检查字段数量
            field_counts = [len(line.split('\t')) for line in tab_lines]
            if all(count >= 6 for count in field_counts):
                return 'netscape_like'

        # 浏览器开发者工具复制格式
        if ':' in cookies_data and '\n' in cookies_data:
            lines = [line.strip() for line in cookies_data.split('\n') if line.strip()]
            colon_lines = [line for line in lines if ':' in line and not line.startswith('#')]
            if len(colon_lines) > 0:
                return 'browser_devtools'

        # EditThisCookie扩展格式
        if 'domain' in cookies_data.lower() and 'path' in cookies_data.lower():
            return 'extension_format'

        # 简单键值对格式
        if '=' in cookies_data:
            if ';' in cookies_data:
                return 'keyvalue_semicolon'
            elif '\n' in cookies_data:
                return 'keyvalue_newline'
            else:
                return 'keyvalue_single'

        # cURL格式检测
        if 'Cookie:' in cookies_data or 'cookie:' in cookies_data:
            return 'curl_header'

        return 'unknown'
    
    def _parse_cookies(self, cookies_data: str, format_type: str) -> List[Dict]:
        """解析Cookies数据 - 增强版"""
        try:
            logger.info(f"🔍 解析cookies格式: {format_type}")

            # JSON格式系列
            if format_type in ['json', 'json_array', 'json_object']:
                return self._parse_json_cookies(cookies_data)

            # Netscape格式系列
            elif format_type in ['netscape', 'netscape_standard', 'netscape_like']:
                return self._parse_netscape_cookies(cookies_data)

            # 键值对格式系列
            elif format_type in ['keyvalue', 'keyvalue_semicolon', 'keyvalue_newline', 'keyvalue_single']:
                return self._parse_keyvalue_cookies(cookies_data)

            # 浏览器开发者工具格式
            elif format_type in ['browser_copy', 'browser_devtools']:
                return self._parse_browser_devtools_cookies(cookies_data)

            # 扩展格式
            elif format_type == 'extension_format':
                return self._parse_extension_cookies(cookies_data)

            # cURL格式
            elif format_type == 'curl_header':
                return self._parse_curl_cookies(cookies_data)

            # 向后兼容
            elif format_type == 'header':
                return self._parse_keyvalue_cookies(cookies_data)

            else:
                logger.warning(f"⚠️ 未知格式类型: {format_type}")
                return []

        except Exception as e:
            logger.error(f"❌ 解析Cookies失败: {e}")
            return []
    
    def _parse_json_cookies(self, cookies_data: str) -> List[Dict]:
        """解析JSON格式Cookies"""
        data = json.loads(cookies_data)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return [data]
        return []
    
    def _parse_netscape_cookies(self, cookies_data: str) -> List[Dict]:
        """解析Netscape格式Cookies"""
        cookies = []
        for line_num, line in enumerate(cookies_data.split('\n'), 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            parts = line.split('\t')
            if len(parts) >= 7:
                domain = parts[0]
                domain_specified = parts[1] == 'TRUE'

                # 验证域名和 domain_specified 字段的一致性
                if domain.startswith('.') and not domain_specified:
                    # 修复不一致的情况：域名以.开头但domain_specified是FALSE
                    logger.warning(f"修复第{line_num}行cookies格式：域名 {domain} 以.开头但domain_specified为FALSE")
                    domain_specified = True
                elif not domain.startswith('.') and domain_specified:
                    # 修复不一致的情况：域名不以.开头但domain_specified是TRUE
                    logger.warning(f"修复第{line_num}行cookies格式：域名 {domain} 不以.开头但domain_specified为TRUE")
                    domain_specified = False

                try:
                    expiration = int(parts[4]) if parts[4] != '0' else 0
                except ValueError:
                    expiration = 0

                cookies.append({
                    'domain': domain,
                    'flag': domain_specified,
                    'path': parts[2],
                    'secure': parts[3] == 'TRUE',
                    'expiration': expiration,
                    'name': parts[5],
                    'value': parts[6] if len(parts) > 6 else ''
                })
            else:
                logger.warning(f"跳过第{line_num}行：格式不正确，只有{len(parts)}个字段")

        return cookies
    
    def _parse_keyvalue_cookies(self, cookies_data: str) -> List[Dict]:
        """解析键值对格式Cookies"""
        cookies = []
        # 处理多行或分号分隔的cookies
        cookie_pairs = re.split(r'[;\n]', cookies_data)

        for pair in cookie_pairs:
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

    def _parse_browser_devtools_cookies(self, cookies_data: str) -> List[Dict]:
        """解析浏览器开发者工具复制格式Cookies"""
        cookies = []
        lines = cookies_data.split('\n')

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    name = parts[0].strip()
                    value = parts[1].strip()

                    # 跳过空值和无效名称
                    if name and value and not name.startswith('//'):
                        cookies.append({
                            'name': name,
                            'value': value,
                            'domain': '',
                            'path': '/',
                            'secure': False,
                            'expiration': 0
                        })
        return cookies

    def _parse_extension_cookies(self, cookies_data: str) -> List[Dict]:
        """解析浏览器扩展导出格式"""
        cookies = []
        try:
            # 尝试作为JSON解析
            if cookies_data.strip().startswith('[') or cookies_data.strip().startswith('{'):
                return self._parse_json_cookies(cookies_data)

            # 否则按行解析
            lines = cookies_data.split('\n')
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                # 查找键值对
                if '=' in line:
                    name, value = line.split('=', 1)
                    cookies.append({
                        'name': name.strip(),
                        'value': value.strip(),
                        'domain': '',
                        'path': '/',
                        'secure': False,
                        'expiration': 0
                    })
        except Exception as e:
            logger.warning(f"⚠️ 扩展格式解析失败: {e}")

        return cookies

    def _parse_curl_cookies(self, cookies_data: str) -> List[Dict]:
        """解析cURL格式的cookies"""
        cookies = []

        # 提取Cookie头部内容
        cookie_header = ''
        for line in cookies_data.split('\n'):
            line = line.strip()
            if line.lower().startswith('cookie:'):
                cookie_header = line[7:].strip()  # 移除'Cookie:'
                break

        if not cookie_header:
            return cookies

        # 解析cookie字符串
        cookie_pairs = cookie_header.split(';')
        for pair in cookie_pairs:
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
    
    def _export_netscape(self, cookies: List[Dict]) -> str:
        """导出为Netscape格式"""
        lines = ['# Netscape HTTP Cookie File', '# Generated by YT-DLP Web V2', '']

        for cookie in cookies:
            domain = cookie.get('domain', '')

            # 修复 domain_specified 字段逻辑
            # 如果域名以 . 开头，domain_specified 应该是 TRUE
            # 如果域名不以 . 开头，domain_specified 应该是 FALSE
            if domain.startswith('.'):
                domain_specified = 'TRUE'
            else:
                domain_specified = 'FALSE'
                # 如果原来的 flag 字段存在，优先使用
                if 'flag' in cookie:
                    domain_specified = 'TRUE' if cookie.get('flag', False) else 'FALSE'

            path = cookie.get('path', '/')
            secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'

            # 处理过期时间，支持多种字段名
            expiration = cookie.get('expiration', 0)
            if expiration == 0:
                expiration = cookie.get('expirationDate', 0)
            if expiration == 0:
                expiration = cookie.get('expires', 0)

            # 确保过期时间是整数
            try:
                expiration = int(float(expiration))
            except (ValueError, TypeError):
                expiration = 0

            name = cookie.get('name', '')
            value = cookie.get('value', '')

            # 确保域名格式正确
            if not domain or not name:
                continue  # 跳过没有域名或名称的cookie

            # 检查是否是示例数据
            if 'PLEASE_REPLACE_WITH_REAL_VALUE' in value or 'example_' in value:
                logger.warning(f"⚠️ 检测到示例数据: {name}={value}")

            line = f"{domain}\t{domain_specified}\t{path}\t{secure}\t{expiration}\t{name}\t{value}"
            lines.append(line)

        return '\n'.join(lines)
    
    def _normalize_website_name(self, website: str) -> str:
        """标准化网站名称"""
        # 移除协议和路径，只保留域名
        if '://' in website:
            website = urlparse(website).netloc
        
        # 移除www前缀
        if website.startswith('www.'):
            website = website[4:]
        
        # 替换特殊字符
        website = re.sub(r'[^\w\-.]', '_', website)
        
        return website.lower()
    
    def _extract_domain(self, url: str) -> str:
        """从URL提取域名"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain.lower()
        except:
            return ''
    
    def _get_current_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()


# 全局实例
_cookies_manager = None

def get_cookies_manager() -> CookiesManager:
    """获取Cookies管理器实例"""
    global _cookies_manager
    if _cookies_manager is None:
        _cookies_manager = CookiesManager()
    return _cookies_manager
