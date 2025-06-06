# -*- coding: utf-8 -*-
"""
yt-dlp安装器 - 自动下载和安装yt-dlp
"""

import os
import sys
import logging
import requests
import zipfile
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class YtdlpInstaller:
    """yt-dlp自动安装器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.ytdlp_dir = self.project_root / 'yt_dlp'
        self.temp_dir = self.project_root / 'temp'
        
    def ensure_ytdlp(self) -> bool:
        """确保yt-dlp可用"""
        try:
            # 检查是否已经可用
            if self._check_ytdlp_available():
                logger.info("✅ yt-dlp已可用")
                return True
            
            # 检测环境并选择安装策略
            from .environment_detector import EnvironmentDetector
            detector = EnvironmentDetector()
            env_info = detector.detect()
            
            strategy = detector.get_install_strategy()
            logger.info(f"🔧 使用安装策略: {strategy}")
            
            if strategy == 'use_prebuilt':
                return self._use_prebuilt_ytdlp()
            elif strategy == 'github_release':
                return self._install_from_github()
            elif strategy == 'pip_install':
                return self._install_from_pip()
            else:
                return self._auto_install()
                
        except Exception as e:
            logger.error(f"❌ yt-dlp安装失败: {e}")
            return False
    
    def _check_ytdlp_available(self) -> bool:
        """检查yt-dlp是否可用"""
        try:
            import yt_dlp
            logger.debug("✅ yt-dlp模块导入成功")
            return True
        except ImportError:
            logger.debug("⚠️ yt-dlp模块未找到")
            return False
    
    def _use_prebuilt_ytdlp(self) -> bool:
        """使用预构建的yt-dlp"""
        try:
            prebuilt_paths = [
                '/ytdlp-prepared',
                '/app/yt-dlp',
                './yt-dlp'
            ]
            
            for path in prebuilt_paths:
                source_path = Path(path)
                if source_path.exists():
                    logger.info(f"📦 发现预构建yt-dlp: {source_path}")
                    
                    # 复制到项目目录
                    if source_path != self.ytdlp_dir:
                        if self.ytdlp_dir.exists():
                            shutil.rmtree(self.ytdlp_dir)
                        shutil.copytree(source_path, self.ytdlp_dir)
                        logger.info(f"📁 复制到: {self.ytdlp_dir}")
                    
                    # 添加到Python路径
                    self._add_to_python_path()
                    
                    # 验证安装
                    if self._check_ytdlp_available():
                        logger.info("✅ 预构建yt-dlp使用成功")
                        return True
            
            logger.warning("⚠️ 未找到预构建yt-dlp")
            return False
            
        except Exception as e:
            logger.error(f"❌ 使用预构建yt-dlp失败: {e}")
            return False
    
    def _install_from_github(self) -> bool:
        """从GitHub下载最新版本"""
        try:
            logger.info("🔽 从GitHub下载yt-dlp...")
            
            # 获取最新版本信息
            api_url = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
            response = requests.get(api_url, timeout=30)
            response.raise_for_status()
            
            release_info = response.json()
            version = release_info['tag_name']
            logger.info(f"📋 最新版本: {version}")
            
            # 查找源码包
            download_url = None
            for asset in release_info['assets']:
                if asset['name'].endswith('.tar.gz') and 'source' in asset['name'].lower():
                    download_url = asset['browser_download_url']
                    break
            
            # 如果没有找到源码包，使用zipball
            if not download_url:
                download_url = release_info['zipball_url']
            
            # 下载并解压
            return self._download_and_extract(download_url, version)
            
        except Exception as e:
            logger.error(f"❌ 从GitHub安装失败: {e}")
            return False
    
    def _install_from_pip(self) -> bool:
        """使用pip安装"""
        try:
            logger.info("📦 使用pip安装yt-dlp...")
            
            # 尝试pip安装
            result = subprocess.run([
                sys.executable, '-m', 'pip', 'install', 
                '--no-cache-dir', '--upgrade', 'yt-dlp'
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info("✅ pip安装成功")
                return self._check_ytdlp_available()
            else:
                logger.error(f"❌ pip安装失败: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ pip安装异常: {e}")
            return False
    
    def _auto_install(self) -> bool:
        """自动选择最佳安装方式"""
        try:
            # 优先尝试pip安装
            if self._install_from_pip():
                return True
            
            # pip失败则尝试GitHub
            if self._install_from_github():
                return True
            
            logger.error("❌ 所有安装方式都失败了")
            return False
            
        except Exception as e:
            logger.error(f"❌ 自动安装失败: {e}")
            return False
    
    def _download_and_extract(self, url: str, version: str) -> bool:
        """下载并解压yt-dlp"""
        try:
            # 创建临时目录
            self.temp_dir.mkdir(exist_ok=True)
            
            # 下载文件
            logger.info(f"⬇️ 下载: {url}")
            response = requests.get(url, timeout=300, stream=True)
            response.raise_for_status()
            
            # 保存到临时文件
            temp_file = self.temp_dir / f"yt-dlp-{version}.zip"
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"💾 下载完成: {temp_file}")
            
            # 解压文件
            extract_dir = self.temp_dir / f"yt-dlp-{version}"
            with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # 查找yt_dlp目录
            ytdlp_source = None
            for item in extract_dir.rglob('yt_dlp'):
                if item.is_dir() and (item / '__init__.py').exists():
                    ytdlp_source = item
                    break
            
            if not ytdlp_source:
                logger.error("❌ 未找到yt_dlp源码目录")
                return False
            
            # 复制到项目目录
            if self.ytdlp_dir.exists():
                shutil.rmtree(self.ytdlp_dir)
            shutil.copytree(ytdlp_source, self.ytdlp_dir)
            
            # 清理临时文件
            shutil.rmtree(self.temp_dir)
            
            # 添加到Python路径
            self._add_to_python_path()
            
            # 验证安装
            if self._check_ytdlp_available():
                logger.info(f"✅ yt-dlp {version} 安装成功")
                return True
            else:
                logger.error("❌ yt-dlp安装验证失败")
                return False
                
        except Exception as e:
            logger.error(f"❌ 下载解压失败: {e}")
            return False
    
    def _add_to_python_path(self):
        """将yt-dlp目录添加到Python路径"""
        try:
            ytdlp_parent = str(self.ytdlp_dir.parent)
            if ytdlp_parent not in sys.path:
                sys.path.insert(0, ytdlp_parent)
                logger.debug(f"📍 添加到Python路径: {ytdlp_parent}")
        except Exception as e:
            logger.error(f"❌ 添加Python路径失败: {e}")
    
    def get_ytdlp_info(self) -> Optional[Dict[str, Any]]:
        """获取yt-dlp信息"""
        try:
            if not self._check_ytdlp_available():
                return None
            
            import yt_dlp
            
            # 获取版本信息
            version = getattr(yt_dlp, '__version__', 'unknown')
            
            # 获取模块路径
            module_path = getattr(yt_dlp, '__file__', 'unknown')
            
            return {
                'version': version,
                'module_path': module_path,
                'available': True,
                'install_path': str(self.ytdlp_dir) if self.ytdlp_dir.exists() else None
            }
            
        except Exception as e:
            logger.error(f"❌ 获取yt-dlp信息失败: {e}")
            return None
    
    def cleanup(self):
        """清理临时文件"""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                logger.info("🗑️ 清理临时文件完成")
        except Exception as e:
            logger.error(f"❌ 清理临时文件失败: {e}")


if __name__ == '__main__':
    # 测试安装器
    logging.basicConfig(level=logging.INFO)
    
    installer = YtdlpInstaller()
    
    print("🔧 开始安装yt-dlp...")
    success = installer.ensure_ytdlp()
    
    if success:
        print("✅ yt-dlp安装成功")
        info = installer.get_ytdlp_info()
        if info:
            print(f"版本: {info['version']}")
            print(f"路径: {info['module_path']}")
    else:
        print("❌ yt-dlp安装失败")
    
    installer.cleanup()
