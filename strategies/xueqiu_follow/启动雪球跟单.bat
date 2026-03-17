@echo off
setlocal

REM 统一控制台编码为 UTF-8，避免中文乱码（需要使用支持的字体）
chcp 65001 >nul 2>nul

REM 设置 Python 输出编码为 UTF-8（便于中文日志显示）
set PYTHONIOENCODING=utf-8

REM 切换到脚本所在目录（本脚本已在 strategies\xueqiu_follow 下）
pushd "%~dp0"

echo ==============================================
echo Xueqiu Follow Trading System (EasyXT Version)
echo Script Location: %~dp0
echo Working Directory: %cd%
echo ==============================================

REM 检查 Python 是否在 PATH 中
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python or add it to PATH.
    echo Example: Install Python 3.10+ and check "Add Python to PATH"
    pause
    exit /b 1
)

REM 启动主程序（显式指定 UTF-8 源码编码与封闭路径）
python "%cd%\start_xueqiu_follow_easyxt.py"

REM 返回原目录并根据退出状态提示
set ERR=%ERRORLEVEL%
popd
if %ERR% NEQ 0 (
    echo.
    echo [FAILED] Program error (code %ERR%), press any key to exit...
    pause
    exit /b %ERR%
) else (
    echo.
    echo [DONE] Program completed, press any key to exit...
    pause
)

endlocal