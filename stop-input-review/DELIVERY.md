# Stop/input repair review — Draft PR #12

Stacked on PR #11 delivery `336d744c0680183832ac499ddaa4a1e93ea47721`. Source/build revision: **a22df221e0f68482017d094c53dce292cc0c2ad0**. Build ID **v41.6.6-stop-input-review1**. Earlier PR8/9/10/11 fixes remain ancestors. No main update, merge, deployment, DNS/TURN change, paid resources, model downloads, production access or recording publication.

## Downloads and installation

This folder contains the complete OWNER source ZIP, matching client-only Windows installer, SHA256SUMS.txt, exact changed-file list and sanitized build/test evidence. Read [STOP_INPUT_REVIEW.md](../STOP_INPUT_REVIEW.md) for the full configuration and Windows 11 acceptance checklist. The ZIP has **159 allowlisted source files plus its manifest**, one application root, verified file hashes/CRC and no nested historical release archives. It excludes accounts, databases, credentials, private files, venvs, models, recordings and teacher EXEs.

1. Extract `MathStudio_v41_6_6_OWNER_Stop_Input_Review.zip` into a new test folder.
2. Run `REVIEW OWNER SETUP.bat`, selecting the existing ready Argos home. The runtime/models/receipt are copied and verified offline; the original is unchanged. No translation models are downloaded. Only pinned OWNER dependencies may be installed.
3. Run `REVIEW OWNER START.bat`. This review uses **5065**, `%LOCALAPPDATA%\MathStudioOwnerStopInputReview`, its own Quick Tunnel and empty private review state. Production 5051, PR9 5059, PR10 5061 and PR11 5063 are untouched; an occupied review port is refused.
4. Install `MathStudio-Stop-Input-Review.exe`, with a new AppID/install directory and `%LOCALAPPDATA%\MathStudioStopInputReview` profile. It remains client-only. Enter the new review HTTPS origin and use OWNER pairing. Keep Windows protections enabled; inspect the actual signature/security report.
5. Deliberately configure the new review's private test R2/FFmpeg/policy and authorized synthetic participants. Defaults do not enable recording or supply consent. No existing account databases are migrated automatically.

```powershell
py -3.13 .\owner_review.py setup --argos-home 'D:\YourExistingReadyArgosHome'
py -3.13 .\owner_review.py start
py -3.13 .\recording_media.py configure --data "$env:LOCALAPPDATA\MathStudioOwnerStopInputReview\data" --path 'C:\Tools\FFmpeg\bin\ffmpeg.exe'
py -3.13 .\recording_media.py status --data "$env:LOCALAPPDATA\MathStudioOwnerStopInputReview\data"
```

Use a trusted explicitly selected FFmpeg; no binary is discovered/downloaded automatically. The inherited recording guide remains in the ZIP as historical PR11 guidance; substitute this candidate's new port/profile as explained in STOP_INPUT_REVIEW.md. Dependencies remain pinned and unchanged. The teacher installer bundles its runtime and needs neither FFmpeg nor Argos locally.

## Findings and repairs

| Finding | Evidence | Repair |
|---|---|---|
| Silent teacher-only capture produces no media | Before patch, actual Chromium against authenticated OWNER returned **zero chunks**, `state=failed`, `fault=false`, yet displayed queued success. No enabled audio inputs were connected to the AudioDestination. | An explicit zero-valued ConstantSource keeps the audio clock running without enabling microphones. The same reproduction now yields nonempty encoded chunks and playable video. Empty output is a failure with `encoder:empty`, not a success notice. |
| Stop/end ordering and misleading completion | Native End removed the room before browser drain; browser End called remote closure first. Capture and finalization shared the same stale-capture state. Library Ready could precede configured seekable processing. | Browser Stop collects the final event and drains acknowledged chunks. Separate bounded finalizing state retains upload permission but no capture lease; native End returns pending until encoder/chunks finish, then explicitly confirms closure. With configured FFmpeg, Ready waits for original R2 and indexed-copy acknowledgment. Recoverable checkpoints/bytes remain on failure. |
| Input surface covers control coordinates | Full-screen native input relied on topmost/lift ordering and had no control-area exclusions. Actual Win32 raised-window hit-testing is part of this candidate's CI evidence. | Clip the input HWND around the toolbar and mapped native panels, updating on map/movement, with fail-safe Interact recovery. Add explicit 64-bit Win32 signatures and release owned capture on mode exit. Pen sampling, rendering and synchronized annotation logic are unchanged. Physical Windows 11 confirmation remains required. |
| Native UI waits on network | End, close/screen cleanup and Video authentication synchronously called HTTP from Tk handlers. A single unreachable request could block for up to eight seconds. | Use owned daemon workers and the existing main-thread queue; local close never waits for OWNER. Explicit pending is not success; failure allows local cleanup with an honest remote-status warning. No unrelated browser/process kill or new global input hook. |

Diagnostics use fixed stages/categories and bounded HTTP/FFmpeg exit codes; no arbitrary worker output, private paths, credentials, media or user content is logged. Original and indexed media remain private. Local file writes/checkpoints are independent of cloud uploads and require successful close before local success.

## Verification

Linux CPython 3.13/Xvfb full suite: **232 run, 226 passed, 6 platform/tool skips, zero failures**, 38.121s. Skips: two genuine Windows DPAPI tests, actual Win32 hit-testing, and three optional browser harnesses run separately with Playwright. Focused native/shutdown/localization/setup:36 run, 35 passed, one Win32 skip. Existing Node workflows: 15 passed; recording-limit test passed. JavaScript syntax, source manifest and ZIP integrity checks passed.

Actual authenticated OWNER/Chromium/FFmpeg integration passed, including a final-source rerun in 6.455s: **sub-second silent teacher-only Start→Stop**, two consenting synthetic participants, repeated cycles, actual encoder output, real multipart implementation with in-memory transport, deliberately delayed cloud completion, non-Ready before acknowledgment, actual original decode/indexed seek and Local Stop/file decode with mocked Save As/writer. A separate backend test stops during an active 8 MiB multipart operation, accepts the final chunk and waits for cloud acknowledgment. End Class remains pending through final chunk drain. Lease expiry/withdrawal checks remain fail closed.

Existing multi-source real-browser test also passed: enabled synthetic cameras/microphones, screen/board transitions, aligned annotations, pause/resume, finalization at simulated time/size limits and original track survival. Persistent student login across separate HTTPS Chromium processes passed. The browser harness runs separately under Linux Python3.12/Playwright; the pinned backend suite uses Python3.13. These tests do not prove receipt of physical remote feeds or actual Windows file-dialog behavior.

Latest isolated browser sample: **29.6 measured capture FPS**, 1280×720 target, VP8/Opus 4.5Mbps/128kbps; 370ms cumulative Canvas CPU, zero missed-capture estimate, 1,429,501-byte available JS heap sample, approximately 63.7% of one core for the whole synthetic browser workload. Original 167,045 bytes; indexed 77 frames / 2.585s / 167,365 bytes; actual decode and seek passed. The 162 received-camera playback-drop count is synthetic input playback, **not RTP or encoded-frame loss**. This is a short Cloud sample, not sustained physical acceptance.

Initial attempts are not hidden: the first full run had seven errors because the old Xvfb display was unavailable. After locating the already-installed Xvfb, verifying a real Tk connection and restoring the display, the complete suite passed. The existing browser FPS assertion initially failed at 19.8 while sharing CPU with the full suite; rerunning unchanged in isolation passed at 29.6. No performance threshold or test assertion was weakened. Subsequent targeted drain checks (five tests) passed after making Stop acknowledgment idempotent; local finalization uses the same fixed deadline. The initial hosted Win32 run passed toolbar checks but failed a blank-panel probe. The probe now matches the actual transient button panel, uses consistent native coordinates and independently checks the installed region and hit target. The focused Windows preflight passed all four tests, including region, actual hit target, repeated mode changes and owned capture release. Windows final-source full suite: **232 run, 225 passed, 7 optional skips, zero failures/errors**, 341.644 seconds. Per-user Unicode/long-path install, no-Python-on-PATH frozen startup, uninstall/reinstall, DPAPI, client-only isolation and owned-process cleanup passed on **Windows Server 2025**, not physical Windows 11. Defender: **scan_completed**, **0 threats**; Authenticode: **NotSigned**. Installer and OWNER manifest hashes match. See accompanying build reports and `verification.json`.

## Exact modified files

[CHANGED_FILES.txt](CHANGED_FILES.txt) lists all 28 source files. Main areas:

- Recording: `classroom_recorder.js`, `classroom.js` (End ordering only), `classroom_recording.py`, `recording_media.py`, `server.py`, `recordings.js`, `teacher_recordings.py`.
- Native input/shutdown: `teacher_meeting_app.py`, new `native_input.py`, `teacher_localization.py`.
- Regressions: new `test_recording_stop.py`, `test_recording_stop_browser.py`, `test_native_input_shutdown.py`; existing local-recording fixture and isolated-setup expectations updated.
- Isolated packaging/docs: `owner_review.py`, `runtime_paths.py`, `version.json`, manifest/checksums, Windows build/installer/smoke/workflow files, setup guides and new `STOP_INPUT_REVIEW.md`.

## Acceptance and rollback

**User's physical Windows 11 testing is the next gate.** Follow the exact checklist in STOP_INPUT_REVIEW.md: silent/enabled-mic solo recordings; permitted remote media; Stop during screen/whiteboard/mic and uploads; Local Save As/disk failures; rapid Pen/Interact/tool/color/undo/clear/panel transitions; focus/Escape/Alt+F4; Close/End while drawing and finalizing; unavailable/slow/error OWNER; repeated cycles and Task Manager check for this review's orphaned native process. Escape applies when MathStudio owns keyboard focus; no global hook is claimed. Unrelated browser processes are never killed.

Live private R2 upload/recovery/deletion/lifecycle, actual mobile receipt, physical pen/mouse, long-duration/5GB, precise audio sync/readability, disk exhaustion and real Windows file picker remain unverified. Local/cloud network failures can still interrupt media; received bytes/copies cannot be remotely recalled. If a browser is abandoned before finalization, unacknowledged data may be lost and must not be labeled completed. Legal/guardian review and private storage configuration remain required. Explicit teacher-only absentee sharing is unchanged; **no automatic sending** and Instant meetings remain private.

The installer remains unsigned unless its actual report states otherwise. Hosted Windows Server 2025 is not physical Windows 11. Completed R2 media is independent of teacher-PC uptime, but future Render still needs persistent protected metadata/spools/index checkpoints and trusted FFmpeg. No deployment is performed.

Rollback: stop and uninstall only MathStudio Stop Input Review. Preserve/dispose its separate review state and private test objects under the approved retention policy; production/PR9/PR10/PR11 remain unchanged. Stop after delivery for physical acceptance. Do not merge or deploy.
