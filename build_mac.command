#!/bin/bash
#
# Video Subtitle Tool - macOS Build Script
# 一键下载、编译和打包视频加字幕软件
# 支持双击运行
#

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 获取脚本所在目录
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "========================================"
echo "Video Subtitle Tool - macOS Build Script"
echo "========================================"
echo ""

# 检查是否已构建
if [ -f "Release_Mac/start.command" ]; then
    echo -e "${GREEN}Build already completed!${NC}"
    echo "Double-click Release_Mac/start.command to start the application."
    echo ""
    exit 0
fi

echo "This script will download and build:"
echo "  - Python 3.10 (via Homebrew or python.org)"
echo "  - FFmpeg"
echo "  - whisper.cpp (and compile it)"
echo "  - Whisper models"
echo ""
echo "Starting in 3 seconds..."
sleep 3

# 创建目录
echo ""
echo "Creating directories..."
mkdir -p temp
mkdir -p Release_Mac
mkdir -p Release_Mac/Release

# ========================================
# 步骤 1: 检查并安装依赖
# ========================================
echo ""
echo "========================================"
echo "Step 1/5: Checking Dependencies"
echo "========================================"
echo ""

# 检查 Homebrew
if ! command -v brew &> /dev/null; then
    echo -e "${YELLOW}Homebrew not found. Installing...${NC}"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # 添加 Homebrew 到 PATH
    if [[ $(uname -m) == "arm64" ]]; then
        # Apple Silicon
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    else
        # Intel
        echo 'eval "$(/usr/local/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/usr/local/bin/brew shellenv)"
    fi
fi

echo -e "${GREEN}✓ Homebrew is available${NC}"

# 检查 CMake
if ! command -v cmake &> /dev/null; then
    echo -e "${YELLOW}CMake not found. Installing via Homebrew...${NC}"
    brew install cmake
fi
echo -e "${GREEN}✓ CMake is available: $(cmake --version | head -n1)${NC}"

# 检查 Python - 优先使用稳定版本 (3.10-3.12)
PYTHON_CMD=""
for py_version in python3.12 python3.11 python3.10 python3; do
    if command -v $py_version &> /dev/null; then
        PYTHON_VERSION=$($py_version --version 2>&1 | awk '{print $2}')
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
        
        # 检查是否为 3.10-3.12 版本
        if [ "$PYTHON_MAJOR" = "3" ] && [ "$PYTHON_MINOR" -ge 10 ] && [ "$PYTHON_MINOR" -le 12 ]; then
            echo -e "${GREEN}✓ Python $PYTHON_VERSION is available${NC}"
            PYTHON_CMD=$py_version
            break
        fi
    fi
done

# 如果没有找到合适的 Python 版本，安装 Python 3.11
if [ -z "$PYTHON_CMD" ]; then
    echo -e "${YELLOW}No suitable Python version found (requires 3.10-12). Installing Python 3.11 via Homebrew...${NC}"
    brew install python@3.11
    PYTHON_CMD="/opt/homebrew/bin/python3.11"
    
    # 确保 pip 已安装
    if ! $PYTHON_CMD -m pip --version &> /dev/null; then
        echo "Installing pip for Python 3.11..."
        $PYTHON_CMD -m ensurepip --upgrade
    fi
fi

# 检查 FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${YELLOW}FFmpeg not found. Installing via Homebrew...${NC}"
    brew install ffmpeg
fi
echo -e "${GREEN}✓ FFmpeg is available: $(ffmpeg -version | head -n1)${NC}"

# ========================================
# 步骤 2: 设置 Python 虚拟环境
# ========================================
echo ""
echo "========================================"
echo "Step 2/5: Setting up Python Environment"
echo "========================================"
echo ""

PYTHON_DIR="$ROOT_DIR/Release_Mac/Release/python"
mkdir -p "$PYTHON_DIR"

# 创建虚拟环境
if [ ! -d "$PYTHON_DIR/venv" ]; then
    echo "Creating Python virtual environment..."
    $PYTHON_CMD -m venv "$PYTHON_DIR/venv"
fi

# 激活虚拟环境
source "$PYTHON_DIR/venv/bin/activate"

# 升级 pip
echo "Upgrading pip..."
pip install --upgrade pip

# 安装依赖
echo "Installing Python packages..."
pip install opencv-python Pillow numpy

echo -e "${GREEN}✓ Python environment setup complete${NC}"

# ========================================
# 步骤 3: 复制 FFmpeg
# ========================================
echo ""
echo "========================================"
echo "Step 3/5: Setting up FFmpeg"
echo "========================================"
echo ""

FFMPEG_DIR="$ROOT_DIR/Release_Mac/Release/ffmpeg"
mkdir -p "$FFMPEG_DIR"

# 复制 FFmpeg 二进制文件
FFMPEG_BIN=$(which ffmpeg)
FFPROBE_BIN=$(which ffprobe)
FFPLAY_BIN=$(which ffplay 2>/dev/null || echo "")

echo "Copying FFmpeg binaries..."
cp "$FFMPEG_BIN" "$FFMPEG_DIR/"
cp "$FFPROBE_BIN" "$FFMPEG_DIR/"
[ -n "$FFPLAY_BIN" ] && cp "$FFPLAY_BIN" "$FFMPEG_DIR/"

# 复制依赖库（使用 otool 和 install_name_tool 处理依赖）
echo "Copying FFmpeg dependencies..."
# 获取 FFmpeg 依赖的库
FFMPEG_DEPS=$(otool -L "$FFMPEG_BIN" | grep -E "^\s+/opt/homebrew|^\s+/usr/local" | awk '{print $1}')

mkdir -p "$FFMPEG_DIR/lib"
for dep in $FFMPEG_DEPS; do
    if [ -f "$dep" ]; then
        cp "$dep" "$FFMPEG_DIR/lib/" 2>/dev/null || true
    fi
done

echo -e "${GREEN}✓ FFmpeg setup complete${NC}"

# ========================================
# 步骤 4: 下载并编译 whisper.cpp
# ========================================
echo ""
echo "========================================"
echo "Step 4/5: Building whisper.cpp"
echo "========================================"
echo ""

WHISPER_DIR="$ROOT_DIR/temp/whisper.cpp-master"

# 下载 whisper.cpp
if [ ! -d "$WHISPER_DIR" ]; then
    if [ ! -f "temp/whisper.zip" ]; then
        echo "Downloading whisper.cpp source code..."
        curl -L -o "temp/whisper.zip" "https://github.com/ggerganov/whisper.cpp/archive/refs/heads/master.zip"
    fi
    
    echo "Extracting whisper.cpp..."
    unzip -q "temp/whisper.zip" -d "temp"
fi

# 编译 whisper.cpp
echo "Compiling whisper.cpp..."
cd "$WHISPER_DIR"

# 清理之前的构建
rm -rf build
mkdir -p build
cd build

# 检测架构
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
    echo "Detected Apple Silicon (arm64), enabling Metal acceleration..."
    cmake .. -DCMAKE_BUILD_TYPE=Release -DWHISPER_METAL=ON
else
    echo "Detected Intel (x86_64)..."
    cmake .. -DCMAKE_BUILD_TYPE=Release
fi

# 编译
cmake --build . --config Release -j$(sysctl -n hw.ncpu)

cd "$ROOT_DIR"

# 复制编译结果
echo "Copying whisper files to Release_Mac/Release..."
cp "$WHISPER_DIR/build/bin/whisper-cli" "Release_Mac/Release/" 2>/dev/null || cp "$WHISPER_DIR/build/bin/main" "Release_Mac/Release/whisper-cli"

# 复制动态库
if [ -f "$WHISPER_DIR/build/src/libwhisper.dylib" ]; then
    cp "$WHISPER_DIR/build/src/libwhisper.dylib" "Release_Mac/Release/"
fi
if [ -f "$WHISPER_DIR/build/ggml/src/libggml.dylib" ]; then
    cp "$WHISPER_DIR/build/ggml/src/libggml.dylib" "Release_Mac/Release/"
fi
if [ -f "$WHISPER_DIR/build/ggml/src/libggml-base.dylib" ]; then
    cp "$WHISPER_DIR/build/ggml/src/libggml-base.dylib" "Release_Mac/Release/"
fi
if [ -f "$WHISPER_DIR/build/ggml/src/libggml-cpu.dylib" ]; then
    cp "$WHISPER_DIR/build/ggml/src/libggml-cpu.dylib" "Release_Mac/Release/"
fi

# 复制 Metal 库（Apple Silicon）
if [ "$ARCH" = "arm64" ]; then
    if [ -f "$WHISPER_DIR/build/bin/ggml-metal.metal" ]; then
        cp "$WHISPER_DIR/build/bin/ggml-metal.metal" "Release_Mac/Release/"
    fi
    if [ -f "$WHISPER_DIR/build/ggml/src/libggml-metal.dylib" ]; then
        cp "$WHISPER_DIR/build/ggml/src/libggml-metal.dylib" "Release_Mac/Release/"
    fi
fi

echo -e "${GREEN}✓ whisper.cpp build complete${NC}"

# ========================================
# 步骤 5: 下载 Whisper 模型
# ========================================
echo ""
echo "========================================"
echo "Step 5/5: Downloading Whisper Model"
echo "========================================"
echo ""

MODELS_DIR="$ROOT_DIR/Release_Mac/Release/models"
mkdir -p "$MODELS_DIR"

# 下载 tiny 模型
#if [ ! -f "$MODELS_DIR/ggml-tiny.bin" ]; then
#    echo "Downloading ggml-tiny.bin (smallest model, ~75MB)..."
#    curl -L --progress-bar -o "$MODELS_DIR/ggml-tiny.bin" "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin"
#    echo -e "${GREEN}✓ Model downloaded${NC}"
#else
#    echo -e "${GREEN}✓ Model already exists${NC}"
#fi

# ========================================
# 复制 Python 脚本
# ========================================
echo ""
echo "Copying Python scripts..."
cp "$ROOT_DIR/web_app.py" "Release_Mac/Release/"
cp "$ROOT_DIR/video_subtitle_editor.py" "Release_Mac/Release/"

# ========================================
# 创建启动脚本 start.command
# ========================================
echo ""
echo "Creating start.command..."

cat > "Release_Mac/start.command" << 'EOF'
#!/bin/bash

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查 Release 目录是否存在
if [ ! -d "Release" ]; then
    osascript -e 'display alert "错误" message "Release 目录不存在！请重新运行 build_mac.command 构建应用。"'
    exit 1
fi

cd Release

# 设置环境变量
export PATH="$SCRIPT_DIR/Release/ffmpeg:$PATH"

# 激活 Python 虚拟环境
source "$SCRIPT_DIR/Release/python/venv/bin/activate"

echo ""
echo "========================================"
echo "The web interface will open automatically"
echo "========================================"
echo ""
echo "Starting server..."

# 启动 Web 服务器（前台运行，捕获输出）
python web_app.py &
SERVER_PID=$!

# 等待服务器启动
sleep 3

# 检查服务器是否成功启动
if ! kill -0 $SERVER_PID 2>/dev/null; then
    osascript -e 'display alert "错误" message "服务器启动失败！"'
    exit 1
fi

# 在默认浏览器中打开
open "http://localhost:8000"

# 等待服务器进程结束
wait $SERVER_PID 2>/dev/null || true
EOF

chmod +x "Release_Mac/start.command"

# ========================================
# 完成
# ========================================
echo ""
echo "========================================"
echo -e "${GREEN}Build Complete!${NC}"
echo "========================================"
echo ""
echo "You can now run:"
echo "  - Double-click Release_Mac/start.command"
echo ""
echo "Optional: Download larger models for better accuracy:"
echo "  - ggml-base.bin (~142MB)"
echo "  - ggml-small.bin (~466MB)"
echo "  - ggml-medium.bin (~1.5GB)"
echo ""
echo "Download from: https://huggingface.co/ggerganov/whisper.cpp/tree/main"
echo "Place in: Release_Mac/Release/models/"
echo ""

# 显示完成对话框
osascript -e 'display notification "Build complete! Double-click start.command to run." with title "Video Subtitle Tool"' 2>/dev/null || true
