@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0.venv\Scripts\python.exe" goto setup
"%~dp0.venv\Scripts\python.exe" "%~dp0private_config.py" test-turn
set "RESULT=%errorlevel%"
pause
exit /b %RESULT%
:setup
echo Run SETUP MATHSTUDIO.bat first.
pause
exit /b 1
