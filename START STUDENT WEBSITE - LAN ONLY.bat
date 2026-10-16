@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0.venv\Scripts\python.exe" goto setup
"%~dp0.venv\Scripts\python.exe" "%~dp0runtime_setup.py" --launch server
set "RESULT=%errorlevel%"
echo Student website stopped. Read INSTALL_WINDOWS.md for recovery.
pause
exit /b %RESULT%
:setup
echo First double-click SETUP MATHSTUDIO.bat in this folder.
pause
exit /b 1
