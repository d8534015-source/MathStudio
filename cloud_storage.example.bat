@echo off
REM Copy this file to cloud_storage.bat and fill in your own Cloudflare R2 credentials.
REM Do NOT upload or share cloud_storage.bat because it contains secrets.
set "MATH_R2_ACCOUNT_ID=YOUR_ACCOUNT_ID"
set "MATH_R2_ACCESS_KEY_ID=YOUR_R2_ACCESS_KEY_ID"
set "MATH_R2_SECRET_ACCESS_KEY=YOUR_R2_SECRET_ACCESS_KEY"
set "MATH_R2_BUCKET=mathstudio-files"
REM Optional: maximum size of one upload, in MB (default 100; maximum 500).
set "MATH_MAX_UPLOAD_MB=100"
