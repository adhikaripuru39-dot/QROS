<#
.SYNOPSIS
    Cleanly shuts down all running QROS background services, supervisor windows, and Python workers.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'

Write-Host "Stopping QROS background services and supervisor windows..." -ForegroundColor Cyan

# 1. Terminate parent PowerShell supervisor loops FIRST so they cannot respawn Python
$psProcs = Get-CimInstance Win32_Process | Where-Object {
    $_.ProcessId -ne $PID -and
    $_.Name -match "powershell|pwsh" -and (
        $_.CommandLine -like "*run_backend.ps1*" -or
        $_.CommandLine -like "*run_data.ps1*" -or
        $_.CommandLine -like "*run_executor.ps1*" -or
        $_.CommandLine -like "*run_worker.ps1*"
    )
}
if ($psProcs) {
    foreach ($p in $psProcs) {
        Write-Host "  Closing supervisor window: ID=$($p.ProcessId)" -ForegroundColor Yellow
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

# 2. Terminate Python microservices (by command line, venv path, or port 8000)
$venvPython = (Resolve-Path -LiteralPath (Join-Path (Split-Path -Parent $PSScriptRoot) 'backend\.venv\Scripts\python.exe') -ErrorAction SilentlyContinue)
$procList = Get-CimInstance Win32_Process | Where-Object { 
    $_.CommandLine -like "*qros.services*" -or 
    $_.CommandLine -like "*qros.api*" -or 
    $_.CommandLine -like "*uvicorn*qros*" -or
    ($venvPython -and $_.ExecutablePath -eq $venvPython.Path)
}

if ($procList) {
    foreach ($p in $procList) {
        Write-Host "  Terminating worker process: ID=$($p.ProcessId) Name=$($p.Name)" -ForegroundColor Yellow
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Write-Host "All QROS Python microservices stopped." -ForegroundColor Green
} else {
    Write-Host "No active QROS Python workers detected." -ForegroundColor Gray
}

# Also ensure nothing is still holding port 8000
$port8000 = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($port8000) {
    foreach ($conn in $port8000) {
        if ($conn.OwningProcess -gt 4) {
            Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
}

# 3. Release any orphaned lock files in runtime directory
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
