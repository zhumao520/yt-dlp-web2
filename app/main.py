#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YT-DLP Web V2 - 应用入口点
轻量化可扩展架构
"""

import os
import sys
import logging
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core import create_app, Config
from app.scripts.environment_detector import EnvironmentDetector
from app.scripts.ytdlp_installer import YtdlpInstaller

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_environment():
    """环境检测和初始化"""
    try:
        logger.info("🔍 检测运行环境...")
        
        # 环境检测
        detector = EnvironmentDetector()
        env_info = detector.detect()
        
        logger.info(f"📋 环境信息: {env_info['environment']}")
        logger.info(f"🐳 容器环境: {env_info['is_container']}")
        logger.info(f"🏗️ 构建环境: {env_info['is_build_environment']}")
        
        # yt-dlp 安装检查
        installer = YtdlpInstaller()
        
        if env_info['is_build_environment']:
            logger.info("🏗️ 构建环境检测到，跳过运行时yt-dlp安装")
        else:
            logger.info("🔽 检查并安装yt-dlp...")
            if installer.ensure_ytdlp():
                logger.info("✅ yt-dlp 准备就绪")
            else:
                logger.warning("⚠️ yt-dlp 安装失败，部分功能可能不可用")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 环境初始化失败: {e}")
        return False


def main():
    """主函数"""
    try:
        logger.info("🚀 启动 YT-DLP Web V2...")
        
        # 环境初始化
        if not setup_environment():
            logger.error("❌ 环境初始化失败，退出")
            sys.exit(1)
        
        # 创建Flask应用
        logger.info("🔧 创建Flask应用...")
        app = create_app()

        # 初始化数据库
        logger.info("🗄️ 初始化数据库...")
        with app.app_context():
            from app.core.database import get_database
            db = get_database()

            # 确保管理员用户存在
            logger.info("👤 检查管理员用户...")
            if not db.ensure_admin_user_exists():
                logger.error("❌ 管理员用户创建失败")
                sys.exit(1)

            logger.info("✅ 数据库初始化完成")

        # 获取配置
        config = Config()
        host = config.get('app.host', '0.0.0.0')
        port = config.get('app.port', 8080)
        debug = config.get('app.debug', False)
        
        logger.info(f"🌐 启动Web服务器: http://{host}:{port}")
        
        # 启动应用
        app.run(
            host=host,
            port=port,
            debug=debug,
            threaded=True
        )
        
    except KeyboardInterrupt:
        logger.info("👋 用户中断，正在退出...")
    except Exception as e:
        logger.error(f"❌ 应用启动失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
