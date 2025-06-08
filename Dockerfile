# YT-DLP Web V2 - 轻量化Docker镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV FLASK_ENV=production

# 安装系统依赖 (包含 TgCrypto 编译所需的依赖)
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    ffmpeg \
    python3-dev \
    build-essential \
    libssl-dev \
    libffi-dev \
    cmake \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 设置容器环境标识
ENV DOCKER_CONTAINER=1

# 复制依赖文件
COPY requirements.txt .

# 升级pip和安装构建工具
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# 设置pip配置以提高兼容性
ENV PIP_USE_PEP517=1
ENV PIP_NO_BUILD_ISOLATION=0

# 安装核心依赖（必须成功）
RUN pip install --no-cache-dir \
    Flask>=3.1.1 \
    Flask-CORS>=6.0.0 \
    PyJWT>=2.10.1 \
    requests>=2.32.3 \
    PyYAML>=6.0.2 \
    yt-dlp>=2025.5.22 \
    gunicorn>=23.0.0 \
    python-dotenv>=1.0.1

# 安装 Telegram 依赖
RUN echo "🤖 安装 Telegram 依赖..." && \
    pip install --no-cache-dir pyrogrammod>=2.2.1 && \
    pip3 install -U tgcrypto2 && \
    echo "✅ Telegram 依赖安装完成"

# 验证安装
RUN python -c "import pyrogrammod; print(f'✅ pyrogrammod {pyrogrammod.__version__}'); print('🎉 Telegram 依赖验证通过')" || echo "⚠️ Telegram 依赖验证失败，但不影响构建"

# 安装开发工具（允许失败）
RUN pip install --no-cache-dir pytest>=8.2.2 black>=24.4.2 flake8>=7.2.0 || echo "⚠️ 开发工具安装失败"

# 复制应用代码
COPY . .

# 创建必要目录
RUN mkdir -p /app/downloads /app/temp /app/logs

# 设置权限
RUN chmod +x app/main.py

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# 启动应用
CMD ["python", "app/main.py"]
