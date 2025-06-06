# -*- coding: utf-8 -*-
"""
文件管理路由 - 文件下载和管理
"""

import os
import logging
from pathlib import Path
from flask import Blueprint, send_file, jsonify, abort
from ...core.auth import auth_required

logger = logging.getLogger(__name__)

files_bp = Blueprint('files', __name__)


@files_bp.route('/download/<filename>')
@auth_required
def download_file(filename):
    """下载文件"""
    try:
        from ...core.config import get_config
        from flask import request

        # 获取下载目录
        download_dir = Path(get_config('downloader.output_dir', '/app/downloads'))
        file_path = download_dir / filename

        # 安全检查：确保文件在下载目录内
        if not str(file_path.resolve()).startswith(str(download_dir.resolve())):
            logger.warning(f"尝试访问下载目录外的文件: {filename}")
            abort(403)

        # 检查文件是否存在
        if not file_path.exists():
            logger.warning(f"文件不存在: {filename}")
            abort(404)

        # 检查是否为在线播放请求
        is_streaming = request.args.get('stream') == '1'

        if is_streaming and _is_video_file(filename):
            # 流媒体播放
            logger.info(f"流媒体播放: {filename}")
            return send_file(file_path, as_attachment=False, mimetype=_get_video_mimetype(filename))
        else:
            # 普通下载
            logger.info(f"下载文件: {filename}")
            return send_file(file_path, as_attachment=True)

    except Exception as e:
        logger.error(f"文件访问失败: {e}")
        abort(500)


@files_bp.route('/stream/<filename>')
@auth_required
def stream_file(filename):
    """流媒体播放文件"""
    try:
        from ...core.config import get_config

        # 获取下载目录
        download_dir = Path(get_config('downloader.output_dir', '/app/downloads'))
        file_path = download_dir / filename

        # 安全检查
        if not str(file_path.resolve()).startswith(str(download_dir.resolve())):
            abort(403)

        if not file_path.exists():
            abort(404)

        # 只允许视频文件流媒体播放
        if not _is_video_file(filename):
            abort(400)

        logger.info(f"流媒体播放: {filename}")
        return send_file(file_path, as_attachment=False, mimetype=_get_video_mimetype(filename))

    except Exception as e:
        logger.error(f"流媒体播放失败: {e}")
        abort(500)


@files_bp.route('/list')
@auth_required
def list_files():
    """获取文件列表"""
    try:
        from ...core.config import get_config
        
        download_dir = Path(get_config('downloader.output_dir', '/app/downloads'))
        
        if not download_dir.exists():
            return jsonify({'files': []})
        
        files = []
        for file_path in download_dir.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    'name': file_path.name,
                    'size': stat.st_size,
                    'modified': stat.st_mtime,
                    'download_url': f'/files/download/{file_path.name}'
                })
        
        # 按修改时间倒序排列
        files.sort(key=lambda x: x['modified'], reverse=True)
        
        return jsonify({'files': files})
        
    except Exception as e:
        logger.error(f"获取文件列表失败: {e}")
        return jsonify({'error': '获取文件列表失败'}), 500


@files_bp.route('/delete/<filename>', methods=['DELETE'])
@auth_required
def delete_file(filename):
    """删除文件"""
    try:
        from ...core.config import get_config
        
        download_dir = Path(get_config('downloader.output_dir', '/app/downloads'))
        file_path = download_dir / filename
        
        # 安全检查
        if not str(file_path.resolve()).startswith(str(download_dir.resolve())):
            abort(403)
        
        if not file_path.exists():
            abort(404)
        
        file_path.unlink()
        logger.info(f"删除文件: {filename}")
        
        return jsonify({'success': True, 'message': '文件删除成功'})
        
    except Exception as e:
        logger.error(f"删除文件失败: {e}")
        return jsonify({'error': '删除文件失败'}), 500


def _is_video_file(filename):
    """检查是否为视频文件"""
    video_extensions = {
        '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv',
        '.webm', '.m4v', '.3gp', '.ogv', '.ts', '.m2ts'
    }
    return Path(filename).suffix.lower() in video_extensions


def _get_video_mimetype(filename):
    """获取视频文件的MIME类型"""
    ext = Path(filename).suffix.lower()
    mime_types = {
        '.mp4': 'video/mp4',
        '.webm': 'video/webm',
        '.ogv': 'video/ogg',
        '.avi': 'video/x-msvideo',
        '.mov': 'video/quicktime',
        '.mkv': 'video/x-matroska',
        '.flv': 'video/x-flv',
        '.wmv': 'video/x-ms-wmv',
        '.m4v': 'video/mp4',
        '.3gp': 'video/3gpp',
        '.ts': 'video/mp2t',
        '.m2ts': 'video/mp2t'
    }
    return mime_types.get(ext, 'video/mp4')
