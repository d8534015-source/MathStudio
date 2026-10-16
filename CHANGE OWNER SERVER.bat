@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0.venv\Scripts\python.exe" goto setup
"%~dp0.venv\Scripts\python.exe" "%~dp0runtime_setup.py" --configure-owner
if errorlevel 1 pause
exit /b %errorlevel%
:setup
echo Run SETUP MATHSTUDIO.bat first.
pause
exit /b 1
