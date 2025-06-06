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
            
            # 查找匹配的Cookies文件
            for cookies_file in self.cookies_dir.glob("*.json"):
                website = cookies_file.stem
                if domain in website or website in domain:
                    # 转换为Netscape格式并保存临时文件
                    temp_file = self.cookies_dir / f"{website}_temp.txt"
                    export_result = self.export_cookies(website, 'netscape')
                    
                    if export_result['success']:
                        with open(temp_file, 'w', encoding='utf-8') as f:
                            f.write(export_result['content'])
                        return str(temp_file)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 获取yt-dlp Cookies失败: {e}")
            return None
    
    def _detect_format(self, cookies_data: str) -> str:
        """检测Cookies格式"""
        cookies_data = cookies_data.strip()
        
        # JSON格式检测
        if cookies_data.startswith('[') or cookies_data.startswith('{'):
            try:
                json.loads(cookies_data)
                return 'json'
            except:
                pass
        
        # Netscape格式检测
        if '# Netscape HTTP Cookie File' in cookies_data or '\t' in cookies_data:
            return 'netscape'
        
        # 简单键值对格式
        if '=' in cookies_data and (';' in cookies_data or '\n' in cookies_data):
            return 'header'
        
        return 'unknown'
    
    def _parse_cookies(self, cookies_data: str, format_type: str) -> List[Dict]:
        """解析Cookies数据"""
        try:
            if format_type == 'json':
                return self._parse_json_cookies(cookies_data)
            elif format_type == 'netscape':
                return self._parse_netscape_cookies(cookies_data)
            elif format_type == 'header':
                return self._parse_header_cookies(cookies_data)
            else:
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
        for line in cookies_data.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split('\t')
            if len(parts) >= 7:
                cookies.append({
                    'domain': parts[0],
                    'flag': parts[1] == 'TRUE',
                    'path': parts[2],
                    'secure': parts[3] == 'TRUE',
                    'expiration': int(parts[4]) if parts[4] != '0' else 0,
                    'name': parts[5],
                    'value': parts[6]
                })
        return cookies
    
    def _parse_header_cookies(self, cookies_data: str) -> List[Dict]:
        """解析Header格式Cookies"""
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
    
    def _export_netscape(self, cookies: List[Dict]) -> str:
        """导出为Netscape格式"""
        lines = ['# Netscape HTTP Cookie File']
        
        for cookie in cookies:
            domain = cookie.get('domain', '')
            flag = 'TRUE' if cookie.get('flag', False) else 'FALSE'
            path = cookie.get('path', '/')
            secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
            expiration = str(cookie.get('expiration', 0))
            name = cookie.get('name', '')
            value = cookie.get('value', '')
            
            line = f"{domain}\t{flag}\t{path}\t{secure}\t{expiration}\t{name}\t{value}"
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
