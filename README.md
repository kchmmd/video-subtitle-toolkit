# Video Subtitle Tool

A simple web-based tool for automatically generating subtitles for videos using OpenAI's Whisper.

## Features

- Web interface for easy use
- Automatic speech recognition (Chinese)
- Traditional to Simplified Chinese conversion
- Subtitle rendering and burning
- One-click generation or step-by-step mode
- Model selection with download hints
- LAN access support (access from other devices on the same network)

## Mainwindow

!\[mainwindow]\(mainwindow\.png null)
!\[mainwindow\_1]\(mainwindow\_1.png null)

## Release

通过网盘分享的文件：video-subtitle-toolkit
链接: <https://pan.baidu.com/s/1IEZzU3UIy1SftBc4kREzEg?pwd=jrp9> 提取码: jrp9
\--来自百度网盘超级会员v5的分享

## Quick Start

### macOS

#### Automatic Build (Recommended)

1. **Run build script** (first time only):

   **Option A: Double-click to run (Recommended)**
   - Double-click `build_mac.command` in Finder
   - This will automatically download and set up everything
     **Option B: Run from terminal**
   ```bash
   ./build_mac.command
   ```
   This will automatically download and set up:
   - Python 3.11 (via Homebrew)
   - FFmpeg (via Homebrew)
   - whisper.cpp (compiled from source with Metal acceleration on Apple Silicon)
   - Whisper model (ggml-tiny.bin)
   - Python dependencies (opencv-python, Pillow, numpy)
   - Start script with auto-browser-open
2. **Start the application**:

   **Option A: Double-click to run (Recommended)**
   - Double-click `Release_Mac/start.command` in Finder
   - The browser will open automatically at <http://localhost:8000>
     **Option B: Run from terminal**
   ```bash
   ./Release_Mac/start.command
   ```
3. **Access from other devices** (same LAN):
   - Find your Mac's IP address: `ifconfig | grep inet`
   - Other devices can access: `http://<your-ip>:8000`

### Requirements (macOS)

- macOS 10.14 or later
- Homebrew (will be installed automatically if not present)
- CMake (will be installed via Homebrew)
- Internet connection (for downloading dependencies)

### Linux

#### Automatic Build (Recommended)

1. **Run build script** (first time only):
   ```bash
   chmod +x build_linux.sh
   ./build_linux.sh
   ```
   This will automatically download and set up:
   - Python 3.x (via package manager)
   - FFmpeg (via package manager)
   - whisper.cpp (compiled from source)
   - Python dependencies (opencv-python, Pillow, numpy)
   - Start script with auto-browser-open
2. **Start the application**:
   ```bash
   ./Release_Linux/start.sh
   ```
   The browser will open automatically at <http://localhost:8000>
3. **Access from other devices** (same LAN):
   - Find your PC's IP address: `ip addr` or `ifconfig`
   - Other devices can access: `http://<your-ip>:8000`

### Requirements (Linux)

- Ubuntu 18.04+, Debian 10+, CentOS 7+, Fedora 30+, Arch Linux, or Alpine Linux
- Python 3.8+ with pip and venv support
- CMake 3.10+
- GCC/G++
- Internet connection (for downloading dependencies)

### Windows

#### Option 1: Automatic Build (Recommended)

1. **Run build script** (first time only):
   ```bash
   build_windows.bat
   ```
   This will automatically download and set up:
   - Embedded Python 3.10
   - FFmpeg
   - whisper.cpp (compiled from source)
   - Whisper model (ggml-tiny.bin)
   - Python dependencies (opencv-python, Pillow, numpy)
   - Start script with auto-browser-open
2. **Start the application**:
   ```bash
   Release_Windows\start.bat
   ```
   The browser will open automatically at <http://localhost:8000>
3. **Access from other devices** (same LAN):
   - Find your PC's IP address: `ipconfig`
   - Other devices can access: `http://<your-ip>:8000`

#### Option 2: Build and Package as MSI Installer

1. **Build the application**:
   ```bash
   build_windows.bat
   ```
2. **Package as MSI installer**:
   ```bash
   package_windows.bat
   ```
   This will:
   - Download WiX Toolset (if not installed)
   - Package Release\_Windows into VideoSubtitleTool.msi
3. **Distribute the MSI**:
   - Silent install: `msiexec /i VideoSubtitleTool.msi /qn`
   - Custom path: `msiexec /i VideoSubtitleTool.msi INSTALLFOLDER="D:\Tools"`
   - Interactive install: Double-click `VideoSubtitleTool.msi`

### Requirements (Windows)

- Windows 10 or later
- CMake (for compiling whisper.cpp)
- Visual Studio 2022 or Build Tools (for compiling whisper.cpp)
- Internet connection (for downloading dependencies)

## Project Structure

```
video-subtitle-toolkit/
├── build_linux.sh             # Linux build script (downloads & compiles everything)
├── build_mac.command          # macOS build script (downloads & compiles everything)
├── build_windows.bat          # Windows build script (downloads & compiles everything)
├── package_windows.bat        # Windows packaging script (creates MSI installer)
├── Product_VideoSubtitleTool.wxs  # WiX configuration for MSI packaging
├── README.md                  # This file
├── requirements.txt           # Python dependencies reference
├── web_app.py                # Web server with model selection UI
└── video_subtitle_editor.py  # Core processing logic
```

**Generated directories after build:**

- `Release_Linux/` - Linux runtime files (created by build\_linux.sh)
- `Release_Mac/` - macOS runtime files (created by build\_mac.command)
- `Release_Windows/` - Windows runtime files (created by build\_windows.bat)
- `temp/` - Temporary files during build

## Build Scripts

### build\_linux.sh

Automatically downloads and compiles all dependencies on Linux:

| Step | Action                                                   | Output                              |
| ---- | -------------------------------------------------------- | ----------------------------------- |
| 1    | Install system dependencies (Python, FFmpeg, CMake, GCC) | System packages                     |
| 2    | Create Python virtual environment                        | `Release_Linux/Release/venv/`       |
| 3    | Setup FFmpeg symlinks                                    | `Release_Linux/Release/ffmpeg/`     |
| 4    | Download & Compile whisper.cpp                           | `Release_Linux/Release/whisper-cli` |
| 5    | Copy Python scripts & Create start.sh                    | `Release_Linux/start.sh`            |

**Features:**

- Auto-detects Linux distribution (Ubuntu, Debian, CentOS, Fedora, Arch, Alpine, Kylin)
- Supports Ubuntu 18.04+, Debian 10+, CentOS 7+, Fedora 30+, Arch Linux, Alpine Linux
- Uses Tsinghua PyPI mirror for faster downloads in China
- Handles corrupted downloads (auto-retry)
- Checks if already built (skips if `start.sh` exists)
- Auto-opens browser when started

**Supported Distributions:**

- Ubuntu / Debian / Kylin
- CentOS / RHEL / Fedora / Rocky / AlmaLinux
- Arch Linux / Manjaro
- Alpine Linux

### build\_mac.command

Automatically downloads and compiles all dependencies on macOS:

| Step | Action                                        | Output                             |
| ---- | --------------------------------------------- | ---------------------------------- |
| 1    | Check/Install Homebrew, CMake, Python, FFmpeg | System dependencies                |
| 2    | Create Python virtual environment             | `Release_Mac/Release/python/venv/` |
| 3    | Copy FFmpeg binaries                          | `Release_Mac/Release/ffmpeg/`      |
| 4    | Download & Compile whisper.cpp                | `Release_Mac/Release/whisper-cli`  |
| 5    | Download ggml-tiny.bin model                  | `Release_Mac/Release/models/`      |
| 6    | Copy Python scripts & Create start.command    | `Release_Mac/start.command`        |

**Features:**

- Supports both Apple Silicon (M1/M2/M3) and Intel Macs
- Automatically enables Metal acceleration on Apple Silicon
- Checks if already built (skips if `start.command` exists)
- Auto-opens browser when started
- Double-click to run (no terminal needed)

### build\_windows.bat

Automatically downloads and compiles all dependencies:

| Step | Action                                 | Output                                    |
| ---- | -------------------------------------- | ----------------------------------------- |
| 1    | Download Embedded Python 3.10          | `Release_Windows/Release/python/`         |
| 2    | Download FFmpeg                        | `Release_Windows/Release/ffmpeg/`         |
| 3    | Download & Compile whisper.cpp         | `Release_Windows/Release/whisper-cli.exe` |
| 4    | Download ggml-tiny.bin model           | `Release_Windows/Release/models/`         |
| 5    | Copy Python scripts & Create start.bat | `Release_Windows/start.bat`               |

**Features:**

- Checks if already built (skips if `start.bat` exists)
- Handles path spaces correctly
- Auto-opens browser when started

### package\_windows.bat

Creates an MSI installer for distribution:

| Step | Action                                      |
| ---- | ------------------------------------------- |
| 1    | Check/Download WiX Toolset 3.14.1           |
| 2    | Copy Release\_Windows files to temp/package |
| 3    | Harvest files with `heat`                   |
| 4    | Compile with `candle`                       |
| 5    | Link MSI with `light`                       |

**Output:** `VideoSubtitleTool.msi`

**MSI Features:**

- Custom installation path
- Desktop shortcut
- Start menu shortcut
- Auto-launch after install
- Auto-terminate on uninstall/upgrade

## Manual Setup

### Linux Manual Setup

If the automatic setup fails, you can manually:

1. **Install Dependencies**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install -y python3 python3-pip python3-venv ffmpeg cmake build-essential git wget

   # CentOS/RHEL/Fedora
   sudo dnf install -y python3 python3-pip ffmpeg cmake gcc gcc-c++ make git wget
   # or: sudo yum install -y python3 python3-pip ffmpeg cmake gcc gcc-c++ make git wget

   # Arch Linux
   sudo pacman -Sy --noconfirm python python-pip ffmpeg cmake base-devel git wget
   ```
2. **Create Python Virtual Environment**:
   ```bash
   mkdir -p Release_Linux/Release
   python3 -m venv Release_Linux/Release/venv
   source Release_Linux/Release/venv/bin/activate
   pip install opencv-python Pillow numpy
   ```
3. **Setup FFmpeg**:
   ```bash
   mkdir -p Release_Linux/Release/ffmpeg
   ln -sf $(which ffmpeg) Release_Linux/Release/ffmpeg/ffmpeg
   ln -sf $(which ffprobe) Release_Linux/Release/ffmpeg/ffprobe
   ```
4. **Compile whisper.cpp**:
   ```bash
   git clone https://github.com/ggerganov/whisper.cpp.git temp/whisper.cpp-master
   cd temp/whisper.cpp-master
   mkdir build && cd build
   cmake .. -DCMAKE_BUILD_TYPE=Release
   cmake --build . --config Release -j$(nproc)
   cd ../..
   cp temp/whisper.cpp-master/build/bin/whisper-cli Release_Linux/Release/
   ```
5. **Create start.sh**:
   ```bash
   cat > Release_Linux/start.sh << 'EOF'
   #!/bin/bash
   cd "$(dirname "$0")"
   cd Release
   source venv/bin/activate
   echo ""
   echo "========================================"
   echo "The web interface will open automatically"
   echo "========================================"
   echo ""
   echo "Starting server..."
   python web_app.py &
   sleep 3
   xdg-open http://localhost:8000
   wait
   EOF
   chmod +x Release_Linux/start.sh
   ```
6. **Download Models**:
   - <https://huggingface.co/ggerganov/whisper.cpp/tree/main>
   - Place `.bin` files in `Release_Linux/Release/models/`

### macOS Manual Setup

If the automatic setup fails, you can manually:

1. **Install Dependencies**:
   ```bash
   brew install python@3.11 ffmpeg cmake
   ```
2. **Create Python Virtual Environment**:
   ```bash
   mkdir -p Release_Mac/Release/python
   python3.11 -m venv Release_Mac/Release/python/venv
   source Release_Mac/Release/python/venv/bin/activate
   pip install opencv-python Pillow numpy
   ```
3. **Compile whisper.cpp**:
   ```bash
   git clone https://github.com/ggerganov/whisper.cpp.git temp/whisper.cpp-master
   cd temp/whisper.cpp-master
   mkdir build && cd build

   # For Apple Silicon:
   cmake .. -DCMAKE_BUILD_TYPE=Release -DWHISPER_METAL=ON

   # For Intel:
   cmake .. -DCMAKE_BUILD_TYPE=Release

   cmake --build . --config Release -j$(sysctl -n hw.ncpu)
   ```
   - Copy `build/bin/whisper-cli` and `.dylib` files to `Release_Mac/Release/`
4. **Create start.command**:
   ```bash
   cat > Release_Mac/start.command << 'EOF'
   #!/bin/bash
   cd "$(dirname "$0")"
   export PATH="$(pwd)/Release/ffmpeg:$PATH"
   source Release/python/venv/bin/activate
   echo ""
   echo "========================================"
   echo "The web interface will open automatically"
   echo "========================================"
   echo ""
   echo "Starting server..."
   python Release/web_app.py &
   sleep 2
   open http://localhost:8000
   wait
   EOF
   chmod +x Release_Mac/start.command
   ```
5. **Download Models**:
   - <https://huggingface.co/ggerganov/whisper.cpp/tree/main>
   - Place `.bin` files in `Release_Mac/Release/models/`

### Windows Manual Setup

If the automatic setup fails, you can manually:

1. **Download Embedded Python**:
   - <https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip>
   - Extract to `Release_Windows/Release/python/`
2. **Download FFmpeg**:
   - <https://www.gyan.dev/ffmpeg/builds/>
   - Extract `bin/` folder to `Release_Windows/Release/ffmpeg/`
3. **Compile whisper.cpp**:
   ```bash
   git clone https://github.com/ggerganov/whisper.cpp.git
   cd whisper.cpp
   mkdir build && cd build
   cmake .. -DCMAKE_BUILD_TYPE=Release
   cmake --build . --config Release
   ```
   - Copy `bin/Release/whisper-cli.exe` and DLLs to `Release_Windows/Release/`
4. **Download Models**:
   - <https://huggingface.co/ggerganov/whisper.cpp/tree/main>
   - Place `.bin` files in `Release_Windows/Release/models/`

## Usage

1. Open <http://localhost:8000> in your browser
2. Select a Whisper model (click ℹ️ for download hints)
3. Upload a video file
4. Select processing mode:
   - **One-click**: Extract audio → Recognize → Burn subtitles
   - **Step-by-step**: Generate SRT first, edit if needed, then burn
5. Download the result

## Models

| Model           | Size   | Accuracy | Speed   |
| --------------- | ------ | -------- | ------- |
| ggml-tiny.bin   | 75 MB  | Basic    | Fastest |
| ggml-base.bin   | 142 MB | Good     | Fast    |
| ggml-small.bin  | 466 MB | Better   | Medium  |
| ggml-medium.bin | 1.5 GB | Best     | Slow    |

Download from: <https://huggingface.co/ggerganov/whisper.cpp/tree/main>

**Linux:** Place in `Release_Linux/Release/models/`

**macOS:** Place in `Release_Mac/Release/models/`

**Windows:** Place in `Release_Windows\Release\models\`

## Network Access

The server binds to all network interfaces by default:

- Local: <http://localhost:8000>
- LAN: http\://<your-ip>:8000

**Firewall:** Allow Python through Windows Firewall for LAN access.

## License

MIT License
