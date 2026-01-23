@echo off
chcp 65001 >nul
title 国债ETF网格交易 - 配置向导

echo.
echo ========================================
echo    国债ETF网格交易 - 配置向导
echo ========================================
echo.

cd /d "%~dp0"

python config_wizard.py

echo.
pause
