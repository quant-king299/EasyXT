@echo off
REM EasyXT Installation Script
REM Auto configure PYTHONPATH and verify installation

echo ========================================
echo EasyXT Installation Script
echo ========================================
echo.

REM Get project directory (where this script is located)
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM Get parent directory (project root)
for %%i in ("%SCRIPT_DIR%") do set "PROJECT_ROOT=%%~dpi"
set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"

echo [1/4] Check project directory...
echo Script dir: %SCRIPT_DIR%
echo Project root: %PROJECT_ROOT%
if not exist "%SCRIPT_DIR%\__init__.py" (
    echo ERROR: easyxt_backtest module not found
    pause
    exit /b 1
)
echo      Found easyxt_backtest module
echo.

echo [2/4] Install dependencies...
echo Installing backtrader...
pip install backtrader >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo      backtrader installed successfully
) else (
    echo      backtrader installation failed
    pause
    exit /b 1
)
echo.

echo [3/4] Configure PYTHONPATH...
echo Adding to user environment variables...
echo      PYTHONPATH=%PROJECT_ROOT%
setx PYTHONPATH "%PROJECT_ROOT%"
if %ERRORLEVEL% EQU 0 (
    echo      Success!
) else (
    echo      Failed!
    pause
    exit /b 1
)
echo.

echo [4/4] Verify installation...
python -c "import sys; sys.path.insert(0, r'%PROJECT_ROOT%'); from easyxt_backtest import BacktestEngine; print('easyxt_backtest: OK')"
if %ERRORLEVEL% EQU 0 (
    echo.
) else (
    echo      Verification failed, please check manually
    echo      Python version:
    python --version
    echo.
    echo TIP: Close this window and open a NEW PowerShell window
    echo      Then try: python -c "from easyxt_backtest import BacktestEngine"
    pause
    exit /b 1
)

echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo IMPORTANT:
echo 1. Close this PowerShell window
echo 2. Open a NEW PowerShell window
echo 3. Then you can use:
echo    from easyxt_backtest import BacktestEngine
echo.
echo - PYTHONPATH: %PROJECT_ROOT%
echo.
pause
