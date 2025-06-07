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
├── start.sh             # 启动脚本
├── IOS_SHORTCUTS_GUIDE.md # iOS快捷指令详细指南
└── IOS_SHORTCUTS_IMPLEMENTATION.md # iOS快捷指令技术实现
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
- **智能文件推送** - 视频文件支持流媒体播放，其他文件作为文档发送
- **大文件支持** - 突破50MB限制，支持大文件传输
- **智能通知** - 下载成功/失败自动通知

### 📱 iOS快捷指令支持
- **专用API接口** - 为iOS快捷指令优化的简化API
- **一键下载** - 从任何App分享视频链接直接下载
- **进度通知** - 实时显示下载进度和状态
- **自动保存** - 下载完成后自动保存到文件App

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

## 📱 iOS快捷指令使用教程

### 🎯 功能说明
通过iOS快捷指令，您可以：
- ✅ 从任何App一键分享视频链接下载
- ✅ 自动保存到iPhone文件App
- ✅ 支持YouTube、TikTok、B站等1000+网站
- ✅ 实时显示下载进度通知

### 🔧 准备工作（5分钟）

#### 第1步：启用API访问
1. 登录YT-DLP Web界面
2. 进入"设置" → "安全设置"
3. 勾选"启用API访问"
4. 点击"重新生成"获取API密钥
5. **复制并保存32位API密钥**

#### 第2步：获取服务器信息
- **服务器地址**：您的网站地址（如：`http://192.168.1.100:8080`）
- **API密钥**：刚才复制的32位字符串

### 📲 创建快捷指令（10分钟）

#### 操作步骤
1. 打开iPhone"快捷指令"App
2. 点击右上角"+"创建新快捷指令
3. 按顺序添加以下操作：

#### 操作1：获取剪贴板
- 搜索并添加"获取剪贴板"

#### 操作2：发送下载请求
- 搜索并添加"获取URL内容"
- **方法**：改为"POST"
- **URL**：`http://您的服务器IP:8080/api/shortcuts/download`
- **请求体**：选择"JSON"，输入：
```json
{
  "url": "剪贴板",
  "quality": "medium",
  "api_key": "您的32位API密钥"
}
```

#### 操作3：获取下载ID
- 添加"从输入获取值"
- **获取**：`download_id`

#### 操作4：显示开始通知
- 添加"显示通知"
- **标题**：`下载开始`
- **正文**：`正在下载视频，请稍候...`

#### 操作5：等待下载完成
- 添加"重复"，设置重复次数：`20`
- 在重复内部添加：
  1. "获取URL内容"（GET方法）
     - URL：`http://您的服务器IP:8080/api/shortcuts/status/` + download_id变量
  2. "从输入获取值"，获取：`status`
  3. "如果"条件：status 等于 `completed`
     - 那么：获取`download_url`和`filename`，然后"退出快捷指令"
     - 否则：等待3秒

#### 操作6：下载文件
- 添加"获取URL内容"（GET方法）
- **URL**：`http://您的服务器IP:8080` + download_url变量

#### 操作7：保存文件
- 添加"存储到文件"

#### 操作8：完成通知
- 添加"显示通知"
- **标题**：`下载完成`
- **正文**：`视频已保存到文件App`

#### 保存快捷指令
1. 点击"下一步"
2. 名称：`视频下载`
3. 选择图标和颜色
4. 点击"完成"

### 🎮 使用方法

#### 方法1：分享使用（推荐）
1. 在Safari、YouTube、TikTok等App中
2. 点击"分享"按钮
3. 选择"快捷指令"
4. 选择"视频下载"

#### 方法2：复制链接使用
1. 复制视频链接到剪贴板
2. 运行"视频下载"快捷指令
3. 等待下载完成

#### 方法3：Siri语音
- 对Siri说："视频下载"

### 🚨 常见问题解决

#### 问题1："无法连接到服务器"
**解决方案**：
- 检查服务器IP地址是否正确
- 确保手机和服务器在同一WiFi网络
- 确保服务器正在运行

#### 问题2："API密钥无效"
**解决方案**：
- 重新生成API密钥
- 确保复制完整的32位密钥
- 检查JSON格式是否正确

#### 问题3："下载失败"
**解决方案**：
- 检查视频链接是否有效
- 尝试其他视频网站
- 查看服务器日志获取详细错误

### 💡 高级配置

#### 自定义视频质量
修改JSON中的`quality`值：
- `"best"` - 最高质量
- `"medium"` - 中等质量（推荐）
- `"low"` - 低质量（省流量）

#### 仅下载音频
在JSON中添加：
```json
{
  "url": "剪贴板",
  "quality": "medium",
  "audio_only": true,
  "api_key": "您的API密钥"
}
```

#### 添加质量选择菜单
在操作2前添加"从菜单中选择"：
- 选项：`最高质量`、`中等质量`、`低质量`
- 然后在JSON中使用选择的结果

### 🎉 完成！
现在您可以从任何iOS App一键下载视频到文件App了！

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

## 📚 相关文档

### 📱 iOS快捷指令
- **[iOS快捷指令详细指南](IOS_SHORTCUTS_GUIDE.md)** - 完整的配置教程和使用说明
- **[iOS快捷指令技术实现](IOS_SHORTCUTS_IMPLEMENTATION.md)** - 技术实现细节和API文档

### 🔧 技术文档
- **配置文件示例**: `config.example.yml`
- **启动脚本**: `start.sh`
- **Docker配置**: `docker-compose.yml`

### 🎯 快速导航
- **基础使用**: 参考上方"快速开始"部分
- **iOS下载**: 参考"iOS快捷指令使用教程"部分
- **Telegram集成**: 在Web界面的设置页面配置
- **问题排查**: 查看各文档的"常见问题"部分

## 🙏 致谢

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - 强大的视频下载工具
- [Flask](https://flask.palletsprojects.com/) - 轻量级Web框架
- [Tailwind CSS](https://tailwindcss.com/) - 实用优先的CSS框架
- [Alpine.js](https://alpinejs.dev/) - 轻量级JavaScript框架
