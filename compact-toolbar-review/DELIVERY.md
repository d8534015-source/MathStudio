# MathStudio PR13 revision2 — Compact Toolbar / Recordings Localization

Source/build commit: `a77444c7bef419210cd6d5b257a5b0dbbca7e1ff`. Parent review delivery: `a7b07a885d828ba72e24a38ac491e01f56f36510`. Build **v41.6.6-layout-review2**. This is a follow-up revision of Draft PR13, not a merged/deployed release.

## Artifacts and isolation

- `MathStudio_v41_6_6_OWNER_Compact_Toolbar_Review.zip`:165 explicitly allowlisted source files plus manifest, including changed shared UI/localization resources and Windows setup/start scripts. CRC, exact allowlist and all file hashes verified. Rebuilt because those resources and matching build metadata changed; the old OWNER remains a historical revision1 build.
- `MathStudio-Compact-Toolbar-Review.exe`: genuine rebuilt Windows client-only installer, with a different AppID/product/install directory and `%LOCALAPPDATA%\MathStudioCompactReview` profile. It does not host OWNER.
- OWNER uses **5069** and `%LOCALAPPDATA%\MathStudioOwnerCompactReview`. Earlier production/review ports and state, previous downloads, external Argos models and installed applications remain untouched.
- Final source/build matching, SHA-256, Windows evidence and limitations: `verification.json`, `SHA256SUMS.txt` and accompanying reports. No credentials, student data, accounts/databases, virtual environments, model payloads or recordings are bundled; OWNER contains no teacher EXE.

## Root causes and focused changes

1. The actual sidebar tuple is `('recordings','●','Recordings')`. The central table lacked `Recordings`; a desktop-only fallback recognized the plain page title but not the prefixed sidebar label. Add the single canonical `Recordings → 录制记录` mapping centrally and remove the stale desktop duplicate. Existing immediate page rebuild/localization handlers now update sidebar/page/dialog titles EN↔中文 without restart. Related existing library translations and content boundaries remain.
2. The prior helper chose width after removing packed children, when nested container requests could be stale/one pixel; it then wrapped groups before measuring complete rows. Measure nested controls bottom-up with actual Tk/font requests and padding, then choose a horizontal default for both primary rows. Wrap only when the current work area or an explicit user-resized width cannot fit them. Bounded status text prevents long connection messages from consuming the entire first row.
3. Windows verification caught an additional geometry constraint: Tk's inherited primary-screen maximum was 1028×749 on CI. It clamped the requested window to 1028×217 and forced a third row despite the 1920 work-area fixture. Set Tk's maximum from the current monitor work area before mapping. The strict test deliberately starts with a smaller stale maximum and retains all two-row, <=200px height, control bounds and move/resize assertions.

The initial geometry still applies while withdrawn. Native input exclusions refresh through the existing callback; native input/ink coordinates, Pen/Interact, owned capture release and nonblocking shutdown implementations are unchanged. User-resized dimensions are retained where compatible with essential controls.

## Changed files (20 source/metadata files)

- `native_toolbar.py`: bottom-up requested-size calculation, horizontal default, intentional resize/fallback behavior and current-monitor WM maximum.
- `teacher_meeting_app.py`: bounded status label wrap width only.
- `teacher_localization.py`: central Recordings mapping; `teacher_desktop_app.py`: remove its stale duplicate fallback.
- `test_responsive_toolbar.py`: actual current mode labels, strict first-launch EN/ZH two-row/shallow-height check at 96 DPI,125/150/200% equivalents, stale-max regression, negative monitor coordinates, narrow resize and exclusion callback assertions.
- `test_annotations_localization.py`: actual navigation tuple and toggle/page handlers round-trip; related available library translations checked.
- `owner_review.py`, `runtime_paths.py`, `test_owner_review.py`: isolated new review port/profile and matching expectations; older profiles remain whitelisted.
- `packaging/windows/MathStudio.iss`, `build.py`, `smoke.ps1`, `verify_distribution.ps1`: distinct installer name/AppID/profile and current instructions.
- `.github/workflows/windows-installer.yml`: add focused sidebar-language regression to existing Windows preflight.
- `version.json`, `release_manifest.json`, `argos-review/SHA256SUMS.txt`: matching revision2 version/allowlist hashes; no Argos implementation changes.
- `COMPACT_TOOLBAR_REVIEW.md`, `REVIEW_OWNER_README.md`, `INSTALL_WINDOWS.md`: current setup/reuse/acceptance instructions. Exact relative paths: `CHANGED_FILES.txt`.

## Executed tests

- **Final corrected Linux suite:**236 run,229 passed,7 platform/optional skips,zero failures,38.825s. Focused native/localization/setup/package:40 run,39 passed,1 Win32-only skip,4.638s.
- **JavaScript:**15 existing workflows +3 existing media-layout assertions +1 limits assertion passed. These were executed; real-browser recording/FFmpeg tests were not rerun for this native-only revision and their priorPR13 results remain historical.
- Actual Tk geometry under Xvfb at the96DPI equivalent: English 1360×170; Chinese 1228×170. The test checks all meeting controls in the first row, all drawing controls in the second, footer below and no clipped control. It also tests labels/mode changes and deliberate narrow resizing. These are synthetic font/work-area tests, not physical Windows11 evidence.
- Python compilation, diff checks, OWNER 165/teacher 35 source allowlist/hash checks, ZIP CRC/exact 166-entry structure and required setup/start files passed.
- Windows final-source full suite: **236 run, 228 passed, 8 optional skips, zero failures/errors**, 578.922 seconds. Per-user Unicode/long-path install, no-Python-on-PATH frozen startup, uninstall/reinstall, DPAPI, client-only isolation and owned-process cleanup passed on **Windows Server 2025**, not physical Windows11. Defender: **scan_completed**, **0 threats**; Authenticode: **NotSigned**. Installer and OWNER manifest hashes match. See accompanying build reports and `verification.json`.

Windows compact geometry checks observed **179px height**, with English widths1186–1210 and Chinese1071–1095 pixels across initial/language states. These are actual Windows Tk/font requests with a mocked1920 work area and96DPI, not a physical monitor test. All strict row/visibility assertions passed.

No failed attempt is described as passed. Original PR13 fails the new strict regression as expected. The first Linux candidate passed but Windows preflight exposed the WM cap; the diagnostic rerun confirmed dimensions only and blocked packaging. After the confirmed correction, the final full Linux suite was rerun because source changed. See `verification.json` for this sequence and Windows outcomes.

## Unchanged functionality

Verified no source difference from priorPR13 delivery for the compositor/classroom media, recording backend/FFmpeg/R2, authorization/guardian/sharing/policy, server/authentication/scheduling, Argos setup/runtime/worker, native input exclusions/annotation pipeline and recording library network/permission logic. `verification.json` lists the exact protected paths. No dependency versions changed, models downloaded, credentials/student data accessed, DNS changed, paid services purchased, recordings published, merge or deployment performed.

## Windows11 installation and acceptance

Read [COMPACT_TOOLBAR_REVIEW.md](../COMPACT_TOOLBAR_REVIEW.md). Extract OWNER into a **new** test folder; keep x64 Python3.13 installed. Run `REVIEW OWNER SETUP.bat` and choose your existing ready Argos home, then `REVIEW OWNER START.bat`. Explicit reuse: `py -3.13 .\owner_review.py setup --argos-home 'D:\YourExistingReadyArgosHome'`. The existing setup verifies/copies external models into isolated review state without downloads or changes to the original. Use this review's HTTPS address with the matching client-only installer; pair/sign in with synthetic accounts.

Acceptance: at1920×1080/100%,  start a meeting before resizing and require two wide primary rows plus a small footer. Switch EN→中文→EN in the dashboard and Recordings page and verify **Recordings/录制记录**, existing page controls, navigation and permissions. Repeat125/150/200% and mixed monitors; narrow fallback is expected only where measured controls cannot fit. Move/resize while repeatedly using Pen/Interact, all rightmost buttons, Undo/Clear/Hide ink and Escape/Alt+F4/Close, including unavailable OWNER/pending Stop. Smoke-test unchanged recording modes with authorized synthetic participants.

Physical Windows11, mixed-DPI monitor transitions, physical pen clickability and actual live-device/R2 recording acceptance remain unverified. Hosted Windows Server/mock work areas are distinct. Prior private data and models are not migrated. Roll back by stopping/uninstalling only Compact Review and retaining earlier review/production installations/state. Never disable Windows protections for this review.
