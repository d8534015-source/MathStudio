@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0restore_media_config.ps1" -TargetDirectory "%~dp0."
title MathStudio Teacher App
set "APP=%~dp0teacher_desktop_app.py"

echo Starting MathStudio Teacher App...
where py.exe >nul 2>&1
if %errorlevel%==0 (
  py "%APP%"
  goto done
)
where python.exe >nul 2>&1
if %errorlevel%==0 (
  python "%APP%"
  goto done
)
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
  if exist "%%~fD\python.exe" (
    "%%~fD\python.exe" "%APP%"
    goto done
  )
)
echo.
echo Python 3 was not found. Install Python 3.11+ from python.org.
pause
exit /b 1

:done
if errorlevel 1 (
  echo.
  echo The Teacher App closed with an error.
  if exist "%~dp0teacher_app_error.log" (
    echo See teacher_app_error.log in this folder.
  )
  pause
)
