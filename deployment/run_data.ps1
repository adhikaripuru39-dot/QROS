param([switch]$NoRestart,[switch]$Once,[double]$IntervalSeconds = 3600)
if ($IntervalSeconds -le 0) { throw 'Positive data synchronization interval required.' }
. (Join-Path $PSScriptRoot 'common.ps1')
$runtime = Initialize-Qros
$arguments = @('-B','-u','-m','qros.services.data_worker','--interval-seconds', $IntervalSeconds.ToString([Globalization.CultureInfo]::InvariantCulture))
if ($Once) { $arguments += '--once' }
Start-QrosSupervised -Runtime $runtime -ServiceName 'data_worker' -NoRestart:($NoRestart -or $Once) -PythonArguments $arguments
