# YT-DLP Web V2 - 轻量化可扩展架构

## 🚀 项目概述

全新设计的 yt-dlp Web 界面，采用模块化架构，支持高度扩展和轻量化部署。

### ✨ 核心特性
- **🏗️ 轻量化架构** - 最小化代码复杂度，最大化功能
- **🔧 模块化设计** - 功能独立，松耦合，易扩展
- **⚡ 事件驱动** - 统一事件总线，组件间通信
- **🔐 统一认证** - JWT认证替代Flask-Login，支持Web+API
- **📱 现代界面** - Tailwind CSS + Alpine.js，黑白双主题
- **🤖 智能部署** - 自动环境检测，GitHub构建/本地运行双模式
- **🔮 扩展预留** - AI分析、云存储、多用户等功能接口

## 🏗️ 架构设计

### 技术栈
- **后端**: Flask 3.1+ + PyJWT 2.10+ + SQLite
- **前端**: Tailwind CSS + Alpine.js + Feather Icons
- **集成**: Pyrogram + TgCrypto (Telegram)
- **部署**: Docker + Docker Compose

### 目录结构
```
yt-dlp-web-v2/
├── app/                    # 应用核心
│   ├── main.py            # 应用入口
│   ├── core/              # 核心模块
│   │   ├── app.py         # Flask应用工厂
│   │   ├── config.py      # 统一配置管理
│   │   ├── events.py      # 事件总线
│   │   ├── database.py    # 轻量化数据库
│   │   └── auth.py        # JWT认证系统
│   ├── modules/           # 功能模块
│   │   ├── auth/          # 认证模块
│   │   ├── downloader/    # 下载管理
│   │   └── telegram/      # Telegram集成
│   ├── api/               # RESTful API
│   ├── web/               # Web界面
│   │   └── templates/     # 页面模板
│   └── scripts/           # 自动化脚本
├── requirements.txt       # 轻量化依赖
├── config.example.yml     # 配置示例
├── Dockerfile            # Docker镜像
├── docker-compose.yml    # 容器编排
└── start.sh             # 启动脚本
```

## 🔧 快速开始

### 方式一：本地运行
```bash
# 1. 克隆项目
git clone <repo-url>
cd yt-dlp-web-v2

# 2. 自动启动（推荐）
./start.sh

# 或手动启动
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app/main.py
```

### 方式二：Docker部署
```bash
# 1. 使用docker-compose（推荐）
docker-compose up -d

# 2. 或手动构建
docker build -t yt-dlp-web-v2 .
docker run -d -p 8080:8080 -v ./downloads:/app/downloads yt-dlp-web-v2
```

### 首次访问
1. 打开浏览器访问 `http://localhost:8080`
2. 首次访问会进入初始化向导
3. 按步骤完成：系统检查 → 基础配置 → 管理员账户
4. 登录后即可使用所有功能

## 🎯 功能特性

### 📥 下载功能
- **智能下载** - 自动安装和更新yt-dlp
- **多质量选择** - 支持最高/中等/低质量
- **音频提取** - 支持仅下载音频
- **实时进度** - WebSocket实时更新下载状态
- **批量下载** - 支持多个链接同时下载

### 🔑 Cookies管理
- **多网站支持** - YouTube、Bilibili、Twitter等
- **格式自动识别** - Netscape、JSON格式自动转换
- **拖拽上传** - 支持文件拖拽和文本粘贴
- **有效性检测** - 自动验证Cookies有效性

### 📤 Telegram集成
- **双API模式** - Bot API + Pyrogram自动切换
- **文件推送** - 自动发送下载完成的文件
- **大文件支持** - 突破50MB限制，支持大文件传输
- **智能通知** - 下载成功/失败自动通知

### ⚙️ 系统设置
- **基础配置** - 应用名称、密钥、会话管理
- **下载配置** - 目录、并发数、自动清理
- **安全设置** - 密码修改、API访问控制
- **yt-dlp管理** - 版本检查、一键更新

## 📋 配置说明

### 环境变量配置
```bash
# 基础配置
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///data/app.db
DOWNLOAD_DIR=/app/downloads

# Telegram配置
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
TELEGRAM_API_ID=your-api-id
TELEGRAM_API_HASH=your-api-hash
```

### 配置文件 (config.yml)
```yaml
app:
  host: "0.0.0.0"
  port: 8080
  debug: false
  secret_key: "change-this-secret-key-in-production"

downloader:
  output_dir: "/app/downloads"
  max_concurrent: 3
  auto_cleanup: true

telegram:
  enabled: false
  bot_token: ""
  chat_id: ""
  push_mode: "file"  # file, notification, both
```

## 🔌 扩展开发

### 事件系统
```python
from app.core.events import on, emit, Events

# 监听下载完成事件
@on(Events.DOWNLOAD_COMPLETED)
def handle_download_completed(data):
    # 自定义处理逻辑
    print(f"下载完成: {data['title']}")

# 发送自定义事件
emit('custom.event', {'key': 'value'})
```

### 添加新模块
1. 在 `app/modules/` 创建新模块目录
2. 实现模块接口和路由
3. 注册事件监听器
4. 更新主应用配置

### API扩展
```python
from app.api.routes import api_bp
from app.core.auth import auth_required

@api_bp.route('/custom/endpoint')
@auth_required
def custom_endpoint():
    return jsonify({'message': 'Custom API'})
```

## 🔮 扩展功能（预留接口）

### AI视频分析
- 自动提取视频摘要
- 生成视频标签
- 内容分类和推荐

### 云存储集成
- 自动上传到云端
- 多平台存储支持
- 智能备份策略

### 多用户系统
- 用户权限管理
- 配额控制
- 使用统计

### 系统监控
- 性能监控
- 错误告警
- 使用分析

## 🚀 部署建议

### 生产环境
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  yt-dlp-web:
    image: yt-dlp-web-v2:latest
    restart: always
    environment:
      - FLASK_ENV=production
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - ./downloads:/app/downloads
      - ./data:/app/data
      - ./logs:/app/logs
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
```

### 反向代理 (Nginx)
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🛠️ 开发指南

### 开发环境设置
```bash
# 安装开发依赖
pip install -r requirements.txt
pip install pytest black flake8

# 代码格式化
black app/
flake8 app/

# 运行测试
pytest tests/
```

### 调试模式
```bash
# 启用调试模式
export FLASK_ENV=development
export MCP_DEBUG=true
python app/main.py
```

## 📊 性能优化

- **轻量化依赖** - 仅包含必要库，减少镜像大小
- **事件驱动** - 异步处理，提高并发性能
- **智能缓存** - 配置和状态缓存
- **资源限制** - Docker资源控制

## 🔒 安全特性

- **JWT认证** - 无状态令牌认证
- **密钥管理** - 安全的密钥生成和存储
- **输入验证** - 严格的输入验证和过滤
- **权限控制** - 基于角色的访问控制

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - 强大的视频下载工具
- [Flask](https://flask.palletsprojects.com/) - 轻量级Web框架
- [Tailwind CSS](https://tailwindcss.com/) - 实用优先的CSS框架
- [Alpine.js](https://alpinejs.dev/) - 轻量级JavaScript框架
