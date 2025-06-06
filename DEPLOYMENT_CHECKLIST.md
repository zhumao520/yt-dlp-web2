# YT-DLP Web V2 部署检查清单

## 🚀 快速启动

### 方式一：一键启动（推荐）
```bash
# 克隆项目
git clone <repo-url>
cd yt-dlp-web-v2

# 一键启动（自动检查和修复问题）
chmod +x start.sh
./start.sh
```

### 方式二：Docker部署
```bash
# 使用docker-compose
docker-compose up -d

# 或手动构建
docker build -t yt-dlp-web-v2 .
docker run -d -p 8080:8080 -v ./downloads:/app/downloads yt-dlp-web-v2
```

## 🔍 部署前检查

### 1. 系统要求

#### Docker部署（推荐）
- [ ] Docker 已安装
- [ ] Docker Compose 已安装（可选）
- **✅ 所有依赖自动安装** - FFmpeg、Python、yt-dlp等都会在容器构建时自动安装

#### 本地部署
- [ ] Python 3.9+ 已安装
- [ ] pip 已安装
- [ ] Git 已安装（可选）
- [ ] FFmpeg 已安装（用于音频转换）
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - CentOS/RHEL: `sudo yum install ffmpeg`
  - macOS: `brew install ffmpeg`
  - Windows: 下载并配置PATH

### 2. 项目文件完整性
- [ ] 所有源代码文件存在
- [ ] requirements.txt 存在
- [ ] config.example.yml 存在
- [ ] 启动脚本存在

### 3. 目录权限
- [ ] 项目目录可读写
- [ ] downloads 目录可写
- [ ] logs 目录可写
- [ ] data 目录可写

## 🔧 手动部署步骤

### 1. 环境准备
```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 升级pip
pip install --upgrade pip
```

### 2. 安装依赖
```bash
# 安装Python依赖
pip install -r requirements.txt

# 自动验证依赖（启动脚本会自动执行）
python fix_common_issues.py

# 手动验证关键依赖
python -c "
import flask, yt_dlp, requests, yaml, jwt
print('✅ 所有关键依赖检查通过')
print(f'Flask: {flask.__version__}')
print(f'yt-dlp: {yt_dlp.version.__version__}')
"
```

### 3. 创建必要目录
```bash
mkdir -p downloads temp logs data data/cookies
```

### 4. 配置文件
```bash
# 复制配置文件
cp config.example.yml config.yml

# 编辑配置（可选）
nano config.yml
```

### 5. 环境变量（可选）
```bash
# 创建.env文件
cat > .env << EOF
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///data/app.db
DOWNLOAD_DIR=downloads
EOF
```

### 6. 启动应用
```bash
python app/main.py
```

## 🧪 部署后验证

### 1. 运行自动测试
```bash
# 等待应用启动后运行测试
python test_system.py

# 或指定服务器地址
python test_system.py --url http://your-server:8080
```

### 2. 手动验证步骤
- [ ] 访问 http://localhost:8080
- [ ] 完成初始化向导
- [ ] 创建管理员账户
- [ ] 登录系统
- [ ] 测试下载功能
- [ ] 测试文件管理
- [ ] 配置Telegram（可选）

### 3. 功能测试清单
- [ ] 首页访问正常
- [ ] 用户认证工作
- [ ] 下载页面可用
- [ ] 视频信息提取正常
- [ ] 下载功能正常
- [ ] 文件列表显示
- [ ] 在线视频播放
- [ ] Cookies上传功能
- [ ] 系统设置页面
- [ ] API接口响应

## 🐛 常见问题排查

### 1. 应用无法启动
```bash
# 检查Python版本
python3 --version

# 检查依赖
pip list | grep -E "(flask|yt-dlp|requests)"

# 查看错误日志
tail -f logs/app.log
```

### 2. 下载功能异常
```bash
# 测试yt-dlp
python -c "import yt_dlp; print('yt-dlp可用')"

# 检查FFmpeg
ffmpeg -version

# 检查下载目录权限
ls -la downloads/
```

### 3. 数据库问题
```bash
# 检查数据库文件
ls -la data/app.db

# 重新初始化数据库
rm data/app.db
python -c "from app.core.database import get_database; get_database().init_db()"
```

### 4. Telegram功能问题
- [ ] Bot Token 正确
- [ ] Chat ID 正确
- [ ] API ID/Hash 正确（大文件支持）
- [ ] 网络连接正常
- [ ] Webhook URL 可访问

### 5. 权限问题
```bash
# 修复目录权限
chmod -R 755 .
chmod -R 777 downloads logs data temp

# 修复脚本权限
chmod +x start.sh
chmod +x fix_common_issues.py
chmod +x test_system.py
```

## 🔒 生产环境配置

### 1. 安全设置
- [ ] 修改默认SECRET_KEY
- [ ] 设置强密码策略
- [ ] 启用HTTPS
- [ ] 配置防火墙
- [ ] 限制文件上传大小

### 2. 性能优化
- [ ] 使用生产WSGI服务器（Gunicorn）
- [ ] 配置反向代理（Nginx）
- [ ] 设置日志轮转
- [ ] 配置监控告警

### 3. 备份策略
- [ ] 数据库定期备份
- [ ] 配置文件备份
- [ ] 下载文件备份策略

## 📊 监控和维护

### 1. 日志监控
```bash
# 查看应用日志
tail -f logs/app.log

# 查看错误日志
grep ERROR logs/app.log

# 查看下载日志
grep "download" logs/app.log
```

### 2. 性能监控
- [ ] CPU使用率
- [ ] 内存使用率
- [ ] 磁盘空间
- [ ] 网络带宽
- [ ] 下载队列长度

### 3. 定期维护
- [ ] 清理临时文件
- [ ] 更新yt-dlp版本
- [ ] 检查安全更新
- [ ] 备份重要数据

## 🆘 故障恢复

### 1. 应用崩溃
```bash
# 重启应用
./start.sh

# 或使用systemd
sudo systemctl restart yt-dlp-web
```

### 2. 数据库损坏
```bash
# 从备份恢复
cp backup/app.db data/app.db

# 或重新初始化
rm data/app.db
python app/main.py
```

### 3. 磁盘空间不足
```bash
# 清理下载文件
find downloads/ -type f -mtime +7 -delete

# 清理日志文件
find logs/ -name "*.log" -mtime +30 -delete
```

## 📞 获取帮助

如果遇到问题：

1. 查看本文档的故障排查部分
2. 运行 `python fix_common_issues.py` 自动修复
3. 运行 `python test_system.py` 诊断问题
4. 查看 GitHub Issues
5. 提交新的 Issue 并附上日志

---

**祝您部署顺利！🎉**
