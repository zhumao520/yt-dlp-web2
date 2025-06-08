# -*- coding: utf-8 -*-
"""
Telegram通知器 - 双API模式推送
"""

import asyncio
import logging
import requests
import threading
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Telegram通知器 - 支持Bot API和Pyrogram双模式"""

    def __init__(self):
        self.config = None
        self.pyrogram_client = None
        self._lock = threading.RLock()
        self._processed_downloads = set()  # 防重复推送
        self._load_config()
    
    def _load_config(self):
        """加载Telegram配置"""
        try:
            from ...core.database import get_database
            db = get_database()
            self.config = db.get_telegram_config()
            
            if self.config:
                logger.info("✅ Telegram配置加载成功")
            else:
                logger.info("ℹ️ 未找到Telegram配置")
                
        except Exception as e:
            logger.error(f"❌ 加载Telegram配置失败: {e}")
    
    def is_enabled(self) -> bool:
        """检查Telegram是否启用"""
        return (self.config and 
                self.config.get('enabled', False) and 
                self.config.get('bot_token') and 
                self.config.get('chat_id'))
    
    def send_message(self, message: str, parse_mode: str = 'Markdown') -> bool:
        """发送文本消息"""
        if not self.is_enabled():
            logger.debug("Telegram未启用，跳过消息发送")
            return False
        
        try:
            # 优先使用Bot API
            if self._send_message_via_bot_api(message, parse_mode):
                return True
            
            # Bot API失败，尝试Pyrogram
            if self.config.get('api_id') and self.config.get('api_hash'):
                return self._send_message_via_pyrogram(message, parse_mode)
            
            return False
            
        except Exception as e:
            logger.error(f"❌ 发送Telegram消息失败: {e}")
            return False
    
    def send_file(self, file_path: str, caption: str = None) -> bool:
        """发送文件 - 智能选择发送方式"""
        if not self.is_enabled():
            logger.debug("Telegram未启用，跳过文件发送")
            return False

        try:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.error(f"文件不存在: {file_path}")
                return False

            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            file_size_limit = self.config.get('file_size_limit', 50)

            logger.info(f"📤 准备发送文件: {file_path.name} ({file_size_mb:.1f}MB)")

            # 策略1: 小文件优先使用Bot API
            if file_size_mb <= file_size_limit:
                logger.debug(f"小文件({file_size_mb:.1f}MB <= {file_size_limit}MB)，使用Bot API")
                if self._send_file_via_bot_api(str(file_path), caption):
                    logger.info("✅ Bot API发送成功")
                    return True
                else:
                    logger.warning("⚠️ Bot API发送失败，尝试Pyrogram备用...")

            # 策略2: 大文件或Bot API失败时使用Pyrogram
            if self.config.get('api_id') and self.config.get('api_hash'):
                logger.debug(f"使用Pyrogram发送文件({file_size_mb:.1f}MB)")
                if self._send_file_via_pyrogram(str(file_path), caption):
                    logger.info("✅ Pyrogram发送成功")
                    return True
                else:
                    logger.warning("⚠️ Pyrogram发送失败")

                    # 策略3: 如果是大文件且Pyrogram失败，尝试Bot API作为最后手段
                    if file_size_mb > file_size_limit:
                        logger.info("🔄 大文件Pyrogram失败，尝试Bot API作为最后手段...")
                        if self._send_file_via_bot_api(str(file_path), caption):
                            logger.info("✅ Bot API备用发送成功")
                            return True
            else:
                logger.warning(f"文件过大({file_size_mb:.1f}MB > {file_size_limit}MB)且未配置Pyrogram")

            logger.error("❌ 所有发送方式都失败")
            return False

        except Exception as e:
            logger.error(f"❌ 发送Telegram文件失败: {e}")
            return False
    
    def _send_message_via_bot_api(self, message: str, parse_mode: str = 'Markdown') -> bool:
        """通过Bot API发送消息"""
        try:
            url = f"https://api.telegram.org/bot{self.config['bot_token']}/sendMessage"
            
            data = {
                'chat_id': self.config['chat_id'],
                'text': message,
                'parse_mode': parse_mode
            }
            
            response = requests.post(url, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get('ok'):
                logger.debug("✅ Bot API消息发送成功")
                return True
            else:
                logger.error(f"❌ Bot API消息发送失败: {result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Bot API消息发送异常: {e}")
            return False
    
    def _send_file_via_bot_api(self, file_path: str, caption: str = None) -> bool:
        """通过Bot API发送文件 - 智能选择发送类型"""
        try:
            file_path_obj = Path(file_path)

            # 检查文件类型
            if self._is_video_file(file_path_obj):
                # 视频文件使用sendVideo API
                return self._send_video_via_bot_api(file_path, caption)
            else:
                # 其他文件使用sendDocument API
                return self._send_document_via_bot_api(file_path, caption)

        except Exception as e:
            logger.error(f"❌ Bot API文件发送异常: {e}")
            return False

    def _send_video_via_bot_api(self, file_path: str, caption: str = None) -> bool:
        """通过Bot API发送视频"""
        try:
            url = f"https://api.telegram.org/bot{self.config['bot_token']}/sendVideo"

            # 获取视频分辨率
            width, height = self._get_video_resolution(file_path)

            with open(file_path, 'rb') as file:
                files = {'video': file}
                data = {
                    'chat_id': self.config['chat_id'],
                    'caption': caption or '',
                    'supports_streaming': True,  # 支持流媒体播放
                    'width': width,   # 动态宽度
                    'height': height  # 动态高度
                }

                response = requests.post(url, files=files, data=data, timeout=300)
                response.raise_for_status()

                result = response.json()
                if result.get('ok'):
                    logger.info("✅ Bot API视频发送成功")
                    return True
                else:
                    logger.error(f"❌ Bot API视频发送失败: {result}")
                    return False

        except Exception as e:
            logger.error(f"❌ Bot API视频发送异常: {e}")
            return False

    def _send_document_via_bot_api(self, file_path: str, caption: str = None) -> bool:
        """通过Bot API发送文档"""
        try:
            url = f"https://api.telegram.org/bot{self.config['bot_token']}/sendDocument"

            with open(file_path, 'rb') as file:
                files = {'document': file}
                data = {
                    'chat_id': self.config['chat_id'],
                    'caption': caption or ''
                }

                response = requests.post(url, files=files, data=data, timeout=300)
                response.raise_for_status()

                result = response.json()
                if result.get('ok'):
                    logger.info("✅ Bot API文档发送成功")
                    return True
                else:
                    logger.error(f"❌ Bot API文档发送失败: {result}")
                    return False

        except Exception as e:
            logger.error(f"❌ Bot API文档发送异常: {e}")
            return False
    
    def _send_message_via_pyrogram(self, message: str, parse_mode: str = 'Markdown') -> bool:
        """通过Pyrogram发送消息"""
        try:
            # 在新线程中运行异步操作
            def run_async():
                return asyncio.run(self._async_send_message(message, parse_mode))
            
            thread = threading.Thread(target=run_async, daemon=True)
            thread.start()
            thread.join(timeout=30)
            
            return thread.is_alive() == False  # 如果线程结束说明发送完成
            
        except Exception as e:
            logger.error(f"❌ Pyrogram消息发送异常: {e}")
            return False
    
    def _send_file_via_pyrogram(self, file_path: str, caption: str = None) -> bool:
        """通过Pyrogram发送文件"""
        try:
            # 在新线程中运行异步操作
            result = [False]  # 使用列表来在线程间传递结果
            exception_info = [None]  # 存储异常信息

            def run_async():
                try:
                    # 创建新的事件循环
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result[0] = loop.run_until_complete(self._async_send_file(file_path, caption))
                    finally:
                        loop.close()
                except Exception as e:
                    logger.error(f"❌ Pyrogram异步文件发送失败: {e}")
                    exception_info[0] = str(e)
                    result[0] = False

            thread = threading.Thread(target=run_async, daemon=True)
            thread.start()
            thread.join(timeout=300)  # 5分钟超时

            if thread.is_alive():
                logger.error("❌ Pyrogram文件发送超时")
                return False

            if exception_info[0]:
                logger.error(f"❌ Pyrogram发送异常: {exception_info[0]}")

            return result[0]

        except Exception as e:
            logger.error(f"❌ Pyrogram文件发送异常: {e}")
            return False
    
    async def _async_send_message(self, message: str, parse_mode: str = 'Markdown') -> bool:
        """异步发送消息"""
        try:
            client = await self._get_pyrogram_client()
            if not client:
                return False
            
            await client.send_message(
                chat_id=int(self.config['chat_id']),
                text=message
            )
            
            logger.debug("✅ Pyrogram消息发送成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ Pyrogram异步消息发送失败: {e}")
            return False
    
    async def _async_send_file(self, file_path: str, caption: str = None) -> bool:
        """异步发送文件 - 智能选择发送类型"""
        client = None
        try:
            client = await self._get_pyrogram_client()
            if not client:
                logger.error("❌ 无法获取Pyrogram客户端")
                return False

            # 确保客户端已连接
            if not client.is_connected:
                logger.info("🔄 Pyrogram客户端未连接，尝试重新连接...")
                await client.start()

            file_path_obj = Path(file_path)

            # 检查文件类型并选择合适的发送方法
            if self._is_video_file(file_path_obj):
                # 获取视频分辨率
                width, height = self._get_video_resolution(file_path)

                # 视频文件使用send_video
                await client.send_video(
                    chat_id=int(self.config['chat_id']),
                    video=file_path,
                    caption=caption or '',
                    supports_streaming=True,  # 支持流媒体播放
                    width=width,   # 动态宽度
                    height=height  # 动态高度
                )
                logger.info("✅ Pyrogram视频发送成功")
            else:
                # 其他文件使用send_document
                await client.send_document(
                    chat_id=int(self.config['chat_id']),
                    document=file_path,
                    caption=caption or ''
                )
                logger.info("✅ Pyrogram文档发送成功")

            return True

        except Exception as e:
            logger.error(f"❌ Pyrogram异步文件发送失败: {e}")

            # 如果连接失败，尝试清理并重置客户端
            if client and "connection" in str(e).lower():
                try:
                    logger.info("🔄 检测到连接问题，重置Pyrogram客户端...")
                    await client.stop()
                    self.pyrogram_client = None
                except:
                    pass

            return False
    
    async def _get_pyrogram_client(self):
        """获取Pyrogram客户端"""
        try:
            # 检查必要的配置
            if not all([self.config.get('api_id'), self.config.get('api_hash'), self.config.get('bot_token')]):
                logger.error("❌ Pyrogram配置不完整")
                return None

            if not self.pyrogram_client:
                from pyrogram import Client

                # 创建客户端时添加更多配置
                self.pyrogram_client = Client(
                    name="ytdlp_bot",
                    api_id=int(self.config['api_id']),
                    api_hash=self.config['api_hash'],
                    bot_token=self.config['bot_token'],
                    workers=1,
                    no_updates=True,
                    sleep_threshold=60,  # 防止flood wait
                    max_concurrent_transmissions=1  # 限制并发传输
                )

                logger.info("🔧 创建新的Pyrogram客户端")

            # 检查连接状态
            if not self.pyrogram_client.is_connected:
                logger.info("🔄 启动Pyrogram客户端...")
                await self.pyrogram_client.start()
                logger.info("✅ Pyrogram客户端已连接")

            return self.pyrogram_client

        except Exception as e:
            logger.error(f"❌ 获取Pyrogram客户端失败: {e}")
            # 清理失败的客户端
            if self.pyrogram_client:
                try:
                    await self.pyrogram_client.stop()
                except:
                    pass
                self.pyrogram_client = None
            return None

    def _is_video_file(self, file_path: Path) -> bool:
        """检查是否为视频文件"""
        video_extensions = {
            '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm',
            '.m4v', '.3gp', '.ogv', '.ts', '.m2ts', '.mts'
        }
        return file_path.suffix.lower() in video_extensions

    def _get_video_resolution(self, file_path: str) -> tuple:
        """获取视频分辨率"""
        try:
            import subprocess
            import json

            # 使用ffprobe获取视频信息
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_streams', '-select_streams', 'v:0', file_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                if 'streams' in data and len(data['streams']) > 0:
                    stream = data['streams'][0]
                    width = stream.get('width', 1280)
                    height = stream.get('height', 720)

                    # 限制最大分辨率以适应Telegram
                    if width > 1920:
                        # 按比例缩放到1920p
                        ratio = 1920 / width
                        width = 1920
                        height = int(height * ratio)

                    logger.info(f"📐 检测到视频分辨率: {width}x{height}")
                    return width, height

            # 如果获取失败，返回默认值
            logger.warning(f"⚠️ 无法获取视频分辨率，使用默认值: {file_path}")
            return 1280, 720

        except Exception as e:
            logger.warning(f"⚠️ 获取视频分辨率失败: {e}")
            return 1280, 720

    def test_connection(self) -> Dict[str, Any]:
        """测试连接"""
        if not self.is_enabled():
            return {'success': False, 'error': 'Telegram未配置或未启用'}
        
        try:
            # 测试Bot API
            test_message = "🧪 YT-DLP Web V2 连接测试"
            bot_api_success = self._send_message_via_bot_api(test_message)
            
            result = {
                'success': bot_api_success,
                'bot_api': bot_api_success,
                'pyrogram': False
            }
            
            # 如果配置了Pyrogram，也测试一下
            if self.config.get('api_id') and self.config.get('api_hash'):
                pyrogram_success = self._send_message_via_pyrogram("🔧 Pyrogram连接测试")
                result['pyrogram'] = pyrogram_success
                result['success'] = bot_api_success or pyrogram_success
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Telegram连接测试失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def cleanup(self):
        """清理资源"""
        try:
            if self.pyrogram_client:
                # 在新线程中停止客户端
                def stop_client():
                    try:
                        # 创建新的事件循环来停止客户端
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            if self.pyrogram_client.is_connected:
                                loop.run_until_complete(self.pyrogram_client.stop())
                        finally:
                            loop.close()
                    except Exception as e:
                        logger.debug(f"停止Pyrogram客户端时出现异常: {e}")

                thread = threading.Thread(target=stop_client, daemon=True)
                thread.start()
                thread.join(timeout=10)  # 增加超时时间

                self.pyrogram_client = None
                logger.info("✅ Pyrogram客户端已清理")

            # 清理已处理下载记录
            if hasattr(self, '_processed_downloads'):
                self._processed_downloads.clear()

            logger.info("✅ Telegram通知器清理完成")

        except Exception as e:
            logger.error(f"❌ Telegram通知器清理失败: {e}")


# 全局Telegram通知器实例
_telegram_notifier = None

def get_telegram_notifier() -> TelegramNotifier:
    """获取Telegram通知器实例"""
    global _telegram_notifier
    if _telegram_notifier is None:
        _telegram_notifier = TelegramNotifier()
    return _telegram_notifier


# 事件监听器 - 自动注册下载完成推送
from ...core.events import on, Events

@on(Events.DOWNLOAD_COMPLETED)
def handle_download_completed(data):
    """处理下载完成事件"""
    try:
        notifier = get_telegram_notifier()
        if not notifier.is_enabled():
            return

        download_id = data.get('download_id')
        title = data.get('title', 'Unknown')
        file_size_mb = data.get('file_size', 0) / (1024 * 1024) if data.get('file_size') else 0
        file_path = data.get('file_path')

        # 防重复推送检查
        if download_id in notifier._processed_downloads:
            logger.debug(f"📤 跳过重复推送: {download_id} - {title}")
            return

        notifier._processed_downloads.add(download_id)

        # 获取配置
        push_mode = notifier.config.get('push_mode', 'file')
        file_size_limit = notifier.config.get('file_size_limit', 50)

        logger.info(f"📤 处理Telegram推送: {title} ({file_size_mb:.1f}MB)")

        # 根据文件大小和配置决定推送方式
        if push_mode == 'notification':
            # 只发送通知，不发送文件
            message = f"✅ **下载完成**\n\n📹 **标题**: {title}\n📁 **大小**: {file_size_mb:.1f}MB"
            notifier.send_message(message)
            logger.info(f"📤 发送通知消息: {title}")

        elif file_size_mb <= file_size_limit:
            # 小文件：直接发送文件（使用Bot API）
            if file_path and push_mode in ['file', 'both']:
                caption = f"📹 {title} ({file_size_mb:.1f}MB)"
                success = notifier.send_file(file_path, caption)
                if success:
                    logger.info(f"📤 发送小文件成功: {title}")
                else:
                    # 文件发送失败，发送通知消息
                    message = f"✅ **下载完成**\n\n📹 **标题**: {title}\n📁 **大小**: {file_size_mb:.1f}MB\n\n⚠️ 文件发送失败，请手动下载"
                    notifier.send_message(message)
                    logger.warning(f"📤 文件发送失败，改为通知: {title}")
            else:
                # 配置为只发通知
                message = f"✅ **下载完成**\n\n📹 **标题**: {title}\n📁 **大小**: {file_size_mb:.1f}MB"
                notifier.send_message(message)
                logger.info(f"📤 发送通知消息: {title}")

        else:
            # 大文件：尝试使用Pyrogram发送，失败则发送通知
            if file_path and push_mode in ['file', 'both'] and notifier.config.get('api_id') and notifier.config.get('api_hash'):
                caption = f"📹 {title} ({file_size_mb:.1f}MB)"
                success = notifier.send_file(file_path, caption)
                if success:
                    logger.info(f"📤 发送大文件成功: {title}")
                else:
                    # Pyrogram发送失败，发送通知消息
                    message = f"✅ **下载完成**\n\n📹 **标题**: {title}\n📁 **大小**: {file_size_mb:.1f}MB\n\n⚠️ 文件过大且Pyrogram配置有误，请手动下载"
                    notifier.send_message(message)
                    logger.warning(f"📤 大文件发送失败，改为通知: {title}")
            else:
                # 大文件但没有Pyrogram配置，只发送通知
                message = f"✅ **下载完成**\n\n📹 **标题**: {title}\n📁 **大小**: {file_size_mb:.1f}MB\n\n💡 文件过大({file_size_mb:.1f}MB > {file_size_limit}MB)，请手动下载"
                notifier.send_message(message)
                logger.info(f"📤 大文件通知: {title}")

        logger.info(f"📤 Telegram推送完成: {title}")

        # 清理旧的下载ID（保留最近100个）
        if len(notifier._processed_downloads) > 100:
            # 转换为列表，保留最新的100个
            recent_downloads = list(notifier._processed_downloads)[-100:]
            notifier._processed_downloads = set(recent_downloads)
            logger.debug(f"📤 清理旧下载ID，保留最近100个")

    except Exception as e:
        logger.error(f"❌ Telegram推送失败: {e}")


@on(Events.DOWNLOAD_FAILED)
def handle_download_failed(data):
    """处理下载失败事件"""
    try:
        notifier = get_telegram_notifier()
        if not notifier.is_enabled():
            return
        
        url = data.get('url', 'Unknown')
        error = data.get('error', 'Unknown error')
        
        message = f"❌ **下载失败**\n\n🔗 **链接**: {url}\n⚠️ **错误**: {error}"
        notifier.send_message(message)
        
        logger.info(f"📤 Telegram错误通知发送: {url}")
        
    except Exception as e:
        logger.error(f"❌ Telegram错误通知失败: {e}")
