@echo off
chcp 65001 >nul
title 101因子分析平台 - 清理缓存并启动

echo ================================================================================
echo                    清理缓存并重新启动 101因子分析平台
echo ================================================================================
echo.

cd /d "%~dp0"

echo [1/3] 正在清理 Streamlit 缓存...
if exist ".streamlit" (
    rmdir /s /q .streamlit
    echo     ✓ 已删除 .streamlit 目录
) else (
    echo     - .streamlit 目录不存在
)

echo.
echo [2/3] 正在清理 Python 缓存...
if exist "__pycache__" rmdir /s /q __pycache__
if exist "src\__pycache__" rmdir /s /q src\__pycache__
if exist "src\workflow\__pycache__" rmdir /s /q src\workflow\__pycache__
if exist "src\easyxt_adapter\__pycache__" rmdir /s /q src\easyxt_adapter\__pycache__
echo     ✓ Python 缓存已清理

echo.
echo [3/3] 正在启动平台...
echo.

python 启动增强版.py

pause
