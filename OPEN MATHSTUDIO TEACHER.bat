@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0.venv\Scripts\python.exe" goto setup
"%~dp0.venv\Scripts\python.exe" "%~dp0runtime_setup.py" --launch teacher
set "RESULT=%errorlevel%"
if not "%RESULT%"=="0" pause
exit /b %RESULT%
:setup
echo First double-click SETUP MATHSTUDIO.bat in this folder.
echo Read INSTALL_WINDOWS.md. No VS Code is required.
pause
exit /b 1
