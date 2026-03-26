@echo off
setlocal enabledelayedexpansion

:: ====================================================================
:: 多周期历史数据下载工具 - Windows批处理版本
:: ====================================================================
:: 功能：下载指定股票的所有周期历史数据
:: 使用：双击运行或在命令行执行
:: ====================================================================

title 多周期历史数据下载工具

cls
echo.
echo ======================================================================
echo                    多周期历史数据下载工具
echo ======================================================================
echo.

:: 检查Python是否安装
echo [1/3] 检查Python环境...
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
echo [2/3] 检查xtquant模块...
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

:: 检查QMT是否启动（简化检查）
echo [3/3] 检查QMT连接状态...
python -c "from xtquant import xtdata; c=xtdata.get_client(); print('OK' if c and c.is_connected() else 'FAIL')" >nul 2>&1
if errorlevel 1 (
    echo [警告] 无法确定QMT状态，但将继续尝试
    echo.
) else (
    echo [OK] QMT服务已启动
    echo.
)

echo ======================================================================
echo.

:: 获取用户输入
set /p stock_code="请输入股票代码 (默认: 000001.SZ): "
if "!stock_code!"=="" set stock_code=000001.SZ

set /p start_date="请输入开始日期 YYYYMMDD (默认: 3个月前，直接回车): "
set /p end_date="请输入结束日期 YYYYMMDD (默认: 今天，直接回车): "

echo.
echo 配置确认：
echo   股票代码: !stock_code!
echo   开始日期: !start_date! (默认: 3个月前)
echo   结束日期: !end_date! (默认: 今天)
echo   下载周期: 1m, 5m, 15m, 30m, 1h, 1d
echo.

set /p confirm="确认下载？ (Y/N, 默认: Y): "
if /i "!confirm!"=="N" (
    echo 已取消
    pause
    exit /b 1
)

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
echo.
echo 按任意键退出...
pause >nul
