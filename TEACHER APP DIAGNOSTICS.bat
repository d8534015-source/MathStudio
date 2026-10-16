@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0.venv\Scripts\python.exe" goto setup
"%~dp0.venv\Scripts\python.exe" "%~dp0runtime_setup.py" --verify
if errorlevel 1 goto done
"%~dp0.venv\Scripts\python.exe" "%~dp0private_config.py" check
:done
pause
exit /b 0
:setup
echo Run SETUP MATHSTUDIO.bat first.
pause
exit /b 1
