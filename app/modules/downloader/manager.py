# -*- coding: utf-8 -*-
"""
下载管理器 - 核心下载逻辑
"""

import os
import uuid
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class DownloadManager:
    """下载管理器"""
    
    def __init__(self):
        self.downloads: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.RLock()
        self.executor = None
        self._initialize()
    
    def _initialize(self):
        """初始化下载管理器"""
        try:
            from ...core.config import get_config
            
            # 获取配置
            max_concurrent = get_config('downloader.max_concurrent', 3)
            self.output_dir = Path(get_config('downloader.output_dir', '/app/downloads'))
            self.temp_dir = Path(get_config('downloader.temp_dir', '/app/temp'))
            
            # 创建目录
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建线程池
            self.executor = ThreadPoolExecutor(max_workers=max_concurrent)
            
            logger.info(f"✅ 下载管理器初始化完成 - 最大并发: {max_concurrent}")
            
        except Exception as e:
            logger.error(f"❌ 下载管理器初始化失败: {e}")
            raise
    
    def create_download(self, url: str, options: Dict[str, Any] = None) -> str:
        """创建下载任务"""
        try:
            download_id = str(uuid.uuid4())
            
            # 创建下载记录
            download_info = {
                'id': download_id,
                'url': url,
                'status': 'pending',
                'progress': 0,
                'title': None,
                'file_path': None,
                'file_size': None,
                'error_message': None,
                'created_at': datetime.now(),
                'completed_at': None,
                'options': options or {}
            }
            
            with self.lock:
                self.downloads[download_id] = download_info
            
            # 保存到数据库
            from ...core.database import get_database
            db = get_database()
            db.save_download_record(download_id, url)
            
            # 发送下载开始事件
            from ...core.events import emit, Events
            emit(Events.DOWNLOAD_STARTED, {
                'download_id': download_id,
                'url': url,
                'options': options
            })
            
            # 提交下载任务
            self.executor.submit(self._execute_download, download_id)
            
            logger.info(f"📥 创建下载任务: {download_id} - {url}")
            return download_id
            
        except Exception as e:
            logger.error(f"❌ 创建下载任务失败: {e}")
            raise
    
    def get_download(self, download_id: str) -> Optional[Dict[str, Any]]:
        """获取下载信息"""
        with self.lock:
            return self.downloads.get(download_id)
    
    def get_all_downloads(self) -> List[Dict[str, Any]]:
        """获取所有下载"""
        with self.lock:
            return list(self.downloads.values())
    
    def cancel_download(self, download_id: str) -> bool:
        """取消下载"""
        try:
            with self.lock:
                download_info = self.downloads.get(download_id)
                if not download_info:
                    return False
                
                if download_info['status'] in ['completed', 'failed', 'cancelled']:
                    return False
                
                download_info['status'] = 'cancelled'
                download_info['error_message'] = '用户取消'
            
            # 更新数据库
            from ...core.database import get_database
            db = get_database()
            db.update_download_status(download_id, 'cancelled', error_message='用户取消')
            
            logger.info(f"🚫 取消下载: {download_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 取消下载失败: {e}")
            return False
    
    def _execute_download(self, download_id: str):
        """执行下载任务"""
        try:
            with self.lock:
                download_info = self.downloads.get(download_id)
                if not download_info:
                    return
                
                url = download_info['url']
                options = download_info['options']
            
            logger.info(f"🔄 开始执行下载: {download_id} - {url}")
            
            # 更新状态为下载中
            self._update_download_status(download_id, 'downloading', 0)
            
            # 获取视频信息
            video_info = self._extract_video_info(url)
            if not video_info:
                self._update_download_status(download_id, 'failed', error_message='无法获取视频信息')
                return
            
            # 更新标题
            title = video_info.get('title', 'Unknown')
            with self.lock:
                self.downloads[download_id]['title'] = title
            
            # 执行下载
            file_path = self._download_video(download_id, url, video_info, options)
            
            if file_path and Path(file_path).exists():
                # 下载成功
                file_size = Path(file_path).stat().st_size
                self._update_download_status(download_id, 'completed', 100, file_path, file_size)
                
                # 发送下载完成事件
                from ...core.events import emit, Events
                emit(Events.DOWNLOAD_COMPLETED, {
                    'download_id': download_id,
                    'url': url,
                    'title': title,
                    'file_path': file_path,
                    'file_size': file_size
                })
                
                logger.info(f"✅ 下载完成: {download_id} - {title}")
            else:
                # 下载失败
                self._update_download_status(download_id, 'failed', error_message='下载文件不存在')
                
        except Exception as e:
            logger.error(f"❌ 下载执行失败 {download_id}: {e}")
            self._update_download_status(download_id, 'failed', error_message=str(e))
            
            # 发送下载失败事件
            from ...core.events import emit, Events
            emit(Events.DOWNLOAD_FAILED, {
                'download_id': download_id,
                'url': download_info.get('url'),
                'error': str(e)
            })
    
    def _extract_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """提取视频信息"""
        try:
            from yt_dlp import YoutubeDL

            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'no_color': True,
                'ignoreerrors': True
            }

            # 添加Cookies支持
            cookies_file = self._get_cookies_for_url(url)
            if cookies_file:
                ydl_opts['cookiefile'] = cookies_file
                logger.info(f"✅ 使用Cookies文件: {cookies_file}")

            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                # 确保返回可序列化的字典
                return ydl.sanitize_info(info) if info else None

        except Exception as e:
            logger.error(f"❌ 提取视频信息失败: {e}")
            return None
    
    def _download_video(self, download_id: str, url: str, video_info: Dict[str, Any], options: Dict[str, Any]) -> Optional[str]:
        """下载视频"""
        try:
            from yt_dlp import YoutubeDL

            # 构建下载选项
            ydl_opts = self._build_download_options(download_id, options, url)

            # 进度回调
            def progress_hook(d):
                if d['status'] == 'downloading':
                    try:
                        total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                        downloaded = d.get('downloaded_bytes', 0)

                        if total > 0:
                            progress = int((downloaded / total) * 100)
                            self._update_download_progress(download_id, progress)
                    except:
                        pass
                elif d['status'] == 'finished':
                    self._update_download_progress(download_id, 100)
                    logger.info(f"✅ 下载完成: {download_id}")
                elif d['status'] == 'error':
                    error_msg = d.get('error', '下载错误')
                    logger.error(f"❌ 下载错误: {error_msg}")
                    self._update_download_status(download_id, 'failed', error_message=error_msg)

            ydl_opts['progress_hooks'] = [progress_hook]

            # 执行下载
            with YoutubeDL(ydl_opts) as ydl:
                # 使用extract_info而不是download，以便更好地处理错误
                info = ydl.extract_info(url, download=True)
                if not info:
                    raise Exception("无法获取视频信息")

            # 查找下载的文件
            downloaded_file = self._find_downloaded_file(download_id, video_info)
            if downloaded_file:
                logger.info(f"✅ 文件下载成功: {downloaded_file}")
                # 获取文件大小
                file_size = Path(downloaded_file).stat().st_size if Path(downloaded_file).exists() else 0
                self._update_download_status(download_id, 'completed', 100, downloaded_file, file_size)

                # 发送下载完成事件
                from ...core.events import emit, Events
                emit(Events.DOWNLOAD_COMPLETED, {
                    'download_id': download_id,
                    'url': url,
                    'title': video_info.get('title', 'Unknown'),
                    'file_path': downloaded_file,
                    'file_size': file_size,
                    'options': options
                })
                logger.info(f"📤 下载完成事件已发送: {download_id}")
            else:
                logger.warning(f"⚠️ 下载完成但未找到文件: {download_id}")
                self._update_download_status(download_id, 'failed', error_message="下载完成但未找到文件")

                # 发送下载失败事件
                from ...core.events import emit, Events
                emit(Events.DOWNLOAD_FAILED, {
                    'download_id': download_id,
                    'url': url,
                    'error': "下载完成但未找到文件"
                })

            return downloaded_file

        except Exception as e:
            logger.error(f"❌ 视频下载失败: {e}")
            self._update_download_status(download_id, 'failed', error_message=str(e))

            # 发送下载失败事件
            from ...core.events import emit, Events
            emit(Events.DOWNLOAD_FAILED, {
                'download_id': download_id,
                'url': url,
                'error': str(e)
            })

            return None
    
    def _build_download_options(self, download_id: str, options: Dict[str, Any], url: str) -> Dict[str, Any]:
        """构建下载选项"""
        from ...core.config import get_config
        
        # 基础选项
        ydl_opts = {
            'outtmpl': str(self.output_dir / f'{download_id}_%(title)s.%(ext)s'),
            'format': get_config('ytdlp.format', 'best[height<=720]'),
            'writesubtitles': False,
            'writeautomaticsub': False,
            'ignoreerrors': False,
            'no_warnings': True,
            'extractaudio': False,
            'audioformat': 'mp3',
            'audioquality': '192',
        }
        
        # 应用用户选项
        if 'format' in options:
            ydl_opts['format'] = options['format']
        
        if 'audio_only' in options and options['audio_only']:
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['extractaudio'] = True
        
        if 'quality' in options:
            quality = options['quality']
            if quality == 'high':
                ydl_opts['format'] = 'best'
            elif quality == 'medium':
                ydl_opts['format'] = 'best[height<=720]'
            elif quality == 'low':
                ydl_opts['format'] = 'worst'

        # 添加Cookies支持
        cookies_file = self._get_cookies_for_url(url)
        if cookies_file:
            ydl_opts['cookiefile'] = cookies_file
            logger.info(f"✅ 使用Cookies文件: {cookies_file}")

        return ydl_opts

    def _get_cookies_for_url(self, url: str) -> Optional[str]:
        """为URL获取对应的Cookies文件"""
        try:
            from ..cookies.manager import get_cookies_manager
            cookies_manager = get_cookies_manager()
            return cookies_manager.get_cookies_for_ytdlp(url)
        except Exception as e:
            logger.warning(f"⚠️ 获取Cookies失败: {e}")
            return None

    def _find_downloaded_file(self, download_id: str, video_info: Dict[str, Any]) -> Optional[str]:
        """查找下载的文件"""
        try:
            # 搜索包含download_id的文件
            for file_path in self.output_dir.glob(f'{download_id}_*'):
                if file_path.is_file():
                    return str(file_path)
            
            # 如果没找到，尝试按标题搜索
            title = video_info.get('title', '')
            if title:
                # 清理标题中的特殊字符
                safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
                for file_path in self.output_dir.glob(f'*{safe_title}*'):
                    if file_path.is_file():
                        return str(file_path)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 查找下载文件失败: {e}")
            return None
    
    def _update_download_status(self, download_id: str, status: str, progress: int = None, 
                               file_path: str = None, file_size: int = None, error_message: str = None):
        """更新下载状态"""
        try:
            with self.lock:
                download_info = self.downloads.get(download_id)
                if download_info:
                    download_info['status'] = status
                    if progress is not None:
                        download_info['progress'] = progress
                    if file_path:
                        download_info['file_path'] = file_path
                    if file_size:
                        download_info['file_size'] = file_size
                    if error_message:
                        download_info['error_message'] = error_message
                    if status == 'completed':
                        download_info['completed_at'] = datetime.now()
            
            # 更新数据库
            from ...core.database import get_database
            db = get_database()
            db.update_download_status(download_id, status, progress, file_path, file_size, error_message)
            
            # 发送进度事件
            if progress is not None:
                from ...core.events import emit, Events
                emit(Events.DOWNLOAD_PROGRESS, {
                    'download_id': download_id,
                    'status': status,
                    'progress': progress
                })
            
        except Exception as e:
            logger.error(f"❌ 更新下载状态失败: {e}")
    
    def _update_download_progress(self, download_id: str, progress: int):
        """更新下载进度"""
        self._update_download_status(download_id, 'downloading', progress)
    
    def cleanup(self):
        """清理资源"""
        try:
            if self.executor:
                self.executor.shutdown(wait=True)
            logger.info("✅ 下载管理器清理完成")
        except Exception as e:
            logger.error(f"❌ 下载管理器清理失败: {e}")


# 全局下载管理器实例
_download_manager = None

def get_download_manager() -> DownloadManager:
    """获取下载管理器实例"""
    global _download_manager
    if _download_manager is None:
        _download_manager = DownloadManager()
    return _download_manager
