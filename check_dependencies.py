#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YT-DLP Web V2 依赖检查脚本
检查所有必需的系统和Python依赖
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DependencyChecker:
    """依赖检查器"""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.success = []
    
    def check_all_dependencies(self):
        """检查所有依赖"""
        logger.info("🔍 开始检查系统依赖...")
        
        # 检查Python版本
        self.check_python_version()
        
        # 检查系统依赖
        self.check_system_dependencies()
        
        # 检查Python包依赖
        self.check_python_packages()
        
        # 检查可选依赖
        self.check_optional_dependencies()
        
        # 输出报告
        self.print_report()
        
        return len(self.issues) == 0
    
    def check_python_version(self):
        """检查Python版本"""
        try:
            version = sys.version_info
            version_str = f"{version.major}.{version.minor}.{version.micro}"
            
            if version.major == 3 and version.minor >= 9:
                logger.info(f"✅ Python版本: {version_str}")
                self.success.append(f"Python {version_str}")
            else:
                logger.error(f"❌ Python版本过低: {version_str}，需要3.9+")
                self.issues.append(f"Python版本过低: {version_str}")
                
        except Exception as e:
            logger.error(f"❌ Python版本检查失败: {e}")
            self.issues.append(f"Python版本检查失败: {e}")
    
    def check_system_dependencies(self):
        """检查系统依赖"""
        # 检查是否在容器环境
        in_docker = os.environ.get('DOCKER_CONTAINER') == '1'
        
        if in_docker:
            logger.info("🐳 检测到Docker容器环境")
            self.success.append("Docker容器环境（依赖预装）")
            return
        
        # 检查FFmpeg
        if self._check_command('ffmpeg'):
            try:
                result = subprocess.run(['ffmpeg', '-version'], 
                                      capture_output=True, text=True, timeout=5)
                version_line = result.stdout.split('\n')[0]
                logger.info(f"✅ FFmpeg: {version_line}")
                self.success.append("FFmpeg")
            except Exception:
                logger.info("✅ FFmpeg 已安装")
                self.success.append("FFmpeg")
        else:
            logger.warning("⚠️ FFmpeg 未安装，音频转换功能可能受限")
            self.warnings.append("FFmpeg 未安装")
        
        # 检查Git（可选）
        if self._check_command('git'):
            logger.info("✅ Git 已安装")
            self.success.append("Git")
        else:
            logger.info("ℹ️ Git 未安装（可选依赖）")
    
    def check_python_packages(self):
        """检查Python包依赖"""
        required_packages = [
            ('flask', 'Flask', '2.0.0'),
            ('requests', 'requests', '2.25.0'),
            ('yaml', 'PyYAML', '5.4.0'),
            ('jwt', 'PyJWT', '2.0.0'),
            ('yt_dlp', 'yt-dlp', '2023.1.0'),
        ]
        
        for module_name, package_name, min_version in required_packages:
            try:
                module = __import__(module_name)
                
                # 获取版本信息
                version = getattr(module, '__version__', None)
                if not version and hasattr(module, 'version'):
                    version = getattr(module.version, '__version__', 'unknown')
                if not version:
                    version = 'unknown'
                
                logger.info(f"✅ {package_name}: {version}")
                self.success.append(f"{package_name} {version}")
                
            except ImportError:
                logger.error(f"❌ {package_name} 未安装")
                self.issues.append(f"{package_name} 未安装")
            except Exception as e:
                logger.warning(f"⚠️ {package_name} 检查异常: {e}")
                self.warnings.append(f"{package_name} 检查异常")
    
    def check_optional_dependencies(self):
        """检查可选依赖"""
        optional_packages = [
            ('pyrogram', 'Pyrogram', 'Telegram大文件支持'),
            ('tgcrypto', 'TgCrypto', 'Telegram加密优化'),
        ]
        
        for module_name, package_name, description in optional_packages:
            try:
                __import__(module_name)
                logger.info(f"✅ {package_name} 已安装 ({description})")
                self.success.append(f"{package_name} (可选)")
            except ImportError:
                logger.info(f"ℹ️ {package_name} 未安装 ({description})")
    
    def _check_command(self, command):
        """检查命令是否可用"""
        try:
            subprocess.run([command, '--version'], 
                         capture_output=True, timeout=5)
            return True
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
            return False
    
    def print_report(self):
        """打印检查报告"""
        logger.info(f"\n{'='*60}")
        logger.info("📊 依赖检查报告")
        logger.info(f"{'='*60}")
        
        if self.success:
            logger.info("✅ 已安装的依赖:")
            for item in self.success:
                logger.info(f"   • {item}")
        
        if self.warnings:
            logger.info("\n⚠️ 警告:")
            for item in self.warnings:
                logger.info(f"   • {item}")
        
        if self.issues:
            logger.info("\n❌ 缺失的依赖:")
            for item in self.issues:
                logger.info(f"   • {item}")
            
            logger.info("\n🔧 修复建议:")
            logger.info("   1. 运行: pip install -r requirements.txt")
            logger.info("   2. 运行: python fix_common_issues.py")
            logger.info("   3. 检查系统包管理器安装FFmpeg")
        
        logger.info(f"\n📈 统计:")
        logger.info(f"   成功: {len(self.success)}")
        logger.info(f"   警告: {len(self.warnings)}")
        logger.info(f"   错误: {len(self.issues)}")
        
        if not self.issues:
            logger.info("\n🎉 所有必需依赖检查通过！")
        else:
            logger.info(f"\n❌ 发现 {len(self.issues)} 个问题需要修复")
    
    def get_installation_commands(self):
        """获取安装命令建议"""
        commands = []
        
        # Python包安装
        if any('未安装' in issue for issue in self.issues):
            commands.append("pip install -r requirements.txt")
        
        # 系统包安装建议
        if any('FFmpeg' in warning for warning in self.warnings):
            commands.extend([
                "# Ubuntu/Debian:",
                "sudo apt update && sudo apt install ffmpeg",
                "",
                "# CentOS/RHEL:",
                "sudo yum install ffmpeg",
                "",
                "# macOS:",
                "brew install ffmpeg"
            ])
        
        return commands


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='YT-DLP Web V2 依赖检查')
    parser.add_argument('--fix', action='store_true',
                       help='检查后自动运行修复脚本')
    parser.add_argument('--install-commands', action='store_true',
                       help='显示安装命令建议')
    
    args = parser.parse_args()
    
    checker = DependencyChecker()
    success = checker.check_all_dependencies()
    
    if args.install_commands:
        commands = checker.get_installation_commands()
        if commands:
            logger.info("\n🔧 建议的安装命令:")
            for cmd in commands:
                logger.info(f"   {cmd}")
    
    if args.fix and not success:
        logger.info("\n🔧 运行自动修复...")
        try:
            subprocess.run([sys.executable, 'fix_common_issues.py'], check=True)
        except subprocess.CalledProcessError:
            logger.error("❌ 自动修复失败")
    
    # 返回退出码
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
