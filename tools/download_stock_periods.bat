@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ====================================================================
:: 多周期历史数据下载工具 - Windows批处理版本
:: ====================================================================
:: 功能：下载指定股票的所有周期历史数据
:: 使用：双击运行或在命令行执行
:: ====================================================================

title 多周期历史数据下载工具

echo.
echo ======================================================================
echo                    多周期历史数据下载工具
echo ======================================================================
echo.

:: 检查Python是否安装
echo [检查] Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Python未安装或未添加到PATH
    echo.
    echo 解决方案：
    echo   1. 安装Python 3.9或更高版本
    echo   2. 将Python添加到系统PATH
    echo.
    pause
    exit /b 1
)
echo [OK] Python已安装

:: 检查xtquant是否安装
echo [检查] xtquant模块...
python -c "import xtquant" >nul 2>&1
if errorlevel 1 (
    echo [错误] xtquant未安装
    echo.
    echo 解决方案：
    echo   1. 确保miniQMT已安装
    echo   2. 将xtquant文件夹添加到Python路径
    echo.
    pause
    exit /b 1
)
echo [OK] xtquant已安装

:: 检查QMT是否启动
echo [检查] QMT连接状态...
python -c "from xtquant import xtdata; client=xtdata.get_client(); exit(0 if client and client.is_connected() else 1)" >nul 2>&1
if errorlevel 1 (
    echo [警告] QMT服务未启动
    echo.
    echo 请先执行以下步骤：
    echo   1. 启动QMT客户端（XtQuant.exe）
    echo   2. 等待QMT完全启动（约10-30秒）
    echo   3. 重新运行此脚本
    echo.
    echo 是否继续尝试下载？ (Y/N)
    set /p continue="请选择: "
    if /i "!continue!" neq "Y" (
        echo 已取消
        pause
        exit /b 1
    )
) else (
    echo [OK] QMT服务已启动
)

echo.
echo ======================================================================
echo.

:: 获取用户输入
set /p stock_code="请输入股票代码 (默认: 000001.SZ): "
if "!stock_code!"=="" set stock_code=000001.SZ

set /p start_date="请输入开始日期 YYYYMMDD (默认: 3个月前): "
if "!start_date!"=="" (
    for /f "tokens=1-3 delims=/ " %%a in ('date /t') do (
        set today=%%c%%a%%b
    )
    :: 简单处理：使用默认值，让Python脚本处理
    set start_date=
)

set /p end_date="请输入结束日期 YYYYMMDD (默认: 今天): "
if "!end_date!"=="" set end_date=

echo.
echo 配置确认：
echo   股票代码: !stock_code!
echo   开始日期: !start_date! (默认: 3个月前)
echo   结束日期: !end_date! (默认: 今天)
echo   下载周期: 1m, 5m, 15m, 30m, 1h, 1d
echo.

set /p confirm="确认下载？ (Y/N, 默认: Y): "
if /i "!confirm!" neq "N" (
    echo.
    echo ======================================================================
    echo  开始下载...
    echo ======================================================================
    echo.

    :: 获取脚本所在目录
    set "SCRIPT_DIR=%~dp0"
    cd /d "!SCRIPT_DIR!"

    :: 调用Python脚本
    if "!start_date!"=="" (
        if "!end_date!"=="" (
            python download_stock_periods.py "!stock_code!"
        ) else (
            python download_stock_periods.py "!stock_code!" "" "!end_date!"
        )
    ) else (
        if "!end_date!"=="" (
            python download_stock_periods.py "!stock_code!" "!start_date!"
        ) else (
            python download_stock_periods.py "!stock_code!" "!start_date!" "!end_date!"
        )
    )

    echo.
    echo ======================================================================
    echo  下载完成！
    echo ======================================================================
) else (
    echo 已取消
)

echo.
echo 按任意键退出...
pause >nul
