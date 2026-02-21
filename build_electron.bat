@echo off
echo === GEMintern Electron Build ===
echo.

REM 1. Frontend build
echo [1/3] Building frontend...
cd /d "%~dp0frontend"
call npm run build
if errorlevel 1 (
    echo Frontend build failed!
    pause
    exit /b 1
)

REM 2. Electron dist
echo [2/3] Building Electron app...
cd /d "%~dp0electron"
call npm run dist
if errorlevel 1 (
    echo Electron build failed!
    pause
    exit /b 1
)

echo.
echo [3/3] Done!
echo Output: %~dp0dist_electron\
pause
