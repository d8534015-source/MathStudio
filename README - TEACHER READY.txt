MathStudio v41.6.6 — TEACHER READY (remote client)

This package DOES NOT HOST THE BACKEND. The OWNER computer/server must
already run the matching OWNER package and provide its public HTTPS URL.
It contains no server.py, website launchers, databases, accounts or TURN keys.

1. Install a supported current 64-bit Python 3.12, 3.13 or 3.14 from python.org,
   including pip, Tcl/Tk and the Python launcher. No VS Code is needed.
2. Extract the ENTIRE ZIP to a normal writable folder. Keep package_role.json.
3. Double-click SETUP MATHSTUDIO.bat once. Internet access to PyPI is needed.
4. Double-click OPEN MATHSTUDIO TEACHER.bat. Enter the OWNER HTTPS origin
   when asked. The app checks TLS and the matching OWNER build before saving.
   Example: https://your-owner-host.example (no /classroom path).
5. Sign in using a teacher/admin account supplied privately by the owner.
6. Start a scheduled or instant meeting. The native annotation toolbar runs
   on YOUR Windows PC; browser camera/audio connects to the OWNER website.
7. To change the OWNER address while signed in, use Student site / Settings
   -> Change OWNER server. Finish active lessons first; changing signs you out.
   If the old server is offline, close the app and double-click CHANGE OWNER SERVER.bat. This matters when a temporary tunnel URL changes.

The saved server URL contains no password. Login passwords are not bundled.
Do NOT configure TURN or cloud storage on the teacher PC; OWNER handles those.
Use HTTPS with a trusted certificate. Never disable Windows security protections.

This is an unsigned Python-source package with Windows BAT launchers, not a
signed EXE installer and not a bundled Python distribution. Windows installation,
physical cameras/audio, native annotations and iPhone/Android remain unverified
in Cloud. Both OWNER and TEACHER READY must show the same version.json build.
See DELIVERY_CHECKLIST.md for the actual verification results and limitations.

中文：这是连接远程 OWNER 的教师客户端，不在本机运行服务器。先安装支持的
64 位 Python（包含 pip 和 Tcl/Tk），完整解压后运行 SETUP MATHSTUDIO.bat。
成功后双击 OPEN MATHSTUDIO TEACHER.bat，输入 OWNER 的 HTTPS 地址并登录。
地址改变时使用 CHANGE OWNER SERVER.bat。无需 VS Code，也不要关闭安全保护。
