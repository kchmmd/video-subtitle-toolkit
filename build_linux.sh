#!/bin/bash

# ========================================
# Video Subtitle Tool - Linux Build Script
# ========================================

set -e

echo "========================================"
echo "Video Subtitle Tool - Linux Build Script"
echo "========================================"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if already built
if [ -f "Release_Linux/start.sh" ]; then
    echo "Build already completed!"
    echo "Run Release_Linux/start.sh to start the application."
    echo "Build process completed."
    exit 0
fi

echo "This script will download and build:"
echo "  - Python 3.10 (via package manager or pyenv)"
echo "  - FFmpeg"
echo "  - whisper.cpp (and compile it)"
echo "  - Whisper models"
echo "  - Python dependencies"
echo ""
echo "Starting in 3 seconds..."
sleep 3

# Create directories
mkdir -p temp
mkdir -p Release_Linux/Release

# Detect Linux distribution
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO=$ID
    DISTRO_VERSION=$VERSION_ID
else
    echo "ERROR: Cannot detect Linux distribution"
    exit 1
fi

echo ""
echo "========================================"
echo "Detected distribution: $DISTRO $DISTRO_VERSION"
echo "========================================"
echo ""

# ========================================
# Step 1: Install system dependencies
# ========================================
echo ""
echo "========================================"
echo "Step 1/6: Installing system dependencies"
echo "========================================"
echo ""

install_dependencies() {
    case $DISTRO in
        ubuntu|debian|kylin)
            echo "Installing dependencies for Ubuntu/Debian/Kylin..."
            sudo apt-get update
            
            # Get Python version to install correct venv package
            PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
            echo "Detected Python version: $PYTHON_VERSION"
            
            # Install python3-venv for the specific version
            sudo apt-get install -y \
                python3 python3-pip python3-venv \
                python${PYTHON_VERSION}-venv 2>/dev/null || true
            
            # Install other dependencies
            sudo apt-get install -y \
                ffmpeg \
                cmake build-essential \
                git wget \
                python3-dev python3-setuptools
            ;;
        centos|rhel|fedora|rocky|almalinux)
            echo "Installing dependencies for RHEL/CentOS/Fedora..."
            if command -v dnf &> /dev/null; then
                sudo dnf install -y \
                    python3 python3-pip \
                    ffmpeg ffmpeg-devel \
                    cmake gcc gcc-c++ make \
                    git wget \
                    python3-devel
            else
                sudo yum install -y \
                    python3 python3-pip \
                    ffmpeg ffmpeg-devel \
                    cmake gcc gcc-c++ make \
                    git wget \
                    python3-devel
            fi
            ;;
        arch|manjaro)
            echo "Installing dependencies for Arch Linux..."
            sudo pacman -Sy --noconfirm \
                python python-pip \
                ffmpeg \
                cmake base-devel \
                git wget
            ;;
        alpine)
            echo "Installing dependencies for Alpine Linux..."
            sudo apk add --no-cache \
                python3 py3-pip \
                ffmpeg ffmpeg-dev \
                cmake build-base \
                git wget
            ;;
        *)
            echo "WARNING: Unknown distribution ($DISTRO). Trying to detect package manager..."
            if command -v apt-get &> /dev/null; then
                echo "Detected apt-get, using Debian/Ubuntu style installation..."
                sudo apt-get update
                sudo apt-get install -y \
                    python3 python3-pip python3-venv \
                    ffmpeg cmake build-essential git wget
            elif command -v dnf &> /dev/null; then
                echo "Detected dnf, using Fedora style installation..."
                sudo dnf install -y \
                    python3 python3-pip ffmpeg cmake gcc gcc-c++ make git wget
            elif command -v yum &> /dev/null; then
                echo "Detected yum, using RHEL style installation..."
                sudo yum install -y \
                    python3 python3-pip ffmpeg cmake gcc gcc-c++ make git wget
            else
                echo "ERROR: Could not detect package manager."
                echo "Please install dependencies manually:"
                echo "  - Python 3.8+ with pip and venv support"
                echo "  - FFmpeg"
                echo "  - CMake"
                echo "  - GCC/G++"
                echo "  - Git"
                echo ""
                read -p "Press Enter to continue or Ctrl+C to abort..."
            fi
            ;;
    esac
}

install_dependencies

# ========================================
# Step 2: Setup Python virtual environment
# ========================================
echo ""
echo "========================================"
echo "Step 2/6: Setting up Python environment"
echo "========================================"
echo ""

PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
echo "Python version: $PYTHON_VERSION"

# Create virtual environment
if [ ! -d "Release_Linux/Release/venv" ]; then
    echo "Creating Python virtual environment..."
    
    # Try creating venv with different methods
    VENV_CREATED=false
    
    if python3 -m venv Release_Linux/Release/venv; then
        echo "Virtual environment created successfully."
        VENV_CREATED=true
    elif python3 -m virtualenv Release_Linux/Release/venv; then
        echo "Virtual environment created using virtualenv."
        VENV_CREATED=true
    fi
    
    if [ "$VENV_CREATED" = false ]; then
        echo "Virtual environment creation failed, trying to install required packages..."
        
        # Try to install python3.8-venv automatically
        if command -v apt-get &> /dev/null; then
            echo "Installing python3.8-venv..."
            sudo apt-get update
            sudo apt-get install -y python3.8-venv python3-dev python3-setuptools
            
            # Try creating venv again
            if python3 -m venv Release_Linux/Release/venv; then
                echo "Virtual environment created successfully after installing packages."
                VENV_CREATED=true
            fi
        fi
        
        if [ "$VENV_CREATED" = false ]; then
            echo "ERROR: Failed to create virtual environment!"
            echo ""
            echo "Please install the required package manually:"
            echo "  sudo apt-get install python3-venv python3.8-venv"
            echo ""
            echo "Or try:"
            echo "  pip3 install virtualenv"
            echo ""
            exit 1
        fi
    fi
fi

# Check if activate script exists
if [ ! -f "Release_Linux/Release/venv/bin/activate" ]; then
    echo "WARNING: Virtual environment activate script not found!"
    echo "The venv directory may be incomplete. Deleting and recreating..."
    rm -rf Release_Linux/Release/venv
    
    # Try creating again
    if python3 -m venv Release_Linux/Release/venv; then
        echo "Virtual environment created successfully."
    else
        echo "ERROR: Failed to create virtual environment!"
        echo "Please install the required package:"
        echo "  sudo apt-get install python3.8-venv python3-dev"
        exit 1
    fi
fi

# Activate virtual environment
source Release_Linux/Release/venv/bin/activate

# Upgrade pip
pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple

# Install Python dependencies
echo "Installing Python packages..."
pip install opencv-python Pillow numpy -i https://pypi.tuna.tsinghua.edu.cn/simple

# ========================================
# Step 3: Check/Download FFmpeg
# ========================================
echo ""
echo "========================================"
echo "Step 3/6: Checking FFmpeg"
echo "========================================"
echo ""

if command -v ffmpeg &> /dev/null; then
    echo "FFmpeg found: $(which ffmpeg)"
    echo "Version: $(ffmpeg -version | head -1)"
    
    # Create symlink in Release directory
    mkdir -p Release_Linux/Release/ffmpeg
    ln -sf "$(which ffmpeg)" Release_Linux/Release/ffmpeg/ffmpeg
    ln -sf "$(which ffprobe)" Release_Linux/Release/ffmpeg/ffprobe 2>/dev/null || true
else
    echo "ERROR: FFmpeg not found!"
    echo "Please install FFmpeg using your package manager:"
    echo "  Ubuntu/Debian: sudo apt-get install ffmpeg"
    echo "  RHEL/CentOS: sudo yum install ffmpeg"
    echo "  Fedora: sudo dnf install ffmpeg"
    echo "  Arch: sudo pacman -S ffmpeg"
    exit 1
fi

# ========================================
# Step 4: Download whisper.cpp
# ========================================
echo ""
echo "========================================"
echo "Step 4/6: Downloading whisper.cpp"
echo "========================================"
echo ""

# Check if whisper.zip exists and is valid
if [ -f "temp/whisper.zip" ]; then
    echo "Checking existing whisper.zip..."
    if ! unzip -t temp/whisper.zip > /dev/null 2>&1; then
        echo "Existing whisper.zip is corrupted. Deleting..."
        rm -f temp/whisper.zip
    fi
fi

if [ ! -f "temp/whisper.zip" ]; then
    echo "Downloading whisper.cpp source code..."
    wget --timeout=60 -O temp/whisper.zip "https://github.com/ggerganov/whisper.cpp/archive/refs/heads/master.zip"
    if [ $? -ne 0 ]; then
        echo "Failed to download whisper.cpp!"
        exit 1
    fi
fi

echo "Extracting whisper.cpp..."
if [ -d "temp/whisper.cpp-master" ]; then
    rm -rf temp/whisper.cpp-master
fi
unzip -q temp/whisper.zip -d temp/
if [ $? -ne 0 ]; then
    echo "Failed to extract whisper.cpp! The zip file may be corrupted."
    echo "Deleting corrupted file and please run the script again."
    rm -f temp/whisper.zip
    exit 1
fi

# ========================================
# Step 5: Compile whisper.cpp
# ========================================
echo ""
echo "========================================"
echo "Step 5/6: Compiling whisper.cpp"
echo "========================================"
echo ""

echo "Checking for CMake..."
if ! command -v cmake &> /dev/null; then
    echo "ERROR: CMake not found! Please install CMake."
    exit 1
fi

echo "Compiling whisper.cpp..."
cd temp/whisper.cpp-master

# Remove old build directory if exists (to avoid Windows/Linux path conflicts)
if [ -d "build" ]; then
    echo "Removing old build directory..."
    rm -rf build
fi

mkdir build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
if [ $? -ne 0 ]; then
    echo "CMake configuration failed!"
    cd "$SCRIPT_DIR"
    exit 1
fi

cmake --build . --config Release -j$(nproc)
if [ $? -ne 0 ]; then
    echo "Build failed!"
    cd "$SCRIPT_DIR"
    exit 1
fi

cd "$SCRIPT_DIR"

echo "Copying whisper files to Release_Linux/Release..."
cp "temp/whisper.cpp-master/build/bin/whisper-cli" "Release_Linux/Release/" 2>/dev/null || \
cp "temp/whisper.cpp-master/build/whisper-cli" "Release_Linux/Release/" 2>/dev/null || \
cp "temp/whisper.cpp-master/whisper-cli" "Release_Linux/Release/" 2>/dev/null || {
    echo "ERROR: Could not find whisper-cli binary"
    exit 1
}

# Copy libraries if any
cp temp/whisper.cpp-master/build/*.so "Release_Linux/Release/" 2>/dev/null || true

# ========================================
# Step 6: Download Whisper Model
# ========================================
echo ""
echo "========================================"
echo "Step 6/6: Downloading Whisper Model"
echo "========================================"
echo ""

mkdir -p Release_Linux/Release/models

# if [ ! -f "Release_Linux/Release/models/ggml-tiny.bin" ]; then
    # echo "Downloading ggml-tiny.bin (smallest model, ~75MB)..."
    # wget -O Release_Linux/Release/models/ggml-tiny.bin \
        # "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin"
    
    # if [ $? -ne 0 ]; then
        # echo "Failed to download model!"
        # echo "You can manually download models from:"
        # echo "https://huggingface.co/ggerganov/whisper.cpp/tree/main"
        # echo "Place them in Release_Linux/Release/models/ folder"
    # fi
# else
    # echo "Model already exists, skipping download."
# fi

# ========================================
# Copy Python scripts
# ========================================
echo ""
echo "Copying Python scripts..."
cp "web_app.py" "Release_Linux/Release/"
cp "video_subtitle_editor.py" "Release_Linux/Release/"

# ========================================
# Create start.sh
# ========================================
echo "Creating start.sh..."
cat > "Release_Linux/start.sh" << 'EOF'
#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if Release subdirectory exists
if [ ! -d "Release" ]; then
    echo "Error: Release directory not found!"
    echo "Please run build_linux.sh first."
    read -p "Press Enter to exit..."
    exit 1
fi

# Switch to Release directory
cd Release

echo "Starting Video Subtitle Tool..."
echo ""
echo "========================================"
echo "The web interface will open automatically"
echo "========================================"
echo ""

# Activate virtual environment
source venv/bin/activate

# Start the web server in background
echo "Starting server..."
python web_app.py &
SERVER_PID=$!

# Wait a moment for the server to start
sleep 3

# Open the web interface in default browser
if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:8000
elif command -v gnome-open &> /dev/null; then
    gnome-open http://localhost:8000
elif command -v kde-open &> /dev/null; then
    kde-open http://localhost:8000
else
    echo "Please open http://localhost:8000 in your browser"
fi

echo ""
echo "Server is running. Press Ctrl+C to stop."
echo ""

# Wait for server
wait $SERVER_PID
EOF

chmod +x "Release_Linux/start.sh"
chmod 1777 Release_Linux/Release
chmod 1777 Release_Linux/Release/models

# ========================================
# Build Complete
# ========================================
echo ""
echo "========================================"
echo "Build Complete!"
echo "========================================"
echo ""
echo "You can now run: Release_Linux/start.sh"
echo ""
echo "The web interface will be available at:"
echo "  http://localhost:8000"
echo ""
echo "Optional: Download larger models for better accuracy:"
echo "  - ggml-small.bin (~466MB)"
echo "  - ggml-base.bin (~142MB)"
echo "  - ggml-medium.bin (~1.5GB)"
echo ""
echo "Download from: https://huggingface.co/ggerganov/whisper.cpp/tree/main"
echo "Place in: Release_Linux/Release/models/"
echo ""
