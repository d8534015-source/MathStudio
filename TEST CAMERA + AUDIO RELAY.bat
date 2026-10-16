@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0media_config.bat" call "%~dp0media_config.bat"
if not defined CLOUDFLARE_TURN_KEY_ID goto missing
if not defined CLOUDFLARE_TURN_API_TOKEN goto missing
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$h=@{Authorization='Bearer '+$env:CLOUDFLARE_TURN_API_TOKEN}; try{$r=Invoke-RestMethod -Method Post -Uri ('https://rtc.live.cloudflare.com/v1/turn/keys/'+$env:CLOUDFLARE_TURN_KEY_ID+'/credentials/generate-ice-servers') -Headers $h -ContentType 'application/json' -Body '{\"ttl\":3600}' -TimeoutSec 12; if($r.iceServers){Write-Host 'SUCCESS: Cloudflare TURN credentials were generated.' -ForegroundColor Green; Write-Host ('ICE server entries: '+$r.iceServers.Count); exit 0}else{throw 'No ICE servers returned'}}catch{Write-Host ('FAILED: '+$_.Exception.Message) -ForegroundColor Red; exit 2}"
goto end
:missing
echo media_config.bat is missing or incomplete.
echo Run SETUP FREE CAMERA + AUDIO.bat first.
:end
echo.
pause
endlocal
