@echo off
REM Keep startup errors visible; no unverified pythonw or executable fallback.
call "%~dp0OPEN MATHSTUDIO TEACHER.bat"
exit /b %errorlevel%
