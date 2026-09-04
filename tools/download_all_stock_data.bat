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

rem 验证目录由用户配置，避免假定某台电脑的 QMT 安装位置。
rem 例：set QMT_DATA_DIR=C:\QMT\userdata_mini
if not defined QMT_DATA_DIR (
    echo ℹ 未设置 QMT_DATA_DIR，跳过 DAT 文件目录验证。
    echo   如需验证，请先设置 QMT_DATA_DIR 为 QMT 的 userdata_mini 目录。
) else (
    set "SZ_DIR=%QMT_DATA_DIR%\datadir\SZ\86400"
    if exist "!SZ_DIR!" (
        echo ✓ 深圳股票数据目录存在: !SZ_DIR!
        for /f %%i in ('dir "!SZ_DIR!\*.DAT" /b ^| find /c /v ""') do set SZ_COUNT=%%i
        echo   深圳股票数据文件数量: !SZ_COUNT!
    ) else (
        echo ℹ 深圳股票数据目录不存在: !SZ_DIR!
    )

    echo.

    set "SH_DIR=%QMT_DATA_DIR%\datadir\SH\86400"
    if exist "!SH_DIR!" (
        echo ✓ 上海股票数据目录存在: !SH_DIR!
        for /f %%i in ('dir "!SH_DIR!\*.DAT" /b ^| find /c /v ""') do set SH_COUNT=%%i
        echo   上海股票数据文件数量: !SH_COUNT!
    ) else (
        echo ℹ 上海股票数据目录不存在: !SH_DIR!
    )
)

echo.
echo ====================================================
echo        全部A股日线数据下载完成
echo ====================================================
echo.

pause
