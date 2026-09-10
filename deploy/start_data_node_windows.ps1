param(
  [string]$HostAddress = "127.0.0.1",
  [int]$Port = 18820,
  [string]$NodeId = "win_data_node_1",
  [string]$DuckdbPath = "D:/StockData/stock_data.ddb",
  [string]$Token = $env:EASYXT_DATA_SERVICE_TOKEN
)

$ErrorActionPreference = "Stop"

if ($HostAddress -notin @("127.0.0.1", "::1", "localhost") -and -not $Token) {
  throw "A non-local listener requires -Token or EASYXT_DATA_SERVICE_TOKEN."
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
if (-not $pythonExe) { throw "Python was not found. Install the project runtime first." }
if (-not (Test-Path $DuckdbPath)) { throw "DuckDB file does not exist: $DuckdbPath" }

$env:EASYXT_DATA_SERVICE_HOST = $HostAddress
$env:EASYXT_DATA_SERVICE_PORT = "$Port"
$env:EASYXT_DATA_NODE_ID = $NodeId
$env:DUCKDB_PATH = $DuckdbPath
$env:EASYXT_DATA_SERVICE_TOKEN = $Token

Write-Host "EasyXT data node: http://$HostAddress`:$Port"
& $pythonExe -m easy_xt.data_service.server
