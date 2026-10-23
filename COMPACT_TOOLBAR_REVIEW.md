# MathStudio v41.6.6 — PR13 revision2: Compact Toolbar / Recordings Localization

This review continues PR13 delivery `a7b07a885d828ba72e24a38ac491e01f56f36510`. It contains the same recording compositor and inherited PR8–13 repairs. Only native toolbar geometry and the Recordings localization are repaired; packaging metadata creates a separate test installation. Build **v41.6.6-layout-review2**. See `compact-toolbar-review/DELIVERY.md` in PR13 for immutable source/build revisions, exact downloads, checksums and executed results.

## Separate Windows installation

1. Keep x64 Python3.13 installed on OWNER. Extract **MathStudio_v41_6_6_OWNER_Compact_Toolbar_Review.zip** into a **new** folder, e.g. `C:\MathStudioTests\CompactToolbar`. Do not overwrite the prior Layout Review, any earlier review or production installation.
2. Run **REVIEW OWNER SETUP.bat** and select your existing installed, ready Argos home. The existing setup verifies/copies its runtime, installed packages and receipt into this review and tests offline translation. It does not download models or modify the original. Keep the Python installation used by that venv installed. Explicit PowerShell reuse, from the extracted application folder:

```powershell
py -3.13 .\owner_review.py setup --argos-home 'D:\YourExistingReadyArgosHome'
py -3.13 .\owner_review.py start
```

`--wheelhouse 'D:\TrustedOwnerWheels'` can reuse pinned OWNER dependency wheels.

3. Alternatively double-click **REVIEW OWNER START.bat** after setup. This review uses port **5069**, `%LOCALAPPDATA%\MathStudioOwnerCompactReview` and its own Quick Tunnel. An occupied port is refused. Production5051 and earlier review ports5059/5061/5063/5065/5067 and their data remain unchanged.
4. Install **MathStudio-Compact-Toolbar-Review.exe**. This is a new per-user **client-only** installation, with a distinct AppID, install directory and `%LOCALAPPDATA%\MathStudioCompactReview` profile. It does not host OWNER and needs no separate Python, FFmpeg or Argos on the teacher PC. Enter the new review OWNER HTTPS URL, pair and sign in. Keep Windows protections enabled; review executables remain unsigned unless the accompanying Authenticode report proves otherwise.
5. Use synthetic test accounts. The new state is empty. Do not copy production account databases, student files or credentials. If you exercise recording, deliberately configure this review's own authorized private test R2/guardian/policy settings and trusted FFmpeg using the inherited recording guides; substitute the new review profile and port. No paid resource, DNS change or recording publication is required.

A new OWNER ZIP is necessary because the complete OWNER source includes the shared teacher localization and native UI modules, and matching build/version metadata must stay consistent. Prior OWNER downloads are retained as historical review builds.

## Focused repairs

- Sidebar route `recordings` uses the glyph-prefixed canonical **Recordings** label. That key was missing from the central table, while a desktop-only fallback recognized only the unprefixed title. Central `teacher_localization.ZH['Recordings']` now supplies **录制记录**, including sidebar, page and dialog titles. EN↔中文 uses the existing immediate page rebuild/localization mechanism. Existing library-control translations and user content boundaries remain.
- The earlier helper measured row widths after forgetting nested packed controls, when their container requests could be stale/one pixel. It then wrapped nested groups before accounting for their combined width. Bottom-up measurement now accounts for both complete primary rows, actual Tk/font requests, padding and gaps before initial geometry. Normal desktop layouts expand horizontally, with a compact footer; wrapping is reserved for a monitor or explicitly user-resized window that cannot fit the whole row. Status text has a bounded wrap width; changing language/mode remeasures controls. No fixed default width replaces the calculation.
- The initial geometry is still applied while withdrawn. Work-area clamping, absolute negative monitor coordinates and existing native input exclusion callbacks remain. Tk's inherited primary-screen maximum is updated from the current monitor work area before mapping; Windows CI confirmed that an inherited1028-pixel cap otherwise forced a third row even with a1920-pixel work-area fixture. User-resized width/height are retained where they fit essential controls. No persisted prior geometry is overwritten.

## Windows11 acceptance checklist

- At **1920×1080 /100%**, start a meeting: title/status and all meeting/media/language controls must share the first primary row; Draw on desktop, student permissions, all tools/colors/sizes, Undo/Clear/Hide ink share the second. Only a small footer remains. Verify the rightmost controls are visible and clickable before manually resizing.
- Switch EN→中文→EN repeatedly. Sidebar and page title must show **Recordings → 录制记录 → Recordings** immediately without restart. Verify library buttons and available table/dialog translations. Verify navigation and authorized recording access still work; student names, recording meeting titles and files remain original.
- Repeat at125%,150%,200%, including Chinese and English. Where actual measured rows exceed the monitor's work area, a deliberate narrow layout is expected. Test a smaller display and move between monitors with different scaling, taskbars and negative origins. Confirm no essential button is clipped.
- Resize wide/narrow and move the toolbar while switching Pen↔Interact at least20times. Every control must remain clickable; ink coordinates must not move with the toolbar. Verify Escape, Clear/Undo/Hide ink and Alt+F4/Close, including an unreachable OWNER and pending recording Stop. Existing input-region protection and nonblocking local close must remain.
- Smoke-test the unchanged camera-only/grid/avatar/share/board recording layouts, private cloud/local Stop/final chunks and playback with authorized test participants. Keep guardian/participant consent and absentee restrictions enforced.

Synthetic Tk/DPI cases and hosted Windows Server CI do not establish physical Windows11/mixed-monitor/pen acceptance. Actual saved-media/liveR2 and long-meeting checks remain yours. No WebRTC, compositor, FFmpeg, R2, authorization/consent/sharing, Argos model, authentication or pen-sampling implementation changes are part of this revision.

## Rollback

Stop only the new Compact Review server and uninstall only **MathStudio Compact Toolbar Review**. Retain previous review/production installations, their data and external Argos models. No data migration or production deployment was performed.
