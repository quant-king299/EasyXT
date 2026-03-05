@echo off
echo ====================================
echo 重启Streamlit应用并清除缓存
echo ====================================
echo.

echo [1] 停止当前Streamlit进程...
taskkill /F /IM streamlit.exe 2>nul
timeout /t 2 /nobreak >nul

echo [2] 清除Streamlit缓存...
rmdir /s /q ".streamlit" 2>nul
rmdir /s /q "__pycache__" 2>nul
rmdir /s /q "src\__pycache__" 2>nul

echo [3] 启动Streamlit应用...
start "" streamlit run main_app.py

echo.
echo ====================================
echo 应用已重新启动！
echo 请在浏览器中访问: http://127.0.0.1:8501
echo ====================================
pause
