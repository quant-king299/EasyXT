@echo off
title Convertible Bonds Download

echo ============================================================
echo       Convertible Bonds Data Download Tool
echo ============================================================
echo.

cd /d "%~dp0.."

echo Select download mode:
echo   1. Quick Test (4 bonds)
echo   2. Year 2024
echo   3. Years 2022-2024
echo   4. Years 2016-2024 (Full History)
echo   5. Custom range
echo.
set /p choice="Enter option (1-5): "

if "%choice%"=="1" goto MODE1
if "%choice%"=="2" goto MODE2
if "%choice%"=="3" goto MODE3
if "%choice%"=="4" goto MODE4
if "%choice%"=="5" goto MODE5
goto MODE1

:MODE1
echo [Mode] Quick Test
python tools\download_all_convertible_bonds.py --demo
goto END

:MODE2
echo [Mode] Year 2024
python tools\download_all_convertible_bonds.py --start-date 20240101 --end-date 20241231
goto END

:MODE3
echo [Mode] Years 2022-2024
python tools\download_all_convertible_bonds.py --start-date 20220101 --end-date 20241231
goto END

:MODE4
echo [Mode] Full History (2016-2024)
python tools\download_all_convertible_bonds.py --start-date 20160101 --end-date 20241231
goto END

:MODE5
echo.
set /p start_date="Enter start date (YYYYMMDD): "
set /p end_date="Enter end date (YYYYMMDD): "
echo [Mode] Custom range: %start_date% to %end_date%
python tools\download_all_convertible_bonds.py --start-date %start_date% --end-date %end_date%
goto END

:END
echo.
echo ============================================================
echo Download completed!
echo.
echo Next: Open GUI and go to Data Management tab
echo       Click Download Convertible Bonds button
echo ============================================================
pause
