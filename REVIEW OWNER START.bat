@echo off
setlocal
cd /d "%~dp0"
py -3.13 owner_review.py start %*
if errorlevel 1 echo Review launch stopped. Read the message above and REVIEW_OWNER_README.md.
pause
