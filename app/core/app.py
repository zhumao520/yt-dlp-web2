# -*- coding: utf-8 -*-
"""
Flask应用工厂 - 轻量化应用创建
"""

import logging
from flask import Flask
from flask_cors import CORS

logger = logging.getLogger(__name__)


def create_app(config_override=None):
    """创建Flask应用实例"""
    try:
        logger.info("🔧 创建Flask应用...")

        # 创建Flask实例
        app = Flask(__name__)

        # 配置应用
        _configure_app(app, config_override)

        # 配置CORS
        CORS(app, supports_credentials=True)

        # 初始化核心组件
        _initialize_core_components(app)

        # 注册蓝图
        _register_blueprints(app)

        # 注册错误处理器
        _register_error_handlers(app)

        # 发送应用启动事件
        with app.app_context():
            from .events import emit, Events

            emit(
                Events.APP_STARTED,
                {"app_name": app.config.get("APP_NAME", "YT-DLP Web V2")},
            )

        logger.info("✅ Flask应用创建完成")
        return app
        
    except Exception as e:
        logger.error(f"❌ Flask应用创建失败: {e}")
        raise


def _configure_app(app: Flask, config_override=None):
    """配置Flask应用"""
    from .config import get_config
    
    # 基础配置
    app.config.update({
        'SECRET_KEY': get_config('app.secret_key'),
        'DEBUG': get_config('app.debug', False),
        'APP_NAME': get_config('app.name', 'YT-DLP Web V2'),
        'APP_VERSION': get_config('app.version', '2.0.0'),
        
        # 文件上传配置
        'MAX_CONTENT_LENGTH': 16 * 1024 * 1024 * 1024,  # 16GB
        
        # JSON配置
        'JSON_AS_ASCII': False,
        'JSON_SORT_KEYS': False,
        
        # 会话配置
        'PERMANENT_SESSION_LIFETIME': get_config('auth.session_timeout', 86400),
    })
    
    # 应用自定义配置覆盖
    if config_override:
        app.config.update(config_override)
        logger.info(f"✅ 应用自定义配置: {list(config_override.keys())}")
    
    logger.info("✅ Flask应用配置完成")


def _initialize_core_components(app: Flask):
    """初始化核心组件"""
    with app.app_context():
        try:
            # 初始化数据库
            from .database import get_database
            db = get_database()
            logger.info("✅ 数据库初始化完成")
            
            # 初始化认证管理器
            from .auth import get_auth_manager
            auth_manager = get_auth_manager()
            logger.info("✅ 认证管理器初始化完成")
            
            # 初始化事件总线
            from .events import event_bus
            logger.info("✅ 事件总线初始化完成")
            
        except Exception as e:
            logger.error(f"❌ 核心组件初始化失败: {e}")
            raise


def _register_blueprints(app: Flask):
    """注册蓝图"""
    try:
        # 主页蓝图
        from ..web.routes import main_bp
        app.register_blueprint(main_bp)
        
        # API蓝图
        from ..api.routes import api_bp
        app.register_blueprint(api_bp, url_prefix='/api')
        
        # 认证蓝图
        from ..modules.auth.routes import auth_bp
        app.register_blueprint(auth_bp, url_prefix='/auth')
        
        # 下载模块蓝图
        from ..modules.downloader.routes import downloader_bp
        app.register_blueprint(downloader_bp, url_prefix='/download')
        
        # Telegram模块蓝图
        from ..modules.telegram.routes import telegram_bp
        app.register_blueprint(telegram_bp, url_prefix='/telegram')

        # Cookies管理蓝图
        from ..modules.cookies.routes import cookies_bp
        app.register_blueprint(cookies_bp, url_prefix='/cookies')

        # 文件管理蓝图
        from ..modules.files.routes import files_bp
        app.register_blueprint(files_bp, url_prefix='/files')
        
        logger.info("✅ 蓝图注册完成")
        
    except Exception as e:
        logger.error(f"❌ 蓝图注册失败: {e}")
        raise


def _register_error_handlers(app: Flask):
    """注册错误处理器"""
    
    @app.errorhandler(404)
    def not_found_error(error):
        from flask import request, jsonify, render_template
        if request.is_json:
            return jsonify({'error': '页面未找到'}), 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        from flask import request, jsonify, render_template
        logger.error(f"内部服务器错误: {error}")
        if request.is_json:
            return jsonify({'error': '内部服务器错误'}), 500
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(401)
    def unauthorized_error(error):
        from flask import request, jsonify, render_template
        if request.is_json:
            return jsonify({'error': '未授权访问'}), 401
        return render_template('errors/401.html'), 401
    
    @app.errorhandler(403)
    def forbidden_error(error):
        from flask import request, jsonify, render_template
        if request.is_json:
            return jsonify({'error': '禁止访问'}), 403
        return render_template('errors/403.html'), 403
    
    logger.info("✅ 错误处理器注册完成")


# WSGI应用入口点
def create_wsgi_app():
    """创建WSGI应用（用于生产部署）"""
    return create_app()


# 为了兼容性，提供应用实例
app = None

def get_app():
    """获取应用实例（延迟初始化）"""
    global app
    if app is None:
        app = create_app()
    return app
