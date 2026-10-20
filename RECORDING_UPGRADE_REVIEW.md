# Recording/resources/policies review — stacked on PR #10

This is a separate review candidate, not a production release. It preserves PR8 Argos, PR9 website/pairing/teacher Remember Me and PR10 drawing fixes. No merge, deployment, DNS/TURN change, paid resource purchase or recording publication is performed. See `recording-upgrade-review/DELIVERY.md` in the draft PR for exact source/build hashes and executed results.

## 1. Separate Windows setup

1. Extract the OWNER ZIP into a **new** folder, e.g. `C:\MathStudioTests\RecordingUpgrade`.
2. Keep the existing OWNER, PR9, PR10, accounts and Argos installation unchanged. Use x64 Python 3.13; the teacher installer bundles its own pinned 3.13.12 runtime.
3. Double-click `REVIEW OWNER SETUP.bat`. Choose your **already installed and ready Argos home**. Setup copies its runtime/packages/receipt locally and self-tests the copy; it does not download translation models. Only pinned OWNER wheels may be installed. Optional offline wheelhouse commands remain in `REVIEW_OWNER_README.md`.
4. Double-click `REVIEW OWNER START.bat`. This candidate uses **5063**, `%LOCALAPPDATA%\MathStudioOwnerRecordingUpgradeReview`, and its own Quick Tunnel. It refuses an occupied port. Production 5051, PR9 review 5059 and PR10 review 5061 remain untouched.
5. Install `MathStudio-Recording-Upgrade-Review.exe`. It uses its own AppID, `MathStudio Recording Upgrade Review` installation directory and `%LOCALAPPDATA%\MathStudioRecordingUpgradeReview` profile. It remains a client-only application. Enter the new HTTPS review origin; first-time setup uses the local OWNER pairing window. Teacher DPAPI Remember Me is unchanged. Do not disable Windows protections; see the actual signature report (an unsigned review installer is not a signed release).

PowerShell alternatives, from the extracted OWNER folder:

```powershell
py -3.13 .\owner_review.py setup --argos-home 'D:\YourExistingInstalledArgosHome'
py -3.13 .\owner_review.py start
```

Use synthetic accounts only until owner/privacy/legal and real-device acceptance is complete. Review cookies are hostname-based, not port-isolated: use the separate Quick Tunnel hostname and browser profile. Starting this review does not migrate an existing account database.

## 2. Private R2, quotas and recording policy

Use an **already-existing private test R2 bucket**, never a publicly accessible bucket or permanent public URL. In the new review state's `empty-config.json`, use Notepad to set the existing allowlisted `MATH_R2_ACCOUNT_ID`, `MATH_R2_ACCESS_KEY_ID`, `MATH_R2_SECRET_ACCESS_KEY` and `MATH_R2_BUCKET` fields. Preserve other fields. Do not put secrets in Git, chat or command-line arguments. Verify `r2.dev` public access and public custom domains are disabled, use bucket-scoped credentials and configure lifecycle cleanup for both object keys and abandoned multipart uploads. No bucket is created by these scripts.

`data\recording-policy.json` is private, OWNER-controlled and absent from the ZIP. Example shape:

```json
{
  "enabled": false,
  "policy_approved": false,
  "private_cloud_approved": false,
  "notice": "Lesson recording notice / 课程录制通知: review the displayed storage, retention, audience and download scope before agreeing.",
  "retention_days": 7,
  "retained_quota_gb": 25,
  "guardian_authorizations": {}
}
```

Keep disabled until reviewed. Cloud mode additionally requires confirmed private R2 configuration; local mode does not require R2 credentials, but still needs OWNER policy/guardian/participant authorization. Retention is 1–30 days. The configurable retained quota is **12–1000 decimal GB**, default **25 GB**. The budget conservatively includes original plus seekable playback copy and index overhead. A new session reserves capacity for a maximum-sized original and derivative; actual byte growth is checked again. Quota/disk guards can stop a session earlier and report the cause.

Legacy PR10 guardian-expiry entries cover only the former private cloud/per-meeting flow. They **do not** authorize new local storage, standing consent, recipient sharing or downloads. New scope requires the verified workflow below.

## 3. Guardian evidence, separate student agreement and policy drafts

Editable English/Chinese drafts are in `policies/privacy.*.md`, `terms.*.md` and `cookies.*.md`. They contain conspicuous placeholders for the legal/business name, contacts, effective date, commercial rules and retention/residency facts. They do not certify Alberta compliance. Owner and qualified Alberta privacy/legal review is required **before real use/publication**. The application is not an automated guardian identity-verification service.

Policy document changes produce a new acknowledgment digest automatically. `policies/manifest.json` also tracks owner/legal review and the recording scope version. A document/scope change invalidates prior standing/guardian scope for new use; do not silently broaden old recordings' permissions. Registration requires separate, initially unchecked Terms acceptance and Privacy/Cookie acknowledgments; accepted versions/timestamps are stored server-side atomically with new-account creation. Existing accounts are notified and can acknowledge at Privacy & recording authorization. Optional recording authorization is never inferred from registration. Current policies must be acknowledged before new standing authorization or catch-up resource access.

OWNER must independently verify a guardian's identity, relationship/authority and actual decision (e.g. an appropriately verified guardian-controlled written process). Keep that evidence securely outside Git. Only after professional/owner review is recorded can OWNER enter a decision using:

```powershell
py -3.13 .\guardian_authorization.py grant --data "$env:LOCALAPPDATA\MathStudioOwnerRecordingUpgradeReview\data" --user-id 42
```

`42` is an example: select the correct existing student ID. The tool verifies the account exists, requires OWNER's explicit verification attestation, prompts privately for an evidence reference, and stores its digest rather than the document/reference text. It then asks for the guardian-approved JSON scope and expiry. It does not send messages or verify a guardian merely because a student checked a box.

Scope example **only when actually authorized**:

```json
{"storage":["local","cloud"],"sharing":true,"download":false,"retention_days":7}
```

The fixed purpose is lesson review; the only supported sharing audience is named, verified absent enrollees of the same scheduled lesson. Do not copy a broad example instead of obtaining the actual decision. Student → Privacy & recording authorization must then separately choose and meaningfully agree to a scope no broader than the verified guardian decision. Standing authorization is optional; when absent, fresh per-recording consent is still possible if guardian scope covers it. Guests remain ineligible. Valid standing scope avoids the same repeated checkbox, but **never removes recording notices or withdrawal controls**.

Guardian withdrawal:

```powershell
py -3.13 .\guardian_authorization.py withdraw --data "$env:LOCALAPPDATA\MathStudioOwnerRecordingUpgradeReview\data" --user-id 42
```

A student can withdraw through privacy settings or the meeting notice. Active capture stops within the existing bounded notification/lease behavior. Future sharing of that student's recorded participation is revoked. Earlier media, local files, already received bytes and downloaded copies require handling under the reviewed policy; this patch cannot remotely erase copies on other devices. Old private recordings cannot acquire a new audience just by changing a checkbox later.

## 4. Teacher recording workflow and limits

Start the lesson and open its existing **Video panel**. Choose **Cloud Recording** or **Local Recording**, optional absentee audience/download permission, and (for local) whether a later explicit cloud upload is authorized. These choices form the displayed consent scope. The native recording controls still operate the meeting browser; no second incompatible encoder is introduced. Only teachers start/pause/resume/stop.

Target: **1280×720, 30 capture FPS**, VP8/Opus where supported, 4.5 Mbps video / 128 kbps audio target. MP4 is selected only when the browser supports it. The main 16:9 screen/board region uses matched letterboxing, with available camera tiles beside it. Enabled, actually available local/received cameras and microphones plus synchronized teacher/student annotations are used. Disabled sources are excluded. Screen/board transitions use the current snapshot; no remote feed is invented. WebRTC negotiation/TURN and native pen input sampling are unchanged.

The UI reports the selected codec, actual stream settings, measured capture FPS, Canvas CPU time, missed-capture estimate, received-video playback-drop counters and available JS heap measurement. `captureStream(0)` uses manually requested frames, so its track may report `frameRate: 0`; measured capture FPS is shown separately. A sustained measurement below 27 FPS generates a visible limitation warning, not a silent quality downgrade. Counters are diagnostics, not proof of physical-device input latency, RTP loss or encoded-frame delivery. Keep the recorder browser visible; hidden/minimized state safely stops capture.

All sizes use **decimal units: 1 GB = 1,000,000,000 bytes**. Limits are **3 hours elapsed session time** (including pauses) or **5 GB encoded original**, whichever comes first. Visible, nonblocking warnings are separate and persist: at **2h30m**, and at **4 GB**. Both may appear. Capture stops slightly before the size ceiling to reserve at most an 8 MiB final chunk, collects the final encoder chunk and finalizes. Unexpected encoder output beyond the hard ceiling is reported interrupted rather than truncated and falsely marked successful. An encoded chunk above 8 MiB or a bounded queue overrun also stops with an error. Duration/size limits are simulated in automated tests, not a claimed three-hour physical endurance run.

Cloud mode continuously sends one-second bounded chunks to OWNER. OWNER fsyncs/checkpoints bytes, starts private R2 multipart parts **during capture**, and gives each transfer a bounded part per turn. Separate processing and transfer workers prevent indexing an older recording from holding up new capture chunks. Network failures retain upload IDs/ETags and retry. States include capturing, processing, uploading, completed (`ready`), local, importing, interrupted, failed and deleting. Final R2 acknowledgment is required before completion. OWNER temporary originals/derivatives are removed after successful processing/upload; crash/failed cleanup can retain private temporary files until retry/retention cleanup.

Local mode requires the File System Access API in current desktop Chrome/Edge. The user chooses Save As; there is **no claim of arbitrary filesystem access or a 5 GB in-memory download fallback**. Bounded writes go to the browser's chosen writable stream, which is closed at finalization. Low disk/permission/write/close failures are reported; a browser/OS crash can lose an uncommitted file. OWNER still must be reachable for consent leases and non-media integrity checkpoints. No local media is automatically uploaded to R2.

For a later explicit upload, select the original file under Recordings → Manage sharing / upload in the authenticated library. This is offered only when the original consent included future cloud storage. Stored per-chunk sizes/hashes bind the selected file to the original authorized recording; mismatches are rejected, uploads resume from acknowledged chunks, and the complete byte count must match before finalization. Consent withdrawal/expiry/scope changes can prevent the upload. Metadata marked failed after an unacknowledged local save is not silently treated as finalized; contact OWNER for review rather than bypassing checks.

## 5. Seekable playback processing — explicit OWNER setup

The original browser container may lack a finished seek index. Absentee sharing is blocked until a **seekable private playback copy** is successfully indexed and uploaded. Explicit Download preserves the original playable format. Teacher access to the original remains private while playback preparation is pending.

This uses an optional, explicitly selected **FFmpeg executable**, stream-copy only (not another recording engine, paid API or Python dependency). No binary is discovered from untrusted folders, downloaded or executed automatically. Obtain a current trusted build using the official project's platform links at https://ffmpeg.org/download.html and verify the distributor's provenance/security updates. The ZIP does not bundle FFmpeg. This Windows installation step remains OWNER-side; the teacher EXE never needs it.

Configure before a lesson, using an **absolute path to the trusted executable you selected**:

```powershell
py -3.13 .\recording_media.py configure --data "$env:LOCALAPPDATA\MathStudioOwnerRecordingUpgradeReview\data" --path 'C:\Tools\FFmpeg\bin\ffmpeg.exe'
py -3.13 .\recording_media.py status --data "$env:LOCALAPPDATA\MathStudioOwnerRecordingUpgradeReview\data"
```

The chosen executable's SHA-256 is saved privately and checked before subsequent use. Reconfigure deliberately after a trusted binary update. Processing disables network input protocols, has wall-time/output bounds and shuts down with OWNER. It creates an index/fast-start container without re-encoding media. Missing/failed indexing never marks absentee playback ready. Interrupted recordings remain in the private teacher library and cannot be shared as successfully finalized lessons. No Windows FFmpeg execution or real R2 completion is claimed by Linux tests.

## 6. Share through Resources, never automatically

MathStudio.exe → Recordings → select completed recording → **Manage sharing / upload**. The authenticated browser library shows its scheduled lesson roster. Actual joins record presence. Lack of a presence record is **unknown**, not automatic absence; the teacher must explicitly and independently verify each eligible absence. Accounts marked present cannot simply be relabeled absent. Enrollment is checked both against the capture roster and current lesson enrollment. Quick Meetings have no eligible scheduled roster and remain private.

Choose the verified absent accounts, expiry and allowed downloads. A 20-character unpredictable code is generated only on explicit teacher action. Use **Copy code**, then existing **Messages** to send it manually. Nothing is sent automatically. Grant history permits revocation. Only the creator manages grants; other teachers/students cannot manage unrelated recordings.

Student: sign in → acknowledge current policies if due → Resources → enter code → lesson title/date/duration → Watch Online, and Download Recording only when permitted. The HTML5 player uses the indexed private object and authenticated Range requests. Every request rechecks the account, current enrollment, verified absence, named viewer list, code expiry/revocation, recording retention, subject/guardian sharing scope and download setting. No R2 credential, permanent public URL or object key is exposed. Codes themselves are insufficient for access. Grants/revocations/redemptions/play/download/delete decisions have content-free private audit records; repeated play/download requests are coalesced within a minute and audits expire after 90 days.

A revoked grant blocks new requests, not bytes already received or copied. A permitted viewer can potentially screen-record; technical download prohibition is not DRM. The reviewed policy and conduct rules remain necessary.

## 7. Student Remember Me

Student website login has a separate **unchecked** Remember me on this device option and shared/public-device warning. It uses a Secure, HttpOnly, SameSite=Strict cookie with rotated random validators and a revocable server-side family; no password/long-lived token is put in localStorage. Maximum absolute lifetime is 30 days, idle lifetime seven days. Restoration does not extend absolute expiry. Explicit logout, password/role invalidation, expiry and replay detection revoke the affected family and its restored sessions. Expired ordinary sessions can restore before a failed authentication/CSRF request is retried once. Unchecked login remains an ordinary session. Teacher DPAPI credentials remain a separate family.

The real browser restart test uses separate Chromium processes/profile persistence over synthetic local HTTPS. It is stronger than page refresh/navigation but does not certify Windows/browser-specific storage settings.

## 8. Data, backup/restore and future hosting

New policy, scope, attendance, share/audit and student credential tables live in a **separate `data/review-features.sqlite3` sidecar**. Existing account table schemas are not migrated by this upgrade. No existing account is retroactively marked as accepting policies or consenting to recording. Both databases and their associated media/checkpoints require persistent, protected storage.

Before deliberately applying any future migration to an existing review, stop that OWNER first. The explicit utility copies selected data into a new location, verifies file hashes and SQLite integrity, and never overwrites the source or an existing destination:

```powershell
py -3.13 .\review_backup.py backup --from-data "$env:LOCALAPPDATA\MathStudioOwnerRecordingUpgradeReview\data" --to-data 'D:\PrivateBackups\MathStudioReview-1' --port 5063
```

Backups include private data: keep them encrypted, access restricted and outside Git. Test restoring into a **new** review state, never directly into production. First create that new state's runtime using `owner_review.py setup --state ... --argos-home ...`; do not start it. If setup created an empty data folder, preserve/rename that empty folder before selecting a fresh destination. Then:

```powershell
py -3.13 .\review_backup.py restore --from-data 'D:\PrivateBackups\MathStudioReview-1' --to-data 'D:\NewReviewState\data' --port 5063
py -3.13 .\owner_review.py start --state 'D:\NewReviewState'
```

The restored runtime/state must have been set up at `D:\NewReviewState`. Restore verifies integrity, revokes teacher/student persistent credentials and all restored guardian/standing/share permissions so an old backup cannot silently resurrect revoked access. Re-verify/re-authorize deliberately. The original data remains unchanged. Ordinary in-memory sessions disappear on restart. Model storage is separate; this utility does not alter the original Argos installation.

No Render deployment is performed. A future single-instance OWNER needs a persistent writable disk for both SQLite files, policy, source spools, indexes and multipart checkpoints; ephemeral storage or multiple independent instances is unsupported. Completed private R2 objects no longer depend on the teacher PC or original local OWNER remaining online, but the replacement server still needs matching persistent metadata/configuration. Processing may require an additional original+indexed temporary copy: budget **at least 12 GB free for one maximum recording**, plus retained quota, accounts/uploads/models and backup reserves. Encrypt/protect disks/backups; configure R2 lifecycle as an offline-retention backstop.

## 9. Storage/cost and manual gates

At nominal 4.5 Mbps video + 128 kbps audio, one hour is about **2.08 decimal GB**, so high-motion content can hit 5 GB at roughly 2h24m. Content-dependent variable bitrate may be much smaller; the 3-hour limit is not a promise that a high-bitrate three-hour recording fits. The indexed copy roughly doubles cloud media storage. Two 5 GB copies consume about **10 GB** before container/accounting overhead, potentially all of R2's commonly advertised free 10 GB-month allowance. This is not a price guarantee. Illustratively, at $0.015/GB-month, 25 GB is $0.375/month gross storage or about $0.225 above a fully available 10 GB free tier; requests, account eligibility, taxes and current billing must be verified at https://developers.cloudflare.com/r2/pricing/. No services are bought here. Multipart operations and playback Range requests add operations; quotas/retention limit growth.

Actual Windows 11 stylus/mouse, camera/audio, 30 FPS sustained encoding, local Save As/disk exhaustion, long-meeting endurance, iPhone/Android receipt, mobile interruptions and audio-level/sync acceptance remain manual. Cloud loopback WebRTC produced no established ICE transport; it is not claimed as a successful remote-device test. Synthetic browser composition, real encoder/decode/index/seek and real browser-restart behavior are separately documented. Live private R2, guardian identity practice, legal publication and Render persistence require review before real students.

Rollback: stop this candidate/browser, uninstall **MathStudio Recording Upgrade Review**, retain or safely dispose of its separate state under the approved retention policy. Production, PR9 and PR10 installations remain separate. Remove review cloud objects through authorized controls/lifecycle before discarding their metadata. Stop for review: do not merge, publish policies/recordings or deploy automatically.
