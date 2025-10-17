@echo off
setlocal

REM 设置 Python 输出编码为 UTF-8（便于中文日志显示）
set PYTHONIOENCODING=utf-8

REM 切换到雪球跟单策略目录
cd /d "%~dp0strategies\xueqiu_follow"

echo ==============================================
echo 启动雪球跟单系统（EasyXT 版本）
echo 项目目录：%~dp0
echo 运行目录：%cd%
echo ==============================================

REM 检查 Python 是否在 PATH 中
where python >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请安装 Python 或将其加入 PATH 环境变量。
    echo 例如：安装 Python 3.10+，并在安装时勾选 "Add Python to PATH"
    pause
    exit /b 1
)

REM 启动主程序
python start_xueqiu_follow_easyxt.py

REM 根据退出状态提示
if errorlevel 1 (
    echo.
    echo [失败] 程序运行出现错误，按任意键退出...
    pause
    exit /b 1
) else (
    echo.
    echo [完成] 程序已结束，按任意键退出...
    pause
)

endlocal