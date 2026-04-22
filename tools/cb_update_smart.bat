@echo off
title Smart Update - Convertible Bonds

echo ============================================================
echo     Convertible Bonds Smart Update
echo     可转债智能更新
echo ============================================================
echo.

cd /d "%~dp0.."

echo Select update period:
echo   1. Recent 1 month
echo   2. Recent 3 months (recommended)
echo   3. Recent 6 months
echo   4. Year to date
echo   5. Custom range
echo.
set /p choice="Enter option (1-5): "

REM Get current date
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set today=%datetime:~0,8%
set current_year=%datetime:~0,4%
set current_month=%datetime:~4,2%

if "%choice%"=="1" goto MONTH1
if "%choice%"=="2" goto MONTH3
if "%choice%"=="3" goto MONTH6
if "%choice%"=="4" goto YTD
if "%choice%"=="5" goto CUSTOM
goto MONTH3

:MONTH1
set /a start_month=%current_month% - 1
set /a start_year=%current_year%
if %start_month% leq 0 (
    set /a start_month += 12
    set /a start_year -= 1
)
if %start_month% lss 10 set start_month=0%start_month%
set start_date=%start_year%%start_month%01
goto RUN

:MONTH3
set /a start_month=%current_month% - 3
set /a start_year=%current_year%
if %start_month% leq 0 (
    set /a start_month += 12
    set /a start_year -= 1
)
if %start_month% lss 10 set start_month=0%start_month%
set start_date=%start_year%%start_month%01
goto RUN

:MONTH6
set /a start_month=%current_month% - 6
set /a start_year=%current_year%
if %start_month% leq 0 (
    set /a start_month += 12
    set /a start_year -= 1
)
if %start_month% lss 10 set start_month=0%start_month%
set start_date=%start_year%%start_month%01
goto RUN

:YTD
set start_date=%current_year%0101
goto RUN

:CUSTOM
echo.
set /p start_date="Enter start date (YYYYMMDD): "
set /p end_date="Enter end date (YYYYMMDD, default=today): "
if "%end_date%"=="" set end_date=%today%
goto RUN_CUSTOM

:RUN
echo.
echo [Update Period] %start_date% to %today%
echo Starting update...
echo.
python tools\download_all_convertible_bonds.py --start-date %start_date% --end-date %today%
goto END

:RUN_CUSTOM
echo.
echo [Update Period] %start_date% to %end_date%
echo Starting update...
echo.
python tools\download_all_convertible_bonds.py --start-date %start_date% --end-date %end_date%

:END
echo.
echo ============================================================
echo Update completed!
echo.
echo IMPORTANT: Please also run GUI update:
echo   1. Open GUI: python rungui.py
echo   2. Go to Data Management tab
echo   3. Click [Update Missing Data] button
echo   This ensures all data is properly imported to DuckDB
echo ============================================================
pause
