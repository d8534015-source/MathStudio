@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0restore_media_config.ps1" -TargetDirectory "%~dp0."
title MathStudio v41.6.6 Student Website - port 5051
echo MathStudio v41.6.6 starting on port 5051

if exist "%~dp0cloud_storage.bat" call "%~dp0cloud_storage.bat"
if exist "%~dp0media_config.bat" call "%~dp0media_config.bat"

set "PORT=5051"
set "BIND_HOST=0.0.0.0"

REM Prefer the HTTPS/Cloudflare launcher because student camera/microphone need HTTPS.
where cloudflared.exe >nul 2>&1
if %errorlevel%==0 goto secure
where cloudflared >nul 2>&1
if %errorlevel%==0 goto secure
if exist "C:\Program Files (x86)\cloudflared\cloudflared.exe" goto secure
if exist "C:\Program Files\cloudflared\cloudflared.exe" goto secure

:lan
echo.
echo ============================================================
echo   MATHSTUDIO STUDENT WEBSITE - LAN MODE
echo   Port: 5051
echo ============================================================
echo.
echo Cloudflared was not found, so this launch uses LAN HTTP.
echo Booking, resources and messages work. Camera/microphone on other
echo devices may require the HTTPS launcher later.
echo.
py server.py
if errorlevel 1 goto python_fallback
goto end

:secure
echo Starting the student website and secure HTTPS link...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_https.ps1"
goto end

:python_fallback
where python.exe >nul 2>&1
if %errorlevel%==0 (
  python server.py
  goto end
)
echo.
echo Python was not found. Install Python 3.11+ from python.org.

:end
echo.
echo Student website stopped. Press any key to close this window.
pause >nul
endlocal
