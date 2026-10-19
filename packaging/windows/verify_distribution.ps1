$ErrorActionPreference = 'Stop'
$build = Join-Path $PSScriptRoot '..\..\work\windows-build'
$installer = Join-Path $build 'installer\MathStudio-Classroom-Review.exe'
$signature = Get-AuthenticodeSignature -LiteralPath $installer
$report = [ordered]@{
    authenticode = [string]$signature.Status
    trusted_signing_performed = $false
    defender = 'unavailable'
    threats_in_build = $null
}
# Inspect only this synthetic build. Never change Defender configuration.
try {
    $status = Get-MpComputerStatus -ErrorAction Stop
    if ($status.AntivirusEnabled -and $status.AMServiceEnabled) {
        Start-MpScan -ScanType CustomScan -ScanPath $build -ErrorAction Stop
        $detections = @(Get-MpThreatDetection -ErrorAction Stop | Where-Object {
            $matched = $false
            foreach ($resource in $_.Resources) {
                if ($resource.IndexOf([IO.Path]::GetFullPath($build), [StringComparison]::OrdinalIgnoreCase) -ge 0) { $matched = $true }
            }
            $matched
        })
        $report.defender = 'scan_completed'
        $report.threats_in_build = $detections.Count
    } else { $report.defender = 'service_not_enabled_on_runner' }
} catch {
    # Availability is a limitation, never a successful scan or a clean verdict.
    $report.defender = 'scan_not_completed'
}
$report | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $build 'installer\distribution-security.json') -Encoding utf8
if ($report.threats_in_build -gt 0) { throw 'Defender reported a threat in the review build; do not distribute it.' }
Write-Host ('Authenticode status: ' + $report.authenticode + '; Defender: ' + $report.defender)
