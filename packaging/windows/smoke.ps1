# Executed by GitHub Actions on a disposable Windows runner, never on a teacher PC.
param([switch]$Review)
$ErrorActionPreference = 'Stop'
$build = Join-Path $env:GITHUB_WORKSPACE 'work\windows-build'
$installerName = if ($Review) { 'MathStudio-Website-Management-Review.exe' } else { 'MathStudio.exe' }
$productName = if ($Review) { 'MathStudio Review' } else { 'MathStudio' }
$stateFolder = if ($Review) { 'MathStudioReview' } else { 'MathStudio' }
$productId = if ($Review) { '{12720784-98AD-4CF5-B89F-90D4CF2B3BA1}' } else { '{E5935B86-2D46-45F3-8B46-E7A922F8A513}' }
$installer = Join-Path $build ('installer\' + $installerName)
$target = Join-Path $env:LOCALAPPDATA ('MathStudio install test 中文 ü ' + ('long folder ' * 5) + 'app')
$listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 5051)
$results = [ordered]@{os=[Environment]::OSVersion.VersionString; windows11=$false; install_path=$target; tests=@()}
function Check([bool]$ok, [string]$name) {
    if (-not $ok) { throw "FAILED: $name" }
    $script:results.tests += $name
    Write-Host "PASS: $name"
}
try {
    $listener.Start()
    $p = Start-Process $installer -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/CURRENTUSER',('/DIR="' + $target + '"'),('/LOG="' + (Join-Path $build 'installer\install-smoke.log') + '"')) -Wait -PassThru
    Check ($p.ExitCode -eq 0) 'Per-user install with port 5051 occupied and Unicode/space/long path'
    $exe = Join-Path $target 'MathStudioClient.exe'
    Check (Test-Path -LiteralPath $exe) 'Installed executable'
    Check ([bool](Get-ChildItem -LiteralPath $target -Recurse -Filter 'python313.dll')) 'Bundled Python runtime'
    Check (-not [bool](Get-ChildItem -LiteralPath $target -Recurse -Filter 'server.py')) 'No OWNER backend source'
    $shortcut = Join-Path ([Environment]::GetFolderPath('Programs')) ($productName + '.lnk')
    Check (Test-Path -LiteralPath $shortcut) 'Per-user Start menu shortcut registered'
    Copy-Item -LiteralPath $shortcut -Destination (Join-Path $build 'installer\MathStudio-shortcut.lnk')
    python packaging/windows/check_shortcut.py $shortcut $exe (Join-Path $build 'installer\shortcut-target.json')
    Check ($LASTEXITCODE -eq 0) 'Unicode Start menu shortcut targets installed application'
    $oldPath=$env:PATH; $oldPythonHome=$env:PYTHONHOME; $oldPythonPath=$env:PYTHONPATH
    $oldLocal=$env:LOCALAPPDATA
    try {
        # Application must launch using only its bundled interpreter and libraries.
        $env:PATH="$env:SystemRoot\System32"; $env:PYTHONHOME=''; $env:PYTHONPATH=''
        $env:LOCALAPPDATA=Join-Path $env:RUNNER_TEMP 'isolated settings 中文'
        $p = Start-Process $exe -ArgumentList '--self-test' -Wait -PassThru
        $startupError=Join-Path $env:LOCALAPPDATA ($stateFolder + '\teacher_startup_error.log')
        if (Test-Path -LiteralPath $startupError) { Copy-Item -LiteralPath $startupError -Destination (Join-Path $build 'installer\runtime-startup-error.log') }
        Check ($p.ExitCode -eq 0) 'Frozen GUI/native import self-test without Python on PATH'
        $report=Join-Path $env:LOCALAPPDATA ($stateFolder + '\installer-self-test.json')
        Check (Test-Path -LiteralPath $report) 'Bundled self-test evidence written'
        $data=Get-Content -LiteralPath $report -Raw -Encoding UTF8 | ConvertFrom-Json
        Check ($data.website_management -and $data.client_only) 'Frozen Website Management module and client-only role'
        Check ($data.frozen -and -not $data.console) 'Bundled runtime and no console window'
        Copy-Item -LiteralPath $report -Destination (Join-Path $build 'installer\runtime-self-test.json')
    } finally {
        $env:PATH=$oldPath; $env:PYTHONHOME=$oldPythonHome; $env:PYTHONPATH=$oldPythonPath; $env:LOCALAPPDATA=$oldLocal
    }
    $uninstallKey='HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\' + $productId + '_is1'
    Check (Test-Path $uninstallKey) 'Current-user uninstall registration'
    $uninstaller=Join-Path $target 'unins000.exe'
    $p=Start-Process $uninstaller -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') -Wait -PassThru
    Check ($p.ExitCode -eq 0 -and -not (Test-Path $exe)) 'Uninstall removes installed executable'
    Check (-not (Test-Path -LiteralPath $shortcut)) 'Uninstall removes Start menu shortcut'
    $p=Start-Process $installer -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/CURRENTUSER',('/DIR="' + $target + '"'),('/LOG="' + (Join-Path $build 'installer\install-smoke.log') + '"')) -Wait -PassThru
    Check ($p.ExitCode -eq 0 -and (Test-Path $exe)) 'Reinstall'
    $p=Start-Process $uninstaller -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') -Wait -PassThru
} finally {
    $listener.Stop()
    $results | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $build 'installer\windows-smoke-results.json') -Encoding UTF8
}
