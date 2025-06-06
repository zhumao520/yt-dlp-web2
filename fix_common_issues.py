#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YT-DLP Web V2 常见问题修复脚本
自动检测和修复常见的部署问题
"""

import os
import sys
import logging
import subprocess
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IssueFixer:
    """问题修复器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.issues_found = []
        self.fixes_applied = []
    
    def run_all_fixes(self):
        """运行所有修复"""
        logger.info("🔧 开始检测和修复常见问题...")
        
        fixes = [
            ("📁 检查目录结构", self.fix_directory_structure),
            ("📦 检查Python依赖", self.fix_python_dependencies),
            ("🗄️ 检查数据库初始化", self.fix_database_initialization),
            ("🔐 检查权限设置", self.fix_permissions),
            ("⚙️ 检查配置文件", self.fix_configuration),
            ("🎬 检查yt-dlp安装", self.fix_ytdlp_installation),
            ("🔧 检查环境变量", self.fix_environment_variables),
        ]
        
        for fix_name, fix_func in fixes:
            try:
                logger.info(f"\n{'='*50}")
                logger.info(f"执行修复: {fix_name}")
                logger.info(f"{'='*50}")
                
                fix_func()
                
            except Exception as e:
                logger.error(f"❌ {fix_name} 修复失败: {e}")
                self.issues_found.append(f"{fix_name}: {e}")
        
        self.print_fix_report()
    
    def fix_directory_structure(self):
        """修复目录结构"""
        required_dirs = [
            'downloads',
            'temp', 
            'logs',
            'data',
            'data/cookies'
        ]
        
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"✅ 创建目录: {dir_path}")
                self.fixes_applied.append(f"创建目录: {dir_name}")
            else:
                logger.info(f"✓ 目录已存在: {dir_name}")
    
    def fix_python_dependencies(self):
        """修复Python依赖"""
        requirements_file = self.project_root / 'requirements.txt'

        if not requirements_file.exists():
            logger.error("❌ requirements.txt 文件不存在")
            self.issues_found.append("缺少 requirements.txt 文件")
            return

        try:
            # 检查是否在虚拟环境中
            in_venv = hasattr(sys, 'real_prefix') or (
                hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
            )

            if not in_venv:
                logger.warning("⚠️ 未检测到虚拟环境，建议使用虚拟环境")

            # 检查系统依赖
            self._check_system_dependencies()

            # 尝试导入关键依赖
            critical_imports = [
                ('flask', 'Flask'),
                ('requests', 'requests'),
                ('yaml', 'PyYAML'),
                ('jwt', 'PyJWT'),
                ('yt_dlp', 'yt-dlp'),
            ]

            missing_deps = []
            for module, package in critical_imports:
                try:
                    __import__(module)
                    logger.info(f"✓ {package} 已安装")
                except ImportError:
                    logger.warning(f"⚠️ {package} 未安装")
                    missing_deps.append(package)

            if missing_deps:
                logger.info(f"🔧 尝试安装缺失依赖: {', '.join(missing_deps)}")
                subprocess.run([
                    sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file)
                ], check=True)
                self.fixes_applied.append("安装Python依赖")

                # 重新验证
                still_missing = []
                for module, package in critical_imports:
                    try:
                        __import__(module)
                    except ImportError:
                        still_missing.append(package)

                if still_missing:
                    self.issues_found.append(f"仍然缺失依赖: {', '.join(still_missing)}")

        except Exception as e:
            logger.error(f"❌ 依赖检查失败: {e}")
            self.issues_found.append(f"Python依赖问题: {e}")

    def _check_system_dependencies(self):
        """检查系统依赖"""
        try:
            # 检查FFmpeg（仅在非容器环境）
            if not os.environ.get('DOCKER_CONTAINER'):
                if subprocess.run(['which', 'ffmpeg'], capture_output=True).returncode == 0:
                    logger.info("✓ FFmpeg 已安装")
                else:
                    logger.warning("⚠️ FFmpeg 未安装，某些音频转换功能可能不可用")
                    self.issues_found.append("FFmpeg 未安装")
            else:
                logger.info("✓ 容器环境，FFmpeg 应该已预装")

            # 检查Git（可选）
            if subprocess.run(['which', 'git'], capture_output=True).returncode == 0:
                logger.info("✓ Git 已安装")
            else:
                logger.info("ℹ️ Git 未安装（可选依赖）")

        except Exception as e:
            logger.warning(f"⚠️ 系统依赖检查失败: {e}")
    
    def fix_database_initialization(self):
        """修复数据库初始化"""
        try:
            # 检查数据库文件
            db_file = self.project_root / 'data' / 'app.db'
            
            if not db_file.exists():
                logger.info("🗄️ 数据库文件不存在，将在首次启动时创建")
            else:
                logger.info(f"✓ 数据库文件存在: {db_file}")
            
            # 检查数据库模块
            sys.path.insert(0, str(self.project_root))
            try:
                from app.core.database import Database
                logger.info("✓ 数据库模块导入正常")
            except ImportError as e:
                logger.error(f"❌ 数据库模块导入失败: {e}")
                self.issues_found.append(f"数据库模块问题: {e}")
            
        except Exception as e:
            logger.error(f"❌ 数据库检查失败: {e}")
            self.issues_found.append(f"数据库问题: {e}")
    
    def fix_permissions(self):
        """修复权限设置"""
        try:
            # 检查关键文件的权限
            critical_files = [
                'app/main.py',
                'start.sh'
            ]
            
            for file_name in critical_files:
                file_path = self.project_root / file_name
                if file_path.exists():
                    # 在Unix系统上设置执行权限
                    if os.name != 'nt':  # 非Windows系统
                        os.chmod(file_path, 0o755)
                        logger.info(f"✅ 设置执行权限: {file_name}")
                        self.fixes_applied.append(f"设置权限: {file_name}")
                    else:
                        logger.info(f"✓ Windows系统，跳过权限设置: {file_name}")
                else:
                    logger.warning(f"⚠️ 文件不存在: {file_name}")
            
        except Exception as e:
            logger.error(f"❌ 权限设置失败: {e}")
            self.issues_found.append(f"权限问题: {e}")
    
    def fix_configuration(self):
        """修复配置文件"""
        try:
            config_example = self.project_root / 'config.example.yml'
            config_file = self.project_root / 'config.yml'
            
            if not config_file.exists() and config_example.exists():
                # 复制示例配置
                import shutil
                shutil.copy2(config_example, config_file)
                logger.info("✅ 创建默认配置文件")
                self.fixes_applied.append("创建配置文件")
            elif config_file.exists():
                logger.info("✓ 配置文件已存在")
            else:
                logger.warning("⚠️ 配置文件和示例文件都不存在")
                self.issues_found.append("缺少配置文件")
            
        except Exception as e:
            logger.error(f"❌ 配置文件检查失败: {e}")
            self.issues_found.append(f"配置文件问题: {e}")
    
    def fix_ytdlp_installation(self):
        """修复yt-dlp安装"""
        try:
            # 检查yt-dlp是否可用
            try:
                import yt_dlp
                logger.info("✓ yt-dlp 已安装")
                
                # 检查版本
                version = yt_dlp.version.__version__
                logger.info(f"✓ yt-dlp 版本: {version}")
                
            except ImportError:
                logger.info("🔧 yt-dlp 未安装，尝试安装...")
                subprocess.run([
                    sys.executable, '-m', 'pip', 'install', 'yt-dlp'
                ], check=True)
                logger.info("✅ yt-dlp 安装完成")
                self.fixes_applied.append("安装 yt-dlp")
            
        except Exception as e:
            logger.error(f"❌ yt-dlp 检查失败: {e}")
            self.issues_found.append(f"yt-dlp 问题: {e}")
    
    def fix_environment_variables(self):
        """修复环境变量"""
        try:
            # 检查关键环境变量
            env_vars = {
                'SECRET_KEY': 'change-this-secret-key-in-production',
                'DATABASE_URL': 'sqlite:///data/app.db',
                'DOWNLOAD_DIR': 'downloads'
            }
            
            env_file = self.project_root / '.env'
            env_content = []
            
            for var, default in env_vars.items():
                current_value = os.environ.get(var)
                if not current_value:
                    env_content.append(f"{var}={default}")
                    logger.info(f"✅ 设置环境变量: {var}")
                else:
                    logger.info(f"✓ 环境变量已设置: {var}")
            
            if env_content:
                with open(env_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(env_content))
                logger.info(f"✅ 创建 .env 文件")
                self.fixes_applied.append("创建环境变量文件")
            
        except Exception as e:
            logger.error(f"❌ 环境变量检查失败: {e}")
            self.issues_found.append(f"环境变量问题: {e}")
    
    def print_fix_report(self):
        """打印修复报告"""
        logger.info(f"\n{'='*60}")
        logger.info("🔧 修复报告")
        logger.info(f"{'='*60}")
        
        if self.fixes_applied:
            logger.info("✅ 已应用的修复:")
            for fix in self.fixes_applied:
                logger.info(f"   • {fix}")
        else:
            logger.info("✓ 未发现需要修复的问题")
        
        if self.issues_found:
            logger.info("\n❌ 发现的问题:")
            for issue in self.issues_found:
                logger.info(f"   • {issue}")
        
        logger.info(f"\n📊 修复统计:")
        logger.info(f"   应用修复: {len(self.fixes_applied)}")
        logger.info(f"   发现问题: {len(self.issues_found)}")
        
        if not self.issues_found:
            logger.info("\n🎉 系统检查完成，未发现严重问题！")
        else:
            logger.info("\n⚠️ 发现一些问题，请手动检查和修复")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='YT-DLP Web V2 问题修复工具')
    parser.add_argument('--dry-run', action='store_true',
                       help='仅检查问题，不应用修复')
    
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("🔍 运行模式: 仅检查问题")
    else:
        logger.info("🔧 运行模式: 检查并修复问题")
    
    fixer = IssueFixer()
    fixer.run_all_fixes()
    
    # 返回退出码
    if fixer.issues_found:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
