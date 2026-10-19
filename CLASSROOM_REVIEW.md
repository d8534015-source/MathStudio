# MathStudio classroom recording and pen review

Review candidate only. Do not replace production or the earlier PR9 review.
See the matching delivery report for executed tests, source revision and checksums.
No cloud resources are provisioned, credentials embedded, or recordings published.

## Isolated Windows installation

1. Extract the complete OWNER ZIP into a new folder, e.g. `C:\MathStudioTests\Classroom`.
2. Keep the original OWNER and Argos installation unchanged. Install/retain x64 Python 3.13.
3. Double-click `REVIEW OWNER SETUP.bat`, select the **existing installed Argos home** when prompted. This copies its runtime, installed models and verified receipt into `%LOCALAPPDATA%\MathStudioOwnerClassroomReview\translation`; no models are downloaded. Pinned OWNER dependency wheels may require internet during this one-time setup. For an offline wheelhouse, use the commands in `REVIEW_OWNER_README.md`.
4. Double-click `REVIEW OWNER START.bat`. It owns a separate Quick Tunnel and listens on **5061**, refusing reuse of an occupied port. Production 5051 and PR9 review 5059 remain separate. Use synthetic accounts only.
5. Install the matching `MathStudio-Classroom-Review.exe`. Its separate AppID, `MathStudio Classroom Review` install directory and `%LOCALAPPDATA%\MathStudioClassroomReview` profile preserve both earlier review and production installations. It is a **client**, not an OWNER server. It does not bundle Argos or models.
6. Enter the current review HTTPS address in Connection & studio. First-time Teacher Setup uses the OWNER's one-time pairing window. Existing security and optional Windows DPAPI Remember Me remain in place.
7. Keep Windows security protections enabled. This review installer is unsigned unless the matching distribution report explicitly says otherwise. No trusted signing certificate is available in Cloud.

PowerShell equivalents from the extracted OWNER folder:

```powershell
py -3.13 .\owner_review.py setup --argos-home 'D:\YourExistingInstalledArgosHome'
py -3.13 .\owner_review.py start
```

## Drawing changes and acceptance

Mode switching completes the active stroke and releases owned Tk/Win32 capture without reapplying layered-window styles or flushing idle events. Worker completions enter a bounded queue and execute on the UI thread. Pen motion draws only the new segment; samples and the final endpoint are retained, with protocol-sized continuation strokes. Up to 128 unsent operations are retained in memory, rebased on conflicting server versions. A full outbox stops accepting new strokes with a visible warning; reconnect or explicitly clear. Pending ink is not durable after an app/process crash. Closing warns before discarding pending ink.

The portable benchmark is `py packaging\benchmark_pen.py`; in a source checkout, `--baseline` reads the previous PR9 source from Git. The measured 1,200-event workload with 100 prior strokes reduced Canvas command submissions from **122,400 to 1,200**, and coordinate submissions from **16,742,476 to 4,800**. Stored current-stroke points increased from 1,149 to 1,201 because the old distance filter discarded samples. Handler timings on Cloud were p50 0.739→0.00116 ms / p95 1.102→0.00215 ms. These measure Python/Canvas-command work, **not physical stylus or input-to-photon latency**.

On actual Windows 11, verify repeated Draw↔Interact switches with an active stroke, mouse and stylus, PowerPoint/PDF interaction, native sharing on/off, disconnect/reconnect, remote concurrent drawing, undo/erase/clear conflicts, and close with pending ink. Write fractions, exponents, integrals, small labels and long curved strokes. Verify no missing endpoints or stuck capture. These hardware checks remain manual.

## Recording: disabled until OWNER approves policy and private R2

The teacher's existing **Video panel/browser** receives the actual meeting media and performs the composite recording. The native desktop overlay alone does not receive remote WebRTC audio/video. No new camera/microphone permissions, transceivers or SDP negotiation are introduced. Native Recording opens a small control panel; open Video panel, read the notice, request consent, then explicitly press Start recording there. Native Pause/resume and Stop recording control that browser recorder. Keep the recorder browser visible; hiding/minimizing it safely stops recording rather than risking background capture or missing frames.

Only enable recording after establishing the applicable school/legal consent policy. This implementation requires **every connected student** to have unexpired OWNER-recorded guardian authorization, plus affirmative consent from every connected participant for each recording. Unverified guests cannot be recorded. This is deliberately conservative. Consent never gives students recording-library access.

In the separate review state folder, use Notepad to edit `empty-config.json`, preserving any existing fields. Set the existing allowlisted `MATH_R2_ACCOUNT_ID`, `MATH_R2_ACCESS_KEY_ID`, `MATH_R2_SECRET_ACCESS_KEY`, and `MATH_R2_BUCKET` fields. Use a bucket-scoped credential for an **already-existing private test bucket**. Do not paste secrets into Git, command-line arguments or chat. Verify in Cloudflare that `r2.dev` access and public custom domains are disabled. Restrict bucket access, enable appropriate audit controls and configure lifecycle cleanup as below. Do not use a production student bucket in review.

Create `%LOCALAPPDATA%\MathStudioOwnerClassroomReview\data\recording-policy.json` as UTF-8 JSON. Example structure (recording stays disabled until the explicit flags are approved):

```json
{
  "enabled": false,
  "policy_approved": false,
  "private_cloud_approved": false,
  "notice": "Recording includes enabled microphones, received cameras, shared screens and annotations. Decline or withdraw if you do not consent. / 录制包括已启用麦克风、收到的摄像头画面、共享屏幕和批注；不同意可拒绝或撤回。",
  "retention_days": 7,
  "guardian_authorizations": {}
}
```

OWNER must verify and retain guardian authorization separately, then enter each authorized student's **numeric account ID** as a JSON property mapped to the authorization expiry as UTC Unix seconds. Example shape only: `"42": 1900000000`; never copy this example as a real authorization. Do not include names, birth dates, guardian documents or private messages in the policy. Restrict state-folder access to the server identity/OWNER. Only after policy and private bucket verification set the three approval/enable flags to `true`. Restart the isolated OWNER to load its R2 configuration. Policy changes/revocation are rechecked during recording heartbeats; no teacher/student API can grant guardian authorization.

Every participant sees the notice and recording/paused indicator. Membership changes stop capture before a new peer is admitted; retry joining after recording stops. Declining or withdrawing stops the session. The recorder renews short leases, stops on loss of authorization, and schedules audio mute at lease expiry. Network propagation is not instantaneous; lease expiry bounds capture when a stop notice cannot be delivered. A paused recording remains visible and requires the same cohort/authorization to resume. Other teachers/students cannot control a recording owned by a different browser peer.

## Media, reliability and storage

The recording combines the browser's **actually available** local/remote enabled camera feeds, enabled microphone tracks, the active received/native shared screen and synchronized board canvas. Missing/unreceived feeds are omitted, not reconstructed or claimed as captured. Screen and annotations use the same 16:9 stage geometry, including letterboxing. Camera tiles occupy a side strip. Canvas capture is capped near 15 fps at 1280×720; nominal VP8/Opus video/audio rates are 1.8 Mbps / 96 kbps. WebM is preferred; MP4 is used only when the browser supports it. No teacher EXE encoder, paid API, or new Python dependency is required.

One-second browser chunks are sequentially uploaded to authenticated OWNER endpoints. The browser queue is bounded (8 chunks / 32 MiB; 8 MiB maximum individual chunk), retries acknowledgments idempotently, and stops visibly on backpressure. OWNER durably checkpoints received bytes and truncates uncommitted tails after a crash. A browser close/network loss can lose the final unacknowledged chunk; recovery marks such recordings interrupted. Interrupted files are not guaranteed playable. Stop awaits the final MediaRecorder chunk before finalization. Browser WebM may have limited seeking/duration metadata until buffered; no server remux/transcoding is claimed.

Limits: **2 hours wall time per recording, 2 GiB each, 5 GiB total metadata-counted retained recordings**, minimum free disk guards and 1–30 day retention. Stop and begin a newly consented recording for a longer meeting. Upload status remains `uploading` until R2 acknowledges multipart completion. Cloud transfers run on an independent worker with 8 MiB buffers, durable upload IDs/ETags, interrupted-transfer retry and lost-completion acknowledgment recovery. Successful completion removes the OWNER spool, leaving the private cloud object. No permanent recording is written to the teacher's PC; an explicit teacher Download intentionally saves a user-selected browser download. Recording adds encoding/network load; actual classroom load testing remains required.

**Recordings** in MathStudio.exe lists date, meeting title, captured duration, processing state and interrupted status. Play/Download open an authenticated browser handoff; Delete requires confirmation. Access is restricted to the **creating teacher account**, with current role/session validation. Playback/download requests require both a current teacher session and a 60-second session-bound access ticket, and are streamed from private R2 with byte-range support. Reopen playback if a later seek encounters ticket expiry. Students cannot list, play, download or delete recordings, even with an ID or copied ticket. No permanent public or presigned bucket URLs are exposed. TLS protects transfers; Cloudflare R2 provides default encryption at rest. The teacher/OWNER must protect the server disk and backups with OS/cloud disk encryption.

Retention cleanup runs on OWNER; expired files become inaccessible immediately even before cloud deletion completes. Deletion removes the private object and unfinished multipart upload, then metadata/spool. Configure private-bucket lifecycle expiration as a backstop, matching the intended retention and covering unfinished multipart uploads. Failed cloud cleanup retries while OWNER is running; bucket lifecycle is needed when it is not. Review retention and any external backups separately.

## Render/server requirements (no deployment performed)

Completed cloud recordings do **not** require the teacher PC or the original local OWNER machine to stay online. A replacement Render OWNER can serve them using the same private R2 configuration and restored metadata. It requires:

- A **persistent writable disk** for `MATH_DATA`: SQLite metadata, consent policy, in-flight spool and multipart checkpoints. Ephemeral/free filesystem storage is insufficient for reliable interrupted uploads or account/recording metadata. Keep at least the configured 5 GiB recording quota plus free-space reserve and database/model capacity.
- A single OWNER process/instance for this SQLite/in-memory classroom architecture. This patch does not implement shared-room state, distributed workers or multi-instance failover.
- A process allowed to run the asynchronous upload/retention worker, outbound HTTPS to the private R2 endpoint, appropriate TLS/public-origin/proxy configuration, and backups of metadata/policy/configuration. Models remain OWNER-side in their existing persistent external location.
- Sufficient CPU/memory for the existing application and optional offline Argos. Recording encoding runs in the meeting browser; this implementation requires no server-side encoder/FFmpeg. Server work is authenticated chunk spooling, private multipart transfer and authenticated streaming.

R2 storage/operations/egress and any Render persistent services can incur costs. No paid resources are created here. At nominal rates a full hour is roughly 0.85 GiB before content/codec variation; quotas and retention bound storage. Measure actual costs/load before enabling production.

## Manual review gates

- Windows 11 Chinese/English locale: setup, separate install/profile, pairing, optional Remember Me, bidirectional existing Argos models, Website Management, scheduling/DST and browser/native handoff.
- Windows teacher with iPhone Safari/Android Chrome peers: simultaneous bidirectional cameras/audio, screen/native sharing and synchronized annotations remain intact before/during/after recording. Mobile sleep/AirPlay/interruptions and reconnect remain manual.
- Guardian missing/expired, declined/withdrawn consent, guest joining, new/rejoining peer, pause/resume, browser hidden/closed, token/session revocation and ended class: no new unauthorized capture, clear notices, safe interruption.
- Teacher-only library controls; second teacher/student/anonymous requests and copied URLs denied. Private bucket public-access settings verified by OWNER. R2 credentials, real retention/delete and Render restart/disk recovery remain unverified with live infrastructure.
- Actual long meeting, slow/disconnected uploads, disk/quota exhaustion, partial playback and cloud finalization. Check actual audio mix levels/sync, annotation alignment on differently shaped screens, all available camera tiles, disabled devices omitted, no original meeting tracks stopped.

Rollback: stop this review OWNER/browser, uninstall **MathStudio Classroom Review**, and retain/remove its separate review state as appropriate. Production and PR9 review remain unchanged. If review recordings exist, delete them through authenticated controls or approved private-bucket retention before disposing of metadata. No merge/deployment is authorized.
