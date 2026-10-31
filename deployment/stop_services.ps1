<#
.SYNOPSIS
    Cleanly shuts down all running QROS background services and Python workers.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'

Write-Host "Stopping QROS background services..." -ForegroundColor Cyan

# Terminate Python processes associated with QROS
$procList = Get-CimInstance Win32_Process | Where-Object { 
    $_.CommandLine -like "*qros.services*" -or 
    $_.CommandLine -like "*qros.api*" -or 
    $_.CommandLine -like "*uvicorn*qros*" 
}

if ($procList) {
    foreach ($p in $procList) {
        Write-Host "  Terminating process: ID=$($p.ProcessId) Name=$($p.Name)" -ForegroundColor Yellow
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Write-Host "All QROS Python microservices stopped." -ForegroundColor Green
} else {
    Write-Host "No active QROS services detected." -ForegroundColor Gray
}

# Release any orphaned lock files in runtime directory
$lockDirs = @('C:\QROS-Runtime\var', 'var')
foreach ($ld in $lockDirs) {
    if (Test-Path $ld) {
        Get-ChildItem -Path $ld -Filter "*.lock" -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
            Write-Host "  Removing stale lock file: $($_.Name)" -ForegroundColor Gray
            Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
        }
    }
}

Write-Host "QROS shutdown complete.`n" -ForegroundColor Green

