param([string]$BindAddress = '127.0.0.1', [ValidateRange(1024,65535)][int]$Port = 8000, [switch]$NoRestart)
. (Join-Path $PSScriptRoot 'common.ps1')
$runtime = Initialize-Qros
Start-QrosSupervised -Runtime $runtime -ServiceName 'api' -NoRestart:$NoRestart -PythonArguments @('-B','-u','-m','uvicorn','qros.api.app:create_app','--factory','--host',$BindAddress,'--port',"$Port",'--workers','1')
