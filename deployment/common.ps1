Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Initialize-Qros {
    param([string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot))
    $root = (Resolve-Path -LiteralPath $ProjectRoot).Path
    if (-not (Test-Path -LiteralPath (Join-Path $root '.env') -PathType Leaf)) {
        throw 'Supply a private .env in the project root before starting QROS. See .env.example.'
    }
    $python = Join-Path $root 'backend\.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        throw 'Backend virtual environment is missing. Run deployment/setup_vps.ps1 first.'
    }
    $env:QROS_ENV = 'prod'
    # Crash recovery always requires owner resume; this supervisor cannot arm entries.
    $env:QROS_RESUME_ON_RESTART = 'false'
    Push-Location (Join-Path $root 'backend')
    try {
        & $python -B -c "from qros.config.settings import Settings; s=Settings(); token=s.api_token.get_secret_value(); assert len(token)>=32 and token.lower() not in ('change-me','changeme'), 'Supply a strong API token (32+ characters)'; print('Environment validated; secrets withheld')" | Out-Host
        if ($LASTEXITCODE -ne 0) { throw 'QROS environment validation failed.' }
    } finally { Pop-Location }
    $logDir = Join-Path $root 'var\logs'
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    return @{ Root = $root; Python = $python; LogDir = $logDir }
}

function Remove-QrosOldLogs {
    param([string]$LogDir, [string]$ServiceName, [int]$Keep = 30)
    $resolvedLogs = (Resolve-Path -LiteralPath $LogDir).Path
    Get-ChildItem -LiteralPath $resolvedLogs -File -Filter "$ServiceName-*.log" |
        Sort-Object LastWriteTime -Descending | Select-Object -Skip $Keep | ForEach-Object {
            $candidate = [IO.Path]::GetFullPath($_.FullName)
            if (-not $candidate.StartsWith($resolvedLogs + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
                throw 'Log retention target escaped its intended directory.'
            }
            if (($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Refusing to prune linked log file.' }
            Remove-Item -LiteralPath $candidate -Force
        }
}

function Start-QrosSupervised {
    param([hashtable]$Runtime, [string]$ServiceName, [string[]]$PythonArguments, [switch]$NoRestart)
    $attempt = 0
    Push-Location (Join-Path $Runtime.Root 'backend')
    try {
        do {
            $startedAt = Get-Date
            $stamp = $startedAt.ToUniversalTime().ToString('yyyyMMdd-HHmmss-fff')
            $logFile = Join-Path $Runtime.LogDir "$ServiceName-$stamp.log"
            Remove-QrosOldLogs -LogDir $Runtime.LogDir -ServiceName $ServiceName
            $script:qrosLogFile = $logFile
            $script:qrosLineCount = 0
            # Windows PowerShell 5 represents native stderr as ErrorRecord objects.
            # Preserve output and use the actual exit code for supervisor recovery.
            $savedErrorPreference = $ErrorActionPreference
            $ErrorActionPreference = 'Continue'
            try {
            & $Runtime.Python @PythonArguments 2>&1 | ForEach-Object {
                $line = $_.ToString()
                Write-Output $line
                Add-Content -LiteralPath $script:qrosLogFile -Value $line -Encoding UTF8
                $script:qrosLineCount++
                if ($script:qrosLineCount % 100 -eq 0 -and (Get-Item -LiteralPath $script:qrosLogFile).Length -gt 15728640) {
                    $nextStamp = (Get-Date).ToUniversalTime().ToString('yyyyMMdd-HHmmss-fff')
                    $script:qrosLogFile = Join-Path $Runtime.LogDir "$ServiceName-$nextStamp.log"
                    Remove-QrosOldLogs -LogDir $Runtime.LogDir -ServiceName $ServiceName
                }
            }
            $exitCode = $LASTEXITCODE
            } finally { $ErrorActionPreference = $savedErrorPreference }
            if ($NoRestart) {
                if ($exitCode -ne 0) { throw "$ServiceName exited with code $exitCode" }
                return
            }
            if (((Get-Date) - $startedAt).TotalSeconds -gt 300) { $attempt = 0 }
            $attempt++
            $backoff = [Math]::Min(30, [Math]::Pow(2, [Math]::Min($attempt, 5)))
            Write-Warning "$ServiceName exited ($exitCode); restarting in $backoff seconds with entries paused."
            Start-Sleep -Seconds $backoff
        } while ($true)
    } finally { Pop-Location }
}
