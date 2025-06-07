# -*- coding: utf-8 -*-
"""
Telegram路由 - 机器人webhook和API接口
"""

import logging
import re
from flask import Blueprint, request, jsonify
from ...core.auth import auth_required

logger = logging.getLogger(__name__)

telegram_bp = Blueprint('telegram', __name__)


@telegram_bp.route('/webhook', methods=['POST'])
def telegram_webhook():
    """Telegram Webhook接收端点"""
    try:
        logger.info("=== 收到 Telegram Webhook 请求 ===")
        logger.info(f"请求头: {dict(request.headers)}")
        logger.info(f"请求来源: {request.remote_addr}")

        # 获取配置
        from ...core.database import get_database
        db = get_database()
        config = db.get_telegram_config()
        
        if not config or not config.get('enabled'):
            logger.warning("Telegram未启用，拒绝请求")
            return jsonify({'error': 'Telegram未启用'}), 403

        # 解析消息
        update = request.get_json()
        logger.info(f"收到的更新数据: {update}")

        if not update:
            logger.error("无效的消息格式")
            return jsonify({'error': '无效的消息格式'}), 400

        # 处理消息
        result = _process_telegram_message(update, config)
        logger.info(f"消息处理结果: {result}")

        return jsonify({'success': True, 'result': result})

    except Exception as e:
        logger.error(f'Telegram webhook处理失败: {e}')
        return jsonify({'error': '处理失败'}), 500


def _process_telegram_message(update, config):
    """处理Telegram消息"""
    try:
        # 提取消息
        message = update.get('message')
        if not message:
            return {'action': 'ignored', 'reason': '非消息更新'}

        # 检查chat_id
        chat_id = str(message.get('chat', {}).get('id', ''))
        expected_chat_id = str(config.get('chat_id', ''))
        
        if chat_id != expected_chat_id:
            logger.warning(f"未授权的chat_id: {chat_id}, 期望: {expected_chat_id}")
            return {'action': 'ignored', 'reason': '未授权的聊天'}

        # 获取用户信息
        user = message.get('from', {})
        username = user.get('username', user.get('first_name', '未知用户'))
        logger.info(f"消息来自: {username} (ID: {user.get('id')})")

        # 获取消息文本
        text = message.get('text', '').strip()
        logger.info(f"消息内容: '{text}'")
        
        if not text:
            return {'action': 'ignored', 'reason': '空消息'}

        # 处理命令
        if text.startswith('/'):
            return _handle_command(text, config)
        
        # 检查是否为URL
        if not _is_valid_url(text):
            # 发送帮助信息
            _send_help_message(config)
            return {'action': 'help_sent', 'message': '已发送帮助信息'}
        
        # 处理下载链接
        if config.get('auto_download', True):
            return _handle_download_request(text, config)
        else:
            # 仅确认收到
            _send_confirmation_message(text, config, auto_download=False)
            return {'action': 'url_received', 'url': text}
            
    except Exception as e:
        logger.error(f'处理Telegram消息失败: {e}')
        return {'action': 'error', 'error': str(e)}


def _handle_command(command, config):
    """处理命令"""
    try:
        from .notifier import get_telegram_notifier
        notifier = get_telegram_notifier()
        
        if command.startswith('/start'):
            help_text = """🤖 **YT-DLP Web V2 机器人**

欢迎使用！我可以帮您下载视频。

**使用方法：**
• 直接发送视频链接，我会自动下载并发送给您
• 支持 YouTube、Bilibili、Twitter 等 1000+ 网站

**命令列表：**
/start - 显示此帮助信息
/status - 查看系统状态
/downloads - 查看下载列表

**示例：**
`https://www.youtube.com/watch?v=dQw4w9WgXcQ`"""
            
            notifier.send_message(help_text)
            return {'action': 'command_processed', 'command': 'start'}
            
        elif command.startswith('/status'):
            # 获取系统状态
            from ...modules.downloader.manager import get_download_manager
            download_manager = get_download_manager()
            downloads = download_manager.get_all_downloads()
            
            active_count = len([d for d in downloads if d['status'] in ['pending', 'downloading']])
            completed_count = len([d for d in downloads if d['status'] == 'completed'])
            
            status_text = f"""📊 **系统状态**

🔄 **活跃下载**: {active_count}
✅ **已完成**: {completed_count}
📁 **总任务**: {len(downloads)}

🤖 **机器人状态**: 正常运行
⚙️ **自动下载**: {'启用' if config.get('auto_download') else '禁用'}"""
            
            notifier.send_message(status_text)
            return {'action': 'command_processed', 'command': 'status'}
            
        elif command.startswith('/downloads'):
            # 获取最近下载
            from ...modules.downloader.manager import get_download_manager
            download_manager = get_download_manager()
            downloads = download_manager.get_all_downloads()
            
            recent_downloads = downloads[:5]  # 最近5个
            
            if not recent_downloads:
                downloads_text = "📋 **最近下载**\n\n暂无下载记录"
            else:
                downloads_text = "📋 **最近下载**\n\n"
                for i, download in enumerate(recent_downloads, 1):
                    status_emoji = {
                        'pending': '⏳',
                        'downloading': '🔄',
                        'completed': '✅',
                        'failed': '❌'
                    }.get(download['status'], '❓')
                    
                    title = download.get('title', 'Unknown')[:30]
                    downloads_text += f"{i}. {status_emoji} {title}\n"
            
            notifier.send_message(downloads_text)
            return {'action': 'command_processed', 'command': 'downloads'}
            
        else:
            # 未知命令
            notifier.send_message("❓ 未知命令，发送 /start 查看帮助")
            return {'action': 'unknown_command', 'command': command}
            
    except Exception as e:
        logger.error(f"处理命令失败: {e}")
        return {'action': 'command_error', 'error': str(e)}


def _handle_download_request(url, config):
    """处理下载请求"""
    try:
        from ...modules.downloader.manager import get_download_manager
        download_manager = get_download_manager()

        # 构建下载选项
        download_options = {
            'telegram_push': True,
            'telegram_push_mode': config.get('push_mode', 'file'),
            'source': 'telegram_webhook',
            'quality': 'medium'  # 默认中等质量
        }

        # 创建下载任务
        download_id = download_manager.create_download(url, download_options)

        # 发送确认消息
        _send_confirmation_message(url, config, download_id=download_id)
        
        return {
            'action': 'download_started',
            'download_id': download_id,
            'url': url
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"处理下载请求失败: {error_msg}")

        # 发送错误消息
        from .notifier import get_telegram_notifier
        notifier = get_telegram_notifier()

        # 根据错误类型提供不同的建议
        if 'cookies' in error_msg.lower() or 'bot' in error_msg.lower():
            error_text = f"""❌ **下载失败 - 需要身份验证**

🔗 **链接**: {url}
⚠️ **错误**: {error_msg}

💡 **解决方案**:
1. 访问 Cookies 管理页面
2. 上传对应网站的 Cookies
3. 重新发送链接下载

📖 **获取Cookies教程**:
使用浏览器扩展或开发者工具导出cookies"""
        else:
            error_text = f"""❌ **下载失败**

🔗 **链接**: {url}
⚠️ **错误**: {error_msg}

💡 **建议**:
• 检查链接是否有效
• 稍后重试
• 联系管理员"""

        notifier.send_message(error_text)

        return {'action': 'download_error', 'error': error_msg}


def _send_help_message(config):
    """发送帮助信息"""
    try:
        from .notifier import get_telegram_notifier
        notifier = get_telegram_notifier()
        
        help_text = """🤖 **使用说明**

请发送视频链接，我会自动下载并发送给您！

**支持的网站：**
• YouTube、Bilibili、Twitter
• Instagram、TikTok、Facebook
• 以及其他 1000+ 网站

**示例：**
`https://www.youtube.com/watch?v=dQw4w9WgXcQ`

发送 /start 查看更多命令"""
        
        notifier.send_message(help_text)
        
    except Exception as e:
        logger.error(f"发送帮助信息失败: {e}")


def _send_confirmation_message(url, config, download_id=None, auto_download=True):
    """发送确认消息"""
    try:
        from .notifier import get_telegram_notifier
        notifier = get_telegram_notifier()
        
        if auto_download and download_id:
            confirm_text = f"""✅ **下载已开始**

🔗 **链接**: {url}
📋 **任务ID**: `{download_id}`

⏳ 下载完成后会自动发送文件给您！"""
        else:
            confirm_text = f"""📥 **收到下载链接**

🔗 {url}

⚠️ 自动下载已禁用，请手动在网页端开始下载。"""
        
        notifier.send_message(confirm_text)
        
    except Exception as e:
        logger.error(f"发送确认消息失败: {e}")


def _is_valid_url(text):
    """验证URL格式"""
    try:
        # 基本URL格式检查
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return bool(url_pattern.match(text))
        
    except Exception:
        return False


# ==================== API接口 ====================

@telegram_bp.route('/api/setup-webhook', methods=['POST'])
@auth_required
def setup_webhook():
    """设置Telegram Webhook"""
    try:
        from ...core.database import get_database
        db = get_database()
        config = db.get_telegram_config()

        if not config or not config.get('bot_token') or not config.get('chat_id'):
            return jsonify({
                'success': False,
                'error': '请先配置 Bot Token 和 Chat ID'
            }), 400

        # 获取请求数据
        request_data = request.get_json() or {}
        custom_webhook_url = request_data.get('webhook_url')

        # 构建 Webhook URL
        if custom_webhook_url:
            webhook_url = custom_webhook_url
            logger.info(f'使用自定义 Webhook URL: {webhook_url}')
        else:
            webhook_url = request.url_root.rstrip('/') + '/telegram/webhook'
            logger.info(f'使用默认 Webhook URL: {webhook_url}')

        # 设置webhook
        import requests
        bot_token = config['bot_token']
        telegram_api_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
        
        webhook_data = {'url': webhook_url}
        
        response = requests.post(telegram_api_url, json=webhook_data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get('ok'):
            logger.info(f"✅ Webhook设置成功: {webhook_url}")
            return jsonify({
                'success': True,
                'message': 'Webhook设置成功',
                'webhook_url': webhook_url
            })
        else:
            error_msg = result.get('description', '未知错误')
            logger.error(f"❌ Webhook设置失败: {error_msg}")
            return jsonify({
                'success': False,
                'error': f'Webhook设置失败: {error_msg}'
            }), 400

    except Exception as e:
        logger.error(f"❌ 设置Webhook失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
