@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo Video Subtitle Tool - Windows Build Script
echo ========================================
echo.

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

REM Check if already built
if exist "Release_Windows\start.bat" (
    echo Build already completed!
    echo Run Release_Windows\start.bat to start the application.
    echo Build process completed.
    exit /b 0
)

echo This script will download and build:
echo   - Embedded Python 3.10
echo   - FFmpeg
echo   - whisper.cpp (and compile it)
echo   - Whisper models
echo.
echo Starting in 3 seconds...
timeout /t 3 /nobreak >nul

REM Create directories
if not exist "temp" mkdir temp
if not exist "Release_Windows" mkdir Release_Windows
if not exist "Release_Windows\Release" mkdir Release_Windows\Release

echo.
echo ========================================
echo Step 1/5: Downloading Embedded Python
echo ========================================
echo.

if not exist "temp\python-embed.zip" (
    echo Downloading Python 3.10.11...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip' -OutFile 'temp\python-embed.zip' -UseBasicParsing"
    if errorlevel 1 (
        echo Failed to download Python!
        pause
        exit /b 1
    )
)

echo Extracting Python...
if not exist "Release_Windows\Release\python" (
    powershell -Command "Expand-Archive -Path 'temp\python-embed.zip' -DestinationPath 'Release_Windows\Release\python' -Force"
)

REM Configure Python to use site-packages
(
echo python310.zip
echo .
echo Lib
echo Lib/site-packages
echo.
echo import site
) > Release_Windows\Release\python\python310._pth

echo Installing pip...
if not exist "temp\get-pip.py" (
    powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile 'temp\get-pip.py' -UseBasicParsing"
)
"Release_Windows\Release\python\python.exe" temp\get-pip.py --no-warn-script-location

echo Installing Python packages...
"Release_Windows\Release\python\python.exe" -m pip install opencv-python Pillow numpy -t Release_Windows\Release\python\Lib\site-packages --no-warn-script-location

echo.
echo ========================================
echo Step 2/5: Downloading FFmpeg
echo ========================================
echo.

if not exist "temp\ffmpeg.zip" (
    echo Downloading FFmpeg...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile 'temp\ffmpeg.zip' -UseBasicParsing"
    if errorlevel 1 (
        echo Failed to download FFmpeg!
        pause
        exit /b 1
    )
)

echo Extracting FFmpeg...
powershell -Command "Expand-Archive -Path 'temp\ffmpeg.zip' -DestinationPath 'temp\ffmpeg' -Force"

REM Move ffmpeg bin folder
for /d %%D in (temp\ffmpeg\ffmpeg-*) do (
    if exist "%%D\bin" (
        move "%%D\bin" "Release_Windows\Release\ffmpeg"
    )
)

echo.
echo ========================================
echo Step 3/5: Downloading whisper.cpp
echo ========================================
echo.

if not exist "temp\whisper.zip" (
    echo Downloading whisper.cpp source code...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/ggerganov/whisper.cpp/archive/refs/heads/master.zip' -OutFile 'temp\whisper.zip' -UseBasicParsing"
    if errorlevel 1 (
        echo Failed to download whisper.cpp!
        pause
        exit /b 1
    )
)

echo Extracting whisper.cpp...
if not exist "temp\whisper.cpp-master" (
    powershell -Command "Expand-Archive -Path 'temp\whisper.zip' -DestinationPath 'temp' -Force"
)

echo.
echo ========================================
echo Step 4/5: Compiling whisper.cpp
echo ========================================
echo.

echo Checking for CMake...
where cmake >nul 2>&1
if errorlevel 1 (
    echo CMake not found! Please install CMake from https://cmake.org/download/
    pause
    exit /b 1
)

echo Compiling whisper.cpp...
if not exist "temp\whisper.cpp-master\build" mkdir temp\whisper.cpp-master\build

cd temp\whisper.cpp-master\build
cmake .. -DCMAKE_BUILD_TYPE=Release
if errorlevel 1 (
    echo CMake configuration failed!
    cd ..\..\..
    echo Build process completed.
    exit /b 1
)

cmake --build . --config Release
if errorlevel 1 (
    echo Build failed!
    cd ..\..\..
    echo Build process completed.
    exit /b 1
)

cd ..\..\..

echo Copying whisper files to Release_Windows\Release...
copy "temp\whisper.cpp-master\build\bin\Release\whisper-cli.exe" "Release_Windows\Release\"
copy "temp\whisper.cpp-master\build\bin\Release\*.dll" "Release_Windows\Release\"

echo.
echo ========================================
echo Step 5/5: Downloading Whisper Model
echo ========================================
echo.

if not exist "Release_Windows\Release\models" mkdir Release_Windows\Release\models

REM echo Downloading ggml-tiny.bin (smallest model, ~75MB)...
REM powershell -Command "Invoke-WebRequest -Uri 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin' -OutFile 'Release_Windows\Release\models\ggml-tiny.bin' -UseBasicParsing"

REM if errorlevel 1 (
    REM echo Failed to download model!
    REM echo You can manually download models from:
    REM echo https://huggingface.co/ggerganov/whisper.cpp/tree/main
    REM echo Place them in Release_Windows\Release\models\ folder
REM )

echo Copying Python scripts...
copy "web_app.py" "Release_Windows\Release\"
copy "video_subtitle_editor.py" "Release_Windows\Release\"

echo Creating start.bat...
(
echo @echo off
echo chcp 65001 ^>nul
echo setlocal enabledelayedexpansion
echo.
echo REM Get the directory where this script is located
echo set "SCRIPT_DIR=%%~dp0"
echo cd /d "%%SCRIPT_DIR%%"
echo.
echo REM Check if Release subdirectory exists
echo if not exist "Release" ^(
echo     echo Error: Release directory not found!
echo     echo Please run build_windows.bat first.
echo     pause
echo     exit /b 1
echo ^)
echo.
echo REM Switch to Release directory
echo cd Release
echo.
echo echo Starting Video Subtitle Tool...
echo echo.
echo echo ========================================
echo echo The web interface will open automatically
echo echo ========================================
echo echo.
echo.
echo REM Start the web server in background
echo start /B "Video Subtitle Tool" "python\python.exe" web_app.py
echo.
echo REM Wait a moment for the server to start
echo timeout /t 3 /nobreak ^>nul
echo.
echo REM Open the web interface in default browser
echo start http://localhost:8000
echo.
echo echo Press any key to stop the server...
echo pause ^>nul
echo.
echo echo Stopping server...
echo taskkill /f /im python.exe ^>nul 2^>^&1
echo echo Server stopped.
) > "Release_Windows\start.bat"

echo.
echo ========================================
echo Build Complete!
echo ========================================
echo.
echo You can now run: Release_Windows\start.bat
echo.
echo Optional: Download larger models for better accuracy:
echo   - ggml-small.bin (~466MB)
echo   - ggml-base.bin (~142MB)
echo   - ggml-medium.bin (~1.5GB)
echo.
echo Download from: https://huggingface.co/ggerganov/whisper.cpp/tree/main
echo Place in: Release_Windows\Release\models\
echo.

echo Build process completed.
