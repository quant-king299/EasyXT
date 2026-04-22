@echo off
title Quick Download - Convertible Bonds 2024

echo ============================================================
echo     Convertible Bonds Quick Download (2024)
echo ============================================================
echo.
echo Starting download...
echo.

cd /d "%~dp0.."
python tools\download_all_convertible_bonds.py --start-date 20240101 --end-date 20241231

echo.
echo ============================================================
echo Download completed!
echo Next: Open GUI - Data Management - Download Bonds
echo ============================================================
pause
