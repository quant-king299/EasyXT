# 一键构建 easy-xt 与 jq2qmt-adapter
param()

$ErrorActionPreference = "Stop"

Write-Host "[1/4] 安装 flit" -ForegroundColor Cyan
pip install flit | Out-Null

Write-Host "[2/4] 构建 easy-xt" -ForegroundColor Cyan
Push-Location "c:\Users\Administrator\Desktop\miniqmt扩展\easy_xt"
flit build
Pop-Location

Write-Host "[3/4] 构建 jq2qmt-adapter" -ForegroundColor Cyan
Push-Location "c:\Users\Administrator\Desktop\miniqmt扩展\jq2qmt_adapter"
flit build
Pop-Location

Write-Host "[4/4] 完成" -ForegroundColor Green
