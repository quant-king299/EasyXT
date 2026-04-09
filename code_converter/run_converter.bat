@echo off
chcp 65001 >nul 2>&1
python "%~dp0run_converter_gui.py"
pause
