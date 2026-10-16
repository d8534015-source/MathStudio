# MathStudio TURN config recovery: runs locally and never prints secrets.
param([string]$TargetDirectory = $PSScriptRoot)
$ErrorActionPreference = 'Stop'
$target = Join-Path $TargetDirectory 'media_config.bat'
if (Test-Path -LiteralPath $target) { exit 0 }
$homeDir = [Environment]::GetFolderPath('UserProfile')
$preferred = @(
  (Join-Path $homeDir 'Desktop\MathStudio_v39_OWNER_FreeMedia\MathStudio_v39_OWNER_FreeMedia\media_config.bat'),
  (Join-Path $homeDir 'Downloads\MathStudio_LAN_v21_Desktop_Overlay_Day_View\MathStudio_v21_Port5051\media_config.bat')
)
$candidates = [System.Collections.Generic.List[string]]::new()
foreach($item in $preferred){ if(Test-Path -LiteralPath $item){$candidates.Add($item)} }
if($candidates.Count -eq 0){
  foreach($folder in @('Desktop','Downloads','Documents')){
    $parent=Join-Path $homeDir $folder
    if(-not(Test-Path -LiteralPath $parent)){continue}
    Get-ChildItem -LiteralPath $parent -Filter media_config.bat -File -Recurse -ErrorAction SilentlyContinue |
      Where-Object { $_.FullName -match 'MathStudio' -and $_.FullName -ne $target } |
      Sort-Object LastWriteTime -Descending |
      ForEach-Object { $candidates.Add($_.FullName) }
  }
}
foreach($source in $candidates){
  if($source -eq $target){continue}
  # Only accept actual TURN configuration files, not empty placeholders.
  $content=Get-Content -LiteralPath $source -Raw -ErrorAction SilentlyContinue
  if($content -notmatch 'CLOUDFLARE_TURN_' -or $content -notmatch 'TOKEN'){continue}
  Copy-Item -LiteralPath $source -Destination $target -ErrorAction Stop
  Write-Host 'Reused an existing local MathStudio TURN configuration (credentials not displayed).'
  exit 0
}
Write-Host 'No existing TURN configuration found; skipping automatic import.'
