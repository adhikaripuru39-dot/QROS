param([switch]$Install)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if (-not $Install) { throw 'Explicit opt-in required: run with -Install to register login-session supervision tasks.' }
. (Join-Path $PSScriptRoot 'common.ps1')
$runtime = Initialize-Qros
$identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$shellPath = (Get-Process -Id $PID).Path
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $identity
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -StartWhenAvailable
foreach ($service in @('backend','executor','worker','data')) {
    $scriptPath = Join-Path $PSScriptRoot "run_$service.ps1"
    $action = New-ScheduledTaskAction -Execute $shellPath -Argument "-NoProfile -NonInteractive -WindowStyle Hidden -File `"$scriptPath`"" -WorkingDirectory $runtime.Root
    # No Force: an existing task must be reviewed rather than silently replaced.
    Register-ScheduledTask -TaskName "QROS-$service" -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'QROS opt-in login-session supervisor; executor crash recovery pauses entries.' | Out-Null
}
Write-Output 'Registered QROS login-session tasks. They have not been started. MT5 requires the same logged-in Windows user session.'
