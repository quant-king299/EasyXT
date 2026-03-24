@echo off
chcp 65001 >nul 2>&1
cls

echo.
echo ================================================================
echo    Simple Small Cap Strategy - Live Trading
echo ================================================================
echo.

cd /d "%~dp0"

echo [INFO] Current Directory: %CD%
echo.

echo [INFO] Checking Python...
python --version
if errorlevel 1 (
    echo [ERROR] Python is not installed
    pause
    exit /b 1
)
echo.

echo [INFO] Starting Strategy...
echo ================================================================
echo.

python main.py

echo.
echo ================================================================
echo    Program Exit
echo ================================================================
echo.

pause
