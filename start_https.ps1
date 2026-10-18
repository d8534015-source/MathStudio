# Compatibility entry point only. Normal OWNER launch uses Python, not PowerShell.
# Do not change execution policy to run this file.
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot '.venv\Scripts\python.exe') (Join-Path $PSScriptRoot 'runtime_setup.py') --launch website
exit $LASTEXITCODE
