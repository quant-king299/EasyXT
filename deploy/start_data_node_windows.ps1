param(
  [string]$HostAddress = "127.0.0.1",
  [int]$Port = 18820,
  [string]$NodeId = "win_data_node_1",
  [string]$DuckdbPath = "D:/StockData/stock_data.ddb",
  [string]$Token = $env:EASYXT_DATA_SERVICE_TOKEN
)

$ErrorActionPreference = "Stop"

if ($HostAddress -notin @("127.0.0.1", "::1", "localhost") -and -not $Token) {
  throw "非本机监听必须通过 -Token 或 EASYXT_DATA_SERVICE_TOKEN 设置随机长 token。"
}

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$pythonCandidates = @(
  (Join-Path $projectRoot ".venv\Scripts\python.exe"),
  (Join-Path $projectRoot "venv\Scripts\python.exe"),
  "python"
)
$pythonExe = $pythonCandidates | Where-Object {
  if ($_ -eq "python") { return [bool](Get-Command python -ErrorAction SilentlyContinue) }
  Test-Path $_
} | Select-Object -First 1
if (-not $pythonExe) { throw "未找到 Python，请先安装项目运行环境。" }
if (-not (Test-Path $DuckdbPath)) { throw "DuckDB 文件不存在: $DuckdbPath" }

$env:EASYXT_DATA_SERVICE_HOST = $HostAddress
$env:EASYXT_DATA_SERVICE_PORT = "$Port"
$env:EASYXT_DATA_NODE_ID = $NodeId
$env:DUCKDB_PATH = $DuckdbPath
$env:EASYXT_DATA_SERVICE_TOKEN = $Token

Write-Host "EasyXT 数据节点: http://$HostAddress`:$Port"
& $pythonExe -m easy_xt.data_service.server
