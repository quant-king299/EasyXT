@echo off
title Test - Convertible Bonds Download

echo ============================================================
echo     Convertible Bonds Download Test
echo ============================================================
echo.
echo Test mode: Download 4 famous bonds
echo Purpose: Test QMT connection
echo.
echo Starting test...
echo.

cd /d "%~dp0.."
python tools\download_all_convertible_bonds.py --demo

echo.
echo ============================================================
echo Test completed!
echo.
echo If successful, QMT connection is working
echo You can now use full download options
echo ============================================================
pause
