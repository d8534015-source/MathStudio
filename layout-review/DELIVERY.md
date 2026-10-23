# Responsive Toolbar / Recording Layout Review — Draft PR #13

Stacked on PR #12. Source: `88c0226b985347f4b4eba59c5dffa684700eefe8`. Build **v41.6.6-layout-review1**. No merge/deployment or production changes.

## Downloads and isolation

- `MathStudio_v41_6_6_OWNER_Layout_Review.zip`: complete allowlisted OWNER source, setup/start scripts, instructions, inherited PR8–12 fixes. **5067**, `%LOCALAPPDATA%\MathStudioOwnerLayoutReview`.
- `MathStudio-Layout-Review.exe`: rebuilt client-only Windows installer, separate AppID/install directory and `%LOCALAPPDATA%\MathStudioLayoutReview`. Enter the separate review OWNER HTTPS URL; no backend is hosted by this client.
- See `SHA256SUMS.txt`, `verification.json` and accompanying Windows reports. Original production/review installations and external models remain untouched.

## Root causes and changed files

`teacher_meeting_app.py` specified 1260×176 despite rows requiring more space; fixed-character widths also ignored translated labels. New `native_toolbar.py` measures actual Tk requests, wraps controls independently, constrains placement to monitor work areas (including absolute negative coordinates), and preserves user sizing above required minima. First geometry is applied while withdrawn. Label/variable changes, moves and resizes refresh layout and existing input exclusions. Existing shutdown, Pen/Interact, capture release and ink coordinates remain.

`classroom_recorder.js` always reserved the board's 1024×576 region and used a fixed six-slot camera strip. It now balances consenting participants across the canvas when no actual screen/whiteboard is active. Disabled/missing/ended/muted video becomes a display-name/initial avatar. A real received screen or an active board preserves existing annotation coordinates and uses a compact participant grid alongside it. Aspect ratios are contained. No audio/peer negotiation is added or changed. `classroom.js` supplies existing live-stage state, participant names (without account identifiers) and participants without received cameras; it excludes duplicate local entries.

Focused tests: `test_responsive_toolbar.py`, `test_recording_layout.mjs`, `test_recording_layout_browser.py`. Packaging isolation/provenance: `owner_review.py`, `runtime_paths.py`, `version.json`, `release_manifest.json`, `test_owner_review.py`, `.github/workflows/windows-installer.yml`, four `packaging/windows` build/installer/smoke/security scripts. Instructions: `LAYOUT_REVIEW.md`, `INSTALL_WINDOWS.md`, `REVIEW_OWNER_README.md`. `argos-review/SHA256SUMS.txt` only updates the shared manifest checksum. Exact 21-file list is in `CHANGED_FILES.txt`.

## Executed verification

- Final Linux pinned Python3.13/Xvfb suite: **234 run, 227 passed, 7 platform/optional skips, no failures**, 39.912s. Focused native/stop/setup/package tests: **35 run, 34 passed, 1 Windows-only skip**. A separate unchanged-test probe with a 600-pixel-high mocked work area also passed the same DPI/language cases.
- JavaScript: **15 existing workflow assertions +3 new layout assertions +1 limits assertion passed**. Python compilation, JS syntax, diff checks and both source manifests passed.
- Real Chromium/FFmpeg: **3 recording tests passed** (23.654s), including decoded actual video pixels through camera-only, grid, camera disabled/disconnected, screen/whiteboard start/stop and zero-participant transitions without restarting the encoder. Existing authenticated Stop/cloud/local/indexing checks passed with synthetic media and in-memory R2.
- Dynamic layout measured **29.2 FPS**, canvas CPU 256.2 ms, JS heap 3.40 MB; existing multi-source measured **28.5 FPS**, canvas CPU 378.6 ms, browser CPU~62.9% of one core, JS heap 1.54 MB. These short synthetic tests do not establish physical Windows/mobile or long-session performance. Output is 1280×720; manual requestFrame targets 30 FPS, so captureStream settings correctly report 0.
- Windows final-source full suite: **234 run, 226 passed, 8 optional skips, zero failures/errors**, 419.395 seconds. Per-user Unicode/long-path install, no-Python-on-PATH frozen startup, uninstall/reinstall, DPAPI, client-only isolation and owned-process cleanup passed on **Windows Server 2025**, not physical Windows11. Defender: **scan_completed**, **0 threats**; Authenticode: **NotSigned**. Installer and OWNER manifest hashes match. See accompanying build reports and `verification.json`.

Initial development failures and fixture corrections are recorded in `verification.json`; no failed acceptance run is described as passed. No model downloads, dependency changes, teacher/student data or real recording uploads were used.

## Installation and acceptance

Read [LAYOUT_REVIEW.md](../LAYOUT_REVIEW.md) for exact Windows setup/start and physical acceptance checklist. Extract OWNER into a **new** folder, run `REVIEW OWNER SETUP.bat` and select the existing ready Argos home, then `REVIEW OWNER START.bat`. For explicit reuse: `py -3.13 .\owner_review.py setup --argos-home 'D:\YourExistingReadyArgosHome'`. The setup copies/verifies into isolated state without model downloads or changes to the original. Configure only this review's private R2, policies and trusted FFmpeg. Install the matching Layout Review client, pair it with the review OWNER HTTPS URL and synthetic accounts. Keep Windows protections enabled.

Required manual acceptance: real Windows11 first launch, EN↔中文, mixed monitor DPI/work areas, moved/resized toolbar clickability in Pen/Interact, Escape/Alt+F4/local close during outages, real remote cameras/mics, camera/participant/share/board transitions in saved video, actual Save As/disk errors, live privateR2 and long meetings. CI Windows Server and synthetic frames are not these physical acceptance results. Screens too small to fit even a single control need display scaling adjustment. No recordings are published; guardian/consent, access control and absentee restrictions remain enforced.

Rollback: stop/uninstall **only** the new Layout Review server/client. Retain previous versions, review state and external Argos models. No production migration was made.
