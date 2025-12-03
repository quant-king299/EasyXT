@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ====================================================
echo        全部A股日线数据一键下载工具
echo ====================================================
echo.

rem 检查Python环境
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未检测到Python环境，请先安装Python
    pause
    exit /b 1
)

echo ✓ Python环境检查通过
echo.

rem 获取当前目录
set "SCRIPT_DIR=%~dp0"
echo 脚本目录: %SCRIPT_DIR%
echo.

rem 下载深圳股票数据
echo [1/3] 开始下载深圳股票日线数据...
echo.
python "%SCRIPT_DIR%download_sz_stocks.py" --force
if %errorlevel% neq 0 (
    echo.
    echo 警告: 深圳股票数据下载过程中出现错误，但将继续执行后续步骤
    echo.
)

echo.
echo ====================================================
echo.

rem 下载上海股票数据
echo [2/3] 开始下载上海股票日线数据...
echo.
python "%SCRIPT_DIR%download_sh_stocks.py" --force
if %errorlevel% neq 0 (
    echo.
    echo 警告: 上海股票数据下载过程中出现错误，但将继续执行后续步骤
    echo.
)

echo.
echo ====================================================
echo.

rem 验证下载结果
echo [3/3] 验证下载结果...
echo.

rem 检查深圳数据目录
set "SZ_DIR=D:\国金QMT交易端模拟\userdata_mini\datadir\SZ\86400"
if exist "%SZ_DIR%" (
    echo ✓ 深圳股票数据目录存在: %SZ_DIR%
    for /f %%i in ('dir "%SZ_DIR%\*.DAT" /b ^| find /c /v ""') do set SZ_COUNT=%%i
    echo   深圳股票数据文件数量: !SZ_COUNT!
) else (
    echo ℹ 深圳股票数据目录不存在: %SZ_DIR%
    echo   （可能是目录尚未创建或路径不同）
)

echo.

rem 检查上海数据目录
set "SH_DIR=D:\国金QMT交易端模拟\userdata_mini\datadir\SH\86400"
if exist "%SH_DIR%" (
    echo ✓ 上海股票数据目录存在: %SH_DIR%
    for /f %%i in ('dir "%SH_DIR%\*.DAT" /b ^| find /c /v ""') do set SH_COUNT=%%i
    echo   上海股票数据文件数量: !SH_COUNT!
) else (
    echo ℹ 上海股票数据目录不存在: %SH_DIR%
    echo   （可能是目录尚未创建或路径不同）
)

echo.
echo ====================================================
echo        全部A股日线数据下载完成
echo ====================================================
echo.

pause