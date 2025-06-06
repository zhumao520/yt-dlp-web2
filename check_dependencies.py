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
            ('flask', 'Flask'),
            ('requests', 'requests'),
            ('yaml', 'PyYAML'),
            ('jwt', 'PyJWT'),
            ('yt_dlp', 'yt-dlp'),
        ]

        for module_name, package_name in required_packages:
            try:
                __import__(module_name)
                logger.info(f"✅ {package_name}: 已安装")
                self.success.append(f"{package_name}")

            except ImportError:
                logger.error(f"❌ {package_name} 未安装")
                self.issues.append(f"{package_name} 未安装")
            except Exception as e:
                logger.warning(f"⚠️ {package_name} 检查异常: {e}")
                self.warnings.append(f"{package_name} 检查异常")
    
    def check_optional_dependencies(self):
        """检查可选依赖"""
        # 检查Telegram相关依赖
        telegram_installed = False
        try:
            import pyrogram
            # 尝试检测是否是PyrogramMod
            try:
                # PyrogramMod通常有更新的版本号
                version = getattr(pyrogram, '__version__', 'unknown')
                if version and version > '2.0.106':
                    logger.info(f"✅ PyrogramMod 已安装 (版本: {version})")
                    self.success.append("PyrogramMod (推荐)")
                else:
                    logger.info(f"✅ Pyrogram 已安装 (版本: {version})")
                    self.success.append("Pyrogram (可选)")
            except:
                logger.info(f"✅ Pyrogram/PyrogramMod 已安装 (Telegram支持)")
                self.success.append("Pyrogram/PyrogramMod (可选)")
            telegram_installed = True
        except ImportError:
            logger.info(f"ℹ️ Pyrogram/PyrogramMod 未安装 (Telegram大文件支持)")

        # 检查TgCrypto
        try:
            import tgcrypto
            logger.info(f"✅ TgCrypto 已安装 (Telegram加密优化)")
            self.success.append("TgCrypto (可选)")
        except ImportError:
            logger.info(f"ℹ️ TgCrypto 未安装 (Telegram加密优化)")

        # 检查开发工具
        dev_packages = [
            ('pytest', 'pytest', '单元测试'),
            ('black', 'black', '代码格式化'),
            ('flake8', 'flake8', '代码检查'),
        ]

        for module_name, package_name, description in dev_packages:
            try:
                __import__(module_name)
                logger.info(f"✅ {package_name} 已安装 ({description})")
                self.success.append(f"{package_name} (开发工具)")
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
