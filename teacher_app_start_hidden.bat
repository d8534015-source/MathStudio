@echo off
cd /d "%~dp0"
set "APP=%~dp0teacher_desktop_app.py"

where pyw.exe >nul 2>&1
if %errorlevel%==0 (
  start "MathStudio Teacher" pyw.exe "%APP%"
  exit /b 0
)
where pythonw.exe >nul 2>&1
if %errorlevel%==0 (
  start "MathStudio Teacher" pythonw.exe "%APP%"
  exit /b 0
)
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
  if exist "%%~fD\pythonw.exe" (
    start "MathStudio Teacher" "%%~fD\pythonw.exe" "%APP%"
    exit /b 0
  )
)
REM If no pythonw is found, deliberately open the visible diagnostic launcher.
start "MathStudio Teacher" cmd.exe /c "\"%~dp0START TEACHER APP.bat\""
exit /b 0
