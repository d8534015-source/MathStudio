$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Run SETUP MATHSTUDIO.bat first.' }
& $python (Join-Path $PSScriptRoot 'private_config.py') configure-turn
exit $LASTEXITCODE
