@echo off
setlocal
cd /d "%~dp0"
title MathStudio - Free Camera and Audio Setup
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_free_media.ps1"
if errorlevel 1 (
  echo.
  echo Setup was not completed.
)
echo.
pause
endlocal
