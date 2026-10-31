<#
.SYNOPSIS
    Starts all QROS background microservices under PowerShell supervision.
#>
param(
    [switch]$HideWindows
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$deployDir = $PSScriptRoot
$root = (Resolve-Path -LiteralPath (Split-Path -Parent $deployDir)).Path

Write-Host "Starting QROS-PROP background services..." -ForegroundColor Cyan

$windowStyle = if ($HideWindows) { 'Hidden' } else { 'Normal' }

# 1. API Service
Write-Host "  [1/3] Launching API Gateway & Web Dashboard..." -ForegroundColor Yellow
Start-Process powershell.exe -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $deployDir 'run_backend.ps1') -WindowStyle $windowStyle

Start-Sleep -Seconds 2

# 2. Data Worker Service
Write-Host "  [2/3] Launching Data Ingestion & Calibration Worker..." -ForegroundColor Yellow
Start-Process powershell.exe -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $deployDir 'run_data.ps1') -WindowStyle $windowStyle

Start-Sleep -Seconds 2

# 3. Execution Service
Write-Host "  [3/3] Launching Core Risk & Order Execution Service..." -ForegroundColor Yellow
Start-Process powershell.exe -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $deployDir 'run_executor.ps1') -WindowStyle $windowStyle

Write-Host "`nAll 3 services successfully launched under supervision." -ForegroundColor Green
Write-Host "Web Dashboard available at: http://127.0.0.1:8000"
Write-Host "Logs are continuously streaming to: C:\QROS-Runtime\var\logs"
Write-Host "To cleanly stop all services, run: .\deployment\stop_services.ps1`n"

