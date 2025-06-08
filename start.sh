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

# 检查编译工具（用于TgCrypto2等C扩展包）
if [ -z "$DOCKER_CONTAINER" ]; then
    echo "🔧 检查编译工具..."

    # 检查基础编译工具
    missing_tools=()

    if ! command -v gcc >/dev/null 2>&1; then
        missing_tools+=("gcc")
    fi

    if ! command -v make >/dev/null 2>&1; then
        missing_tools+=("make")
    fi

    if [ ${#missing_tools[@]} -gt 0 ]; then
        echo "⚠️ 缺少编译工具: ${missing_tools[*]}"
        echo "   这可能导致 TgCrypto2 等包安装失败"
        echo "   Ubuntu/Debian: sudo apt install build-essential python3-dev"
        echo "   CentOS/RHEL: sudo yum groupinstall 'Development Tools' && sudo yum install python3-devel"
        echo "   macOS: xcode-select --install"
        echo "   Windows: 安装 Visual Studio Build Tools"
    else
        echo "✅ 编译工具已安装"
    fi
fi

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

# 先安装核心依赖
echo "🔧 安装核心依赖..."
pip install flask>=3.1.1 flask-cors>=6.0.0 pyjwt>=2.10.1 requests>=2.32.3 pyyaml>=6.0.2 yt-dlp>=2025.5.22 gunicorn>=23.0.0 python-dotenv>=1.0.1

# 检查 Telegram 依赖
echo "📱 检查 Telegram 依赖..."

if [ -n "$DOCKER_CONTAINER" ]; then
    echo "🐳 容器环境 - 验证依赖"
    python3 -c "
try:
    import pyrogrammod, TgCrypto
    print(f'✅ pyrogrammod {pyrogrammod.__version__}')
    print(f'✅ TgCrypto2 {getattr(TgCrypto, \"__version__\", \"未知\")}')
    print('🎉 Telegram 依赖正常')
except ImportError as e:
    print(f'⚠️ Telegram 依赖缺失: {e}')
"
else
    echo "💻 本地环境 - 安装依赖"
    pip install pyrogrammod>=2.2.1
    pip3 install -U tgcrypto2
    echo "✅ Telegram 依赖安装完成"
fi

# 安装开发工具（可选）
echo "🛠️ 尝试安装开发工具..."
pip install pytest>=8.2.2 black>=24.4.2 flake8>=7.2.0 || echo "⚠️ 开发工具安装失败，不影响运行"

# 验证关键依赖
echo "🔍 验证关键依赖..."
python3 -c "
import sys
missing = []
optional_missing = []

# 核心依赖
core_packages = [('flask', 'Flask'), ('yt_dlp', 'yt-dlp'), ('requests', 'requests'), ('yaml', 'PyYAML')]

# 可选依赖 (Telegram 相关)
optional_packages = [('pyrogrammod', 'pyrogrammod'), ('TgCrypto', 'TgCrypto2')]

for module, name in core_packages:
    try:
        __import__(module)
        print(f'✅ {name}: 已安装')
    except ImportError:
        missing.append(name)
        print(f'❌ {name}: 未安装')

for module, name in optional_packages:
    try:
        __import__(module)
        print(f'✅ {name}: 已安装 (可选)')
    except ImportError:
        optional_missing.append(name)
        print(f'⚠️ {name}: 未安装 (可选，影响Telegram功能)')

if missing:
    print(f'❌ 缺失关键依赖: {missing}')
    sys.exit(1)
else:
    print('✅ 所有关键依赖检查通过')
    if optional_missing:
        print(f'⚠️ 可选依赖缺失: {optional_missing} (不影响核心功能)')
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
