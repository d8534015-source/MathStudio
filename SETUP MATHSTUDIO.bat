@echo off
setlocal
cd /d "%~dp0"
echo MathStudio setup - close all MathStudio lessons before continuing.
echo This creates a private Python environment with verified package hashes.
where py.exe >nul 2>&1
if errorlevel 1 goto python
py -3 "%~dp0runtime_setup.py" --install
set "RESULT=%errorlevel%"
goto done
:python
where python.exe >nul 2>&1
if errorlevel 1 goto missing
python.exe "%~dp0runtime_setup.py" --install
set "RESULT=%errorlevel%"
goto done
:missing
echo Install current supported 64-bit Python 3.12, 3.13 or 3.14 from python.org.
echo Include pip and Tcl/Tk. Then run this setup again. VS Code is not needed.
set "RESULT=1"
:done
if not "%RESULT%"=="0" echo Setup did not finish. See INSTALL_WINDOWS.md for recovery steps.
pause
exit /b %RESULT%
