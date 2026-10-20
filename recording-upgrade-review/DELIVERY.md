# Recording upgrade review delivery — Draft PR #11

This candidate is stacked on [PR #10](https://github.com/d8534015-source/MathStudio/pull/10), preserving PR #8 Argos, PR #9 website/installer/authentication and PR #10 drawing responsiveness fixes. Source: `b23bb7b1e21ec966838ffe3154b666319a0386df`; stacked base: `416438d798362234ce821e5e17e6b65d0275e3f2`. Build ID: **v41.6.6-recording-upgrade-review1**. No production account schema migration, main update, merge, deployment, cloud purchase or recording publication.

## Downloads and setup

Download the OWNER ZIP and matching `MathStudio-Recording-Upgrade-Review.exe` from this folder in the same delivery revision. Verify `SHA256SUMS.txt`. The OWNER ZIP contains **154 explicitly allowlisted source files plus its release manifest**, with verified hashes and ZIP CRC. It excludes private data, accounts, databases, credentials, virtual environments, model archives/weights, media recordings and teacher executables. The installer is client-only.

Read [RECORDING_UPGRADE_REVIEW.md](../RECORDING_UPGRADE_REVIEW.md) before use. Exact separate Windows steps:

1. Extract OWNER into a new folder, e.g. `C:\MathStudioTests\RecordingUpgrade`.
2. Run `REVIEW OWNER SETUP.bat`; select your existing ready Argos home. Its installed runtime/models/receipt are copied and self-tested, **not downloaded again**. The original remains untouched.
3. Run `REVIEW OWNER START.bat`. This candidate uses **5063**, `%LOCALAPPDATA%\MathStudioOwnerRecordingUpgradeReview`, a separate browser/profile and its own HTTPS Quick Tunnel. Production 5051, PR9 5059 and PR10 5061 remain separate.
4. Install the matching review EXE, which has a new AppID/install directory and `%LOCALAPPDATA%\MathStudioRecordingUpgradeReview` profile. Enter the new HTTPS review address and use OWNER pairing. Keep Windows protections enabled. See the actual signature/security report before running this unsigned review candidate.
5. Use synthetic accounts. Recording remains disabled until OWNER approves the actual policy, independently verifies guardian decisions and configures an already-existing private test R2 bucket. No secrets are supplied or cloud resources created by this delivery.
6. For seekable absentee playback, explicitly obtain a trusted FFmpeg build from the official platform links and configure its absolute path using the guide. The ZIP does not install/download FFmpeg. Sharing stays blocked until processing succeeds. Existing original teacher downloads remain private.

PowerShell alternatives:

```powershell
py -3.13 .\owner_review.py setup --argos-home 'D:\YourExistingInstalledArgosHome'
py -3.13 .\owner_review.py start
py -3.13 .\recording_media.py configure --data "$env:LOCALAPPDATA\MathStudioOwnerRecordingUpgradeReview\data" --path 'C:\Tools\FFmpeg\bin\ffmpeg.exe'
py -3.13 .\recording_media.py status --data "$env:LOCALAPPDATA\MathStudioOwnerRecordingUpgradeReview\data"
```

## Delivered behavior

- 1280×720 / 30 FPS target, VP8/Opus where supported, 4.5 Mbps video / 128 kbps audio target; available cameras, enabled microphones, screen/board and synchronized annotations. No WebRTC/TURN/pen sampling rewrite. Visible measured-quality diagnostics and warning below 27 FPS.
- Cloud: fsynced bounded chunks and multipart R2 upload **during recording**, durable retry checkpoints, asynchronous bounded indexing/transfer, private seekable playback copy, cleanup after acknowledgment, honest interrupted/failed states.
- Local: explicit supported desktop Chrome/Edge Save As, bounded file-stream writes, no automatic media upload, byte/hash-bound explicit resumable upload only if originally authorized. Unsupported file APIs fail clearly; no 5 GB RAM fallback.
- Hard **3 hours elapsed or 5 decimal GB**, independent **2h30m and 4 GB warnings**, final-chunk reserve/finalization, configurable **12–1000 GB retained budget** (25 GB default, includes original + playback copy). No maximum-size/endurance claim from simulated thresholds.
- Absentee resources: only specific scheduled individual/group classes, immutable capture roster plus current enrollment, positively verified absence, named authenticated viewers, explicit teacher grants, expiry/revoke/download controls and authorization on every Range. Unknown attendance is not absence. Quick Meetings remain private. Codes alone confer no access; no automated sending.
- Separate guardian evidence/scope and optional meaningful student standing agreement, current policy version, expiry/withdrawal; conservative guardian requirement retained. Enrollment/Terms acceptance does not grant recording consent. No retrospective expansion of private recordings.
- Six editable bilingual Privacy/Terms/Cookie **drafts**, required unchecked registration acknowledgments with atomic server-side version/timestamp, privacy controls and version re-notification. OWNER and qualified Alberta professional review required before real use/publication; business/contact/legal facts remain marked placeholders.
- Separate unchecked student Remember Me using Secure/HttpOnly/SameSite=Strict rotating cookies, 30-day absolute/seven-day idle lifetime, replay/logout/password/role invalidation; teacher DPAPI remains separate.
- Additive private sidecar metadata, explicit backup/restore into new destinations with hash/SQLite integrity checks and credential/grant revocation on restore. No existing account database automatically migrated.

## Executed verification

Linux CPython 3.13/Xvfb full suite: **222 run, 218 passed, four platform/tool skips, zero failures**, 35.937 seconds. Skips: two Windows DPAPI tests and two optional browser harnesses; browser harnesses executed separately in the Playwright runtime. Subsequent changes only added first-party localization strings; eight focused localization tests and final Node checks passed afterward. Windows then exposed an open SQLite backup handle; deterministic connection closure and a closure-count regression were added, and all five recording-upgrade tests passed. A second Windows run progressed without assertion errors but hit the eight-minute runner limit near the end; its CI-only allowance was raised to 15 minutes. The final Windows suite includes the handle correction; application timeouts and assertions are unchanged. Windows final-source full suite: **222 run, 216 passed, 6 optional skips, zero failures/errors**, 277.999 seconds. Per-user Unicode/long-path install, no-Python-on-PATH frozen startup, uninstall/reinstall, DPAPI, client-only isolation and owned-process cleanup passed on **Windows Server 2025**, not physical Windows11. Defender: **scan_completed**, **0 threats**; Authenticode: **NotSigned**. Installer and OWNER manifest hashes match. See accompanying build reports and `verification.json`.

Other passing checks: **15 existing Node browser workflows**, recording-limit Node test, 51 preservation-focused Python checks, 28 recording/sharing-focused checks, 15 policy/auth/local-upload checks, actual Chromium synthetic media encoding and FFmpeg decode/index/seek, authenticated Resources HTML5 playback/Range through the real backend with mocked R2, bilingual unchecked policy/privacy controls, and persistent login across **separate Chromium process restarts over synthetic HTTPS**. These overlapping checks are not additional independent suite totals.

Latest short Cloud recording sample: target 1280×720/30, measured **29.6 capture FPS**, 329.1 ms cumulative Canvas CPU, one estimated missed capture frame, 1,385,312-byte available JS heap sample; whole-browser CPU approximately **58.1% of one core**, including synthetic inputs/test activity. Original 171,705 bytes; indexed 77 frames /2.629 s /172,025 bytes and actual seek passed. The **162 received-camera playback-drop counter** is synthetic offscreen input playback, **not RTP packet loss or encoded output loss**. Manual `requestFrame` track settings can report0 FPS; actual capture is separately measured. These are short synthetic Cloud results, not Windows sustained-performance acceptance.

The multi-source compositor test uses real synthetic MediaStreams but cannot certify remote reception: the attempted Cloud WebRTC loopback did **not establish ICE**. Physical Windows/iPhone/Android transport is explicitly unverified. Local Save As picker/writer is contract-mocked in browser tests. Time/size thresholds are simulated; no actual three-hour/five-GB physical run.

## Changed files

See [CHANGED_FILES.txt](CHANGED_FILES.txt) for the exact 53 source files. Areas:

| Area | Main files |
|---|---|
| Recording capture/limits/cloud | `classroom_recorder.js`, `recording_limits.js`, `classroom_recording.py`, `recording_cloud.py`, new `recording_media.py` |
| Resources/library/access | `server.py`, `recordings.js`, `teacher_recordings.py`, new `recording_resources.py`, `recording_resource.js`, `recording_management.js` |
| Guardian/policy/student auth | new `review_features.py`, `recording_authorization.py`, `guardian_authorization.py`, `policy_service.py`, `student_auth.py`, `account_privacy.js`, `policies/*`, `app.js` |
| Localization | `locales.js`, `teacher_localization.py` |
| Preservation/feature tests | new `test_recording_upgrade.py`, `test_recording_sharing.py`, `test_student_policies.py`, `test_student_browser.py`, `test_recording_limits.mjs`; existing recording, server and isolated-setup tests |
| Isolation/integrity/instructions | `owner_review.py`, `runtime_paths.py`, `review_backup.py`, `version.json`, `release_manifest.json`, `argos-review/SHA256SUMS.txt`, `.gitignore`, Windows build/installer/smoke/workflow files, setup guides |

No new Python dependencies. Existing pinned/hash-locked OWNER/client dependencies remain; Argos runtime/models are reused. FFmpeg is an explicit separately installed OWNER tool with saved executable hash, network input disabled, time/output/cancellation bounds and stream-copy indexing. The Windows installer is rebuilt because the native library navigation/localization and isolated installation profile changed.

## Remaining gates and cost/persistence limits

- Physical Windows 11 and iPhone/Android camera/audio/screen/annotation receipt, readability/sync, long-meeting 30 FPS and actual local Save As/low-disk/crash acceptance.
- Real private R2 multipart/restart/delete/lifecycle/security configuration; no live R2 was contacted. Windows FFmpeg setup and processing need actual OWNER acceptance.
- Guardian-controlled identity/evidence practice, owner/Alberta legal review and filling policy placeholders. Automated tests establish no legal compliance.
- Recorder browser must stay visible; minimization/hidden state safely stops capture. Unreceived feeds are not invented. Downloads/received bytes/local copies cannot be remotely recalled.
- Future Render requires one instance with persistent protected metadata (both SQLite databases), policy/config, spool/index/multipart state, trusted FFmpeg and adequate disk; no ephemeral/multi-instance deployment. Completed R2 recordings are independent of the teacher PC, but replacement OWNER still needs matching metadata/config. No Render deployment performed.
- 4.628 Mbps nominal is about 2.08 decimal GB/hour; 5 GB can arrive around 2h24m. The indexed copy roughly doubles storage. 25 GB retained budget is illustrative; at $0.015/GB-month it is $0.375 gross or about $0.225 above a fully available 10 GB free tier, excluding requests/taxes/eligibility and subject to current official R2 pricing. No zero-cost guarantee or purchase.
- Installer signature status and hosted Windows evidence are reported separately; do not treat Windows Server 2025 CI as a physical Windows 11 test.

Rollback: stop the review/browser, uninstall only MathStudio Recording Upgrade Review, retain/dispose its separate state and private cloud objects under the approved retention policy. Existing OWNER/PR9/PR10 installations remain unchanged. **Stop for review; do not merge, deploy or publish.**
