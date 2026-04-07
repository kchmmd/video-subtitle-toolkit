@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo Video Subtitle Tool - Windows Build Script
echo ========================================
echo.

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

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

REM 检查 Release 目录是否已有 Python，如果有则跳过下载和安装
if exist "Release_Windows\Release\python\python.exe" (
    echo Python already exists in Release directory, skipping download and installation.
    echo If you need to add new packages, please delete Release_Windows\Release\python directory manually.
) else (
    REM 删除可能损坏的 Python zip 文件，确保重新下载
    if exist "temp\python-embed.zip" (
        echo Removing potentially corrupted Python zip file...
        del "temp\python-embed.zip"
    )
    
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
    REM 先清理目标目录
    if exist "Release_Windows\Release\python" (
        rd /s /q "Release_Windows\Release\python"
    )
    md "Release_Windows\Release\python"
    
    REM 解压 Python
    powershell -Command "Expand-Archive -Path 'temp\python-embed.zip' -DestinationPath 'Release_Windows\Release\python' -Force"
    if errorlevel 1 (
        echo Failed to extract Python!
        pause
        exit /b 1
    )
    
    REM 验证 Python 是否存在
    if not exist "Release_Windows\Release\python\python.exe" (
        echo Python executable not found!
        pause
        exit /b 1
    )
    echo Python extracted successfully!
    
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
)

echo.
echo ========================================
echo Step 2/5: Downloading FFmpeg
echo ========================================
echo.

REM 检查 Release 目录是否已有 FFmpeg，如果有则跳过下载
if exist "Release_Windows\Release\ffmpeg\ffmpeg.exe" (
    echo FFmpeg already exists in Release directory, skipping download.
) else (
    REM 删除可能损坏的 FFmpeg zip 文件，确保重新下载
    if exist "temp\ffmpeg.zip" (
        echo Removing potentially corrupted FFmpeg zip file...
        del "temp\ffmpeg.zip"
    )
    
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
    REM 先清理目标目录
    if exist "temp\ffmpeg" (
        rd /s /q "temp\ffmpeg"
    )
    md "temp\ffmpeg"
    powershell -Command "Expand-Archive -Path 'temp\ffmpeg.zip' -DestinationPath 'temp\ffmpeg' -Force"
    if errorlevel 1 (
        echo Failed to extract FFmpeg!
        echo Removing corrupted zip file and trying again...
        del "temp\ffmpeg.zip"
        pause
        exit /b 1
    )
    
    REM Move ffmpeg bin folder
    for /d %%D in (temp\ffmpeg\ffmpeg-*) do (
        if exist "%%D\bin" (
            move "%%D\bin" "Release_Windows\Release\ffmpeg"
        )
    )
)

echo.
echo ========================================
echo Step 3/5: Downloading whisper.cpp
echo ========================================
echo.

REM 检查 temp 目录是否已有 whisper.cpp 源代码，如果有则跳过下载
if exist "temp\whisper.cpp-master" (
    echo whisper.cpp source code already exists in temp directory, skipping download.
) else (
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

REM 检查 CUDA 是否可用
where nvcc >nul 2>&1
if errorlevel 1 (
    echo CUDA not found, building without CUDA...
    cmake .. -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=OFF
    if errorlevel 1 (
        echo CMake configuration failed!
        cd ..\..\..
        echo Build process completed.
        exit /b 1
    )
) else (
    echo CUDA found, building with CUDA support...
    cmake .. -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON
    if errorlevel 1 (
        echo CUDA build failed, trying without CUDA...
        cmake .. -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=OFF
        if errorlevel 1 (
            echo CMake configuration failed!
            cd ..\..\..
            echo Build process completed.
            exit /b 1
        )
    )
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

echo Copying Python scripts...
copy "web_app.py" "Release_Windows\Release\"
copy "video_subtitle_editor.py" "Release_Windows\Release\"

echo Creating start.bat...
(
echo @echo off
echo chcp 65001 ^>nul
echo setlocal enabledelayedexpansion
echo.
echo echo ========================================
echo echo Video Subtitle Tool - GPU Detection
echo echo ========================================
echo echo.
echo.
echo REM Check for NVIDIA GPU using nvidia-smi
echo where nvidia-smi ^>nul 2^>^&1
echo if errorlevel 1 ^(
echo     echo No NVIDIA GPU detected.
echo     echo Starting application with CPU mode...
echo     echo.
echo     echo Starting Video Subtitle Tool...
echo     echo.
echo     goto :start_app
echo ^)
echo.
echo REM NVIDIA GPU found, check for CUDA Toolkit
echo where nvcc ^>nul 2^>^&1
echo if errorlevel 1 ^(
echo     echo NVIDIA GPU detected but CUDA Toolkit not found.
echo     echo.
echo     set /p install_cuda="Do you want to download and install CUDA Toolkit now? (Y/N): "
echo     if /i "!install_cuda!"=="Y" ^(
echo         echo.
echo         echo Downloading CUDA Toolkit installer...
echo         echo This may take a while depending on your internet connection.
echo         echo.
echo         REM Download CUDA Toolkit installer
echo         powershell -Command "Invoke-WebRequest -Uri 'https://developer.download.nvidia.com/compute/cuda/12.4.0/local_installers/cuda_12.4.0_551.61_windows.exe' -OutFile '%%TEMP%%\\cuda_installer.exe' -UseBasicParsing"
echo         if errorlevel 1 ^(
echo             echo Failed to download CUDA Toolkit!
echo             echo Please download manually from: https://developer.nvidia.com/cuda-downloads
echo         ^) else ^(
echo             echo.
echo             CUDA installer downloaded to: %%TEMP%%\\cuda_installer.exe
echo             echo.
echo             echo Starting CUDA Toolkit installation...
echo             echo Please follow the installation wizard.
echo             echo.
echo             pause
echo             start /wait "" "%%TEMP%%\\cuda_installer.exe"
echo             echo.
echo             echo CUDA Toolkit installation completed!
echo             echo Please re-run build_windows.bat to enable GPU support.
echo             echo.
echo             del "%%TEMP%%\\cuda_installer.exe"
echo         ^)
echo         goto :eof
echo     ^) else ^(
echo         echo.
echo         echo Starting application with CPU mode...
echo         echo.
echo     ^)
echo ^) else ^(
echo     echo NVIDIA GPU and CUDA Toolkit found!
echo     echo GPU acceleration is enabled.
echo     echo.
echo     echo Starting Video Subtitle Tool...
echo     echo.
echo ^)
echo.
echo :start_app
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
echo REM Enter the Release directory
echo cd Release
echo.
echo REM Start the web application
echo python\python.exe web_app.py
echo.
echo if errorlevel 1 ^(
echo     echo Application crashed!
echo     pause
echo ^)
) > Release_Windows\start.bat

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo.
echo You can now run the application:
echo   1. Navigate to Release_Windows folder
echo   2. Run start.bat
echo.
echo Download from: https://huggingface.co/ggerganov/whisper.cpp/tree/main
echo Place model files in Release_Windows\Release\models\ folder
echo.
