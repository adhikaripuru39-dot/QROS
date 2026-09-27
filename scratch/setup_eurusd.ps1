$src = "C:\Users\adhik\OneDrive\Desktop\QROS"
$dest = "C:\Users\adhik\OneDrive\Desktop\qros eurusd"

Write-Host "Creating $dest..."
New-Item -ItemType Directory -Force -Path $dest | Out-Null

# 1. Copy core scientific research codebase & statistical engine
Write-Host "Copying src and tests..."
Copy-Item -Path "$src\src" -Destination "$dest\src" -Recurse -Force
Copy-Item -Path "$src\tests" -Destination "$dest\tests" -Recurse -Force

# 2. Copy configs and dependencies
Write-Host "Copying configuration files..."
Copy-Item -Path "$src\requirements.txt" -Destination "$dest\requirements.txt" -Force
Copy-Item -Path "$src\pytest.ini" -Destination "$dest\pytest.ini" -Force

# 3. Copy full institutional governance, constitution, charters, and guidelines
Write-Host "Copying governance constitution & binding charters..."
New-Item -ItemType Directory -Force -Path "$dest\docs\GOVERNANCE" | Out-Null
New-Item -ItemType Directory -Force -Path "$dest\docs\research\tracking" | Out-Null
Copy-Item -Path "$src\docs\GOVERNANCE\*" -Destination "$dest\docs\GOVERNANCE" -Recurse -Force

if (Test-Path "$src\Research-001 Guidelines.txt") {
    Copy-Item -Path "$src\Research-001 Guidelines.txt" -Destination "$dest\Research-001 Guidelines.txt" -Force
}

# 4. Copy paper trading engine with fresh logs
Write-Host "Copying execution engine..."
Copy-Item -Path "$src\paper_trading" -Destination "$dest\paper_trading" -Recurse -Force
if (Test-Path "$dest\paper_trading\logs") {
    Remove-Item -Path "$dest\paper_trading\logs\*" -Recurse -Force -ErrorAction SilentlyContinue
}

# 5. Initialize fresh directories for EURUSD
New-Item -ItemType Directory -Force -Path "$dest\data\raw\eurusd" | Out-Null
New-Item -ItemType Directory -Force -Path "$dest\data\interim\eurusd" | Out-Null
New-Item -ItemType Directory -Force -Path "$dest\data\processed\eurusd" | Out-Null
New-Item -ItemType Directory -Force -Path "$dest\scripts" | Out-Null

Write-Host "Successfully provisioned QROS EURUSD."
