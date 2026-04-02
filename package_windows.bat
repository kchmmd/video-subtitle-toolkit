@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo Video Subtitle Tool - Windows Package Script
echo ========================================
echo.

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

set "ProjectName=VideoSubtitleTool"
set "WixVersion=3.14.1"
set "WixUrl=https://github.com/wixtoolset/wix3/releases/download/wix3%WixVersion%/wix3%WixVersion%-binaries.zip"

REM Check if Release_Windows exists
if not exist "Release_Windows\start.bat" (
    echo.
    echo ========================================
    echo ERROR: Release_Windows not found!
    echo ========================================
    echo Please run build_windows.bat first to build the application.
    echo.
    pause
    exit /b 1
)

echo This script will:
echo   1. Download and setup WiX Toolset (if not found)
echo   2. Package Release_Windows into MSI installer
echo.
echo Starting in 3 seconds...
timeout /t 3 /nobreak >nul

REM Create temp directory
if not exist "temp" mkdir temp

REM ========================================
REM Step 1: Check/Download WiX Toolset
REM ========================================
echo.
echo ========================================
echo Step 1/3: Checking WiX Toolset
echo ========================================
echo.

set "WixPath="

REM Check if WiX is already in PATH
where candle >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo WiX Toolset found in PATH.
    goto wix_check_done
)

REM Check if WiX is in temp directory
if exist "temp\wix\candle.exe" (
    echo WiX Toolset found in temp directory.
    set "WixPath=%ROOT_DIR%temp\wix"
    set "PATH=%WixPath%;%PATH%"
    goto wix_check_done
)

REM Download WiX Toolset
echo WiX Toolset not found. Downloading...
echo Download URL: %WixUrl%
echo.

if not exist "temp\wix-binaries.zip" (
    powershell -Command "Invoke-WebRequest -Uri '%WixUrl%' -OutFile 'temp\wix-binaries.zip' -UseBasicParsing"
    if errorlevel 1 (
        echo Failed to download WiX Toolset!
        echo Please check your internet connection.
        pause
        exit /b 1
    )
)

echo Extracting WiX Toolset...
powershell -Command "Expand-Archive -Path 'temp\wix-binaries.zip' -DestinationPath 'temp\wix' -Force"
if errorlevel 1 (
    echo Failed to extract WiX Toolset!
    pause
    exit /b 1
)

set "WixPath=%ROOT_DIR%temp\wix"
set "PATH=%WixPath%;%PATH%"
echo WiX Toolset setup complete.

:wix_check_done

REM Verify WiX tools
echo.
echo Verifying WiX tools...
where heat >nul 2>&1
if errorlevel 1 (
    echo ERROR: heat not found!
    pause
    exit /b 1
)
echo   [OK] heat

where candle >nul 2>&1
if errorlevel 1 (
    echo ERROR: candle not found!
    pause
    exit /b 1
)
echo   [OK] candle

where light >nul 2>&1
if errorlevel 1 (
    echo ERROR: light not found!
    pause
    exit /b 1
)
echo   [OK] light

REM ========================================
REM Step 2: Prepare files for packaging
REM ========================================
echo.
echo ========================================
echo Step 2/3: Preparing files
echo ========================================
echo.

REM Create package directory
if exist "temp\package" rmdir /s /q "temp\package"
mkdir "temp\package"

REM Copy Release_Windows contents to package directory
echo Copying Release_Windows files...
xcopy /E /I /Y "Release_Windows\*" "temp\package\" >nul
if errorlevel 1 (
    echo ERROR: Failed to copy files!
    pause
    exit /b 1
)

echo Files prepared successfully.

REM ========================================
REM Step 3: Create MSI package
REM ========================================
echo.
echo ========================================
echo Step 3/3: Creating MSI package
echo ========================================
echo.

REM Check if Product.wxs exists
if not exist "Product_%ProjectName%.wxs" (
    echo.
    echo ========================================
    echo ERROR: Product_%ProjectName%.wxs not found!
    echo ========================================
    echo Please ensure Product_%ProjectName%.wxs exists in the project root.
    echo.
    pause
    exit /b 1
)

REM Copy WiX config to temp directory
copy /Y "Product_%ProjectName%.wxs" "temp\Product.wxs" >nul

cd temp

set WXSPRODUCT=Product.wxs
set MSIOUTPUT=%ProjectName%.msi

REM Remove old MSI
if exist "..\%MSIOUTPUT%" del "..\%MSIOUTPUT%"

echo Harvesting application files...
heat dir package -cg AppFiles -dr INSTALLFOLDER -gg -sfrag -sreg -suid -srd -var var.AppSource -out AppFiles.wxs
if errorlevel 1 (
    echo.
    echo ========================================
    echo ERROR: heat command failed!
    echo ========================================
    echo.
    cd ..
    pause
    exit /b 1
)

echo Compiling WiX files...
candle -dAppSource=package %WXSPRODUCT% AppFiles.wxs -ext WixUtilExtension
if %ERRORLEVEL% neq 0 (
    echo.
    echo ========================================
    echo ERROR: candle command failed!
    echo ========================================
    echo.
    cd ..
    pause
    exit /b 1
)

echo Linking MSI package...
light -out "..\%MSIOUTPUT%" Product.wixobj AppFiles.wixobj -ext WixUIExtension -ext WixUtilExtension
if %ERRORLEVEL% neq 0 (
    echo.
    echo ========================================
    echo ERROR: light command failed!
    echo ========================================
    echo.
    cd ..
    pause
    exit /b 1
)

cd ..

echo.
echo ========================================
echo Packaging Complete!
echo ========================================
echo.
echo MSI package: %MSIOUTPUT%
echo.
echo Installation features:
echo   - Silent install: msiexec /i %MSIOUTPUT% /qn
echo   - Custom install path: msiexec /i %MSIOUTPUT% INSTALLFOLDER="C:\YourPath"
echo.

pause
