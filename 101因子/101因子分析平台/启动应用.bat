@echo off
chcp 65001 >nul
title 101因子分析平台

echo ================================================================
echo   101因子分析平台 - 启动
echo ================================================================
echo.

cd /d "%~dp0"

echo [1/2] 检查并停止旧进程...
taskkill /F /IM streamlit.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo [2/2] 启动应用...
echo.
echo   访问地址: http://localhost:8501
echo.
start "" streamlit run main_app.py

pause
