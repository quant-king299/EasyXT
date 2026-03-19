@echo off
chcp 65001 >nul
title 自适应网格策略测试

echo.
echo ========================================
echo    自适应网格策略测试
echo ========================================
echo.

cd /d "%~dp0"

echo 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python
    pause
    exit /b 1
)

echo [OK] Python环境正常
echo.

echo 检查配置文件...
if not exist "adaptive_grid_config.json" (
    echo [警告] 配置文件不存在，将使用默认配置
)

echo [OK] 准备启动测试脚本
echo.
echo ========================================
echo.

python run_adaptive_grid.py

echo.
echo ========================================
echo 测试已结束
echo ========================================
pause
