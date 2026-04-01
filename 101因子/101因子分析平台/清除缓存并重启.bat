@echo off
chcp 65001 >nul
title 101因子分析平台 - 清除缓存并重启

echo ================================================================
echo   清除缓存并重启 101因子分析平台
echo ================================================================
echo.

echo [1/5] 停止进程...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM streamlit.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo [2/5] 清除用户级缓存...
if exist "%USERPROFILE%\.streamlit" (
    rmdir /s /q "%USERPROFILE%\.streamlit"
    echo     已删除: %USERPROFILE%\.streamlit
) else (
    echo     跳过: 不存在
)

echo [3/5] 清除项目缓存...
cd /d "%~dp0"
for %%d in (.streamlit __pycache__ src\__pycache__) do (
    if exist "%%d" (
        rmdir /s /q "%%d"
        echo     已删除: %%d
    )
)

echo [4/5] 清除 easyxt_backtest 缓存...
cd /d "%~dp0..\..\easyxt_backtest"
for %%d in (.streamlit __pycache__) do (
    if exist "%%d" (
        rmdir /s /q "%%d"
        echo     已删除: easyxt_backtest\%%d
    )
)
for %%s in (web_app config strategies sources) do (
    if exist "%%s\__pycache__" (
        rmdir /s /q "%%s\__pycache__"
        echo     已删除: easyxt_backtest\%%s\__pycache__
    )
)

echo [5/5] 启动应用...
cd /d "%~dp0"
echo.
echo   访问地址: http://localhost:8501
echo.
start "" streamlit run main_app.py

echo.
echo ================================================================
echo   完成!
echo ================================================================
pause
