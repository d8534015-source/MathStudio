# Classroom recording / pen review delivery

Draft PR: https://github.com/d8534015-source/MathStudio/pull/10

Source: `5c3a5e16412d252782121727564d3029e4e4076a`, stacked on PR9 `d0580ff83bbcec0b61f313c00ff89d09abb2f0e0`; PR8 and earlier fixes remain ancestors. Build: `v41.6.6-classroom-review1`. No main update, merge, deployment, cloud resource creation or release publication.

## Downloads and installation

The OWNER source ZIP and matching Windows installer are in this folder. Use the SHA256SUMS.txt checksums; download both from this same delivery revision.

Read [CLASSROOM_REVIEW.md](../CLASSROOM_REVIEW.md) for exact setup, existing-model reuse, separate profiles, recording policy/private-R2 configuration, Render persistence, rollback and manual acceptance steps.

- Extract OWNER into a new test folder. Run `REVIEW OWNER SETUP.bat`, selecting the existing Argos home, then `REVIEW OWNER START.bat`. Models are copied locally, not downloaded. Review state: `%LOCALAPPDATA%\MathStudioOwnerClassroomReview`; port **5061**. Production 5051 and PR9 review 5059 are separate.
- Install `MathStudio-Classroom-Review.exe`. It is client-only, with a distinct AppID/install directory and `%LOCALAPPDATA%\MathStudioClassroomReview` profile. Enter the review HTTPS address and use first-time OWNER pairing. Keep Windows protections enabled.
- Recording is disabled by default. OWNER must approve its consent policy, enter valid guardian-authorization expirations and configure/verify an already-existing private test R2 bucket before enabling it. No credentials, student data, databases, models or recordings are bundled.

## Changes

- Native mode switching finishes active ink and releases owned capture; worker callbacks execute on Tk's main thread. Incremental pen rendering and bounded optimistic operations preserve pending undo/erase/clear intent across conflicts. Pending ink is memory-only and close warns before discarding it.
- Recording runs in the visible teacher meeting browser, captures only its actually received media and synchronized board, and does not modify WebRTC negotiation. Teachers request/start/pause/resume/stop; students consent/decline/withdraw. Guardian authorization is required for every student; guests are excluded. Membership/lease changes stop capture before a new participant is admitted.
- Bounded sequential browser uploads, fsynced OWNER checkpoints, interrupted-recording recovery and resumable private R2 multipart transfers. Transfer locks are isolated between recordings; a focused test reproduced the prior collision (13 unique locks for 20 recordings) and now passes with 20 distinct locks.
- Creator-only desktop Recordings section: date, meeting, duration, status, play/download/delete. Authenticated browser handoff and session-bound 60-second playback/download tickets; private streamed byte-range access, no public object URLs. R2 finalization removes the successful local spool. Retention is configurable from 1–30 days; private bucket lifecycle is the backstop if OWNER is offline.
- Separate classroom review OWNER port/profile and installer AppID/profile preserve earlier review and production state. No new production Python dependencies, Argos changes, teacher pairing/Remember Me changes or booking changes.

## Verification

Final Linux full-suite result: **204 run, 201 passed, 3 skipped, zero failures** (32.875 s). The only subsequent application change was the browser button guard, verified by its focused real-browser test. Windows full-suite result on the exact final source: **204 run, 199 passed, 5 optional skips, zero failures** (172.229 s). Focused Python checks: **27 passed**. Existing Node browser workflow tests: **15 passed**. Synthetic Chromium/MediaRecorder audio/video mux and FFmpeg decode: **passed**, including rapid duplicate-click protection, pause/resume, disabled audio exclusion, annotation alignment, track survival and authorization loss. Integrated classroom/library English/Chinese smoke: **passed**.

Windows per-user Unicode/long-path installation, no-Python-on-PATH frozen self-test, uninstall/reinstall, DPAPI, Start menu target, OWNER child-process cleanup and client-only payload isolation: **passed**. Hosted OS was Windows Server 2025, **not an actual Windows 11 PC**. Defender scan completed with **zero threats detected**. Authenticode: **NotSigned**. Build and OWNER ZIP source-manifest hashes match.

Final results and Windows build evidence are recorded in `verification.json` and the accompanying sanitized build reports. Tests use only temporary synthetic accounts/media and mocked R2. No actual student or production data was accessed.

The first Cloud full-suite attempt encountered seven unavailable-display GUI errors; all seven passed after restoring Xvfb. A subsequently found recording lock issue was reproduced and repaired, and the final complete suite was rerun after that code change. Do not interpret synthetic mux tests as physical camera/microphone or mobile-device acceptance.

The pen benchmark submits the same 1,200 samples with 100 historical strokes: Canvas calls **122,400 → 1,200**, coordinate submissions **16,742,476 → 4,800**, stored draft points **1,149 → 1,201**. Cloud handler p50/p95 were 0.739/1.102 ms before and 0.00116/0.00215 ms after. These are Canvas-command workload measurements, not physical pen latency.

## Modified files

| Area | Files |
|---|---|
| Native drawing and controls | `teacher_meeting_app.py`, new `annotation_pipeline.py`, `teacher_localization.py` |
| Recording authorization/storage | `server.py`, new `classroom_recording.py`, new `recording_cloud.py` |
| Browser recording and library | `classroom.js`, new `classroom_recorder.js`, new `recordings.html`, new `recordings.js`, `locales.js` |
| Desktop recording library | `teacher_desktop_app.py`, new `teacher_recordings.py` |
| Focused tests/workload | new `test_classroom_drawing.py`, new `test_classroom_recording.py`, new `test_recording_browser.py`, `test_annotations_localization.py`, `test_owner_review.py`, new `packaging/benchmark_pen.py` |
| Isolation/build/package integrity | `owner_review.py`, `runtime_paths.py`, `version.json`, `release_package.py`, `release_manifest.json`, `argos-review/SHA256SUMS.txt`, `.gitignore`, `.github/workflows/windows-installer.yml`, `packaging/windows/MathStudio.iss`, `packaging/windows/MathStudio.spec`, `packaging/windows/build.py`, `packaging/windows/check_client_payload.py`, `packaging/windows/smoke.ps1`, `packaging/windows/verify_distribution.ps1` |
| Instructions | `REVIEW_OWNER_README.md`, new `CLASSROOM_REVIEW.md` |

This delivery folder adds the reviewed artifacts, checksums and verification reports; it is outside the source ZIP allowlist.

## Remaining review gates

- Actual Windows 11 stylus/mouse mode switching, precise mathematical handwriting, desktop sharing and camera/microphone acceptance; iPhone/Android bidirectional media and recording combinations. Hosted Windows CI is not a physical Windows 11/device test.
- Real private R2 upload/resume/deletion/lifecycle and encryption/access configuration; actual Render deployment and persistent-disk restart. No live cloud storage was used in development.
- Recorder browser must remain visible; hidden/minimized state stops recording. No remote/unreceived feed is reconstructed. Browser close/crash can lose final unacknowledged data; interrupted files may not play. Browser WebM seeking/duration metadata can be limited until buffered.
- Two-hour recording session / 2 GiB per-file / 5 GiB total quota, bounded browser upload buffer and disk guards. For a longer session stop, obtain fresh consent and begin another recording. Long-duration CPU, audio-level/synchronization and network-cost acceptance remain manual.
- Completed files are in private R2, independent of teacher PC/local OWNER uptime. Render still needs the same persistent SQLite metadata/policy/configuration and durable spool/multipart checkpoints while uploading. An ephemeral filesystem or multiple OWNER instances is unsupported. Disk/backup encryption and privacy policy/guardian evidence are OWNER responsibilities.
- Installer remains unsigned unless the actual signature report states otherwise. No bypass of Windows security protections is recommended.

Stop here for review. No merge or deployment is authorized.
