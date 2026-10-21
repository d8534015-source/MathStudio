For the latest isolated responsive toolbar/recording review, use [LAYOUT_REVIEW.md](LAYOUT_REVIEW.md).

# Recording upgrade review candidate

For this candidate read `STOP_INPUT_REVIEW.md` first. Its OWNER port/profile, teacher installer AppID/profile, policy/legal draft gates and optional trusted FFmpeg setup differ from the historical general instructions below. Earlier PR9/PR10 and production installs remain separate.

# Windows installer development

For the bundled teacher installer **MathStudio.exe** (no separate Python or BAT launchers), see [installer instructions](packaging/windows/README.md). The source/OWNER instructions below apply only to source distributions. See the installer PR test report for actual Windows build status.

# MathStudio v41.6.6 — Windows installation

Build: `v41.6.6-delivery-candidate1`.

**TEACHER READY is a remote client.** Follow `README - TEACHER READY.txt`: setup once, open the Teacher launcher, supply the OWNER HTTPS origin and sign in. It never hosts a backend, creates local accounts, or configures TURN. The instructions below apply to the **OWNER backend computer** unless stated otherwise. This is a source release candidate, not a signed Windows installer. No VS Code, compiler, administrator account, or development environment is needed for normal use. A Windows 10/11 x64 computer and supported 64-bit CPython with Tcl/Tk and pip are required. Windows installation and physical-device media acceptance are still pending.

## OWNER first installation

1. Obtain the reviewed OWNER or TEACHER READY source candidate from the owner. Verify its SHA-256 against the manifest/checksum obtained through a trusted channel. Extract the whole ZIP once; do not run files inside the ZIP or mix application versions. A normal writable folder such as Documents\MathStudio is suitable. Keep all files together, including `version.json` and `requirements.txt`.
2. Install a currently supported 64-bit CPython 3.12, 3.13, or 3.14 from **https://www.python.org/downloads/windows/**. Include pip, Tcl/Tk and the Python launcher. Use the current security update for your selected series. This Cloud validation used CPython 3.12.14 on Linux; the exact Windows interpreter/installer hash must be recorded during Windows acceptance. Python itself is not bundled.
3. Close all MathStudio classes and stop the website before setup. Double-click **SETUP MATHSTUDIO.bat**. It creates `.venv`, installs the exact hashed wheels, checks dependencies/timezones/Tk, and shows success or a visible error. Internet access to PyPI is needed the first time. OWNER setup refuses to run while port 5051 is listening; client-only Teacher Ready setup does not inspect or reserve that port. Re-running setup recreates this application's `.venv`; keep personal files out of that directory.
4. For separately hosted delivery, first start **START STUDENT WEBSITE.bat** on OWNER. It prompts for the first admin account in its terminal if needed and keeps the backend/tunnel running. Then double-click **OPEN MATHSTUDIO TEACHER.bat** on OWNER for local administration. Alternatively, On a fresh computer, create the first teacher account in the dialog, then sign in. Use a unique password of at least 12 characters. The app starts the website if absent and reuses a matching healthy server. It never stops a process occupying port 5051. `START TEACHER APP.bat` is a compatibility alias.
5. For remote camera/microphone use, install **cloudflared** from https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/ . Verify the official download's provenance/hash and record its version during Windows acceptance. The package does not bundle or download cloudflared automatically. The Teacher App's existing tunnel feature uses the installed tool; share the HTTPS student link shown in the app. LAN HTTP is useful for bookings/files but is insufficient for media on other devices.
6. Configure TURN using **SETUP FREE CAMERA + AUDIO.bat**, then **TEST CAMERA + AUDIO RELAY.bat**. The token input is hidden, and the checker reports success/failure without credentials. Restart the website outside class time to apply changed configuration. HTTPS alone does not guarantee relay connectivity.

The website can also be started visibly with `START STUDENT WEBSITE.bat`; `START STUDENT WEBSITE - LAN ONLY.bat` forces LAN mode. The normal HTTPS launcher now uses Python directly, with the backend in the console process and only its own tunnel cleaned up on exit. It does not execute a PowerShell script or require execution-policy changes. Do not disable Windows protections, unblock an unknown executable, or bypass SmartScreen to make an unsigned package run.

## Private files and existing installations

New installations keep state outside the application folder:

- Database/resources: `%LOCALAPPDATA%\MathStudio\data`.
- TURN/R2 configuration: `%LOCALAPPDATA%\MathStudio\private_config.json`.
- Native startup log: `%LOCALAPPDATA%\MathStudio\teacher_app_error.log`.
- Website startup log: `%LOCALAPPDATA%\MathStudio\server_startup.log`.
- Teacher UI language preferences retain their existing `%APPDATA%\MathStudio` location.

`MATH_DATA` and `MATH_CONFIG` may explicitly select alternate locations. If the application folder already contains `bulletin_data`, it is preserved and used in place; nothing automatically moves or deletes it. Before an upgrade, finish lessons, stop all MathStudio processes, and back up the **entire** active data directory, configuration and preferences to private storage. Never send those files with a Teacher Ready ZIP.

Extract upgrades to a separate versioned folder and run setup there. For a legacy in-folder database, copy the entire backed-up `bulletin_data` directory into the new application folder, or set `MATH_DATA` explicitly to the original data directory. Keep file storage and database together. Confirm accounts, resources and bookings before teaching. Do not run old and new builds concurrently against the same data. A mismatched server build is rejected; stop it only after classes finish.

**Timezone note:** the runtime now uses pinned IANA 2026d on every OS. That data keeps Edmonton at UTC−6 in November 2026, while some system/browser databases still change to UTC−7. Existing stored timestamps are not rewritten. Review future bookings against the studio's intended local time when upgrading; do not bulk-edit student bookings automatically.

## Explicit configuration migration

Old `media_config.bat` and `cloud_storage.bat` files are **never searched for, copied, or executed automatically**. Select a trusted file yourself. In a command prompt opened in the new application folder:

```bat
".venv\Scripts\python.exe" private_config.py import --from-path "C:\chosen trusted folder\media_config.bat"
".venv\Scripts\python.exe" private_config.py import --from-path "C:\chosen trusted folder\cloud_storage.bat"
".venv\Scripts\python.exe" private_config.py check
```

Only quoted, allowlisted `set "KEY=value"` assignments and comments are accepted. Other commands, duplicate assignments and placeholders cause an error. Values are treated literally, not expanded or executed. Differing existing values require an explicit `--replace` after review. The parser cannot prove credentials are current; test the selected TURN account explicitly. Logs show configured **field names**, never values. JSON files inherit the user's Windows profile permissions; review their ACL so other ordinary users cannot read them. Do not store them in a shared/synced public folder.

## Recovery, offline setup and shutdown

- **Python missing/unsupported:** install a supported x64 Python with Tcl/Tk and pip. If `py -3` selects an unsupported interpreter, run `py -3.13 runtime_setup.py --install` (or your supported series) in this folder. Do not use Python from an unrelated virtual environment.
- **Download/hash/install failure:** retain the failure output, verify network and trusted source, and rerun setup outside class time. Never remove hash checks or install arbitrary fallback versions.
- **Offline setup:** on a trusted online Windows computer of the **same Python series and architecture**, run `py -3.13 -m pip download --require-hashes --only-binary=:all: -r requirements.txt -d wheelhouse`. Copy those wheels and the source candidate privately, then run `py -3.13 runtime_setup.py --install --wheelhouse "D:\verified wheelhouse"`. The same hashes are enforced. Offline Windows installation is not Cloud-verified.
- **Port 5051 busy/build mismatch:** do not kill an unknown process. Finish any live class and close the corresponding website terminal normally. Confirm that the intended build is running via `/api/desktop-info`; then reopen the matching Teacher App.
- **Startup errors:** use `TEACHER APP DIAGNOSTICS.bat` and the private logs above. Redact personal data, paths and credentials before sharing logs. The diagnostic launcher does not start a second app or show secrets.
- **Shutdown:** closing the dashboard leaves its website process running. End live classes first; stop a visible website using Ctrl+C. For a dashboard-started hidden website, use Windows Task Manager to identify its `.venv\Scripts\python.exe ... server.py` command line and end **only that process** after all classes finish. A dedicated graceful shutdown UI remains a limitation.
- **Rollback:** stop the new build, restore your private pre-upgrade backup, and reopen the previous verified package with its matching runtime. Do not overwrite a live database. Phase 2C introduces no schema migration; package rollback alone does not undo lessons/bookings made after upgrading.

## 中文快速开始

从可信来源获取并核对文件校验值，完整解压安装包。安装受支持的 64 位 Python 3.12、3.13 或 3.14，并包含 pip、Tcl/Tk 和 Python 启动器。无需 VS Code。结束所有课程并停止网站后，先双击 **SETUP MATHSTUDIO.bat**，成功后双击 **OPEN MATHSTUDIO TEACHER.bat**。首次使用时创建教师账户并登录。远程音视频需要可信安装的 cloudflared、HTTPS 学生链接及 TURN 配置。配置前请阅读上述凭据迁移和备份说明；不要分享数据库、学生文件或 TURN 密钥，也不要关闭 Windows 安全保护。此版本仍需完成 Windows/iPhone/Android 真机验收和正式签名。
