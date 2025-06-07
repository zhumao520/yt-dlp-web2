# -*- coding: utf-8 -*-
"""
数据库管理 - 轻量化数据库操作
"""

import logging
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class Database:
    """轻量化数据库管理器"""
    
    def __init__(self, db_path: str = 'app.db'):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表"""
        try:
            with self.get_connection() as conn:
                # 用户表
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        is_admin BOOLEAN DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP
                    )
                ''')
                
                # Telegram配置表
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS telegram_config (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        bot_token TEXT,
                        chat_id TEXT,
                        api_id INTEGER,
                        api_hash TEXT,
                        enabled BOOLEAN DEFAULT 0,
                        push_mode TEXT DEFAULT 'file',
                        auto_download BOOLEAN DEFAULT 1,
                        file_size_limit INTEGER DEFAULT 50,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 下载记录表
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS downloads (
                        id TEXT PRIMARY KEY,
                        url TEXT NOT NULL,
                        title TEXT,
                        status TEXT DEFAULT 'pending',
                        progress INTEGER DEFAULT 0,
                        file_path TEXT,
                        file_size INTEGER,
                        error_message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP
                    )
                ''')
                
                # 系统设置表
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()

                # 创建默认用户
                self._create_default_user(conn)

                # 确保用户创建后提交事务
                conn.commit()

                logger.info("✅ 数据库初始化完成")
                
        except Exception as e:
            logger.error(f"❌ 数据库初始化失败: {e}")
            raise
    
    def _create_default_user(self, conn):
        """创建默认管理员用户"""
        try:
            # 检查是否已有用户
            cursor = conn.execute('SELECT COUNT(*) FROM users')
            user_count = cursor.fetchone()[0]

            logger.info(f"📊 当前用户数量: {user_count}")

            if user_count == 0:
                import hashlib
                import os

                # 优先从环境变量读取，然后使用默认值
                username = os.getenv('ADMIN_USERNAME', 'admin')
                password = os.getenv('ADMIN_PASSWORD', 'admin123')

                # 记录凭据来源
                username_source = "环境变量" if os.getenv('ADMIN_USERNAME') else "默认值"
                password_source = "环境变量" if os.getenv('ADMIN_PASSWORD') else "默认值"

                logger.info(f"🔧 准备创建用户: {username} (来源: {username_source})")
                logger.info(f"🔑 使用密码: {'***' if password else '未设置'} (来源: {password_source})")

                password_hash = hashlib.sha256(password.encode()).hexdigest()
                logger.info(f"🔐 密码哈希: {password_hash[:20]}...")

                # 插入用户
                cursor = conn.execute('''
                    INSERT INTO users (username, password_hash, is_admin, created_at)
                    VALUES (?, ?, 1, CURRENT_TIMESTAMP)
                ''', (username, password_hash))

                # 验证插入结果
                if cursor.rowcount > 0:
                    logger.info(f"✅ 成功插入用户记录")

                    # 再次检查用户数量
                    cursor = conn.execute('SELECT COUNT(*) FROM users')
                    new_count = cursor.fetchone()[0]
                    logger.info(f"📊 插入后用户数量: {new_count}")

                    # 验证用户数据
                    cursor = conn.execute('SELECT username, is_admin FROM users WHERE username = ?', (username,))
                    user_data = cursor.fetchone()
                    if user_data:
                        logger.info(f"✅ 用户验证成功: {user_data[0]} (管理员: {user_data[1]})")
                    else:
                        logger.error("❌ 用户验证失败：找不到刚创建的用户")
                else:
                    logger.error("❌ 用户插入失败：rowcount = 0")

                logger.info(f"✅ 创建默认管理员用户完成: {username}")
            else:
                logger.info(f"ℹ️ 已存在 {user_count} 个用户，跳过默认用户创建")

        except Exception as e:
            logger.error(f"❌ 创建默认用户失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 使结果可以按列名访问
        try:
            yield conn
        finally:
            conn.close()
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """执行查询并返回结果"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ 查询执行失败: {e}")
            return []
    
    def execute_update(self, query: str, params: tuple = ()) -> bool:
        """执行更新操作"""
        try:
            with self.get_connection() as conn:
                conn.execute(query, params)
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"❌ 更新执行失败: {e}")
            return False
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """根据用户名获取用户"""
        results = self.execute_query(
            'SELECT * FROM users WHERE username = ?',
            (username,)
        )
        return results[0] if results else None
    
    def verify_user_password(self, username: str, password: str) -> bool:
        """验证用户密码"""
        import hashlib
        user = self.get_user_by_username(username)
        if not user:
            return False
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        return user['password_hash'] == password_hash
    
    def update_user_login_time(self, username: str):
        """更新用户最后登录时间"""
        self.execute_update(
            'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = ?',
            (username,)
        )
    
    def get_telegram_config(self) -> Optional[Dict[str, Any]]:
        """获取Telegram配置"""
        results = self.execute_query('SELECT * FROM telegram_config LIMIT 1')
        return results[0] if results else None
    
    def save_telegram_config(self, config: Dict[str, Any]) -> bool:
        """保存Telegram配置"""
        existing = self.get_telegram_config()
        
        if existing:
            # 更新现有配置
            return self.execute_update('''
                UPDATE telegram_config SET
                    bot_token = ?, chat_id = ?, api_id = ?, api_hash = ?,
                    enabled = ?, push_mode = ?, auto_download = ?,
                    file_size_limit = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                config.get('bot_token', ''),
                config.get('chat_id', ''),
                config.get('api_id'),
                config.get('api_hash', ''),
                config.get('enabled', False),
                config.get('push_mode', 'file'),
                config.get('auto_download', True),
                config.get('file_size_limit', 50),
                existing['id']
            ))
        else:
            # 创建新配置
            return self.execute_update('''
                INSERT INTO telegram_config 
                (bot_token, chat_id, api_id, api_hash, enabled, push_mode, auto_download, file_size_limit)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                config.get('bot_token', ''),
                config.get('chat_id', ''),
                config.get('api_id'),
                config.get('api_hash', ''),
                config.get('enabled', False),
                config.get('push_mode', 'file'),
                config.get('auto_download', True),
                config.get('file_size_limit', 50)
            ))
    
    def save_download_record(self, download_id: str, url: str, title: str = None) -> bool:
        """保存下载记录"""
        return self.execute_update('''
            INSERT OR REPLACE INTO downloads (id, url, title, status)
            VALUES (?, ?, ?, 'pending')
        ''', (download_id, url, title))
    
    def update_download_status(self, download_id: str, status: str, 
                             progress: int = None, file_path: str = None,
                             file_size: int = None, error_message: str = None) -> bool:
        """更新下载状态"""
        if status == 'completed':
            return self.execute_update('''
                UPDATE downloads SET 
                    status = ?, progress = ?, file_path = ?, file_size = ?,
                    completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, progress or 100, file_path, file_size, download_id))
        else:
            return self.execute_update('''
                UPDATE downloads SET 
                    status = ?, progress = ?, error_message = ?
                WHERE id = ?
            ''', (status, progress or 0, error_message, download_id))
    
    def get_download_records(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取下载记录"""
        return self.execute_query('''
            SELECT * FROM downloads 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (limit,))
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """获取系统设置"""
        results = self.execute_query('SELECT value FROM settings WHERE key = ?', (key,))
        if results:
            return results[0]['value']
        return default
    
    def set_setting(self, key: str, value: str) -> bool:
        """设置系统设置"""
        return self.execute_update('''
            INSERT OR REPLACE INTO settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (key, value))

    def ensure_admin_user_exists(self) -> bool:
        """确保管理员用户存在（智能创建/更新）"""
        try:
            import hashlib
            import os

            # 获取环境变量中的用户名和密码
            env_username = os.getenv('ADMIN_USERNAME', 'admin')
            env_password = os.getenv('ADMIN_PASSWORD', 'admin123')

            # 记录使用的凭据来源
            username_source = "环境变量" if os.getenv('ADMIN_USERNAME') else "默认值"
            password_source = "环境变量" if os.getenv('ADMIN_PASSWORD') else "默认值"

            logger.info(f"🔧 管理员用户名: {env_username} (来源: {username_source})")
            logger.info(f"🔑 管理员密码: {'***' if env_password else '未设置'} (来源: {password_source})")

            env_password_hash = hashlib.sha256(env_password.encode()).hexdigest()

            with self.get_connection() as conn:
                # 检查是否存在管理员用户
                cursor = conn.execute('SELECT * FROM users WHERE username = ?', (env_username,))
                existing_user = cursor.fetchone()

                if existing_user:
                    # 用户存在，检查密码是否需要更新
                    if existing_user['password_hash'] != env_password_hash:
                        logger.info(f"🔄 更新管理员用户密码: {env_username}")
                        conn.execute('''
                            UPDATE users
                            SET password_hash = ?, last_login = NULL
                            WHERE username = ?
                        ''', (env_password_hash, env_username))
                        conn.commit()
                        logger.info("✅ 管理员密码更新成功")
                    else:
                        logger.info(f"ℹ️ 管理员用户已存在且密码正确: {env_username}")
                else:
                    # 用户不存在，创建新用户
                    logger.info(f"🔧 创建管理员用户: {env_username}")
                    conn.execute('''
                        INSERT INTO users (username, password_hash, is_admin, created_at)
                        VALUES (?, ?, 1, CURRENT_TIMESTAMP)
                    ''', (env_username, env_password_hash))
                    conn.commit()
                    logger.info("✅ 管理员用户创建成功")

                # 确保至少有一个管理员用户
                cursor = conn.execute('SELECT COUNT(*) FROM users WHERE is_admin = 1')
                admin_count = cursor.fetchone()[0]

                if admin_count == 0:
                    logger.warning("⚠️ 没有管理员用户，强制创建...")
                    self._create_default_user(conn)
                    conn.commit()

                logger.info(f"📊 当前管理员用户数量: {admin_count}")
                return True

        except Exception as e:
            logger.error(f"❌ 确保管理员用户存在失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return False


# 全局数据库实例
_db_instance = None

def get_database() -> Database:
    """获取数据库实例"""
    global _db_instance
    if _db_instance is None:
        from .config import get_config
        db_path = get_config('database.url', 'sqlite:///app.db')
        # 提取SQLite文件路径
        if db_path.startswith('sqlite:///'):
            db_path = db_path[10:]  # 移除 'sqlite:///' 前缀
        _db_instance = Database(db_path)
    return _db_instance
