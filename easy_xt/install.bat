@echo off
chcp 65001 > nul
echo ======================================================================
echo EasyXT 一键安装脚本
echo ======================================================================
echo.

echo [1/3] 正在检查 xtquant 依赖...
python check_xtquant.py
if errorlevel 1 (
    echo.
    echo ======================================================================
    echo xtquant 检查未通过！请先安装 xtquant 后再运行此脚本
    echo ======================================================================
    echo.
    pause
    exit /b 1
)

echo.
echo [2/3] 正在安装 easy-xt...
REM 切换到项目根目录（easy_xt的父目录）
cd /d "%~dp0.."
echo 当前工作目录: %CD%
pip install -e .
if errorlevel 1 (
    echo.
    echo ======================================================================
    echo easy-xt 安装失败！
    echo ======================================================================
    echo.
    cd /d "%~dp0"
    pause
    exit /b 1
)
REM 切换回批处理文件所在目录
cd /d "%~dp0"

echo.
echo [3/3] 验证安装...
python -c "from easy_xt import get_api; print('✓ easy-xt 安装成功！')"

if errorlevel 1 (
    echo.
    echo ======================================================================
    echo 安装验证失败！
    echo ======================================================================
    echo.
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo ✓ 所有安装步骤完成！
echo ======================================================================
echo.
echo 快速测试：
echo   python -c "from easy_xt import get_api; api = get_api(); print(api)"
echo.
pause
