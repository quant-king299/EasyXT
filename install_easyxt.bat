@echo off
REM EasyXT 安装脚本
REM 自动配置 PYTHONPATH 并验证安装

echo ========================================
echo EasyXT 安装脚本
echo ========================================
echo.

REM 获取项目目录（脚本所在目录）
set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

echo [1/3] 检测项目目录...
echo 项目目录: %PROJECT_DIR%
if not exist "%PROJECT_DIR%\easyxt_backtest" (
    echo 错误：找不到 easyxt_backtest 目录
    pause
    exit /b 1
)
echo      找到 easyxt_backtest
echo.

echo [2/3] 配置 PYTHONPATH...
echo 正在添加到用户环境变量...

REM 设置用户级 PYTHONPATH
setx PYTHONPATH "%PROJECT_DIR%"
if %ERRORLEVEL% EQU 0 (
    echo      成功！
) else (
    echo      失败！
    pause
    exit /b 1
)
echo.

echo [3/3] 验证安装...
python -c "import sys; sys.path.insert(0, r'%PROJECT_DIR%'); from easyxt_backtest import BacktestEngine; print('easyxt_backtest: OK')"
if %ERRORLEVEL% EQU 0 (
    echo.
) else (
    echo      验证失败，请手动检查
    echo      Python 版本:
    python --version
    pause
    exit /b 1
)

echo ========================================
echo 安装完成！
echo ========================================
echo.
echo 重要提示：
echo 1. 请关闭当前 PowerShell/命令提示符窗口
echo 2. 重新打开一个新的窗口
echo 3. 然后就可以使用了：
echo    from easyxt_backtest import BacktestEngine
echo.
echo - PYTHONPATH: %PROJECT_DIR%
echo.
pause
