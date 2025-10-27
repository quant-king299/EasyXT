# 一键本地可编辑安装（开发模式）
param()

$ErrorActionPreference = "Stop"

Write-Host "[1/3] 安装 easy-xt (editable)" -ForegroundColor Cyan
Push-Location "c:\Users\Administrator\Desktop\miniqmt扩展\easy_xt"
pip install -e .
Pop-Location

Write-Host "[2/3] 安装 jq2qmt-adapter (editable)" -ForegroundColor Cyan
Push-Location "c:\Users\Administrator\Desktop\miniqmt扩展\jq2qmt_adapter"
pip install -e .
Pop-Location

Write-Host "[3/3] 校验导入" -ForegroundColor Cyan
python -c "import easy_xt, jq2qmt_adapter; import importlib; print('easy_xt version:', getattr(easy_xt, '__version__', 'unknown')); print('jq2qmt_adapter import OK'); print('SUCCESS')"

Write-Host "完成" -ForegroundColor Green
