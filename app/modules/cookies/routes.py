# -*- coding: utf-8 -*-
"""
Cookies管理路由
"""

import logging
from flask import Blueprint, request, jsonify, send_file
from ...core.auth import auth_required
from .manager import get_cookies_manager

logger = logging.getLogger(__name__)

cookies_bp = Blueprint('cookies', __name__)


@cookies_bp.route('/api/upload', methods=['POST'])
@auth_required
def upload_cookies():
    """上传Cookies"""
    try:
        # 支持JSON和FormData两种格式
        if request.content_type and 'application/json' in request.content_type:
            # JSON格式
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': '无效的请求数据'}), 400

            website = data.get('website', '').strip()
            cookies_data = data.get('cookies', '').strip()
            format_type = data.get('format', 'auto')
        else:
            # FormData格式
            website = request.form.get('website', '').strip()
            format_type = request.form.get('format', 'auto')

            # 检查是否有文件上传
            if 'file' in request.files:
                file = request.files['file']
                if file.filename:
                    cookies_data = file.read().decode('utf-8')
                else:
                    return jsonify({'success': False, 'error': '请选择文件'}), 400
            else:
                # 文本内容
                cookies_data = request.form.get('content', '').strip()

        if not website:
            return jsonify({'success': False, 'error': '网站名称不能为空'}), 400

        if not cookies_data:
            return jsonify({'success': False, 'error': 'Cookies数据不能为空'}), 400

        # 保存Cookies
        cookies_manager = get_cookies_manager()
        result = cookies_manager.save_cookies(website, cookies_data, format_type)

        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"❌ 上传Cookies失败: {e}")
        return jsonify({'success': False, 'error': '服务器内部错误'}), 500


@cookies_bp.route('/api/list', methods=['GET'])
@auth_required
def list_cookies():
    """获取Cookies列表"""
    try:
        cookies_manager = get_cookies_manager()
        result = cookies_manager.list_cookies()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ 获取Cookies列表失败: {e}")
        return jsonify({'success': False, 'error': '服务器内部错误'}), 500


@cookies_bp.route('/api/get/<website>', methods=['GET'])
@auth_required
def get_cookies(website):
    """获取指定网站的Cookies"""
    try:
        cookies_manager = get_cookies_manager()
        result = cookies_manager.get_cookies(website)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 404
            
    except Exception as e:
        logger.error(f"❌ 获取Cookies失败: {e}")
        return jsonify({'success': False, 'error': '服务器内部错误'}), 500


@cookies_bp.route('/api/delete/<website>', methods=['DELETE'])
@auth_required
def delete_cookies(website):
    """删除指定网站的Cookies"""
    try:
        cookies_manager = get_cookies_manager()
        result = cookies_manager.delete_cookies(website)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 404
            
    except Exception as e:
        logger.error(f"❌ 删除Cookies失败: {e}")
        return jsonify({'success': False, 'error': '服务器内部错误'}), 500


@cookies_bp.route('/api/export/<website>', methods=['GET'])
@auth_required
def export_cookies(website):
    """导出Cookies"""
    try:
        format_type = request.args.get('format', 'netscape')
        
        cookies_manager = get_cookies_manager()
        result = cookies_manager.export_cookies(website, format_type)
        
        if result['success']:
            # 创建临时文件并返回
            import tempfile
            import os
            
            temp_file = tempfile.NamedTemporaryFile(
                mode='w', 
                suffix=f".{'txt' if format_type == 'netscape' else 'json'}", 
                delete=False,
                encoding='utf-8'
            )
            
            temp_file.write(result['content'])
            temp_file.close()
            
            def remove_file(response):
                try:
                    os.unlink(temp_file.name)
                except:
                    pass
                return response
            
            return send_file(
                temp_file.name,
                as_attachment=True,
                download_name=result['filename'],
                mimetype='text/plain' if format_type == 'netscape' else 'application/json'
            )
        else:
            return jsonify(result), 404
            
    except Exception as e:
        logger.error(f"❌ 导出Cookies失败: {e}")
        return jsonify({'success': False, 'error': '服务器内部错误'}), 500


@cookies_bp.route('/api/validate', methods=['POST'])
@auth_required
def validate_cookies():
    """验证Cookies格式"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400
        
        cookies_data = data.get('cookies', '').strip()
        if not cookies_data:
            return jsonify({'success': False, 'error': 'Cookies数据不能为空'}), 400
        
        cookies_manager = get_cookies_manager()
        
        # 检测格式
        format_type = cookies_manager._detect_format(cookies_data)
        
        # 尝试解析
        parsed_cookies = cookies_manager._parse_cookies(cookies_data, format_type)
        
        if parsed_cookies:
            return jsonify({
                'success': True,
                'format': format_type,
                'count': len(parsed_cookies),
                'preview': parsed_cookies[:3] if len(parsed_cookies) > 3 else parsed_cookies
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Cookies格式无效或无法解析'
            }), 400
            
    except Exception as e:
        logger.error(f"❌ 验证Cookies失败: {e}")
        return jsonify({'success': False, 'error': '服务器内部错误'}), 500


@cookies_bp.route('/api/test/<website>', methods=['POST'])
@auth_required
def test_cookies(website):
    """测试Cookies有效性"""
    try:
        cookies_manager = get_cookies_manager()
        cookies_data = cookies_manager.get_cookies(website)
        
        if not cookies_data['success']:
            return jsonify(cookies_data), 404
        
        # 这里可以添加实际的Cookies测试逻辑
        # 比如发送HTTP请求验证Cookies是否有效
        
        # 目前返回基本信息
        cookies = cookies_data['data']['cookies']
        
        # 检查过期时间
        expired_count = 0
        valid_count = 0
        current_time = int(__import__('time').time())
        
        for cookie in cookies:
            expiration = cookie.get('expiration', 0)
            if expiration > 0 and expiration < current_time:
                expired_count += 1
            else:
                valid_count += 1
        
        return jsonify({
            'success': True,
            'website': website,
            'total_cookies': len(cookies),
            'valid_cookies': valid_count,
            'expired_cookies': expired_count,
            'test_time': __import__('datetime').datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ 测试Cookies失败: {e}")
        return jsonify({'success': False, 'error': '服务器内部错误'}), 500


@cookies_bp.route('/api/batch-delete', methods=['POST'])
@auth_required
def batch_delete_cookies():
    """批量删除Cookies"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400
        
        websites = data.get('websites', [])
        if not websites:
            return jsonify({'success': False, 'error': '没有指定要删除的网站'}), 400
        
        cookies_manager = get_cookies_manager()
        results = []
        success_count = 0
        
        for website in websites:
            result = cookies_manager.delete_cookies(website)
            results.append({
                'website': website,
                'success': result['success'],
                'message': result.get('message', result.get('error', ''))
            })
            if result['success']:
                success_count += 1
        
        return jsonify({
            'success': True,
            'total': len(websites),
            'success_count': success_count,
            'failed_count': len(websites) - success_count,
            'results': results
        })
        
    except Exception as e:
        logger.error(f"❌ 批量删除Cookies失败: {e}")
        return jsonify({'success': False, 'error': '服务器内部错误'}), 500
