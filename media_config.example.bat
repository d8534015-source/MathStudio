@echo off
REM MathStudio v39 media configuration.
REM Preferred free option: Cloudflare Realtime TURN.
REM Keep this file PRIVATE. Never send the token in chat or commit media_config.bat to GitHub.
set "CLOUDFLARE_TURN_KEY_ID=YOUR_TURN_KEY_ID"
set "CLOUDFLARE_TURN_API_TOKEN=YOUR_TURN_KEY_TOKEN"

REM Optional legacy/static TURN fallback:
REM set "TURN_URL=turn:YOUR_TURN_HOST:3478?transport=udp"
REM set "TURN_USERNAME=YOUR_TURN_USERNAME"
REM set "TURN_CREDENTIAL=YOUR_TURN_PASSWORD"
