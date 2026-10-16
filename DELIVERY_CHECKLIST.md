# MathStudio v41.6.6 — delivery candidate

Build: `v41.6.6-delivery-candidate1`. Based on Phase 2C commit b8fc294f5b55ab0f389ef2e74408088b74e64dde, which contains Phase 2A (89fbccd), Phase 2B Part 1 (157d21c) and Phase 2B Part 2 (1857869). No merge/deployment/release publication is authorized or performed.

## Package roles

- **OWNER:** full application source, backend, website, setup, native controls, tests and owner configuration helpers. OWNER alone hosts the Python HTTP backend on port 5051 and supplies HTTPS/TURN.
- **TEACHER READY:** desktop dashboard, native annotation controls, their required Python modules, pinned requirements, setup and OPEN MATHSTUDIO TEACHER.bat. No server.py, student website, backend launchers, TURN setup tools or private state. Its package_role.json forces remote-client mode. First launch asks for the OWNER public HTTPS origin, verifies TLS/origin/build before saving it locally, and revalidates at connection. Student site / Settings → Change OWNER server updates it after sign-in; CHANGE OWNER SERVER.bat is the offline recovery option. No account/password is bundled.
- Native teacher controls launch on the teacher PC using a server-issued token. A client-launch flag prevents launching them on the separately hosted OWNER. Browser camera/audio negotiation is unchanged. Both packages must use this exact build; install/review them together before exposing a new OWNER build.

## Installation and launch

1. Verify SHA256SUMS.txt through the owner's trusted channel. Extract each ZIP once, preserving its single versioned root folder and all files.
2. On each Windows PC, install current supported 64-bit CPython 3.12/3.13/3.14 from python.org with pip, Tcl/Tk and Python launcher. Run SETUP MATHSTUDIO.bat once, outside any live lesson. Internet is required for hash-pinned wheel installation unless using the documented verified offline wheelhouse.
3. On OWNER, install trusted official cloudflared if this computer will supply a tunnel. Run SETUP FREE CAMERA + AUDIO.bat and TEST CAMERA + AUDIO RELAY.bat privately; do not send configuration to the teacher. Start START STUDENT WEBSITE.bat; create the first admin in its terminal if prompted, record the HTTPS link and keep the backend terminal running. A stable separately configured HTTPS origin may be used instead of the temporary quick tunnel. If Windows execution policy blocks the supplied HTTPS PowerShell script, do not bypass it: have an administrator review/sign it or use the already approved hosting/tunnel arrangement. No live backend was deployed here.
4. On Teacher Ready, double-click OPEN MATHSTUDIO TEACHER.bat, enter the OWNER HTTPS origin only (no /classroom path), and sign in with an owner-provided teacher/admin account. Credentials are exchanged privately and are never embedded in either ZIP. No VS Code is needed. To replace a changed temporary tunnel URL, use Student site / Settings → Change OWNER server after finishing active lessons, or close the app and use CHANGE OWNER SERVER.bat if offline. The change signs out and clears cached account/class data.
5. Start a class and verify both browser media and local native annotations. The OWNER must keep its server running; Teacher Ready cannot replace it. Closing the dashboard does not stop OWNER.

## Delivery checks

- [x] Prior approved commits confirmed in ancestry; main left unchanged.
- [x] Source manifests have explicit SHA-256 allowlists and one root folder per package.
- [x] No private databases/accounts, student resources, real credentials, configuration, logs, EXE files or virtual environments selected.
- [x] Teacher backend-start/account-creation paths disabled; remote URL is HTTPS-only with no credentials/query/path.
- [x] Pinned dependencies: Pillow 12.3.0, pypdf 6.20.1, tzdata 2026.4 (IANA 2026d); hash-checked setup retained. Requirements are included; Python and wheels are not bundled.
- [x] Complete regression suite executed once: **91 tests passed in 13.815 seconds**, including the wrapper for all 12 JavaScript checks. Compilation and syntax checks passed; no failures or skipped tests.
- [x] After the final server-settings clarification, **18 focused tests passed** (delivery, localization and manifest), covering connection validation before saving, persistence, changing server/sign-out and clearing client state.
- [ ] Clean Windows install, actual cmd/PowerShell launch, native toolbar/camera/audio, iPhone/Android and remote live HTTPS/provider connectivity: **not executed in Cloud**.
- [ ] Signed executable/installer: **not produced**. The archives contain Python source plus BAT launchers, not a self-contained signed EXE distribution. Never disable Windows protections.

Timezone data remains pinned/authoritative; stored booking timestamps are not rewritten. Edmonton's November 2026 offset is UTC−6 in IANA 2026d. PDF workers still lack a Windows Job Object memory cap. Existing deployment limits in BUILD_RELEASE.md remain applicable.

## Rebuild on Windows, without publishing

From a clean copy of the reviewed delivery branch, with Python installed:

```bat
py -3.13 release_package.py --kind owner --output "MathStudio_v41_6_6_OWNER_Delivery_Candidate.zip"
py -3.13 release_package.py --kind teacher --output "MathStudio_v41_6_6_TEACHER_READY_Delivery_Candidate.zip"
certutil -hashfile "MathStudio_v41_6_6_OWNER_Delivery_Candidate.zip" SHA256
certutil -hashfile "MathStudio_v41_6_6_TEACHER_READY_Delivery_Candidate.zip" SHA256
```

Run outside either existing output ZIP path; the builder refuses overwrites. It includes only reviewed manifest inputs and does not search private directories. BUILD_RELEASE.md documents the additional Windows MSVC build, signing certificate, Authenticode verification and installer-definition steps if a signed EXE installer is required. Cloud ZIP generation does not certify those steps.
