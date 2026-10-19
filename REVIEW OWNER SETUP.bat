@echo off
setlocal
cd /d "%~dp0"
py -3.13 owner_review.py setup %*
if errorlevel 1 echo Review setup failed. Read the message above and REVIEW_OWNER_README.md.
pause
