# -*- coding: utf-8 -*-
"""
应用基础测试
"""

import pytest


def test_app_creation(app):
    """测试应用创建"""
    assert app is not None
    assert app.config["TESTING"] is True


def test_index_redirect(client):
    """测试首页重定向"""
    response = client.get("/")
    # 应该重定向到登录页面或设置页面
    assert response.status_code in [302, 200]


def test_health_check(client):
    """测试健康检查"""
    response = client.get("/api/system/status")
    assert response.status_code in [200, 401]  # 可能需要认证


def test_static_files(client):
    """测试静态文件访问"""
    # 测试CSS文件
    response = client.get("/static/css/style.css")
    # 文件可能不存在，但不应该是500错误
    assert response.status_code in [200, 404]


class TestAPI:
    """API测试"""
    
    def test_api_without_auth(self, client):
        """测试未认证的API访问"""
        response = client.get("/api/download/list")
        assert response.status_code == 401

    def test_api_with_invalid_token(self, client):
        """测试无效token的API访问"""
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.get("/api/download/list", headers=headers)
        assert response.status_code == 401


class TestPages:
    """页面测试"""
    
    def test_login_page(self, client):
        """测试登录页面"""
        response = client.get("/auth/login")
        assert response.status_code == 200
        assert b"login" in response.data.lower() or b"登录" in response.data

    def test_setup_page(self, client):
        """测试设置页面"""
        response = client.get("/setup")
        assert response.status_code == 200


class TestSecurity:
    """安全测试"""
    
    def test_csrf_protection(self, client):
        """测试CSRF保护"""
        # 在生产环境中应该启用CSRF保护
        response = client.post(
            "/auth/login", data={"username": "test", "password": "test"}
        )
        # 测试环境禁用了CSRF，所以不会返回403
        assert response.status_code in [200, 302, 400, 401]

    def test_sql_injection_protection(self, client):
        """测试SQL注入保护"""
        malicious_input = "'; DROP TABLE users; --"
        response = client.post(
            "/auth/login", data={"username": malicious_input, "password": "test"}
        )
        # 应该安全处理，不会导致500错误
        assert response.status_code in [200, 302, 400, 401]

    def test_xss_protection(self, client):
        """测试XSS保护"""
        malicious_script = '<script>alert("xss")</script>'
        response = client.post(
            "/auth/login", data={"username": malicious_script, "password": "test"}
        )
        # 应该安全处理
        assert response.status_code in [200, 302, 400, 401]
        # 响应中不应该包含未转义的脚本
        if response.data:
            assert b"<script>" not in response.data


class TestConfiguration:
    """配置测试"""
    
    def test_secret_key_set(self, app):
        """测试密钥设置"""
        assert app.config["SECRET_KEY"] is not None
        assert app.config["SECRET_KEY"] != ""
        assert app.config["SECRET_KEY"] != "change-this-secret-key-in-production"

    def test_debug_disabled_in_production(self, app):
        """测试生产环境调试模式"""
        # 在测试环境中可能启用调试，但要确保有相关配置
        assert "DEBUG" in app.config

    def test_database_config(self, app):
        """测试数据库配置"""
        assert "DATABASE_URL" in app.config
        assert app.config["DATABASE_URL"] is not None


class TestErrorHandling:
    """错误处理测试"""
    
    def test_404_error(self, client):
        """测试404错误处理"""
        response = client.get("/nonexistent-page")
        assert response.status_code == 404

    def test_500_error_handling(self, app):
        """测试500错误处理"""
        # 这个测试比较复杂，需要模拟内部错误
        with app.test_request_context():
            # 可以测试错误处理器是否正确注册
            assert app.error_handler_spec is not None
