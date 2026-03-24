# -*- coding: utf-8 -*-
# Simple Small Cap Strategy - Live Trading Launcher

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "  Simple Small Cap Strategy - Live Trading" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host ""

# Set directory
$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptPath

Write-Host "[INFO] Current Directory: $PWD" -ForegroundColor Green
Write-Host ""

# Check Python
Write-Host "[INFO] Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "      $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python is not installed" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host ""

# Check config
$configPath = "..\..\..\config\unified_config.json"
if (Test-Path $configPath) {
    Write-Host "[OK] Config file found: $configPath" -ForegroundColor Green
} else {
    Write-Host "[WARN] Config file not found, using defaults" -ForegroundColor Yellow
}
Write-Host ""

# Run strategy
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "  Starting Strategy..." -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host ""

try {
    python main.py
} catch {
    Write-Host "[ERROR] $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "  Program Exit" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host ""

Read-Host "Press Enter to exit"
