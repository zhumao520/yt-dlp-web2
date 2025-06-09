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

            # 清理遗留的下载任务
            self._cleanup_orphaned_downloads()

            # 创建线程池
            self.executor = ThreadPoolExecutor(max_workers=max_concurrent)

            # 启动自动清理
            self._start_cleanup()

            logger.info(f"✅ 下载管理器初始化完成 - 最大并发: {max_concurrent}")

        except Exception as e:
            logger.error(f"❌ 下载管理器初始化失败: {e}")
            raise

    def _cleanup_orphaned_downloads(self):
        """清理遗留的下载任务（应用重启时调用）"""
        try:
            from ...core.database import get_database
            db = get_database()

            # 获取所有pending和downloading状态的任务
            orphaned_downloads = db.execute_query('''
                SELECT id, url FROM downloads
                WHERE status IN ('pending', 'downloading')
            ''')

            if orphaned_downloads:
                logger.info(f"🧹 发现 {len(orphaned_downloads)} 个遗留下载任务，正在清理...")

                # 将这些任务标记为失败
                for download in orphaned_downloads:
                    download_id = download['id']
                    url = download['url']

                    # 更新数据库状态
                    db.execute_update('''
                        UPDATE downloads
                        SET status = 'failed',
                            error_message = '应用重启，任务已取消',
                            completed_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (download_id,))

                    logger.debug(f"🧹 清理遗留任务: {download_id} - {url}")

                logger.info(f"✅ 已清理 {len(orphaned_downloads)} 个遗留下载任务")
            else:
                logger.info("✅ 没有发现遗留的下载任务")

        except Exception as e:
            logger.error(f"❌ 清理遗留下载任务失败: {e}")

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
                'options': options or {},
                'retry_count': 0,  # 重试计数
                'max_retries': self._get_max_retries(options)  # 最大重试次数
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
        """执行下载任务 - 带智能重试机制"""
        try:
            with self.lock:
                download_info = self.downloads.get(download_id)
                if not download_info:
                    return

                url = download_info['url']
                options = download_info['options']
                retry_count = download_info.get('retry_count', 0)
                max_retries = download_info.get('max_retries', 3)

            logger.info(f"🔄 开始执行下载: {download_id} - {url} (尝试 {retry_count + 1}/{max_retries + 1})")

            # 更新状态为下载中
            self._update_download_status(download_id, 'downloading', 0)

            # 获取视频信息
            video_info = self._extract_video_info(url)
            if not video_info:
                error_msg = '无法获取视频信息'
                self._handle_download_failure(download_id, url, error_msg, retry_count, max_retries)
                return

            # 更新标题
            title = video_info.get('title', 'Unknown')
            with self.lock:
                self.downloads[download_id]['title'] = title

            # 执行下载
            file_path = self._download_video(download_id, url, video_info, options)

            if file_path and Path(file_path).exists():
                # 下载成功 - 重置重试计数
                with self.lock:
                    self.downloads[download_id]['retry_count'] = 0
                logger.info(f"✅ 下载完成: {download_id} - {title}")
            else:
                # 下载失败
                error_msg = '下载文件不存在'
                self._handle_download_failure(download_id, url, error_msg, retry_count, max_retries)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ 下载执行失败 {download_id}: {error_msg}")

            with self.lock:
                download_info = self.downloads.get(download_id, {})
                retry_count = download_info.get('retry_count', 0)
                max_retries = download_info.get('max_retries', 3)
                url = download_info.get('url', '')

            self._handle_download_failure(download_id, url, error_msg, retry_count, max_retries)

    def _handle_download_failure(self, download_id: str, url: str, error_msg: str, retry_count: int, max_retries: int):
        """智能处理下载失败 - 决定是否重试或放弃"""
        try:
            # 检查是否应该重试
            should_retry = self._should_retry_download(error_msg, retry_count, max_retries)

            if should_retry:
                # 增加重试计数
                with self.lock:
                    if download_id in self.downloads:
                        self.downloads[download_id]['retry_count'] = retry_count + 1

                # 计算重试延迟（指数退避）
                retry_delay = self._calculate_retry_delay(retry_count)

                logger.info(f"🔄 下载失败，{retry_delay}秒后重试 ({retry_count + 1}/{max_retries}): {download_id}")
                logger.info(f"🔄 失败原因: {error_msg}")

                # 更新状态为等待重试
                self._update_download_status(download_id, 'retrying', error_message=f"重试中 ({retry_count + 1}/{max_retries}): {error_msg}")

                # 延迟后重新提交任务
                import threading
                def delayed_retry():
                    import time
                    time.sleep(retry_delay)
                    if download_id in self.downloads:  # 确保任务还存在
                        self.executor.submit(self._execute_download, download_id)

                retry_thread = threading.Thread(target=delayed_retry, daemon=True)
                retry_thread.start()

            else:
                # 放弃重试，标记为最终失败
                final_error = f"重试{retry_count}次后仍然失败: {error_msg}"
                self._update_download_status(download_id, 'failed', error_message=final_error)

                logger.error(f"❌ 下载最终失败，已放弃: {download_id}")
                logger.error(f"❌ 最终错误: {final_error}")

                # 发送下载失败事件
                from ...core.events import emit, Events
                emit(Events.DOWNLOAD_FAILED, {
                    'download_id': download_id,
                    'url': url,
                    'error': final_error
                })

        except Exception as e:
            logger.error(f"❌ 处理下载失败时出错: {e}")
            # 确保任务被标记为失败
            self._update_download_status(download_id, 'failed', error_message=f"处理失败: {str(e)}")

    def _should_retry_download(self, error_msg: str, retry_count: int, max_retries: int) -> bool:
        """判断是否应该重试下载"""
        # 如果已达到最大重试次数，不再重试
        if retry_count >= max_retries:
            return False

        error_lower = error_msg.lower()

        # 不应该重试的错误类型
        permanent_errors = [
            'private',  # 私有视频
            'not available',  # 视频不可用
            'removed',  # 视频已删除
            'copyright',  # 版权问题
            'age restricted',  # 年龄限制
            'geo blocked',  # 地理限制
            'invalid url',  # 无效URL
            'unsupported url',  # 不支持的URL
            'no video formats',  # 没有可用格式
            'video unavailable',  # 视频不可用
            'this video is not available',  # 视频不可用
            'sign in to confirm',  # 账号被封或需要验证
            'confirm you\'re not a bot',  # 机器人检测或账号问题
            'account has been terminated',  # 账号被终止
            'account suspended',  # 账号被暂停
        ]

        # 检查是否是永久性错误
        for permanent_error in permanent_errors:
            if permanent_error in error_lower:
                # 特殊处理账号相关错误
                if permanent_error in ['sign in to confirm', 'confirm you\'re not a bot']:
                    logger.warning(f"🚫 检测到账号问题: YouTube账号可能被封或需要重新登录")
                    logger.warning(f"💡 建议: 1) 清理现有cookies 2) 重新导出有效账号的cookies 3) 或使用无cookies模式")
                else:
                    logger.info(f"🚫 检测到永久性错误，不重试: {permanent_error}")
                return False

        # 可以重试的错误类型
        retryable_errors = [
            'timeout',  # 超时
            'connection',  # 连接问题
            'network',  # 网络问题
            'temporary',  # 临时错误
            'rate limit',  # 速率限制
            'server error',  # 服务器错误
            'http error 5',  # 5xx服务器错误
            'http error 429',  # 请求过多
            'http error 503',  # 服务不可用
            'http error 502',  # 网关错误
            'http error 504',  # 网关超时
        ]

        # 检查是否是可重试的错误
        for retryable_error in retryable_errors:
            if retryable_error in error_lower:
                logger.info(f"🔄 检测到可重试错误: {retryable_error}")
                return True

        # 默认情况：如果不确定，允许重试（但有次数限制）
        logger.info(f"🤔 未知错误类型，允许重试: {error_msg[:100]}")
        return True

    def _get_max_retries(self, options: Dict[str, Any] = None) -> int:
        """获取最大重试次数"""
        from ...core.config import get_config

        # 优先使用选项中的设置
        if options and 'max_retries' in options:
            return max(0, int(options['max_retries']))

        # 使用配置文件中的设置
        return max(0, get_config('downloader.max_retries', 3))

    def _calculate_retry_delay(self, retry_count: int) -> int:
        """计算重试延迟（指数退避）"""
        from ...core.config import get_config

        base = get_config('downloader.retry_delay_base', 2)
        max_delay = get_config('downloader.retry_delay_max', 60)

        # 指数退避：base^retry_count，但不超过最大延迟
        delay = min(base ** retry_count, max_delay)
        return max(1, int(delay))  # 至少1秒

    def _get_proxy_config(self) -> Optional[str]:
        """获取代理配置"""
        from ...core.config import get_config
        import os

        # 优先使用配置文件中的代理
        proxy = get_config('downloader.proxy', None)
        if proxy:
            return proxy

        # 其次使用环境变量
        proxy = os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY')
        if proxy:
            return proxy

        return None

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
        """应用智能文件名策略到已下载的文件（包括所有相关文件）"""
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
                # 提取download_id
                download_id = self._extract_download_id_from_filename(file_path.name)
                if download_id:
                    # 批量重命名所有相关文件
                    return self._apply_smart_filename_to_all_files(download_id, title, downloaded_file)
                else:
                    # 如果无法提取download_id，按单文件处理
                    return self._apply_smart_filename_single(file_path, title)
            else:
                # 非临时文件，按单文件处理
                return self._apply_smart_filename_single(file_path, title)

        except Exception as e:
            logger.error(f"❌ 应用智能文件名失败: {e}")
            return downloaded_file

    def _extract_download_id_from_filename(self, filename: str) -> Optional[str]:
        """从临时文件名中提取download_id"""
        try:
            # 文件名格式：temp_{download_id}_title.ext
            if filename.startswith('temp_'):
                parts = filename.split('_', 2)  # 分割为 ['temp', download_id, 'title.ext']
                if len(parts) >= 2:
                    return parts[1]  # 返回download_id部分
            return None
        except Exception:
            return None

    def _apply_smart_filename_single(self, file_path: Path, title: str) -> str:
        """对单个文件应用智能文件名"""
        try:
            ext = file_path.suffix[1:]  # 移除点号
            smart_filename = self._generate_smart_filename(title, ext)

            # 如果文件名没有变化，直接返回
            if smart_filename == file_path.name:
                return str(file_path)

            # 重命名文件
            new_file_path = file_path.parent / smart_filename

            try:
                file_path.rename(new_file_path)
                logger.info(f"📝 文件重命名成功: {file_path.name} -> {smart_filename}")
                return str(new_file_path)
            except Exception as e:
                logger.warning(f"⚠️ 文件重命名失败: {e}，保持原文件名")
                return str(file_path)

        except Exception as e:
            logger.error(f"❌ 单文件重命名失败: {e}")
            return str(file_path)

    def _apply_smart_filename_to_all_files(self, download_id: str, title: str, main_file: str) -> str:
        """批量重命名所有相关文件"""
        try:
            # 1. 查找所有相关文件
            all_files = self._find_all_related_files(download_id)
            if not all_files:
                logger.warning(f"⚠️ 未找到任何相关文件: {download_id}")
                return main_file

            logger.info(f"🔍 找到 {len(all_files)} 个相关文件需要重命名")

            # 2. 文件分类
            classified_files = self._classify_files(all_files)

            # 3. 确定主文件
            main_file_path = Path(main_file)

            # 4. 生成基础文件名（不含扩展名）
            base_filename = self._generate_base_filename(title)

            # 5. 重命名所有文件
            renamed_files = []
            main_renamed_file = main_file

            for file_path in all_files:
                try:
                    new_filename = self._generate_specific_filename(
                        base_filename, file_path, classified_files
                    )

                    new_file_path = file_path.parent / new_filename

                    # 如果新文件名与当前文件名相同，跳过重命名
                    if new_filename == file_path.name:
                        logger.info(f"📝 文件名无需更改: {file_path.name}")
                        renamed_files.append(str(file_path))
                        if file_path == main_file_path:
                            main_renamed_file = str(file_path)
                        continue

                    # 执行重命名
                    file_path.rename(new_file_path)
                    renamed_files.append(str(new_file_path))

                    # 记录主文件的新路径
                    if file_path == main_file_path:
                        main_renamed_file = str(new_file_path)

                    logger.info(f"📝 文件重命名成功: {file_path.name} -> {new_filename}")

                except Exception as e:
                    logger.warning(f"⚠️ 文件重命名失败: {file_path.name}, 错误: {e}")
                    # 重命名失败时，至少记录原文件
                    renamed_files.append(str(file_path))
                    if file_path == main_file_path:
                        main_renamed_file = str(file_path)

            logger.info(f"✅ 批量重命名完成，共处理 {len(all_files)} 个文件，成功 {len(renamed_files)} 个")
            return main_renamed_file

        except Exception as e:
            logger.error(f"❌ 批量重命名失败: {e}")
            return main_file

    def _find_all_related_files(self, download_id: str) -> List[Path]:
        """查找所有相关的下载文件（视频+字幕+其他）"""
        try:
            related_files = []

            # 查找所有以 temp_{download_id}_ 开头的文件
            pattern = f'temp_{download_id}_*'
            for file_path in self.output_dir.glob(pattern):
                if file_path.is_file():
                    related_files.append(file_path)

            logger.info(f"🔍 找到 {len(related_files)} 个相关文件: {[f.name for f in related_files]}")
            return related_files

        except Exception as e:
            logger.error(f"❌ 查找相关文件失败: {e}")
            return []

    def _classify_files(self, files: List[Path]) -> Dict[str, List[Path]]:
        """将文件按类型分类"""
        classification = {
            'video': [],      # 视频文件 (.mp4, .mkv, .webm 等)
            'audio': [],      # 音频文件 (.mp3, .m4a, .wav 等)
            'subtitle': [],   # 字幕文件 (.vtt, .srt, .ass 等)
            'other': []       # 其他文件
        }

        video_exts = {'.mp4', '.mkv', '.webm', '.avi', '.mov', '.flv', '.m4v'}
        audio_exts = {'.mp3', '.m4a', '.wav', '.aac', '.ogg', '.flac'}
        subtitle_exts = {'.vtt', '.srt', '.ass', '.ssa', '.sub', '.sbv', '.ttml'}

        for file_path in files:
            ext = file_path.suffix.lower()

            # 首先检查扩展名
            if ext in video_exts:
                classification['video'].append(file_path)
            elif ext in audio_exts:
                classification['audio'].append(file_path)
            elif ext in subtitle_exts:
                classification['subtitle'].append(file_path)
            else:
                classification['other'].append(file_path)

        return classification

    def _generate_specific_filename(self, base_filename: str, file_path: Path,
                                   classified_files: Dict[str, List[Path]]) -> str:
        """为特定文件生成具体的文件名"""
        try:
            # 获取文件扩展名
            ext = file_path.suffix.lower()

            # 处理字幕文件的特殊情况
            if file_path in classified_files['subtitle']:
                # 从原始文件名中提取语言代码
                lang_code = self._extract_language_code_from_filename(file_path.name)
                if lang_code:
                    return f"{base_filename}.{lang_code}{ext}"
                else:
                    # 如果没有语言代码，但有多个字幕文件，添加序号
                    if len(classified_files['subtitle']) > 1:
                        index = classified_files['subtitle'].index(file_path)
                        return f"{base_filename} ({index + 1}){ext}"
                    else:
                        return f"{base_filename}{ext}"

            # 处理多个同类型文件的情况
            elif file_path in classified_files['video'] and len(classified_files['video']) > 1:
                # 如果有多个视频文件，添加序号
                index = classified_files['video'].index(file_path)
                if index == 0:
                    return f"{base_filename}{ext}"  # 主文件不加序号
                else:
                    return f"{base_filename} ({index + 1}){ext}"

            elif file_path in classified_files['audio'] and len(classified_files['audio']) > 1:
                # 如果有多个音频文件，添加序号
                index = classified_files['audio'].index(file_path)
                if index == 0:
                    return f"{base_filename}{ext}"
                else:
                    return f"{base_filename} ({index + 1}){ext}"

            else:
                # 默认情况：直接使用基础文件名 + 扩展名
                return f"{base_filename}{ext}"

        except Exception as e:
            logger.error(f"❌ 生成文件名失败: {e}")
            return file_path.name  # 出错时返回原文件名

    def _extract_language_code_from_filename(self, filename: str) -> Optional[str]:
        """从文件名中提取语言代码"""
        try:
            # 文件名格式：temp_id_title.lang.ext 或 temp_id_title.ext
            # 移除扩展名
            name_without_ext = filename.rsplit('.', 1)[0]

            # 检查是否有语言代码
            if '.' in name_without_ext:
                parts = name_without_ext.split('.')
                potential_lang = parts[-1]

                # 常见的语言代码
                valid_lang_codes = ['zh', 'en', 'zh-CN', 'zh-TW', 'en-US', 'ja', 'ko', 'fr', 'de', 'es', 'it', 'pt', 'ru']

                if potential_lang in valid_lang_codes:
                    return potential_lang

            return None

        except Exception:
            return None

    def _generate_base_filename(self, title: str) -> str:
        """生成基础文件名（不含扩展名）"""
        import re
        from ...core.config import get_config

        try:
            # Windows文件名限制为255字符，但考虑到路径长度，我们设置更保守的限制
            max_length = min(get_config('downloader.max_filename_length', 150), 100)

            # 清理危险字符（保持最小清理，保留原有逻辑）
            dangerous_chars = r'[<>:"/\\|?*\x00-\x1f]'
            base_filename = re.sub(dangerous_chars, '', title)
            base_filename = re.sub(r'\s+', ' ', base_filename).strip()

            # 处理长度限制（为扩展名和可能的后缀预留空间）
            max_base_length = max_length - 30  # 预留30个字符给扩展名、语言代码和后缀

            if len(base_filename) > max_base_length:
                if any('\u4e00' <= c <= '\u9fff' for c in base_filename):
                    # 中文，直接截断
                    base_filename = base_filename[:max_base_length].rstrip(' -_')
                else:
                    # 英文，在词边界截断
                    words = base_filename[:max_base_length].split()
                    if len(words) > 1:
                        base_filename = ' '.join(words[:-1])
                    else:
                        base_filename = base_filename[:max_base_length].rstrip(' -_')

                logger.info(f"📏 文件名过长，已截断: {title[:50]}... -> {base_filename}")

            return base_filename or 'video'

        except Exception as e:
            logger.error(f"❌ 生成基础文件名失败: {e}")
            return 'video'

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
            # 🚨 关键修复：防止播放列表处理
            'noplaylist': True,        # 只处理单个视频，忽略播放列表
            'extract_flat': True,      # 防止播放列表展开
            # 添加重试和错误处理选项
            'extractor_retries': 3,
            'fragment_retries': 3,
            'retry_sleep_functions': {'http': lambda n: min(2 ** n, 30)},
            'socket_timeout': min(timeout, 300),  # 使用配置的超时时间，最大300秒
            # 添加User-Agent
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            },
            # 代理支持（如果配置了代理）
            'proxy': self._get_proxy_config(),
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
            'extract_flat': True,   # 防止播放列表展开
            'noplaylist': True,     # 只处理单个视频，忽略播放列表
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
            'extract_flat': True,   # 防止播放列表展开
            'noplaylist': True,     # 只处理单个视频，忽略播放列表
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
            'extract_flat': True,   # 防止播放列表展开
            'noplaylist': True,     # 只处理单个视频，忽略播放列表
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
                'extract_flat': True,   # 防止播放列表展开
            'noplaylist': True,     # 只处理单个视频，忽略播放列表
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
            'extract_flat': True,   # 防止播放列表展开
            'noplaylist': True,     # 只处理单个视频，忽略播放列表
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

            # 发送进度事件（但不为重试状态发送事件，避免干扰）
            if progress is not None and status != 'retrying':
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
