# Install MathStudio on Windows 11

The teacher needs **one file: MathStudio.exe**. Python, VS Code, pip, batch launchers and the other review files are not installation prerequisites.

1. Obtain MathStudio.exe through the owner's trusted delivery channel. The owner should compare its SHA-256 with SHA256SUMS.txt. This review build is unsigned; follow your organization's software approval policy and do not disable Defender, SmartScreen or other Windows protections.
2. Finish active lessons and close MathStudio before installing an upgrade or uninstalling.
3. Open MathStudio.exe and follow the installer. It installs for the current Windows user without requesting administrator elevation. Optionally select a desktop shortcut.
4. Open **Start → MathStudio**. A Start menu entry is installed for Windows Search discovery; interactive Search/reboot acceptance remains to be completed on Windows 11.
5. On first launch, enter the separately hosted OWNER server's **HTTPS root address**. Do not include a classroom path, password or token. The app validates the server connection and matching build before saving the public address locally.
6. Sign in with the teacher/admin account provided privately by the owner. The OWNER backend must stay running elsewhere; this application does not host it.
7. If the OWNER tunnel URL changes, use **Student site / Settings → Change OWNER server**, or **Change OWNER server** on the login/connection-error screen. Retry reconnects to the saved address. Finish lessons before changing servers; the dashboard signs out and clears old account/class cache.

To remove: **Windows Settings → Apps → Installed apps → MathStudio → Uninstall**.
Reinstall by opening MathStudio.exe again. Connection/language preferences are retained intentionally. Do not delete the entire MathStudio application-data folder: it may contain OWNER data for the same Windows account.

Connection settings: `%LOCALAPPDATA%\MathStudio\teacher_connection.json` (public URL only).
No OWNER credentials, TURN keys, databases or student files are included in the installer.

## 简体中文

教师仅需 **MathStudio.exe** 一个安装文件，无需另行安装 Python、VS Code 或运行批处理。结束课程后打开安装程序，按提示为当前用户安装，可选创建桌面快捷方式。从开始菜单打开 **MathStudio**，首次输入 OWNER 的 HTTPS 根地址，验证成功后使用所有者私下提供的教师账户登录。OWNER 后端必须在其他位置持续运行。

服务器地址变化时，在 **学生网站 / 设置 → 更改 OWNER 服务器** 中更新，也可在登录或连接错误页面更改，无需重新安装。卸载请使用 **Windows 设置 → 应用 → 已安装的应用 → MathStudio → 卸载**。此审核版本尚未签名，请遵循机构的软件审批要求，不要关闭 Windows 安全保护。
