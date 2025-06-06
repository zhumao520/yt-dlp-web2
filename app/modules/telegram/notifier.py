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
        """发送文件"""
        if not self.is_enabled():
            logger.debug("Telegram未启用，跳过文件发送")
            return False
        
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.error(f"文件不存在: {file_path}")
                return False
            
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            logger.info(f"📤 准备发送文件: {file_path.name} ({file_size_mb:.1f}MB)")
            
            # 根据文件大小选择发送方式
            if file_size_mb <= 50:
                # 小文件优先使用Bot API
                if self._send_file_via_bot_api(str(file_path), caption):
                    return True
            
            # 大文件或Bot API失败，使用Pyrogram
            if self.config.get('api_id') and self.config.get('api_hash'):
                return self._send_file_via_pyrogram(str(file_path), caption)
            
            logger.warning(f"文件过大({file_size_mb:.1f}MB)且未配置Pyrogram，无法发送")
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
        """通过Bot API发送文件"""
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
                    logger.info("✅ Bot API文件发送成功")
                    return True
                else:
                    logger.error(f"❌ Bot API文件发送失败: {result}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Bot API文件发送异常: {e}")
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
            
            def run_async():
                try:
                    result[0] = asyncio.run(self._async_send_file(file_path, caption))
                except Exception as e:
                    logger.error(f"❌ Pyrogram异步文件发送失败: {e}")
                    result[0] = False
            
            thread = threading.Thread(target=run_async, daemon=True)
            thread.start()
            thread.join(timeout=300)  # 5分钟超时
            
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
        """异步发送文件"""
        try:
            client = await self._get_pyrogram_client()
            if not client:
                return False
            
            await client.send_document(
                chat_id=int(self.config['chat_id']),
                document=file_path,
                caption=caption or ''
            )
            
            logger.info("✅ Pyrogram文件发送成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ Pyrogram异步文件发送失败: {e}")
            return False
    
    async def _get_pyrogram_client(self):
        """获取Pyrogram客户端"""
        try:
            if not self.pyrogram_client:
                from pyrogram import Client
                
                self.pyrogram_client = Client(
                    name="ytdlp_bot",
                    api_id=int(self.config['api_id']),
                    api_hash=self.config['api_hash'],
                    bot_token=self.config['bot_token'],
                    workers=1,
                    no_updates=True
                )
            
            if not self.pyrogram_client.is_connected:
                await self.pyrogram_client.start()
            
            return self.pyrogram_client
            
        except Exception as e:
            logger.error(f"❌ 获取Pyrogram客户端失败: {e}")
            return None
    
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
                        asyncio.run(self.pyrogram_client.stop())
                    except:
                        pass
                
                thread = threading.Thread(target=stop_client, daemon=True)
                thread.start()
                thread.join(timeout=5)
                
                self.pyrogram_client = None
            
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
        
        # 发送通知消息
        title = data.get('title', 'Unknown')
        file_size_mb = data.get('file_size', 0) / (1024 * 1024) if data.get('file_size') else 0
        
        message = f"✅ **下载完成**\n\n📹 **标题**: {title}\n📁 **大小**: {file_size_mb:.1f}MB"
        notifier.send_message(message)
        
        # 根据配置决定是否发送文件
        push_mode = notifier.config.get('push_mode', 'file')
        if push_mode in ['file', 'both'] and data.get('file_path'):
            caption = f"📹 {title}"
            notifier.send_file(data['file_path'], caption)
        
        logger.info(f"📤 Telegram推送完成: {title}")
        
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
