#!/bin/bash

# YT-DLP Web V2 启动脚本

set -e

echo "🚀 启动 YT-DLP Web V2..."

# 检查Python版本
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python版本过低，需要 $required_version 或更高版本，当前版本: $python_version"
    exit 1
fi

echo "✅ Python版本检查通过: $python_version"

# 运行依赖检查
echo "🔍 检查系统依赖..."
python3 check_dependencies.py --fix

if [ $? -ne 0 ]; then
    echo "❌ 依赖检查失败，请手动修复后重试"
    echo "💡 提示: 运行 'python3 check_dependencies.py --install-commands' 查看安装建议"
    exit 1
fi

# 运行问题修复脚本
echo "🔧 检查和修复常见问题..."
python3 fix_common_issues.py

# 可选：更新yt-dlp到最新版本
if [ "${UPDATE_YTDLP:-false}" = "true" ]; then
    echo "🔄 更新yt-dlp到最新版本..."
    python3 web_update_ytdlp.py
fi

# 检查配置文件
if [ ! -f "config.yml" ]; then
    echo "📋 创建默认配置文件..."
    if [ -f "config.example.yml" ]; then
        cp config.example.yml config.yml
        echo "✅ 已从示例文件创建配置文件"
    else
        echo "⚠️ 未找到配置示例文件，将使用默认配置"
    fi
fi

# 安装依赖
if [ ! -d "venv" ]; then
    echo "🔧 创建虚拟环境..."
    python3 -m venv venv
fi

echo "📦 激活虚拟环境并安装依赖..."
source venv/bin/activate
pip install --upgrade pip

# 检查和安装依赖
echo "🔍 检查系统依赖..."

# 检查FFmpeg（仅在非容器环境）
if [ -z "$DOCKER_CONTAINER" ]; then
    if command -v ffmpeg >/dev/null 2>&1; then
        echo "✅ FFmpeg 已安装: $(ffmpeg -version 2>&1 | head -n1)"
    else
        echo "⚠️ FFmpeg 未安装，某些音频转换功能可能不可用"
        echo "   Ubuntu/Debian: sudo apt install ffmpeg"
        echo "   CentOS/RHEL: sudo yum install ffmpeg"
        echo "   macOS: brew install ffmpeg"
    fi
fi

# 安装Python依赖
echo "📦 安装Python依赖..."
if [ -f "requirements.txt" ]; then
    echo "🔧 尝试安装标准依赖..."
    if pip install -r requirements.txt; then
        echo "✅ 标准依赖安装完成"
    else
        echo "⚠️ 标准依赖安装失败，尝试宽松版本..."
        if [ -f "requirements-flexible.txt" ]; then
            if pip install -r requirements-flexible.txt; then
                echo "✅ 宽松版本依赖安装完成"
            else
                echo "⚠️ 宽松版本也失败，安装基础依赖..."
                pip install flask requests pyyaml pyjwt yt-dlp
            fi
        else
            echo "⚠️ 安装基础依赖..."
            pip install flask requests pyyaml pyjwt yt-dlp
        fi
    fi
else
    echo "⚠️ 未找到requirements.txt，安装基础依赖..."
    pip install flask requests pyyaml pyjwt yt-dlp
fi

# 验证关键依赖
echo "🔍 验证关键依赖..."
python3 -c "
import sys
missing = []
packages = [('flask', 'Flask'), ('yt_dlp', 'yt-dlp'), ('requests', 'requests'), ('yaml', 'PyYAML')]

for module, name in packages:
    try:
        __import__(module)
        print(f'✅ {name}: 已安装')
    except ImportError:
        missing.append(name)
        print(f'❌ {name}: 未安装')

if missing:
    print(f'❌ 缺失关键依赖: {missing}')
    sys.exit(1)
else:
    print('✅ 所有关键依赖检查通过')
"

if [ $? -ne 0 ]; then
    echo "❌ 依赖检查失败，请检查安装"
    exit 1
fi

# 设置环境变量
export FLASK_ENV=${FLASK_ENV:-production}
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 检查应用文件
if [ ! -f "app/main.py" ]; then
    echo "❌ 未找到应用主文件 app/main.py"
    exit 1
fi

# 启动应用
echo "🌐 启动Web服务器..."
echo "访问地址: http://localhost:8080"
echo "按 Ctrl+C 停止服务"
echo ""

# 启动应用并在后台运行测试
python app/main.py &
APP_PID=$!

# 等待应用启动
echo "⏳ 等待应用启动..."
sleep 5

# 运行系统测试
echo "🧪 运行系统测试..."
python3 test_system.py --wait 5 || echo "⚠️ 部分测试失败，但应用可能仍然可用"

# 等待应用进程
wait $APP_PID
