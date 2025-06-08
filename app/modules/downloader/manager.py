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

            # 启动自动清理
            self._start_cleanup()

            logger.info(f"✅ 下载管理器初始化完成 - 最大并发: {max_concurrent}")

        except Exception as e:
            logger.error(f"❌ 下载管理器初始化失败: {e}")
            raise

    def _start_cleanup(self):
        """启动自动清理"""
        try:
            from .cleanup import get_cleanup_manager
            cleanup_manager = get_cleanup_manager()
            cleanup_manager.start()
        except Exception as e:
            logger.warning(f"⚠️ 启动自动清理失败: {e}")
    
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
                # 下载成功 - 注意：不在这里发送事件，由_download_video方法统一处理
                logger.info(f"✅ 下载完成: {download_id} - {title}")
            else:
                # 下载失败
                self._update_download_status(download_id, 'failed', error_message='下载文件不存在')

                # 发送下载失败事件
                from ...core.events import emit, Events
                emit(Events.DOWNLOAD_FAILED, {
                    'download_id': download_id,
                    'url': url,
                    'error': '下载文件不存在'
                })
                
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
        """提取视频信息 - 使用智能回退机制"""
        try:
            # 检查是否是YouTube链接
            is_youtube = 'youtube.com' in url or 'youtu.be' in url

            if is_youtube:
                return self._extract_youtube_info_with_fallback(url)
            else:
                return self._extract_general_video_info(url)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ 提取视频信息失败: {error_msg}")
            raise

    def _extract_youtube_info_with_fallback(self, url: str) -> Optional[Dict[str, Any]]:
        """YouTube视频信息提取 - 智能回退机制"""
        from yt_dlp import YoutubeDL

        # 2025年最新的YouTube回退策略
        strategies = [
            {
                'name': 'Android VR客户端',
                'opts': self._get_android_vr_opts(),
                'description': '无需PO Token，当前最稳定'
            },
            {
                'name': 'iOS客户端',
                'opts': self._get_ios_opts(),
                'description': '移动端API，稳定可靠'
            },
            {
                'name': 'Android客户端',
                'opts': self._get_android_opts(),
                'description': '移动端API备用方案'
            },
            {
                'name': '静态Cookies',
                'opts': self._get_cookies_opts(url),
                'description': '使用预配置的cookies文件'
            },
            {
                'name': '默认方式',
                'opts': self._get_default_opts(url),
                'description': '标准网页端API'
            }
        ]

        last_error = None

        for strategy in strategies:
            if strategy['opts'] is None:
                continue

            try:
                logger.info(f"🔄 尝试使用 {strategy['name']} 获取YouTube视频信息...")

                with YoutubeDL(strategy['opts']) as ydl:
                    info = ydl.extract_info(url, download=False)
                    if info:
                        logger.info(f"✅ {strategy['name']} 成功获取视频信息")
                        return ydl.sanitize_info(info)

            except Exception as e:
                error_msg = str(e)
                logger.warning(f"❌ {strategy['name']} 失败: {error_msg}")
                last_error = error_msg

                # 如果是严重错误，直接抛出
                if 'private' in error_msg.lower() or 'not available' in error_msg.lower():
                    raise Exception("视频不可用或为私有内容。")

                continue

        # 所有策略都失败了
        if last_error:
            if 'Sign in to confirm' in last_error or 'bot' in last_error.lower():
                raise Exception("YouTube检测到机器人行为。建议：1) 上传有效的Cookies；2) 稍后重试。")
            elif 'timeout' in last_error.lower():
                raise Exception("网络超时，请稍后重试。")
            else:
                raise Exception(f"所有方法都失败了。最后错误: {last_error}")
        else:
            raise Exception("无法获取视频信息，请检查链接是否正确。")

    def _extract_general_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """提取非YouTube视频信息"""
        from yt_dlp import YoutubeDL

        try:
            ydl_opts = self._get_default_opts(url)

            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return ydl.sanitize_info(info) if info else None

        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ 提取视频信息失败: {error_msg}")

            if 'timeout' in error_msg.lower():
                raise Exception("网络超时，请稍后重试。")
            elif 'not available' in error_msg.lower():
                raise Exception("视频不可用或为私有内容。")
            else:
                raise Exception(f"获取视频信息失败: {error_msg}")
    
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

                # 应用智能文件名策略（如果需要）
                final_file = self._apply_smart_filename(downloaded_file, video_info)

                # 获取文件大小
                file_size = Path(final_file).stat().st_size if Path(final_file).exists() else 0
                self._update_download_status(download_id, 'completed', 100, final_file, file_size)

                # 发送下载完成事件
                from ...core.events import emit, Events
                emit(Events.DOWNLOAD_COMPLETED, {
                    'download_id': download_id,
                    'url': url,
                    'title': video_info.get('title', 'Unknown'),
                    'file_path': final_file,
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

            return final_file if downloaded_file else None

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
    
    def _sanitize_filename(self, filename: str, max_length: int = 80) -> str:
        """清理和截断文件名"""
        import re

        # 移除或替换特殊字符
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = re.sub(r'[｜｜]', '_', filename)  # 替换中文竖线
        filename = re.sub(r'[，。！？；：]', '_', filename)  # 替换中文标点
        filename = re.sub(r'\s+', '_', filename)  # 替换空格为下划线
        filename = re.sub(r'_+', '_', filename)  # 合并多个下划线
        filename = filename.strip('_')  # 移除首尾下划线

        # 截断长度
        if len(filename) > max_length:
            filename = filename[:max_length].rstrip('_')

        return filename or 'video'  # 如果为空则使用默认名称

    def _generate_smart_filename(self, title: str, ext: str) -> str:
        """生成智能文件名：处理长度限制和重复冲突"""
        import re
        from ...core.config import get_config

        # 获取长度限制配置
        max_length = get_config('downloader.max_filename_length', 200)

        # 智能处理原始文件名
        base_filename = title

        # 1. 清理危险字符（保持最小清理）
        # 只清理真正有问题的字符，保留大部分原始字符
        dangerous_chars = r'[<>:"/\\|?*\x00-\x1f]'
        base_filename = re.sub(dangerous_chars, '', base_filename)

        # 清理多余的空格和特殊字符
        base_filename = re.sub(r'\s+', ' ', base_filename).strip()

        # 2. 处理文件名长度
        # 考虑扩展名长度，为可能的冲突后缀预留空间
        max_base_length = max_length - len(ext) - 1  # -1 for dot
        conflict_suffix_space = 12  # 为 _(数字) 或 _(短UUID) 预留空间

        if len(base_filename) > max_base_length - conflict_suffix_space:
            # 如果太长，智能截断
            # 优先保留前面的内容，但尝试保留完整的词
            truncated = base_filename[:max_base_length - conflict_suffix_space]

            # 尝试在词边界截断（中文按字符，英文按单词）
            if any('\u4e00' <= c <= '\u9fff' for c in truncated):
                # 包含中文，直接截断
                base_filename = truncated.rstrip(' -_')
            else:
                # 英文，尝试在单词边界截断
                words = truncated.split()
                if len(words) > 1:
                    # 移除最后一个可能不完整的词
                    truncated = ' '.join(words[:-1])
                base_filename = truncated.rstrip(' -_')

            logger.info(f"📏 文件名过长，已截断: {title[:50]}... -> {base_filename}")

        # 3. 检查文件是否已存在
        candidate_filename = f"{base_filename}.{ext}"
        candidate_path = self.output_dir / candidate_filename

        if not candidate_path.exists():
            # 文件不存在，直接使用
            logger.info(f"📝 生成文件名: {candidate_filename}")
            return candidate_filename

        # 4. 文件已存在，尝试添加数字后缀
        for i in range(2, 100):  # 尝试 (2) 到 (99)
            numbered_filename = f"{base_filename} ({i}).{ext}"
            numbered_path = self.output_dir / numbered_filename
            if not numbered_path.exists():
                logger.info(f"📝 文件名冲突，添加数字后缀: {candidate_filename} -> {numbered_filename}")
                return numbered_filename

        # 5. 如果数字后缀也用完了，使用短UUID
        import uuid
        short_uuid = str(uuid.uuid4())[:8]  # 使用短UUID
        final_filename = f"{base_filename}_{short_uuid}.{ext}"

        logger.info(f"📝 文件名冲突严重，使用UUID后缀: {candidate_filename} -> {final_filename}")
        return final_filename

    def _apply_smart_filename(self, downloaded_file: str, video_info: Dict[str, Any]) -> str:
        """应用智能文件名策略到已下载的文件"""
        try:
            # 获取文件信息
            file_path = Path(downloaded_file)
            if not file_path.exists():
                logger.warning(f"⚠️ 文件不存在，无法重命名: {downloaded_file}")
                return downloaded_file

            title = video_info.get('title', '')
            if not title:
                logger.warning(f"⚠️ 视频标题为空，保持原文件名: {downloaded_file}")
                return downloaded_file

            # 检查是否是临时文件（以temp_开头）
            if file_path.name.startswith('temp_'):
                # 生成最终的智能文件名
                ext = file_path.suffix[1:]  # 移除点号
                smart_filename = self._generate_smart_filename(title, ext)

                # 重命名为最终文件名
                new_file_path = file_path.parent / smart_filename

                try:
                    file_path.rename(new_file_path)
                    logger.info(f"📝 临时文件重命名成功: {file_path.name} -> {smart_filename}")
                    return str(new_file_path)
                except Exception as e:
                    logger.warning(f"⚠️ 临时文件重命名失败: {e}，保持临时文件名")
                    return downloaded_file
            else:
                # 非临时文件，检查是否需要优化文件名
                ext = file_path.suffix[1:]  # 移除点号
                smart_filename = self._generate_smart_filename(title, ext)

                # 如果文件名没有变化，直接返回
                if smart_filename == file_path.name:
                    return downloaded_file

                # 重命名文件
                new_file_path = file_path.parent / smart_filename

                try:
                    file_path.rename(new_file_path)
                    logger.info(f"📝 文件重命名成功: {file_path.name} -> {smart_filename}")
                    return str(new_file_path)
                except Exception as e:
                    logger.warning(f"⚠️ 文件重命名失败: {e}，保持原文件名")
                    return downloaded_file

        except Exception as e:
            logger.error(f"❌ 应用智能文件名失败: {e}")
            return downloaded_file

    def _build_download_options(self, download_id: str, options: Dict[str, Any], url: str) -> Dict[str, Any]:
        """构建下载选项"""
        from ...core.config import get_config

        # 基础选项
        timeout = get_config('downloader.timeout', 300)

        # 智能文件名策略：截断标题避免过长，使用临时ID确保下载成功
        # 先用临时ID下载，成功后重命名为合适的文件名
        outtmpl = str(self.output_dir / f'temp_{download_id}_%(title).80s.%(ext)s')
        restrict_filenames = True  # 限制文件名字符，避免特殊字符问题
        windows_filenames = True   # 兼容Windows文件名规则

        ydl_opts = {
            'outtmpl': outtmpl,
            'format': get_config('ytdlp.format', 'best[height<=720]'),
            'writesubtitles': False,
            'writeautomaticsub': False,
            'ignoreerrors': False,
            'no_warnings': True,
            'extractaudio': False,
            'audioformat': 'mp3',
            'audioquality': '192',
            # 添加重试和错误处理选项
            'extractor_retries': 3,
            'fragment_retries': 3,
            'retry_sleep_functions': {'http': lambda n: min(2 ** n, 30)},
            'socket_timeout': min(timeout, 300),  # 使用配置的超时时间，最大300秒
            # 添加User-Agent
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            },
            # 根据策略设置文件名清理选项
            'restrictfilenames': restrict_filenames,
            'windowsfilenames': windows_filenames,
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
                # 4K优先，然后1080p，确保获得最高质量
                ydl_opts['format'] = 'bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=2160]+bestaudio/bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best'
            elif quality == 'medium':
                # 720p质量，优先mp4格式
                ydl_opts['format'] = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]'
            elif quality == 'low':
                # 360p质量
                ydl_opts['format'] = 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/worst[height>=360]/worst'

            logger.info(f"🎬 设置视频质量: {quality} -> {ydl_opts['format']}")

        # 针对YouTube的特殊处理
        if 'youtube.com' in url or 'youtu.be' in url:
            ydl_opts.update({
                'merge_output_format': 'mp4',    # 确保输出mp4格式
                'writesubtitles': True,          # YouTube通常有字幕
                'writeautomaticsub': True,       # 自动生成的字幕
                'subtitleslangs': ['zh', 'zh-CN', 'en'],
            })
            logger.info("🎬 检测到YouTube链接，应用特殊配置")

        # 添加Cookies支持
        cookies_file = self._get_cookies_for_url(url)
        if cookies_file:
            ydl_opts['cookiefile'] = cookies_file
            logger.info(f"✅ 使用Cookies文件: {cookies_file}")
        else:
            # 如果是YouTube且没有cookies，给出警告
            if 'youtube.com' in url or 'youtu.be' in url:
                logger.warning(f"⚠️ YouTube下载未使用Cookies，可能遇到机器人检测")

        return ydl_opts

    def _get_android_vr_opts(self) -> Dict[str, Any]:
        """获取Android VR客户端配置"""
        return {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'no_color': True,
            'ignoreerrors': True,
            'socket_timeout': 30,
            'extractor_retries': 1,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android_vr']
                }
            },
            'http_headers': {
                'User-Agent': 'com.google.android.apps.youtube.vr.oculus/1.56.21 (Linux; U; Android 12L; eureka-user Build/SQ3A.220605.009.A1) gzip'
            }
        }

    def _get_ios_opts(self) -> Dict[str, Any]:
        """获取iOS客户端配置"""
        return {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'no_color': True,
            'ignoreerrors': True,
            'socket_timeout': 25,
            'extractor_retries': 1,
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios']
                }
            },
            'http_headers': {
                'User-Agent': 'com.google.ios.youtube/19.29.1 (iPhone16,2; U; CPU iOS 17_5_1 like Mac OS X;)'
            }
        }

    def _get_android_opts(self) -> Dict[str, Any]:
        """获取Android客户端配置"""
        return {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'no_color': True,
            'ignoreerrors': True,
            'socket_timeout': 25,
            'extractor_retries': 1,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android']
                }
            },
            'http_headers': {
                'User-Agent': 'com.google.android.youtube/19.29.37 (Linux; U; Android 14) gzip'
            }
        }

    def _get_cookies_opts(self, url: str) -> Optional[Dict[str, Any]]:
        """获取静态Cookies配置"""
        try:
            cookies_file = self._get_cookies_for_url(url)
            if not cookies_file:
                return None

            return {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'no_color': True,
                'ignoreerrors': True,
                'socket_timeout': 30,
                'extractor_retries': 1,
                'cookiefile': cookies_file,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
            }
        except Exception:
            return None

    def _get_default_opts(self, url: str) -> Dict[str, Any]:
        """获取默认配置"""
        opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'no_color': True,
            'ignoreerrors': True,
            'socket_timeout': 30,
            'extractor_retries': 2,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        }

        # 添加Cookies支持（如果有的话）
        cookies_file = self._get_cookies_for_url(url)
        if cookies_file:
            opts['cookiefile'] = cookies_file

        return opts

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
            # 优先搜索临时文件（新的下载方式）
            for file_path in self.output_dir.glob(f'temp_{download_id}_*'):
                if file_path.is_file():
                    logger.info(f"✅ 找到临时下载文件: {file_path.name}")
                    return str(file_path)

            # 兼容：搜索包含download_id的文件（旧的命名方式）
            for file_path in self.output_dir.glob(f'{download_id}_*'):
                if file_path.is_file():
                    logger.info(f"✅ 找到下载文件: {file_path.name}")
                    return str(file_path)

            # 兼容旧的命名方式：按标题搜索
            title = video_info.get('title', '')
            if title:
                # 尝试精确匹配
                for ext in ['mp4', 'mkv', 'webm', 'avi', 'mov', 'flv', 'm4a', 'mp3', 'wav']:
                    exact_file = self.output_dir / f"{title}.{ext}"
                    if exact_file.exists():
                        logger.info(f"✅ 找到下载文件（精确匹配）: {exact_file.name}")
                        return str(exact_file)

                # 如果精确匹配失败，尝试模糊匹配
                # 清理标题中的特殊字符进行搜索
                safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
                if safe_title:
                    for file_path in self.output_dir.glob(f'*{safe_title}*'):
                        if file_path.is_file():
                            logger.info(f"✅ 找到下载文件（模糊匹配）: {file_path.name}")
                            return str(file_path)

                # 最后尝试搜索包含部分标题的文件
                title_words = title.split()[:3]  # 取前3个词
                for word in title_words:
                    if len(word) > 3:  # 只搜索长度大于3的词
                        clean_word = "".join(c for c in word if c.isalnum())
                        if clean_word:
                            for file_path in self.output_dir.glob(f'*{clean_word}*'):
                                if file_path.is_file():
                                    logger.info(f"✅ 找到下载文件（词匹配）: {file_path.name}")
                                    return str(file_path)

            logger.warning(f"⚠️ 未找到下载文件: download_id={download_id}, title={title[:50]}...")
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
            # 停止自动清理
            try:
                from .cleanup import get_cleanup_manager
                cleanup_manager = get_cleanup_manager()
                cleanup_manager.stop()
            except Exception as e:
                logger.warning(f"⚠️ 停止自动清理失败: {e}")

            # 关闭线程池
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
