# -*- coding: utf-8 -*-
"""
API路由 - 统一API接口
"""

import logging
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
            "source": "api",
        }
        
        from ..modules.downloader.manager import get_download_manager
        download_manager = get_download_manager()
        download_id = download_manager.create_download(url, options)
        
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
        from ..core.database import get_database
        db = get_database()
        config = db.get_telegram_config()
        
        if not config:
            return jsonify({
                "enabled": False,
                "bot_token": "",
                "chat_id": "",
                "api_id": None,
                "api_hash": "",
                "push_mode": "file",
            })
        
        # 脱敏处理
        safe_config = {
            "enabled": config.get("enabled", False),
            "bot_token": config.get("bot_token", "")[:8] + "..." if config.get("bot_token") else "",
            "chat_id": config.get("chat_id", ""),
            "api_id": config.get("api_id"),
            "api_hash": config.get("api_hash", "")[:8] + "..." if config.get("api_hash") else "",
            "push_mode": config.get("push_mode", "file"),
            "auto_download": config.get("auto_download", True),
        }
        
        return jsonify(safe_config)
        
    except Exception as e:
        logger.error(f"❌ 获取Telegram配置失败: {e}")
        return jsonify({"error": "获取配置失败"}), 500


@api_bp.route('/telegram/config', methods=['POST'])
@auth_required
def api_save_telegram_config():
    """保存Telegram配置"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "需要配置数据"}), 400

        config = {
            "bot_token": data.get("bot_token", "").strip(),
            "chat_id": data.get("chat_id", "").strip(),
            "api_id": data.get("api_id"),
            "api_hash": data.get("api_hash", "").strip(),
            "enabled": data.get("enabled", False),
            "push_mode": data.get("push_mode", "file"),
            "auto_download": data.get("auto_download", True),
        }
        
        # 验证必要字段
        if config["enabled"]:
            if not config["bot_token"] or not config["chat_id"]:
                return jsonify({"error": "Bot Token和Chat ID不能为空"}), 400
        
        from ..core.database import get_database
        db = get_database()
        success = db.save_telegram_config(config)
        
        if success:
            # 重新加载配置
            from ..modules.telegram.notifier import get_telegram_notifier
            notifier = get_telegram_notifier()
            notifier._load_config()
            
            return jsonify({"success": True, "message": "配置保存成功"})
        else:
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
            import yt_dlp
            ytdlp_available = True
            ytdlp_version = getattr(yt_dlp, "__version__", "Unknown")
        except ImportError:
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


@api_bp.route("/system/ytdlp/update", methods=["POST"])
@auth_required
def api_update_ytdlp():
    """更新yt-dlp"""
    try:
        from ..scripts.ytdlp_installer import YtdlpInstaller

        installer = YtdlpInstaller()
        # 使用新的update_ytdlp方法，强制更新
        success = installer.update_ytdlp()

        if success:
            # 获取新版本信息
            info = installer.get_ytdlp_info()
            return jsonify({
                "success": True,
                "message": "yt-dlp更新成功",
                "version": info.get("version", "Unknown") if info else "Unknown",
            })
        else:
            return jsonify({"error": "yt-dlp更新失败"}), 500

    except Exception as e:
        logger.error(f"❌ 更新yt-dlp失败: {e}")
        return jsonify({"error": "更新失败"}), 500


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
            return jsonify({"success": False, "error": "yt-dlp未安装或不可用"}), 404

    except Exception as e:
        logger.error(f"❌ 获取yt-dlp信息失败: {e}")
        return jsonify({"error": "获取信息失败"}), 500


# ==================== 辅助函数 ====================

def _extract_video_info(url: str):
    """提取视频信息"""
    try:
        import yt_dlp
        
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
            
    except Exception as e:
        logger.error(f"❌ 提取视频信息失败: {e}")
        return None
