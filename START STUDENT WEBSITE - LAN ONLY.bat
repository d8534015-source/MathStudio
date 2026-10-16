@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0restore_media_config.ps1" -TargetDirectory "%~dp0."
title MathStudio Student Website - LAN only
if exist "%~dp0cloud_storage.bat" call "%~dp0cloud_storage.bat"
if exist "%~dp0media_config.bat" call "%~dp0media_config.bat"
set "BIND_HOST=0.0.0.0"
set "PORT=5051"
py server.py
if errorlevel 1 (
  where python.exe >nul 2>&1 && python server.py
)
echo.
pause
