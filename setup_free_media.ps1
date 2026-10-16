$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
Write-Host ''
Write-Host 'MathStudio free camera + audio setup' -ForegroundColor Cyan
Write-Host 'Uses Cloudflare Realtime TURN. Your long-lived TURN token stays on this computer.'
Write-Host ''
$keyId = (Read-Host 'Paste your Cloudflare Realtime TURN Key ID').Trim()
if (-not $keyId) { throw 'No TURN Key ID entered.' }
$secure = Read-Host 'Paste the TURN Key token (input hidden)' -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try { $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
if (-not $token) { throw 'No TURN Key token entered.' }
$lines = @(
  '@echo off',
  'REM Private MathStudio TURN credentials - do not share this file.',
  ('set "CLOUDFLARE_TURN_KEY_ID={0}"' -f $keyId),
  ('set "CLOUDFLARE_TURN_API_TOKEN={0}"' -f $token)
)
[IO.File]::WriteAllLines((Join-Path $PSScriptRoot 'media_config.bat'), $lines, [Text.UTF8Encoding]::new($false))
Write-Host ''
Write-Host 'Saved media_config.bat successfully.' -ForegroundColor Green
Write-Host 'Restart MathStudio Student Website so the TURN relay is loaded.'
