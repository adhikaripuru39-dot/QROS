<#
.SYNOPSIS
    Automated VPS Deployment & Initialization Script for QROS-PROP S-Tier.
.DESCRIPTION
    Sets up the local Python virtual environment, installs dependencies,
    creates isolated runtime directories, initializes the database with the
    $5,000 dynamic account profile, and validates system readiness.
#>
param(
    [string]$PythonCommand = 'python',
    [double]$AccountBalance = 5000.0,
    [string]$RuntimeDir = 'C:\QROS-Runtime'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   QROS-PROP S-Tier Institutional VPS Deployment Setup      " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$root = (Resolve-Path -LiteralPath (Split-Path -Parent $PSScriptRoot)).Path
Set-Location $root

# 1. Check Python Version
Write-Host "`n[1/6] Checking Python installation..." -ForegroundColor Yellow
try {
    $verOutput = & $PythonCommand -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}'); assert sys.version_info >= (3, 11)"
    Write-Host "  Found compatible Python version: $verOutput" -ForegroundColor Green
} catch {
    Write-Error "Python 3.11 or later is required. Please install Python 3.11+ and ensure it is on your PATH."
    exit 1
}

# 2. Setup Isolated Python Virtual Environment
Write-Host "`n[2/6] Configuring virtual environment..." -ForegroundColor Yellow
$venvDir = Join-Path $root 'backend\.venv'
$venvPython = Join-Path $venvDir 'Scripts\python.exe'

if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    Write-Host "  Creating venv at $venvDir..."
    & $PythonCommand -m venv $venvDir
    if ($LASTEXITCODE -ne 0) { throw "Failed to create virtual environment." }
}

Write-Host "  Installing/verifying dependencies from backend\requirements.txt..."
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r (Join-Path $root 'backend\requirements.txt')
if ($LASTEXITCODE -ne 0) { throw "Pip dependency installation failed." }
Write-Host "  Dependencies successfully installed." -ForegroundColor Green

# 3. Create Local Runtime Storage (Decoupled from Cloud Sync)
Write-Host "`n[3/6] Setting up local storage directories at $RuntimeDir..." -ForegroundColor Yellow
$varData = Join-Path $RuntimeDir 'var\data'
$varLogs = Join-Path $RuntimeDir 'var\logs'
$backups = Join-Path $RuntimeDir 'backups'

New-Item -ItemType Directory -Path $varData, $varLogs, $backups -Force | Out-Null
Write-Host "  Storage paths initialized: data, logs, backups." -ForegroundColor Green

# 4. Generate or Validate .env Configuration
Write-Host "`n[4/6] Checking .env configuration..." -ForegroundColor Yellow
$envPath = Join-Path $root '.env'
if (-not (Test-Path -LiteralPath $envPath -PathType Leaf)) {
    Write-Host "  Creating new .env from .env.vps.template..."
    $templatePath = Join-Path $root '.env.vps.template'
    if (Test-Path -LiteralPath $templatePath -PathType Leaf) {
        $envContent = Get-Content -LiteralPath $templatePath -Raw
    } else {
        $envContent = Get-Content -LiteralPath (Join-Path $root '.env.example') -Raw
    }
    
    # Generate secure 64-character token
    $genToken = & $venvPython -c "import secrets; print(secrets.token_hex(32))"
    $envContent = $envContent.Replace("REPLACE_WITH_YOUR_64_CHAR_HEX_TOKEN", $genToken.Trim())
    $envContent = $envContent.Replace("change-me", $genToken.Trim())
    
    # Update default database and directory paths
    $dbUrl = "sqlite:///" + (Join-Path $RuntimeDir 'var\qros.db').Replace('\', '/')
    $envContent = $envContent -replace 'QROS_DATABASE_URL=.*', "QROS_DATABASE_URL=$dbUrl"
    $envContent = $envContent -replace 'QROS_DATA_DIR=.*', "QROS_DATA_DIR=$varData"
    $envContent = $envContent -replace 'QROS_LOG_DIR=.*', "QROS_LOG_DIR=$varLogs"
    
    Set-Content -LiteralPath $envPath -Value $envContent -Encoding UTF8
    Write-Host "  Generated fresh .env with a cryptographic 64-char API token." -ForegroundColor Green
} else {
    Write-Host "  Found existing .env file." -ForegroundColor Green
}

# 5. Initialize & Bind Active Account ($5,000 Baseline)
Write-Host "`n[5/6] Initializing database and binding active account ($AccountBalance USD)..." -ForegroundColor Yellow
$env:PYTHONPATH = (Join-Path $root 'backend')
& $venvPython (Join-Path $root 'scripts\bind_active_account.py') --balance $AccountBalance
if ($LASTEXITCODE -ne 0) { throw "Account binding script encountered an error." }
Write-Host "  Account rules bound and 12 strategy instances commissioned." -ForegroundColor Green

# 6. Check Overall System Readiness
Write-Host "`n[6/6] Verifying system readiness..." -ForegroundColor Yellow
& $venvPython -c "
from qros.db.session import session_factory, session_scope
from qros.config.settings import Settings
from qros.services.readiness import readiness
s = Settings()
factory = session_factory(s.database_url)
with session_scope(factory) as db:
    r = readiness(db, s)
    for c in r.get('checks', []):
        tag = '[PASS]' if c['passed'] else '[BLOCKED]'
        print(f'  {tag:9} {c[\"name\"]:30} : {c[\"detail\"]}')
"

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  QROS-PROP VPS Environment Successfully Deployed!          " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Launch MT5 Terminal and verify login to your FTMO account."
Write-Host "2. Enable 'Algo Trading' in MT5 (Toolbar button must be green)."
Write-Host "3. Attach 'QROSCalendarExport' EA to any single chart."
Write-Host "4. Start QROS services: .\deployment\start_services.ps1"
Write-Host "5. Open Dashboard: http://127.0.0.1:8000"
Write-Host "============================================================`n"
