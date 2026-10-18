# MathStudio Windows installer delivery verification

## Delivered artifact and provenance

- File: `installer-review/MathStudio.exe` — **15,979,616 bytes**, genuine Inno Setup installer, not a placeholder or a source ZIP.
- SHA-256: `c05b5e9f160d0c9dddb428128dab1ddd3d87527d5fb6ed7e97094f494d8990cc`.
- Status: **unsigned review candidate**. No signing credentials were available. Signing and Windows 11 interactive acceptance remain outstanding.
- Successful real Windows build/test run: https://github.com/d8534015-source/MathStudio/actions/runs/39165705626
- Reviewed source head: `b76e32cd38c4325770781598fdd97d0829c724af`; Actions tested its PR merge snapshot `6841abf8028d49a778e99eb410c4410f882ef762`.
- Baseline: latest delivery `2249e4cb1dc69f965c2b54ec98c5865832f854f7`, including all Phase 2A, 2B localization/annotations/booking and Phase 2C protections. Main was not used as the development branch.
- Runtime: CPython **3.13.12 x64**, Tcl/Tk, Pillow **12.3.0**, pypdf **6.20.1**, tzdata **2026.4**. Freezer: PyInstaller **6.22.3** plus hash-pinned transitive build tools. Installer compiler: Inno Setup **7.1.0**, downloaded from its pinned upstream release and SHA-256 checked.
- `installer-review/build-manifest.json` records source commit, source manifest/requirements hashes, compiler hash and all 1,635 frozen payload files. The retrieved artifact CRC, EXE SHA-256, PE signature and input-manifest hashes were verified locally. Private databases/configuration/key/log filenames are absent from the payload inventory.

## Actual test results

| Executed check | Result |
|---|---|
| Linux full regression suite, CPython 3.12.14 | **103 passed**, no failures/skips, 14.274 seconds; before later Windows-specific fixes |
| Final Windows full regression suite | **103 passed**, no failures/skips, **91.932 seconds** |
| Windows Chinese console codepage 936, PYTHONUTF8=0 startup suite | **9 passed**, 0.109 seconds; includes simulated GBK file-default reads |
| Existing browser JavaScript regressions | Included in both complete suites; all 12 checks passed |
| Windows bundled runtime/native GUI import self-test | Passed with Python removed from PATH, PYTHONHOME/PYTHONPATH empty; recorded frozen=True, console=False, Asia/Shanghai timezone |
| Per-user installation with port 5051 occupied | Passed |
| Unicode/space/extended installation path | Passed at the path recorded in windows-smoke-results.json |
| Start menu shortcut and correct Unicode target | Passed via **IShellLinkW** and Windows file identity |
| Per-user uninstall registration | Passed |
| Uninstall removes application and Start menu entry | Passed |
| Reinstall | Passed |
| Owned Windows tunnel child/job cleanup | Passed; a separate child remained running until the test harness cleaned up its own processes |
| Synthetic OWNER start, Ctrl+C and immediate 5051 rebind on Linux | Passed, exit code 0; temporary synthetic DB only |
| Compilation, source manifest and workflow YAML syntax | Passed |

All **13 installation/runtime smoke assertions** passed on **Windows Server 2025, build 26100**, using a GitHub-hosted runner. This is real Windows evidence, not a physical Windows 11 clean-machine test. The machine already contained development tools; removing Python from PATH demonstrates the installed app uses its bundled runtime, but does not establish an OS image with no Python installed.

Evidence is retained in `installer-review/windows-regression.log`, `windows-regression-outcome.txt`, `windows-smoke-results.json`, `runtime-self-test.json`, `shortcut-target.json`, `owner-cleanup-results.json` and `install-smoke.log`.

## Startup defects addressed

- **WIN-01:** Explicit UTF-8 for requirements, manifests, teacher settings and cloudflared output; invalid subprocess bytes are replaced rather than crashing GBK decoding.
- **WIN-02:** Standard OWNER website launch runs Python directly. The old PowerShell file is only a compatibility wrapper. No teacher/OWNER startup execution-policy change is required.
- **WIN-03:** Client-only setup does not probe local port 5051; the EXE installer requires no separate Python or dependency setup.
- **WIN-04:** OWNER backend runs in its launcher console process; only its own tunnel child is cleaned up. Windows kill-on-close job ownership is configured. Windows HTTP sockets use **SO_EXCLUSIVEADDRUSE** and disable reuse to prevent a second listener resetting a live classroom. The existing duplicate-start regression passes against a real Windows socket.
- **WIN-05:** Diagnostics distinguish bad saved settings, network/timeout, certificate, gateway/OWNER availability, response/build mismatch and gateway authentication. Teacher login failures remain login errors. Healthy remote OWNER bootstrap never depends on localhost:5051.
- **WIN-06:** URL changes are available in settings and on login/error screens, without reinstalling. Changes validate TLS/build before saving and clear old dashboard authentication/cache state.

The frozen entry point dispatches native meeting launches through the bundled executable rather than treating it as a Python interpreter. Browser media negotiation, camera/microphone/screen-sharing logic and booking/annotation authorization were not rewritten.

## Failures encountered and resolved

An initial workflow had a YAML scalar error, fixed before a Windows job could run. Windows verification then demonstrated a genuine duplicate-bind/live-class reset defect, fixed with exclusive binding. Test-fixture problems also surfaced: real GUI spawning in API tests, unresolved 8.3 paths, a SQLite seed connection left open, an invalid trailing-space install test path, and **WScript.Shell's ANSI shortcut API losing Chinese characters**. Fixtures now use client handoff, normalized paths, explicit SQLite close, a valid Unicode path and IShellLinkW. Existing security assertions were preserved. Earlier failed/cancelled runs are not counted as passes. A few local targeted invocations used nonexistent selectors; corrected test selections executed successfully.

## Unverified acceptance / precise remaining steps

1. Install this exact EXE on a clean **Windows 11** standard-user VM without Python, in both English and Chinese Windows display locales, with normal Defender/SmartScreen and downloaded-file protections enabled.
2. Exercise actual Windows Search indexing, optional desktop shortcut, interactive installer pages and launch after reboot. The automated checks prove Start menu registration/target and uninstall integration, not Search GUI behavior.
3. Supply a non-production OWNER HTTPS address and synthetic teacher account to exercise real remote TLS/login, changing a temporary tunnel URL, native lesson controls and browser media end to end. The permanent OWNER origin is not finalized; nothing was hardcoded or deployed for this test.
4. Test native annotation use over real desktop applications and bidirectional camera/audio/screen sharing on Windows/iPhone/Android. Unit/API tests do not establish physical-device behavior.
5. Test Windows OWNER Ctrl+C and console-window close interactively, immediate restart after real HTTP traffic, and paths exceeding MAX_PATH where supported. Linux Ctrl+C and Windows owned-child cleanup are narrower automated checks.
6. Apply the legitimate publisher's Authenticode signing process, sign payload/installer/uninstaller, verify signatures/timestamps, recompute the final checksum and rerun acceptance. The signing certificate/private key and approved signing service were not available here. Never disable security protections to suppress unsigned-publisher warnings.

No automatic updates, main merge, deployment or GitHub Release publication occurred. See `packaging/windows/README.md` for the pinned rebuild/signing procedure and `installer-review/INSTALL_AND_UNINSTALL.md` for teacher instructions. Review/approval is required before further release work.
