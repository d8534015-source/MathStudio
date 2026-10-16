$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

$port = 5051
$origin = "http://127.0.0.1:$port"
$runtime = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $runtime)) { throw 'Run SETUP MATHSTUDIO.bat first.' }

function Find-Cloudflared {
    $cmd = Get-Command cloudflared.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $cmd = Get-Command cloudflared -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    $candidates = @(
        'C:\Program Files (x86)\cloudflared\cloudflared.exe',
        'C:\Program Files\cloudflared\cloudflared.exe',
        (Join-Path $env:LOCALAPPDATA 'cloudflared\cloudflared.exe')
    )
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) { return $candidate }
    }
    return $null
}

$cloudflared = Find-Cloudflared
if (-not $cloudflared) {
    Write-Host ''
    Write-Host 'Cloudflared was not found.' -ForegroundColor Red
    Write-Host 'The normal LAN server still works with START STUDENT WEBSITE - LAN ONLY.bat, but browser media on another device needs HTTPS.'
    Write-Host 'Install cloudflared or place cloudflared.exe on PATH, then run this launcher again.'
    exit 1
}

$existing = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    try {
        $info = Invoke-RestMethod -Uri "$origin/api/desktop-info" -TimeoutSec 3
        $version = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'version.json') -Raw | ConvertFrom-Json
        if ($info.build -eq $version.build_id) {
            if ($info.public_origin -like 'https://*') {
                Write-Host ('Reusing the running MathStudio website: '+$info.public_origin)
                exit 0
            }
            throw 'A matching LAN server is running. Open the Teacher App to start its HTTPS tunnel, or stop the server after all classes end and retry.'
        }
    } catch { Write-Host 'Port 5051 is occupied. No process or live classroom was changed.' }
    Write-Host 'Use the matching Teacher App to manage the running server. Do not stop a live class.'
    exit 1
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$stdout = Join-Path $env:TEMP "mathstudio-cloudflared-$stamp.out.log"
$stderr = Join-Path $env:TEMP "mathstudio-cloudflared-$stamp.err.log"

Write-Host ''
Write-Host 'Starting secure MathStudio classroom link...' -ForegroundColor Cyan
$tunnel = Start-Process -FilePath $cloudflared `
    -ArgumentList @('tunnel','--url',$origin) `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr `
    -PassThru `
    -WindowStyle Hidden

try {
    $url = $null
    $deadline = (Get-Date).AddSeconds(35)
    while ((Get-Date) -lt $deadline -and -not $url) {
        Start-Sleep -Milliseconds 350
        if ($tunnel.HasExited) { break }
        $text = ''
        if (Test-Path $stdout) { $text += (Get-Content $stdout -Raw -ErrorAction SilentlyContinue) }
        if (Test-Path $stderr) { $text += "`n" + (Get-Content $stderr -Raw -ErrorAction SilentlyContinue) }
        $m = [regex]::Match($text, 'https://[a-z0-9-]+\.trycloudflare\.com', 'IgnoreCase')
        if ($m.Success) { $url = $m.Value }
    }

    if (-not $url) {
        Write-Host ''
        Write-Host 'Cloudflared did not produce an HTTPS address.' -ForegroundColor Red
        if (Test-Path $stderr) {
            Write-Host 'Recent cloudflared output:'
            Get-Content $stderr -Tail 20 -ErrorAction SilentlyContinue
        }
        exit 1
    }

    $env:BIND_HOST = '0.0.0.0'
    $env:PORT = "$port"
    $env:PUBLIC_ORIGIN = $url
    # This launcher owns a local cloudflared connector. Trust only its loopback
    # peer address for CF-Connecting-IP; direct LAN clients remain untrusted.
    $env:MATH_TRUSTED_PROXIES = '127.0.0.1/32,::1/128'

    Write-Host ''
    Write-Host '============================================================' -ForegroundColor Green
    Write-Host '  MATHSTUDIO SECURE CLASSROOM' -ForegroundColor Green
    Write-Host ''
    Write-Host "  $url" -ForegroundColor Yellow
    Write-Host ''
    Write-Host '  Open THIS HTTPS address on the teacher and student devices.'
    Write-Host '  Do NOT use the http://10.x / 192.168.x LAN address for live media.' -ForegroundColor Yellow
    Write-Host '  Camera, microphone, and screen sharing can request permission only on the secure URL.'
    Write-Host '  TURN: the server loads private configuration. Verify relay access with TEST CAMERA + AUDIO RELAY.bat.'
    Write-Host '============================================================' -ForegroundColor Green
    Write-Host ''
    Write-Host 'This temporary URL changes each time you restart the HTTPS launcher.'
    Write-Host 'Keep this window open. Ctrl+C stops MathStudio; closing it also ends the tunnel.'
    Write-Host ''

    $python = $env:MATH_PYTHON
    if (-not $python) { $python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe' }
    & $python (Join-Path $PSScriptRoot 'server.py')
    if ($LASTEXITCODE -ne 0) { throw 'The website could not start. Review the error above.' }
}
finally {
    if ($tunnel -and -not $tunnel.HasExited) {
        Stop-Process -Id $tunnel.Id -Force -ErrorAction SilentlyContinue
    }
    Remove-Item $stdout,$stderr -Force -ErrorAction SilentlyContinue
}
