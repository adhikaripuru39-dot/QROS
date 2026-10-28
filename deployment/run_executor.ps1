param([switch]$NoRestart)
. (Join-Path $PSScriptRoot 'common.ps1')
$runtime = Initialize-Qros
Start-QrosSupervised -Runtime $runtime -ServiceName 'executor' -NoRestart:$NoRestart -PythonArguments @('-B','-u','-m','qros.services.executor')
