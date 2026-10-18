@echo off
setlocal
cd /d "%~dp0"
echo MathStudio OWNER - optional free offline English/Chinese translation.
echo Stop OWNER and finish all lessons first. This setup downloads models once.
echo Teacher Ready does not need this setup. No key or translation account is required.
where py.exe >nul 2>&1
if errorlevel 1 goto missing
py -3.13 "%~dp0argos_setup.py" install
set "RESULT=%errorlevel%"
goto done
:missing
echo Install 64-bit Python 3.13 from python.org, including pip, then try again.
set "RESULT=1"
:done
if not "%RESULT%"=="0" echo Setup did not finish. Read ARGOS_OFFLINE_SETUP.md. Existing classroom and originals are unchanged.
pause
exit /b %RESULT%
