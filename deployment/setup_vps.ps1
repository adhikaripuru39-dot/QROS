param([string]$PythonCommand = 'python', [switch]$InstallDependencies)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Split-Path -Parent $PSScriptRoot)).Path
if (-not (Test-Path -LiteralPath (Join-Path $root '.env') -PathType Leaf)) {
    throw 'Create a private .env from .env.example first. Keep real trading disabled during commissioning.'
}
$venv = Join-Path $root 'backend\.venv'
if (-not (Test-Path -LiteralPath (Join-Path $venv 'Scripts\python.exe'))) {
    if (-not $InstallDependencies) { throw 'Use -InstallDependencies to create the virtual environment and install project dependencies.' }
    & $PythonCommand -c 'import sys; assert sys.version_info >= (3,11), "Python 3.11 or later required"'
    if ($LASTEXITCODE -ne 0) { throw 'Compatible Python unavailable.' }
    & $PythonCommand -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
}
if ($InstallDependencies) {
    & (Join-Path $venv 'Scripts\python.exe') -m pip install -r (Join-Path $root 'backend\requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
}
New-Item -ItemType Directory -Path (Join-Path $root 'var\logs'),(Join-Path $root 'var\backups') -Force | Out-Null
. (Join-Path $PSScriptRoot 'common.ps1')
$null = Initialize-Qros
Write-Output 'QROS host prepared. No service, OS task, broker order or trading mode was started.'
