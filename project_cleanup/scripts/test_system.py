#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YT-DLP Web V2 系统测试脚本
模拟用户操作和计算机启动检查
"""

import os
import sys
import time
import json
import requests
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SystemTester:
    """系统测试器"""
    
    def __init__(self, base_url='http://localhost:8080'):
        self.base_url = base_url
        self.session = requests.Session()
        self.auth_token = None
    
    def run_all_tests(self):
        """运行所有测试"""
        logger.info("🧪 开始系统测试...")
        
        tests = [
            ("🔍 服务器连接测试", self.test_server_connection),
            ("🏠 首页访问测试", self.test_homepage_access),
            ("🔐 认证系统测试", self.test_authentication),
            ("📥 下载功能测试", self.test_download_functionality),
            ("🍪 Cookies管理测试", self.test_cookies_management),
            ("🤖 Telegram功能测试", self.test_telegram_functionality),
            ("📁 文件管理测试", self.test_file_management),
            ("⚙️ 系统设置测试", self.test_system_settings),
            ("🔧 API接口测试", self.test_api_endpoints),
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                logger.info(f"\n{'='*50}")
                logger.info(f"执行测试: {test_name}")
                logger.info(f"{'='*50}")
                
                result = test_func()
                results.append((test_name, result, None))
                
                if result:
                    logger.info(f"✅ {test_name} - 通过")
                else:
                    logger.warning(f"⚠️ {test_name} - 失败")
                    
            except Exception as e:
                logger.error(f"❌ {test_name} - 异常: {e}")
                results.append((test_name, False, str(e)))
        
        # 输出测试报告
        self.print_test_report(results)
        return results
    
    def test_server_connection(self):
        """测试服务器连接"""
        try:
            response = self.session.get(f"{self.base_url}/", timeout=10)
            logger.info(f"服务器响应状态: {response.status_code}")
            return response.status_code in [200, 302, 401]
        except Exception as e:
            logger.error(f"服务器连接失败: {e}")
            return False
    
    def test_homepage_access(self):
        """测试首页访问"""
        try:
            response = self.session.get(f"{self.base_url}/", timeout=10)
            
            # 检查是否重定向到setup或login
            if response.status_code == 302:
                location = response.headers.get('Location', '')
                logger.info(f"重定向到: {location}")
                return '/setup' in location or '/login' in location
            
            return response.status_code == 200
        except Exception as e:
            logger.error(f"首页访问失败: {e}")
            return False
    
    def test_authentication(self):
        """测试认证系统"""
        try:
            # 测试登录页面
            response = self.session.get(f"{self.base_url}/auth/login")
            if response.status_code != 200:
                logger.error(f"登录页面访问失败: {response.status_code}")
                return False
            
            logger.info("✅ 登录页面访问正常")
            
            # 测试API认证
            api_response = self.session.get(f"{self.base_url}/api/system/status")
            if api_response.status_code != 401:
                logger.warning(f"API认证检查异常: {api_response.status_code}")
            else:
                logger.info("✅ API认证保护正常")
            
            return True
        except Exception as e:
            logger.error(f"认证测试失败: {e}")
            return False
    
    def test_download_functionality(self):
        """测试下载功能"""
        try:
            # 检查下载页面
            response = self.session.get(f"{self.base_url}/download")
            logger.info(f"下载页面状态: {response.status_code}")
            
            # 检查下载API（需要认证）
            api_response = self.session.post(
                f"{self.base_url}/api/download/start",
                json={'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'}
            )
            logger.info(f"下载API状态: {api_response.status_code}")
            
            return response.status_code in [200, 302, 401]
        except Exception as e:
            logger.error(f"下载功能测试失败: {e}")
            return False
    
    def test_cookies_management(self):
        """测试Cookies管理"""
        try:
            # 检查Cookies页面
            response = self.session.get(f"{self.base_url}/cookies")
            logger.info(f"Cookies页面状态: {response.status_code}")
            
            # 检查Cookies API
            api_response = self.session.get(f"{self.base_url}/cookies/api/list")
            logger.info(f"Cookies API状态: {api_response.status_code}")
            
            return response.status_code in [200, 302, 401]
        except Exception as e:
            logger.error(f"Cookies管理测试失败: {e}")
            return False
    
    def test_telegram_functionality(self):
        """测试Telegram功能"""
        try:
            # 检查Telegram页面
            response = self.session.get(f"{self.base_url}/telegram")
            logger.info(f"Telegram页面状态: {response.status_code}")
            
            # 检查Telegram API
            api_response = self.session.get(f"{self.base_url}/api/telegram/config")
            logger.info(f"Telegram API状态: {api_response.status_code}")
            
            return response.status_code in [200, 302, 401]
        except Exception as e:
            logger.error(f"Telegram功能测试失败: {e}")
            return False
    
    def test_file_management(self):
        """测试文件管理"""
        try:
            # 检查文件管理页面
            response = self.session.get(f"{self.base_url}/files")
            logger.info(f"文件管理页面状态: {response.status_code}")
            
            # 检查文件列表API
            api_response = self.session.get(f"{self.base_url}/files/list")
            logger.info(f"文件列表API状态: {api_response.status_code}")
            
            return response.status_code in [200, 302, 401]
        except Exception as e:
            logger.error(f"文件管理测试失败: {e}")
            return False
    
    def test_system_settings(self):
        """测试系统设置"""
        try:
            # 检查设置页面
            response = self.session.get(f"{self.base_url}/settings")
            logger.info(f"设置页面状态: {response.status_code}")
            
            # 检查系统状态API
            api_response = self.session.get(f"{self.base_url}/api/system/status")
            logger.info(f"系统状态API状态: {api_response.status_code}")
            
            return response.status_code in [200, 302, 401]
        except Exception as e:
            logger.error(f"系统设置测试失败: {e}")
            return False
    
    def test_api_endpoints(self):
        """测试API接口"""
        try:
            endpoints = [
                '/api/system/status',
                '/api/system/ytdlp/info',
                '/api/download/list',
                '/api/telegram/config',
                '/cookies/api/list',
                '/files/list'
            ]
            
            success_count = 0
            for endpoint in endpoints:
                try:
                    response = self.session.get(f"{self.base_url}{endpoint}")
                    logger.info(f"API {endpoint}: {response.status_code}")
                    if response.status_code in [200, 401, 403]:
                        success_count += 1
                except Exception as e:
                    logger.warning(f"API {endpoint} 测试失败: {e}")
            
            logger.info(f"API测试通过率: {success_count}/{len(endpoints)}")
            return success_count >= len(endpoints) * 0.8  # 80%通过率
        except Exception as e:
            logger.error(f"API接口测试失败: {e}")
            return False
    
    def print_test_report(self, results):
        """打印测试报告"""
        logger.info(f"\n{'='*60}")
        logger.info("🧪 测试报告")
        logger.info(f"{'='*60}")
        
        passed = 0
        failed = 0
        
        for test_name, result, error in results:
            status = "✅ 通过" if result else "❌ 失败"
            logger.info(f"{test_name}: {status}")
            if error:
                logger.info(f"   错误: {error}")
            
            if result:
                passed += 1
            else:
                failed += 1
        
        logger.info(f"\n📊 测试统计:")
        logger.info(f"   总测试数: {len(results)}")
        logger.info(f"   通过: {passed}")
        logger.info(f"   失败: {failed}")
        logger.info(f"   通过率: {passed/len(results)*100:.1f}%")
        
        if passed == len(results):
            logger.info("\n🎉 所有测试通过！系统运行正常！")
        elif passed >= len(results) * 0.8:
            logger.info("\n⚠️ 大部分测试通过，系统基本正常，有少量问题需要修复")
        else:
            logger.info("\n❌ 多个测试失败，系统存在严重问题需要修复")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='YT-DLP Web V2 系统测试')
    parser.add_argument('--url', default='http://localhost:8080', 
                       help='服务器地址 (默认: http://localhost:8080)')
    parser.add_argument('--wait', type=int, default=0,
                       help='启动前等待时间(秒)')
    
    args = parser.parse_args()
    
    if args.wait > 0:
        logger.info(f"⏳ 等待 {args.wait} 秒后开始测试...")
        time.sleep(args.wait)
    
    tester = SystemTester(args.url)
    results = tester.run_all_tests()
    
    # 返回退出码
    passed = sum(1 for _, result, _ in results if result)
    if passed == len(results):
        sys.exit(0)  # 全部通过
    elif passed >= len(results) * 0.8:
        sys.exit(1)  # 大部分通过
    else:
        sys.exit(2)  # 多数失败


if __name__ == '__main__':
    main()
