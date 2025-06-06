# -*- coding: utf-8 -*-
"""
测试配置
"""

import pytest
import tempfile
import os
from pathlib import Path


@pytest.fixture
def app():
    """创建测试应用"""
    from app.core.app import create_app
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    
    # 测试配置
    test_config = {
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key',
        'DATABASE_URL': f'sqlite:///{temp_dir}/test.db',
        'DOWNLOAD_DIR': f'{temp_dir}/downloads',
        'WTF_CSRF_ENABLED': False
    }
    
    app = create_app(test_config)
    
    with app.app_context():
        # 创建必要目录
        os.makedirs(test_config['DOWNLOAD_DIR'], exist_ok=True)
        
        # 初始化数据库
        from app.core.database import get_database
        db = get_database()
        
        yield app
    
    # 清理临时文件
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """创建CLI测试运行器"""
    return app.test_cli_runner()


@pytest.fixture
def auth_headers():
    """认证头部"""
    return {
        'Authorization': 'Bearer test-token',
        'Content-Type': 'application/json'
    }


@pytest.fixture
def sample_video_url():
    """示例视频URL"""
    return 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'


@pytest.fixture
def sample_file_data():
    """示例文件数据"""
    return {
        'name': 'test_video.mp4',
        'size': 1024 * 1024,  # 1MB
        'modified': 1640995200  # 2022-01-01
    }
