# MathStudio v41.6.6 — Phase 2C delivery

Branch: `codex/release-hardening-v4166`, based on Phase 2B Part 2 commit `1857869b0d94409be11fa17f8d9f6bd29a487e3f`. Scope is limited to PKG-01/02/03/04, DEP-01 and SEC-05. Main is unchanged. No merge, deployment, release publication, production credentials or student data were used.

**Review status: source hardening implemented; Windows release acceptance/signing/distribution remains blocked pending the steps below.** The manifest describes source candidates, not a complete signed Teacher Ready installer. No final distribution ZIP, replacement executable or bundled interpreter was produced.

## Findings addressed

| Finding | Result and evidence |
| --- | --- |
| PKG-01 | Explicit setup installs/verifies a private runtime before teaching. OPEN MATHSTUDIO TEACHER.bat is provided; the existing launcher delegates to it. Fresh-account bootstrap starts the website; healthy matching servers are reused and mismatched ports are not stopped. State defaults outside the application folder while existing in-folder data is retained. Tests cover startup ordering, server reuse/mismatch, setup refusal during a running server, offline/hash flags, and upgrade paths. Actual Windows double-click behavior is pending. |
| PKG-02 | Removed the undocumented unsigned EXE. Added Unicode launcher C source, exact Windows build/signing/verification steps, an explicit SHA-256 source manifest, and a deterministic source packager that rejects private files, linked inputs and binaries. Synthetic package tests verify reproducibility, hash failures and exclusions. No signed binary or Windows installer is claimed. |
| PKG-03 | Removed recursive discovery and execution of TURN/cloud-storage batch files. Explicit imports parse allowlisted data only, reject commands/duplicates/placeholders/incomplete credentials, preserve environment overrides and avoid credential logs. New secrets live in the private user profile. No real credentials/provider requests were used in tests. |
| PKG-04 | version.json supplies the shared build ID and web cache identity. Older v41.6.6 builds fail the new exact build match. Legacy /admin redirects to /teacher instructions; classroom exit/navigation uses a supported route. Stale startup/readme/help labels are corrected without enabling the old browser admin renderer. |
| DEP-01 | Exact hashed Pillow/pypdf/tzdata wheels; no PyPDF2 fallback or meeting-time pip install. Clean Linux installation/import/timezone/pip checks and Windows x64 wheel resolution for CPython 3.12/3.13/3.14 pass. PDF parsing runs in a child with input/output/page/deadline bounds. Pinned IANA data is authoritative on all OSes. |
| SEC-05 | Broad inline MIME prefixes are replaced by matching PDF signatures or verified PNG/JPEG/GIF/WebP formats. Unknown, mismatched or active content downloads as octet-stream attachments. Download/preview responses include nosniff, restrictive sandbox CSP and safe filename encoding. Grant isolation/revocation behavior is retained. Synthetic Chromium PDF/PNG viewing and backend regressions pass; Safari/mobile rendering remains unverified. |

## Dependencies and timezone behavior

Pillow **12.3.0**, pypdf **6.20.1**, tzdata **2026.4 / IANA 2026d**. requirements.txt contains exact versions and SHA-256 wheel hashes. A new CPython **3.12.14 Linux x86-64** environment installed all three using `--require-hashes --only-binary=:all:`; `pip check` found no conflicts. Windows x64 wheels for each supported CPython series were downloaded with the same required hashes; Windows execution was not performed. pip-audit **2.10.1**, PyPI advisory service, **2026-10-16**: no known vulnerabilities for the three pinned versions. Recheck at release time.

A regression exposed an OS database difference: IANA 2026d keeps Edmonton at UTC−6 in November 2026, while the Cloud OS database changes it to UTC−7. Scheduling now reads the pinned package directly. DST recurrence tests still cover real transitions, using Toronto. Browser tests receive corresponding authoritative rules. **Stored booking timestamps and user data are not rewritten.** Review future local-time expectations during upgrade; no automatic booking migration is performed.

## Verification

- Focused security/config/setup/package/route/dependency regressions pass, including rejection of disguised HTML/SVG/XML and MIME-mismatched images/PDF, legitimate PDF/PNG previews, cross-session grants, header injection, unsupported old Pillow, malformed PDFs and worker timeout.
- Existing teaching tests pass with the pinned timezone rules, preserving wall-clock recurrence, rollback on invalid/conflicting occurrences, and browser/device-zone independence.
- Node browser workflow tests: **12 passed**, preserving annotation permissions, localization/content boundaries, resource retention and scheduling checks.
- Python compilation, JavaScript syntax validation and `git diff --check` pass.
- Manifest validation passes for both package selections. Deterministic ZIP behavior/exclusions were tested with synthetic fixtures only; no actual distribution ZIP is produced.
- Headless Linux Chromium displayed a generated PDF containing “MathStudio synthetic preview” and a generated PNG under the new response policy. This is a browser-header smoke check, not physical-device media validation. The initial Chromium command-line capture timed out; a subsequent local debugging-protocol check succeeded.
- Complete suite: `python -m unittest discover -v` — **85 tests passed in 14.494 seconds**, including all prior Phase 2A/2B regressions and the wrapper for all 12 JavaScript checks. No failures or skipped tests.

## Changed files

- Setup/launch: `runtime_setup.py`, `dependency_check.py`, `runtime_paths.py`, `SETUP MATHSTUDIO.bat`, `OPEN MATHSTUDIO TEACHER.bat`, `START TEACHER APP.bat`, `teacher_app_start_hidden.bat`, both `START STUDENT WEBSITE` BAT files, `TEACHER APP DIAGNOSTICS.bat`, `start_https.ps1`, `teacher_app_bootstrap.py`, `teacher_desktop_app.py`.
- Private configuration: `private_config.py`, `restore_media_config.ps1`, `setup_free_media.ps1`, `SETUP FREE CAMERA + AUDIO.bat`, `TEST CAMERA + AUDIO RELAY.bat`, `media_config.example.bat`, `cloud_storage.example.bat`, `.gitignore`.
- Backend/documents/timezones: `server.py`, `document_worker.py`, `studio_time.py`, `requirements.txt`.
- Build/navigation/localized guidance: `version.json`, `build_info.py`, `index.html`, `diagnostics.js`, `app.js`, `classroom.js`, `teacher.html`, `teacher_meeting_app.py`, `teacher_localization.py`.
- Integrity/provenance: `.gitattributes`, `release_manifest.json`, `release_package.py`, `launcher/teacher_launcher.c`; removed `MathStudioTeacher.exe`.
- Documentation: `README.md`, `README - OWNER.txt`, `INSTALL_WINDOWS.md`, `BUILD_RELEASE.md`, `RELEASE_NOTES_v41_6_6.md`, `RELEASE_CHECKLIST.md`, this report.
- Tests: `test_release_hardening.py` adds focused regressions; `test_security_stability.py` isolates private configuration in its temporary fixture; `test_teaching_workflows.py` and `test_browser_workflows.mjs` retain prior regressions with current authoritative timezone expectations.

WebRTC negotiation, transceiver, sender/track, camera/microphone capture, screen-share transport and annotation-conflict code are preserved. Classroom edits in this phase are limited to valid navigation/help text. Main, prior branches and databases are not modified by this development work.

## Remaining limitations and required steps

1. Run documented setup/open/upgrade/rollback on clean Windows 10/11 x64 standard-user accounts, including Unicode/space paths, downloaded Mark-of-the-Web files, offline wheels, occupied/mismatched ports, old packages, missing Tk and Python variants. Actual cmd.exe/Windows PowerShell were unavailable here.
2. Compile the optional C launcher with a recorded MSVC/SDK; build it twice and compare unsigned output. Obtain legitimate signing, timestamp and verify the expected Authenticode publisher and after-signing SHA-256. A reviewed installer definition, bundled-runtime/licensing/update strategy and signed installer are still absent. BUILD_RELEASE.md gives the exact missing procedure. No security protections should be disabled.
3. Verify the official cloudflared Windows artifact/version and the tutor's real HTTPS/TURN setup privately; real provider credentials were deliberately not used. The Teacher App offers its existing Python tunnel path if PowerShell policy blocks the standalone script.
4. Complete Windows/iPhone/Android camera/audio/share/annotation/booking/localization acceptance and mobile Safari/Chrome PDF/image preview checks. Passing unit tests or Linux Chromium does not establish physical-device WebRTC behavior.
5. PDF workers have a Unix address-space cap, but no Windows Job Object memory cap. The parent deadline limits runtime, not peak Windows memory. DOCX/ZIP processing resource budgets remain a separate concern. The dashboard still leaves its server running on close; documented identification/shutdown outside live classes is required until a dedicated shutdown UI is approved.
6. Source package integrity checks are complete, but actual signed distribution assembly remains a release-review action. Preserve private data/config/backups outside artifact inputs and obtain approval before publication.

Rollback: finish lessons, stop the new build, reopen the prior verified package/runtime and restore the pre-upgrade backup if required. There is no Phase 2C schema migration. Reverting the Phase 2C commit does not undo new bookings/messages written after upgrade. Do not downgrade against a live database or discard post-upgrade student work.
