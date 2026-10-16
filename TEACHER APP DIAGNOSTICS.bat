@echo off
cd /d "%~dp0"
title MathStudio Teacher App Diagnostics
echo ============================================================
echo MathStudio Teacher App diagnostics
echo ============================================================
echo.
echo [1] Python
where py.exe
where python.exe
echo.
echo [2] Tkinter test
py -c "import tkinter as tk; r=tk.Tk(); r.withdraw(); print('Tkinter OK'); r.destroy()"
echo.
echo [3] Website server on port 5051
powershell -NoProfile -Command "$x=Get-NetTCPConnection -LocalPort 5051 -State Listen -ErrorAction SilentlyContinue; if($x){Write-Host 'Port 5051 is listening.' -ForegroundColor Green}else{Write-Host 'Port 5051 is OFFLINE. Start START STUDENT WEBSITE.bat first.' -ForegroundColor Yellow}"
echo.
echo [4] Starting Teacher App visibly...
py teacher_desktop_app.py
echo.
echo If it failed, send teacher_app_error.log or a screenshot of this window.
pause
