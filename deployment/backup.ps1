param([ValidateRange(1,365)][int]$Keep = 14)
. (Join-Path $PSScriptRoot 'common.ps1')
$runtime = Initialize-Qros
$backupDir = Join-Path $runtime.Root 'var\backups'
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMdd-HHmmss-fff')
$destination = Join-Path $backupDir "qros-$stamp"
New-Item -ItemType Directory -Path $destination | Out-Null
$env:QROS_BACKUP_DESTINATION = $destination
Push-Location (Join-Path $runtime.Root 'backend')
try {
    & $runtime.Python -B (Join-Path $PSScriptRoot 'backup_sqlite.py')
    if ($LASTEXITCODE -ne 0) { throw 'Online database backup or integrity check failed.' }
} finally { Pop-Location; Remove-Item Env:\QROS_BACKUP_DESTINATION }
Copy-Item -LiteralPath (Join-Path $runtime.Root 'config') -Destination $destination -Recurse
# Secrets are deliberately excluded; preserve .env separately in an encrypted store.
$resolvedBackup = (Resolve-Path -LiteralPath $backupDir).Path
Get-ChildItem -LiteralPath $resolvedBackup -Directory -Filter 'qros-*' | Sort-Object Name -Descending | Select-Object -Skip $Keep | ForEach-Object {
    $candidate = (Resolve-Path -LiteralPath $_.FullName).Path
    if (-not $candidate.StartsWith($resolvedBackup + '\', [StringComparison]::OrdinalIgnoreCase) -or ($_.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Unsafe backup retention target.' }
    Remove-Item -LiteralPath $candidate -Recurse -Force
}
Write-Output "Backup completed: $destination"
