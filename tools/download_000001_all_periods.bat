@echo off
setlocal enabledelayedexpansion

:: ====================================================================
:: 快速下载 000001.SZ 所有周期数据
:: ====================================================================
:: 功能：一键下载平安银行所有周期的历史数据
:: 使用：双击运行即可
:: ====================================================================

title 下载 000001.SZ 所有周期数据

:: 设置控制台编码为UTF-8
chcp 65001 >nul 2>&1

cls
echo.
echo ======================================================================
echo              下载 000001.SZ (平安银行) 所有周期数据
echo ======================================================================
echo.

:: 检查Python是否安装
echo [1/3] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Python未安装
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
    pause
    exit /b 1
)
echo [OK] xtquant已安装

:: 检查QMT是否启动
echo [3/3] 检查QMT连接状态...
python -c "from xtquant import xtdata; c=xtdata.get_client(); print('OK' if c and c.is_connected() else 'FAIL')" >nul 2>&1
if errorlevel 1 (
    echo [警告] 无法确定QMT状态，但将继续尝试
) else (
    echo [OK] QMT服务已启动
)

echo.
echo ======================================================================
echo  开始下载 000001.SZ 所有周期数据...
echo ======================================================================
echo.
echo  下载周期：1m, 5m, 15m, 30m, 1h, 1d
echo  时间范围：最近3个月
echo.
echo  请耐心等待，下载可能需要几分钟...
echo.

:: 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:: 调用Python脚本（使用默认参数）
python download_stock_periods.py 000001.SZ

echo.
echo ======================================================================
echo  下载完成！
echo ======================================================================
echo.
echo 提示：
echo   1. 数据已保存到QMT数据目录
echo   2. 可以使用EasyXT读取这些数据
echo   3. 建议定期更新数据
echo.
echo 按任意键退出...
pause >nul
