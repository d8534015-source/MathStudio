param([Parameter(Mandatory=$true)][string]$SourcePath, [switch]$Replace)
$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Run SETUP MATHSTUDIO.bat first.' }
$arguments = @((Join-Path $PSScriptRoot 'private_config.py'),'import','--from-path',$SourcePath)
if ($Replace) { $arguments += '--replace' }
& $python @arguments
exit $LASTEXITCODE
