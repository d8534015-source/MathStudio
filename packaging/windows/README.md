# MathStudio Windows teacher installer

The installer build creates exactly one teacher-facing download: **MathStudio.exe**.
It embeds the x64 CPython runtime, Tcl/Tk, pinned libraries and client application.
It does not host OWNER. The development workflow artifacts also include checksums
and evidence for the owner/reviewer; those are not additional teacher prerequisites.

## Install and remove

1. Download the reviewed `MathStudio.exe` and verify its SHA-256 through the owner's
   trusted channel. The current build is unsigned unless an Authenticode certificate
   is explicitly applied and verified. Never disable Defender/SmartScreen or change
   system execution policy. Follow your organization's software approval policy.
2. Run it as the current user. No administrator elevation, Python, pip, VS Code,
   batch file or PowerShell script is needed on the teacher PC.
3. Optionally select the desktop shortcut. A per-user **MathStudio** Start menu
   shortcut and uninstall entry are created. Windows Search can discover that entry;
   actual search indexing/interaction still needs desktop verification.
4. Open MathStudio from Start. Enter the OWNER HTTPS origin and sign in with a
   teacher/admin account supplied privately by the owner. The application checks TLS,
   reachability and matching backend build before saving the URL in
   `%LOCALAPPDATA%\MathStudio\teacher_connection.json`. Only the public URL is stored.
5. Use **Student site / Settings → Change OWNER server**, or the same button on the
   login/connection-error screen, to update a changed tunnel URL without reinstalling.
   Finish live lessons before changing servers. Retry reconnects to the configured
   OWNER; the teacher's local port 5051 is irrelevant.
6. Remove via Windows **Settings → Apps → Installed apps → MathStudio → Uninstall**.
   Reinstall normally. User connection/language settings are retained intentionally;
   remove only the MathStudio settings JSON files manually if resetting preferences.
   Do not delete the entire data directory: an OWNER may share this Windows account.

## Rebuild (Windows x64)

Use CPython **3.13.12** x64 with Tcl/Tk and pip on a trusted build PC:

```
py -3.13 packaging\windows\build.py
```

The script checks the exact Python patch version, creates an isolated build venv,
installs hash-locked runtime and packaging dependencies, validates the source
manifest, generates the icon/file version metadata, freezes a windowless onedir
client with **PyInstaller 6.22.3**, and compiles a single installer with
**Inno Setup 7.1.0**. All transitive build tools are pinned in
`requirements-build.txt`; the Inno installer is pinned by upstream SHA-256.
Review upstream tool licenses, including Inno Setup's applicable usage terms,
before commercial redistribution. No private configuration is auto-discovered or
copied into the frozen application. The data selection is explicit in MathStudio.spec.

Outputs: `work\windows-build\installer\MathStudio.exe`, `SHA256SUMS.txt`,
`build-manifest.json`. This fixes inputs/tool versions; binary-identical output is
not claimed because PE/installer timestamps and signing vary. Builds must occur on
Windows; PyInstaller cannot cross-build a genuine Windows binary from Linux.

The PR workflow uses a Windows Server 2025 runner (not Windows 11) and records
installer, shortcut, uninstall/reinstall, Unicode path and bundled-runtime evidence.
It does not prove physical-device teaching or a clean Windows 11 machine test.
PowerShell is used only for trusted build/CI automation, not teacher or OWNER launch.

## Code signing

No signing key is included or requested in source. An authorized publisher must
use its legitimate certificate and identity. Sign `MathStudioClient.exe` after
freezing and before compiling Inno; configure Inno Setup `SignTool`/`SignedUninstaller`
with that publisher's trusted signing command to sign the installer and uninstaller.
Use SHA-256 file digests and the certificate provider's trusted RFC3161 timestamp
service. Verify `signtool verify /pa /all /v MathStudio.exe` and
`Get-AuthenticodeSignature` for installer, payload and uninstaller. Recompute the
final SHA-256 after signing and rerun installation/smoke tests. Signing establishes
publisher/integrity; it does not guarantee SmartScreen reputation or policy approval.
No automatic software update mechanism is added.

## OWNER startup corrections

OWNER remains source-hosted and separate. Its normal `START STUDENT WEBSITE.bat`
now runs the Python owner launcher directly, without `start_https.ps1`. No execution
policy change or unblocking step is required. Python owns the listening server in
its own console process and the tunnel is an owned child with a Windows kill-on-close
job. Ctrl+C closes this server and that tunnel; no unrelated process is terminated.
An existing server is reused or reported as occupied without touching lessons.
A running OWNER/dashboard from an older build must be stopped normally after lessons
before switching launchers. The old PowerShell file is only a compatibility wrapper.

## Manual acceptance still required

Clean Windows 11 VM without Python; English and Chinese display languages;
Start/Search and launch after reboot; desktop shortcut; first-run URL prompt;
valid HTTPS and teacher authentication; expired/changed tunnel URL, wrong build,
wrong password and recovery; live native annotations plus browser camera/audio;
physical iPhone/Android media; uninstall/reinstall and preserved preferences;
Ctrl+C and console-close OWNER cleanup with active unrelated Python processes.
Never interrupt a real lesson to run these tests.
