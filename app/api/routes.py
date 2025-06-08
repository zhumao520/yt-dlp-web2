# -*- coding: utf-8 -*-
"""
API路由 - 统一API接口
"""

import logging
import time
from flask import Blueprint, request, jsonify
from ..core.auth import auth_required, optional_auth

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__)


# ==================== 认证相关API ====================

@api_bp.route('/auth/login', methods=['POST'])
def api_login():
    """API登录"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "需要JSON数据"}), 400
        
        username = data.get("username", "").strip()
        password = data.get("password", "")

        if not username or not password:
            return jsonify({"error": "用户名和密码不能为空"}), 400
        
        from ..core.auth import get_auth_manager
        auth_manager = get_auth_manager()
        
        token = auth_manager.login(username, password)
        if not token:
            return jsonify({"error": "用户名或密码错误"}), 401

        return jsonify({
            "success": True,
            "message": "登录成功",
            "token": token,
            "username": username,
        })
        
    except Exception as e:
        logger.error(f"❌ API登录失败: {e}")
        return jsonify({"error": "登录处理失败"}), 500


@api_bp.route('/auth/status')
@optional_auth
def api_auth_status():
    """检查认证状态"""
    try:
        if hasattr(request, "current_user") and request.current_user:
            return jsonify({
                "authenticated": True,
                "username": request.current_user.get("username"),
                "is_admin": request.current_user.get("is_admin", False),
            })
        else:
            return jsonify({"authenticated": False})
            
    except Exception as e:
        logger.error(f"❌ 检查认证状态失败: {e}")
        return jsonify({"authenticated": False, "error": "状态检查失败"}), 500


# ==================== 下载相关API ====================

@api_bp.route('/download/start', methods=['POST'])
@auth_required
def api_start_download():
    """开始下载"""
    try:
        data = request.get_json()
        if not data or "url" not in data:
            return jsonify({"error": "需要提供URL"}), 400

        url = data["url"].strip()
        if not url:
            return jsonify({"error": "URL不能为空"}), 400
        
        # 获取下载选项
        options = {
            "quality": data.get("quality", "medium"),
            "audio_only": data.get("audio_only", False),
            "format": data.get("format"),
            "source": "web_api",
            "web_callback": True,
        }

        # 使用统一的下载API
        from ..modules.downloader.api import get_unified_download_api
        api = get_unified_download_api()
        result = api.create_download(url, options)

        if not result['success']:
            return jsonify({"error": result['error']}), 500

        download_id = result['data']['download_id']
        
        return jsonify({
            "success": True,
            "message": "下载已开始",
            "download_id": download_id,
        })
        
    except Exception as e:
        logger.error(f"❌ API开始下载失败: {e}")
        return jsonify({"error": "下载启动失败"}), 500


@api_bp.route('/download/status/<download_id>')
@auth_required
def api_download_status(download_id):
    """获取下载状态"""
    try:
        from ..modules.downloader.manager import get_download_manager
        download_manager = get_download_manager()
        
        download_info = download_manager.get_download(download_id)
        if not download_info:
            return jsonify({"error": "下载任务不存在"}), 404

        response_data = {
            "id": download_info["id"],
            "url": download_info["url"],
            "status": download_info["status"],
            "progress": download_info["progress"],
            "title": download_info["title"],
            "created_at": download_info["created_at"].isoformat() if download_info["created_at"] else None,
        }
        
        if download_info["status"] == "completed" and download_info["file_path"]:
            response_data["file_info"] = {
                "filename": download_info["file_path"].split("/")[-1],
                "size": download_info["file_size"],
            }

        if download_info["status"] == "failed" and download_info["error_message"]:
            response_data["error_message"] = download_info["error_message"]
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"❌ API获取下载状态失败: {e}")
        return jsonify({"error": "获取状态失败"}), 500


@api_bp.route('/download/list')
@auth_required
def api_download_list():
    """获取下载列表"""
    try:
        from ..modules.downloader.manager import get_download_manager
        download_manager = get_download_manager()
        
        downloads = download_manager.get_all_downloads()
        
        response_data = []
        for download in downloads:
            item = {
                "id": download["id"],
                "url": download["url"],
                "status": download["status"],
                "progress": download["progress"],
                "title": download["title"],
                "created_at": download["created_at"].isoformat() if download["created_at"] else None,
            }

            if download["status"] == "completed" and download["file_path"]:
                item["filename"] = download["file_path"].split("/")[-1]
                item["file_size"] = download["file_size"]

            response_data.append(item)
        
        response_data.sort(key=lambda x: x["created_at"] or "", reverse=True)

        return jsonify({
            "success": True,
            "downloads": response_data,
            "total": len(response_data),
        })
        
    except Exception as e:
        logger.error(f"❌ API获取下载列表失败: {e}")
        return jsonify({"error": "获取列表失败"}), 500


@api_bp.route('/video/info', methods=['POST'])
@auth_required
def api_video_info():
    """获取视频信息"""
    try:
        data = request.get_json()
        if not data or "url" not in data:
            return jsonify({"error": "需要提供URL"}), 400

        url = data["url"].strip()
        if not url:
            return jsonify({"error": "URL不能为空"}), 400
        
        # 提取视频信息
        video_info = _extract_video_info(url)
        if not video_info:
            return jsonify({"error": "无法获取视频信息"}), 400

        response_data = {
            "title": video_info.get("title", "Unknown"),
            "description": video_info.get("description", ""),
            "duration": video_info.get("duration"),
            "uploader": video_info.get("uploader", ""),
            "thumbnail": video_info.get("thumbnail", ""),
            "view_count": video_info.get("view_count"),
        }
        
        return jsonify({
            "success": True,
            "video_info": response_data,
        })
        
    except Exception as e:
        logger.error(f"❌ API获取视频信息失败: {e}")
        return jsonify({"error": "获取信息失败"}), 500


# ==================== Telegram相关API ====================

@api_bp.route('/telegram/config', methods=['GET'])
@auth_required
def api_telegram_config():
    """获取Telegram配置"""
    try:
        logger.info("🔄 收到Telegram配置获取请求")
        from ..core.database import get_database
        db = get_database()
        config = db.get_telegram_config()
        logger.info(f"📥 从数据库获取的配置: {config}")
        
        if not config:
            logger.info("ℹ️ 数据库中没有配置，返回默认配置")
            default_config = {
                "enabled": False,
                "bot_token": "",
                "chat_id": "",
                "api_id": None,
                "api_hash": "",
                "push_mode": "file",
                "auto_download": True,
                "file_size_limit": 50,
            }
            return jsonify(default_config)

        # 返回完整配置（用于编辑）
        # 确保布尔值正确转换（SQLite中可能存储为0/1）
        full_config = {
            "enabled": bool(config.get("enabled", False)),
            "bot_token": config.get("bot_token", ""),
            "chat_id": config.get("chat_id", ""),
            "api_id": config.get("api_id"),
            "api_hash": config.get("api_hash", ""),
            "push_mode": config.get("push_mode", "file"),
            "auto_download": bool(config.get("auto_download", True)),
            "file_size_limit": config.get("file_size_limit", 50),
        }

        logger.info(f"📤 返回的配置: {full_config}")
        return jsonify(full_config)
        
    except Exception as e:
        logger.error(f"❌ 获取Telegram配置失败: {e}")
        return jsonify({"error": "获取配置失败"}), 500


@api_bp.route('/telegram/config', methods=['POST'])
@auth_required
def api_save_telegram_config():
    """保存Telegram配置"""
    try:
        logger.info("🔄 收到Telegram配置保存请求")
        data = request.get_json()
        logger.info(f"📥 接收到的数据: {data}")

        if not data:
            logger.error("❌ 没有接收到配置数据")
            return jsonify({"error": "需要配置数据"}), 400

        # 处理api_id的类型转换
        api_id = data.get("api_id")
        if api_id is not None:
            try:
                api_id = int(api_id) if api_id != "" else None
            except (ValueError, TypeError):
                api_id = None

        config = {
            "bot_token": data.get("bot_token", "").strip(),
            "chat_id": data.get("chat_id", "").strip(),
            "api_id": api_id,
            "api_hash": data.get("api_hash", "").strip(),
            "enabled": data.get("enabled", False),
            "push_mode": data.get("push_mode", "file"),
            "auto_download": data.get("auto_download", True),
            "file_size_limit": data.get("file_size_limit", 50),
        }

        logger.info(f"🔧 处理后的配置: {config}")
        
        # 验证必要字段
        if config["enabled"]:
            if not config["bot_token"] or not config["chat_id"]:
                logger.error("❌ 启用状态下Bot Token和Chat ID不能为空")
                return jsonify({"error": "Bot Token和Chat ID不能为空"}), 400

        logger.info("🔧 开始保存配置到数据库")
        from ..core.database import get_database
        db = get_database()
        success = db.save_telegram_config(config)
        logger.info(f"💾 数据库保存结果: {'成功' if success else '失败'}")

        if success:
            # 重新加载配置
            logger.info("🔄 重新加载Telegram通知器配置")
            from ..modules.telegram.notifier import get_telegram_notifier
            notifier = get_telegram_notifier()
            notifier._load_config()

            logger.info("✅ Telegram配置保存完成")
            return jsonify({"success": True, "message": "配置保存成功"})
        else:
            logger.error("❌ 数据库保存失败")
            return jsonify({"error": "配置保存失败"}), 500
        
    except Exception as e:
        logger.error(f"❌ 保存Telegram配置失败: {e}")
        return jsonify({"error": "保存配置失败"}), 500


@api_bp.route('/telegram/test', methods=['POST'])
@auth_required
def api_test_telegram():
    """测试Telegram连接"""
    try:
        from ..modules.telegram.notifier import get_telegram_notifier
        notifier = get_telegram_notifier()
        
        result = notifier.test_connection()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ 测试Telegram连接失败: {e}")
        return jsonify({"success": False, "error": "测试失败"}), 500


# ==================== 系统相关API ====================

@api_bp.route('/health')
def api_health_check():
    """健康检查端点（无需认证）"""
    try:
        # 基础健康检查
        health_status = {
            "status": "healthy",
            "timestamp": int(time.time()),
            "app_name": "YT-DLP Web V2"
        }

        # 检查数据库连接
        try:
            from ..core.database import get_database
            db = get_database()
            db.execute_query('SELECT 1')
            health_status["database"] = "connected"
        except Exception:
            health_status["database"] = "disconnected"
            health_status["status"] = "degraded"

        # 检查yt-dlp
        try:
            import yt_dlp
            health_status["ytdlp"] = "available"
        except ImportError:
            health_status["ytdlp"] = "unavailable"
            health_status["status"] = "degraded"

        return jsonify(health_status)

    except Exception as e:
        logger.error(f"❌ 健康检查失败: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": int(time.time())
        }), 500


@api_bp.route('/system/status')
@auth_required
def api_system_status():
    """获取系统状态"""
    try:
        from ..core.config import get_config

        # 检查yt-dlp状态
        ytdlp_available = False
        ytdlp_version = "Unknown"
        try:
            from ..scripts.ytdlp_installer import YtdlpInstaller
            installer = YtdlpInstaller()

            if installer._check_ytdlp_available():
                ytdlp_available = True
                ytdlp_version = installer._get_ytdlp_version()
        except Exception as e:
            logger.warning(f"检查yt-dlp状态失败: {e}")
            pass

        # 获取下载统计
        from ..modules.downloader.manager import get_download_manager
        download_manager = get_download_manager()
        downloads = download_manager.get_all_downloads()

        download_stats = {
            "total": len(downloads),
            "completed": len([d for d in downloads if d["status"] == "completed"]),
            "failed": len([d for d in downloads if d["status"] == "failed"]),
            "pending": len([d for d in downloads if d["status"] in ["pending", "downloading"]]),
        }

        return jsonify({
            "app_name": get_config("app.name"),
            "app_version": get_config("app.version"),
            "ytdlp_available": ytdlp_available,
            "ytdlp_version": ytdlp_version,
            "download_stats": download_stats,
        })

    except Exception as e:
        logger.error(f"❌ 获取系统状态失败: {e}")
        return jsonify({"error": "获取状态失败"}), 500


@api_bp.route('/debug/users')
def api_debug_users():
    """调试用户信息（无需认证，仅用于调试）"""
    try:
        from ..core.database import get_database
        import os

        db = get_database()
        users = db.execute_query('SELECT username, is_admin, created_at FROM users')

        debug_info = {
            "users": users,
            "env_admin_username": os.getenv('ADMIN_USERNAME', 'not_set'),
            "env_admin_password_set": bool(os.getenv('ADMIN_PASSWORD')),
            "total_users": len(users)
        }

        return jsonify(debug_info)

    except Exception as e:
        logger.error(f"❌ 用户调试失败: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route('/admin/reset-password', methods=['POST'])
def api_reset_admin_password():
    """重置管理员密码（无需认证，紧急使用）"""
    try:
        from ..core.database import get_database
        import hashlib
        import os

        # 获取环境变量中的密码
        env_password = os.getenv('ADMIN_PASSWORD')
        if not env_password:
            return jsonify({"error": "未设置 ADMIN_PASSWORD 环境变量"}), 400

        env_username = os.getenv('ADMIN_USERNAME', 'admin')
        password_hash = hashlib.sha256(env_password.encode()).hexdigest()

        db = get_database()

        # 更新或创建管理员用户
        result = db.execute_update('''
            INSERT OR REPLACE INTO users (username, password_hash, is_admin, created_at)
            VALUES (?, ?, 1, CURRENT_TIMESTAMP)
        ''', (env_username, password_hash))

        if result:
            logger.info(f"🔄 管理员密码重置成功: {env_username}")
            return jsonify({
                "success": True,
                "message": f"管理员密码重置成功",
                "username": env_username
            })
        else:
            return jsonify({"error": "密码重置失败"}), 500

    except Exception as e:
        logger.error(f"❌ 重置管理员密码失败: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/system/ytdlp/update", methods=["POST"])
@auth_required
def api_update_ytdlp():
    """更新yt-dlp"""
    try:
        from ..scripts.ytdlp_installer import YtdlpInstaller

        installer = YtdlpInstaller()

        # 先尝试强制更新
        logger.info("🔄 开始更新yt-dlp...")
        success = installer.update_ytdlp()

        if success:
            # 获取新版本信息
            info = installer.get_ytdlp_info()
            version = info.get("version", "Unknown") if info else "Unknown"

            logger.info(f"✅ yt-dlp更新成功，版本: {version}")
            return jsonify({
                "success": True,
                "message": f"yt-dlp更新成功，版本: {version}",
                "version": version,
            })
        else:
            # 如果更新失败，尝试重新安装
            logger.warning("⚠️ 更新失败，尝试重新安装...")
            success = installer.ensure_ytdlp(force_update=True)

            if success:
                info = installer.get_ytdlp_info()
                version = info.get("version", "Unknown") if info else "Unknown"

                logger.info(f"✅ yt-dlp重新安装成功，版本: {version}")
                return jsonify({
                    "success": True,
                    "message": f"yt-dlp重新安装成功，版本: {version}",
                    "version": version,
                })
            else:
                return jsonify({"error": "yt-dlp安装失败，请检查网络连接或手动安装"}), 500

    except Exception as e:
        logger.error(f"❌ 更新yt-dlp失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return jsonify({"error": f"更新失败: {str(e)}"}), 500


@api_bp.route("/system/ytdlp/info")
@auth_required
def api_ytdlp_info():
    """获取yt-dlp详细信息"""
    try:
        from ..scripts.ytdlp_installer import YtdlpInstaller

        installer = YtdlpInstaller()
        info = installer.get_ytdlp_info()

        if info:
            return jsonify({"success": True, "info": info})
        else:
            # 如果获取不到信息，尝试安装
            logger.info("🔧 yt-dlp信息获取失败，尝试安装...")
            success = installer.ensure_ytdlp()

            if success:
                info = installer.get_ytdlp_info()
                if info:
                    return jsonify({"success": True, "info": info})

            return jsonify({"success": False, "error": "yt-dlp未安装或不可用"}), 404

    except Exception as e:
        logger.error(f"❌ 获取yt-dlp信息失败: {e}")
        return jsonify({"error": "获取信息失败"}), 500


@api_bp.route("/system/ytdlp/install", methods=["POST"])
@auth_required
def api_install_ytdlp():
    """强制安装yt-dlp"""
    try:
        from ..scripts.ytdlp_installer import YtdlpInstaller

        installer = YtdlpInstaller()

        logger.info("🔧 开始强制安装yt-dlp...")
        success = installer.ensure_ytdlp(force_update=True)

        if success:
            info = installer.get_ytdlp_info()
            version = info.get("version", "Unknown") if info else "Unknown"

            logger.info(f"✅ yt-dlp安装成功，版本: {version}")
            return jsonify({
                "success": True,
                "message": f"yt-dlp安装成功，版本: {version}",
                "version": version,
            })
        else:
            return jsonify({"error": "yt-dlp安装失败，请检查网络连接"}), 500

    except Exception as e:
        logger.error(f"❌ 安装yt-dlp失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return jsonify({"error": f"安装失败: {str(e)}"}), 500


# ==================== 设置相关API ====================

@api_bp.route('/settings/general', methods=['GET'])
@auth_required
def api_get_general_settings():
    """获取基础设置"""
    try:
        from ..core.config import get_config

        settings = {
            "app_name": get_config("app.name", "YT-DLP Web V2"),
            "app_version": get_config("app.version", "2.0.0"),
            "host": get_config("app.host", "0.0.0.0"),
            "port": get_config("app.port", 8080),
            "debug": get_config("app.debug", False),
            "secret_key": get_config("app.secret_key", "")[:10] + "..." if get_config("app.secret_key") else ""
        }

        return jsonify({"success": True, "settings": settings})

    except Exception as e:
        logger.error(f"❌ 获取基础设置失败: {e}")
        return jsonify({"error": "获取设置失败"}), 500


@api_bp.route('/settings/general', methods=['POST'])
@auth_required
def api_save_general_settings():
    """保存基础设置"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "需要提供设置数据"}), 400

        # 这里应该保存到配置文件或数据库
        # 目前只是返回成功，实际项目中需要实现配置保存逻辑
        logger.info(f"📝 保存基础设置: {data}")

        return jsonify({"success": True, "message": "基础设置保存成功"})

    except Exception as e:
        logger.error(f"❌ 保存基础设置失败: {e}")
        return jsonify({"error": "保存设置失败"}), 500


@api_bp.route('/settings/download', methods=['GET'])
@auth_required
def api_get_download_settings():
    """获取下载设置"""
    try:
        from ..core.config import get_config

        # 从数据库获取设置，如果没有则使用默认值
        from ..core.database import get_database
        db = get_database()

        # 质量映射（后端到前端）
        format_to_quality = {
            "best": "best",
            "best[height<=720]": "medium",
            "worst": "low"
        }

        current_format = get_config("ytdlp.format", "best[height<=720]")
        current_quality = format_to_quality.get(current_format, "medium")

        settings = {
            "output_dir": get_config("downloader.output_dir", "/app/downloads"),
            "max_concurrent": get_config("downloader.max_concurrent", 3),
            "timeout": get_config("downloader.timeout", 300),
            "default_quality": current_quality,
            "auto_cleanup": get_config("downloader.auto_cleanup", True),
            "file_retention_hours": get_config("downloader.file_retention_hours", 24),
            "cleanup_interval": get_config("downloader.cleanup_interval", 1),
            "max_storage_mb": get_config("downloader.max_storage_mb", 2048),
            "keep_recent_files": get_config("downloader.keep_recent_files", 20)
        }

        return jsonify({"success": True, "settings": settings})

    except Exception as e:
        logger.error(f"❌ 获取下载设置失败: {e}")
        return jsonify({"error": "获取设置失败"}), 500


@api_bp.route('/settings/download', methods=['POST'])
@auth_required
def api_save_download_settings():
    """保存下载设置"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "需要提供设置数据"}), 400

        logger.info(f"📝 保存下载设置: {data}")

        # 保存到数据库
        from ..core.database import get_database
        db = get_database()

        # 映射前端字段到后端配置
        quality_mapping = {
            "best": "best",
            "medium": "best[height<=720]",
            "low": "worst"
        }

        # 保存各个设置项（使用正确的字段名）
        settings_to_save = [
            ("downloader.output_dir", data.get("output_dir", "/app/downloads")),
            ("downloader.max_concurrent", str(data.get("max_concurrent", 3))),
            ("downloader.timeout", str(data.get("timeout", 300))),
            ("downloader.auto_cleanup", str(data.get("auto_cleanup", True))),
            ("downloader.file_retention_hours", str(data.get("file_retention_hours", 24))),
            ("downloader.cleanup_interval", str(data.get("cleanup_interval", 1))),
            ("downloader.max_storage_mb", str(data.get("max_storage_mb", 2048))),
            ("downloader.keep_recent_files", str(data.get("keep_recent_files", 20))),
            ("ytdlp.format", quality_mapping.get(data.get("default_quality", "medium"), "best[height<=720]"))
        ]

        for key, value in settings_to_save:
            db.set_setting(key, value)

        # 重新初始化下载管理器以应用新设置
        try:
            from ..modules.downloader.manager import get_download_manager
            download_manager = get_download_manager()
            # 这里可以添加重新加载配置的逻辑
            logger.info("✅ 下载管理器配置已更新")
        except Exception as e:
            logger.warning(f"⚠️ 重新加载下载管理器配置失败: {e}")

        return jsonify({"success": True, "message": "下载配置保存成功"})

    except Exception as e:
        logger.error(f"❌ 保存下载设置失败: {e}")
        return jsonify({"error": "保存设置失败"}), 500


@api_bp.route('/settings/api-key', methods=['GET'])
@auth_required
def api_get_api_key():
    """获取API密钥设置"""
    try:
        from ..core.database import get_database
        db = get_database()

        api_key = db.get_setting("api_key", "")

        return jsonify({
            "success": True,
            "api_key": api_key,
            "has_key": bool(api_key)
        })

    except Exception as e:
        logger.error(f"❌ 获取API密钥失败: {e}")
        return jsonify({"error": "获取API密钥失败"}), 500


@api_bp.route('/settings/api-key', methods=['POST'])
@auth_required
def api_save_api_key():
    """保存API密钥设置"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "需要提供数据"}), 400

        api_key = data.get("api_key", "").strip()

        from ..core.database import get_database
        db = get_database()

        if api_key:
            db.set_setting("api_key", api_key)
            message = "API密钥保存成功"
        else:
            db.delete_setting("api_key")
            message = "API密钥已删除"

        return jsonify({
            "success": True,
            "message": message
        })

    except Exception as e:
        logger.error(f"❌ 保存API密钥失败: {e}")
        return jsonify({"error": "保存API密钥失败"}), 500


@api_bp.route('/settings/api-key/generate', methods=['POST'])
@auth_required
def api_generate_api_key():
    """生成新的API密钥"""
    try:
        import secrets
        import string

        # 生成32位随机API密钥
        alphabet = string.ascii_letters + string.digits
        api_key = ''.join(secrets.choice(alphabet) for _ in range(32))

        from ..core.database import get_database
        db = get_database()
        db.set_setting("api_key", api_key)

        return jsonify({
            "success": True,
            "api_key": api_key,
            "message": "新API密钥生成成功"
        })

    except Exception as e:
        logger.error(f"❌ 生成API密钥失败: {e}")
        return jsonify({"error": "生成API密钥失败"}), 500


@api_bp.route("/system/cleanup", methods=["POST"])
@auth_required
def api_manual_cleanup():
    """手动执行文件清理"""
    try:
        from ..modules.downloader.cleanup import get_cleanup_manager

        cleanup_manager = get_cleanup_manager()
        result = cleanup_manager.manual_cleanup()

        if result["success"]:
            return jsonify({
                "success": True,
                "message": result["message"]
            })
        else:
            return jsonify({"error": result["error"]}), 500

    except Exception as e:
        logger.error(f"❌ 手动清理失败: {e}")
        return jsonify({"error": "清理失败"}), 500


@api_bp.route("/system/paths")
@auth_required
def api_system_paths():
    """获取系统路径信息"""
    try:
        from ..core.config import get_config
        import os
        from pathlib import Path

        # 获取配置的路径
        download_dir = get_config('downloader.output_dir', '/app/downloads')
        temp_dir = get_config('downloader.temp_dir', '/app/temp')

        # 检查路径是否存在
        download_path = Path(download_dir)
        temp_path = Path(temp_dir)

        # 获取文件列表
        download_files = []
        if download_path.exists():
            try:
                download_files = [
                    {
                        'name': f.name,
                        'size': f.stat().st_size,
                        'modified': f.stat().st_mtime,
                        'is_video': f.suffix.lower() in ['.mp4', '.avi', '.mkv', '.mov', '.webm']
                    }
                    for f in download_path.iterdir()
                    if f.is_file()
                ]
            except Exception as e:
                logger.warning(f"读取下载目录失败: {e}")

        # 获取环境变量
        env_download_dir = os.getenv('DOWNLOAD_DIR')

        path_info = {
            "download_directory": {
                "configured_path": download_dir,
                "resolved_path": str(download_path.resolve()) if download_path.exists() else None,
                "exists": download_path.exists(),
                "is_writable": download_path.exists() and os.access(download_path, os.W_OK),
                "file_count": len(download_files),
                "files": download_files[:10]  # 只返回前10个文件
            },
            "temp_directory": {
                "configured_path": temp_dir,
                "resolved_path": str(temp_path.resolve()) if temp_path.exists() else None,
                "exists": temp_path.exists(),
                "is_writable": temp_path.exists() and os.access(temp_path, os.W_OK)
            },
            "environment_variables": {
                "DOWNLOAD_DIR": env_download_dir,
                "PWD": os.getenv('PWD'),
                "HOME": os.getenv('HOME')
            },
            "current_working_directory": os.getcwd(),
            "container_info": {
                "is_container": os.path.exists('/.dockerenv'),
                "hostname": os.getenv('HOSTNAME', 'unknown')
            }
        }

        return jsonify({
            "success": True,
            "paths": path_info
        })

    except Exception as e:
        logger.error(f"❌ 获取系统路径失败: {e}")
        return jsonify({"error": f"获取路径信息失败: {str(e)}"}), 500


# ==================== iOS快捷指令API ====================

@api_bp.route('/shortcuts/download', methods=['POST'])
def api_shortcuts_download():
    """iOS快捷指令下载接口 - 支持简化认证"""
    try:
        # 支持多种数据格式
        if request.content_type == 'application/json':
            data = request.get_json()
        elif request.content_type == 'application/x-www-form-urlencoded':
            data = request.form.to_dict()
        else:
            # 尝试从查询参数获取
            data = request.args.to_dict()
            if not data:
                data = request.get_json() or {}

        if not data:
            return jsonify({"error": "需要提供数据"}), 400

        # 获取URL
        url = data.get("url", "").strip()
        if not url:
            return jsonify({"error": "需要提供视频URL"}), 400

        # 简化认证 - 支持API密钥或用户名密码
        auth_token = None
        api_key = data.get("api_key") or request.headers.get("X-API-Key")

        if api_key:
            # 使用API密钥认证
            if not _verify_api_key(api_key):
                return jsonify({"error": "API密钥无效"}), 401
        else:
            # 使用用户名密码认证
            username = data.get("username")
            password = data.get("password")

            if not username or not password:
                return jsonify({"error": "需要提供用户名和密码或API密钥"}), 401

            from ..core.auth import get_auth_manager
            auth_manager = get_auth_manager()
            auth_token = auth_manager.login(username, password)

            if not auth_token:
                return jsonify({"error": "用户名或密码错误"}), 401

        # 获取下载选项
        options = {
            "quality": data.get("quality", "medium"),
            "audio_only": data.get("audio_only", "false").lower() in ["true", "1", "yes"],
            "source": "ios_shortcuts",
            "ios_callback": True,
        }

        # 使用统一的下载API
        from ..modules.downloader.api import get_unified_download_api
        api = get_unified_download_api()
        result = api.create_download(url, options)

        if not result['success']:
            return jsonify({"error": result['error']}), 500

        download_id = result['data']['download_id']

        # 返回简化的响应
        response = {
            "success": True,
            "message": "下载已开始",
            "download_id": download_id,
            "status_url": f"/api/shortcuts/status/{download_id}"
        }

        # 如果需要，添加认证令牌
        if auth_token:
            response["token"] = auth_token

        return jsonify(response)

    except Exception as e:
        logger.error(f"❌ iOS快捷指令下载失败: {e}")
        return jsonify({"error": "下载启动失败"}), 500


@api_bp.route('/shortcuts/status/<download_id>')
def api_shortcuts_status(download_id):
    """iOS快捷指令状态查询 - 无需认证"""
    try:
        from ..modules.downloader.manager import get_download_manager
        download_manager = get_download_manager()

        download_info = download_manager.get_download(download_id)
        if not download_info:
            return jsonify({"error": "下载任务不存在"}), 404

        # 简化的状态响应
        response = {
            "id": download_info["id"],
            "status": download_info["status"],
            "progress": download_info["progress"],
            "title": download_info.get("title", "Unknown"),
        }

        # 如果下载完成，添加文件信息
        if download_info["status"] == "completed" and download_info.get("file_path"):
            filename = download_info["file_path"].split("/")[-1]
            response.update({
                "filename": filename,
                "file_size": download_info.get("file_size", 0),
                "download_url": f"/api/shortcuts/file/{filename}",
                "completed": True
            })
        elif download_info["status"] == "failed":
            response["error"] = download_info.get("error_message", "下载失败")

        return jsonify(response)

    except Exception as e:
        logger.error(f"❌ 获取下载状态失败: {e}")
        return jsonify({"error": "获取状态失败"}), 500


@api_bp.route('/shortcuts/file/<filename>')
def api_shortcuts_file(filename):
    """iOS快捷指令文件下载 - 无需认证"""
    try:
        from ..core.config import get_config
        from flask import send_file
        from pathlib import Path

        # 获取下载目录
        download_dir = Path(get_config('downloader.output_dir', '/app/downloads'))
        file_path = download_dir / filename

        # 安全检查
        if not str(file_path.resolve()).startswith(str(download_dir.resolve())):
            logger.warning(f"尝试访问下载目录外的文件: {filename}")
            return jsonify({"error": "文件访问被拒绝"}), 403

        if not file_path.exists():
            return jsonify({"error": "文件不存在"}), 404

        # 返回文件
        return send_file(file_path, as_attachment=True)

    except Exception as e:
        logger.error(f"❌ 文件下载失败: {e}")
        return jsonify({"error": "文件下载失败"}), 500


@api_bp.route('/shortcuts/info')
def api_shortcuts_info():
    """iOS快捷指令服务信息 - 无需认证"""
    try:
        from ..core.config import get_config

        return jsonify({
            "service": "YT-DLP Web V2",
            "version": get_config("app.version", "2.0.0"),
            "supported_sites": "1000+ 网站",
            "max_file_size": "无限制",
            "formats": ["视频", "音频"],
            "qualities": ["最高质量", "中等质量", "低质量"],
            "endpoints": {
                "download": "/api/shortcuts/download",
                "status": "/api/shortcuts/status/{download_id}",
                "file": "/api/shortcuts/file/{filename}"
            }
        })

    except Exception as e:
        logger.error(f"❌ 获取服务信息失败: {e}")
        return jsonify({"error": "获取信息失败"}), 500


def _verify_api_key(api_key: str) -> bool:
    """验证API密钥"""
    try:
        from ..core.database import get_database
        db = get_database()

        # 从设置中获取API密钥
        stored_key = db.get_setting("api_key")
        if not stored_key:
            return False

        return api_key == stored_key

    except Exception as e:
        logger.error(f"❌ API密钥验证失败: {e}")
        return False


# ==================== 辅助函数 ====================

def _extract_video_info(url: str):
    """提取视频信息 - 使用统一的下载管理器和智能回退"""
    try:
        # 使用统一的下载管理器，它包含智能回退机制
        from ..modules.downloader.manager import get_download_manager
        download_manager = get_download_manager()

        # 使用下载管理器的智能回退机制
        return download_manager._extract_video_info(url)

    except Exception as e:
        logger.error(f"❌ 提取视频信息失败: {e}")
        return None
