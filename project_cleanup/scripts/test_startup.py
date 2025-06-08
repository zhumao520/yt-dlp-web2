#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动测试脚本
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_database_init():
    """测试数据库初始化"""
    print("🧪 测试数据库初始化...")
    
    try:
        from app.core.database import get_database
        db = get_database()
        print("✅ 数据库初始化成功")
        
        # 测试数据库连接
        with db.get_connection() as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            print(f"✅ 数据库表: {tables}")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_app_startup():
    """测试应用启动"""
    print("\n🧪 测试应用启动...")
    
    try:
        from app.core.app import create_app
        from app.core.config import Config
        
        # 创建应用
        app = create_app()
        print("✅ 应用创建成功")
        
        # 测试配置
        config = Config()
        host = config.get('app.host', '0.0.0.0')
        port = config.get('app.port', 8080)
        print(f"✅ 配置加载成功: {host}:{port}")
        
        # 测试应用上下文
        with app.app_context():
            print("✅ 应用上下文正常")
            
            # 测试数据库在应用上下文中的访问
            from app.core.database import get_database
            db = get_database()
            print("✅ 应用上下文中数据库访问正常")
        
        return True
        
    except Exception as e:
        print(f"❌ 应用启动失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_routes():
    """测试路由注册"""
    print("\n🧪 测试路由注册...")
    
    try:
        from app.core.app import create_app
        app = create_app()
        
        # 获取所有路由
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append(f"{rule.methods} {rule.rule}")
        
        print(f"✅ 注册的路由数量: {len(routes)}")
        for route in routes[:10]:  # 显示前10个路由
            print(f"   {route}")
        
        if len(routes) > 10:
            print(f"   ... 还有 {len(routes) - 10} 个路由")
        
        return True
        
    except Exception as e:
        print(f"❌ 路由测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("🚀 开始启动测试...\n")
    
    tests = [
        test_database_init,
        test_app_startup,
        test_routes,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有启动测试通过！应用应该可以正常启动。")
        print("\n💡 启动命令:")
        print("   python app/main.py")
        return True
    else:
        print("⚠️ 部分测试失败，请检查上述错误信息")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
