# PR #9 paired-login review distribution

Build identity: **v41.6.6-pr9-pairing-review1**. Both artifacts use the same
hash-verified `release_manifest.json`; the adjacent delivery/build manifests
record the precise source head, CI checkout and artifact SHA-256. A GitHub
temporary test-merge checkout is not a merge of the protected branches.

## Windows sequence

Follow `REVIEW_OWNER_README.md`: extract into a new source folder, run
`REVIEW OWNER SETUP.bat` to locally copy the existing ready Argos runtime and
models, install official cloudflared if needed, then run
`REVIEW OWNER START.bat`. Review data/models are isolated outside the source
tree and the backend uses loopback port 5059. Only base OWNER wheels are
installed; existing Argos dependencies/models are neither changed nor downloaded.

Install the matching teacher **review** EXE at its default MathStudio Review
location. Select the OWNER's displayed HTTPS origin. For an uninitialized
OWNER, explicitly enter its locally displayed, 15-minute one-time code in
First-Time Teacher Setup, enter a username/name and 12–256-character password,
and create the teacher account. No visitor can create an admin without that
code. Account creation, publication and translation administration require
server authorization and CSRF. No secret appears in a URL or OWNER log.

Use new synthetic student accounts for browsing, scheduling and classroom
tests through the same HTTPS origin. Do not point the review app at production.
The temporary tunnel is a testing feature, not permanent hosting or deployment.

## Login boundaries

Remember Me defaults off. Enabling it requires the teacher's password again
on the authenticated API and saves only an origin/profile-bound, per-user
Windows DPAPI ciphertext. The server stores hashes of the random credential
and random device binding, the password fingerprint, and bounded expirations.
Each restoration atomically rotates the secret and replaces previous access
sessions for that device. Replay revokes its credential family. Rotation does
not extend the original 30-day limit; inactivity expires it after 7 days.

Password changes, admin-role removal, expiry and revocation invalidate the
remembered browser/native session, including native annotation/meeting tokens.
Settings can disable Remember Me while keeping the current ordinary session.
Sign out revokes the device credential and clears its local ciphertext.
If remote logout cannot be confirmed, the app reports failure and lets you
retry; it does not pretend the server has revoked it. A failed refresh or lost
rotation response falls back to password login; invalid output never restores
authentication. Sensitive credential management uses password reauthentication;
this change adds no unauthenticated password-change or admin-reset API.

The review profile is separate from production. A new Quick Tunnel origin
requires login again; use Connection settings to update it. If the previous origin is
offline, switching clears its local credential and explicitly warns that
remote revocation is unconfirmed. The old device expires normally; an OWNER
password reset revokes it immediately on its next authenticated request.
Disabling all
administrators does not reopen first-run setup: a durable initialized flag
prevents a new claim. Use the existing local OWNER account-recovery commands
explicitly if needed, never a public reset endpoint. For a code that expires
before first setup, restart only the uninitialized review OWNER to renew it.

## Changed files and purpose

- `owner_launcher.py`: parameterize the existing owned Quick Tunnel launcher
  for port 5059/loopback and refuse review server adoption; preserve 5051 defaults.
- `owner_review.py`: launch that tested tunnel path instead of a bare server.
- `owner_auth.py`: one-time local pairing window, durable initialization,
  hashed rotating credentials and expiry/role/password validation.
- `server.py`: additive credential schema and focused desktop auth routes;
  startup no longer asks for an account; native authorization observes
  remembered-session revocation. Existing auth/CSRF/rate controls remain.
- `desktop_credentials.py`: Windows DPAPI storage; no plaintext fallback,
  no passwords, atomic writes and separate per-origin/profile storage.
- `teacher_desktop_app.py`: first-run setup, asynchronous login/restoration,
  optional Remember Me, disable/sign-out and credential-safe server switching.
- `teacher_localization.py`: English/Simplified Chinese authentication labels;
  original teacher/student text remains unchanged.
- `version.json`: one shared review identity to reject incompatible clients.
- `windows_teacher.py`: bundled DPAPI self-test evidence.
- `packaging/windows/{MathStudio.spec,check_client_payload.py}`: keep OWNER auth
  modules out of the teacher payload alongside Argos and model exclusions.
- `packaging/windows/{build.py,smoke.ps1,verify_distribution.ps1}` and the
  Windows workflow: publisher/provenance metadata, real bundled DPAPI check,
  signature inspection and Defender scan when actually available.
- `test_desktop_auth.py`: synthetic first-run, CSRF, brute-force, concurrency,
  replay/revocation/expiry, native authorization, Tk and actual Windows DPAPI
  process-restart tests. Two existing bootstrap tests now expect paired auth.
- Manifest/checksums/review instructions and delivery evidence: track exactly
  the source and artifacts included in this review distribution.

Argos worker/setup/runtime, language-model locks, WebRTC negotiation,
transceivers, camera/microphone/screen-share implementation, booking/timezone
and annotation operations are intentionally unchanged. No models, secrets,
databases, accounts, venvs or server packages are in the teacher installer.

## Authenticity, signing and SmartScreen

This review is **unsigned unless the delivery verification explicitly proves
otherwise**. No authorized signing certificate or managed signing identity was
provided. No certificate is purchased, no self-signed certificate is used,
and Windows/browser protections must remain enabled. The installer is per-user
(`PrivilegesRequired=lowest`), uses accurate project publisher/version metadata,
and uses no UPX/packer obfuscation. Review paths/App ID/profile are separate.

Windows CI records `Get-AuthenticodeSignature` and attempts a Microsoft
Defender custom scan only if its service is enabled. A missing/unavailable
scanner is recorded as **not scanned**, not as a malware-free verdict.
No file is sent to a third-party scanning service.

For trusted public distribution, obtain a CA-issued Authenticode certificate
or an eligible managed signing service and authorized signing environment.
Indicative budgeting only (verify provider/current regional pricing):
commercial OV signing often costs roughly US$200–600/year plus hardware or
managed key storage; Microsoft Artifact Signing's entry tier has historically
started around US$10/month, subject to identity, region and eligibility rules.
No current quote was obtained and nothing was purchased. Signing must occur
after building, then be checked with `signtool verify /pa /v` and
`Get-AuthenticodeSignature`; recalculate all hashes after signing.

Signing proves publisher identity/integrity. **SmartScreen reputation is a
separate assessment**: a newly signed executable/publisher can still receive
warnings. Consistent legitimate signing/distribution and Microsoft's normal
false-positive submission process may help; a certificate does not guarantee
warnings disappear. Never disable Defender/SmartScreen or add exclusions.

## Acceptance still required

The final delivery report distinguishes local synthetic tests, actual hosted
Windows CI tests, scanner availability and physical-device checks. A mock
tunnel lifecycle test does not prove public HTTPS reachability. Test the real
temporary URL in student and teacher clients, first-run pairing, app restart
with/without Remember Me, remote logout/revocation, content translation review
and explicit publication. Test actual Windows 11, iPhone and Android
bidirectional audio/video, screen share/annotation, sleep/resume and reconnect.
No production account, live class, DNS, deployment or installed app was changed.

Stop the review OWNER with Ctrl+C before removing its **review-only** data
folder. Keep production data untouched; do not copy review databases into it.
Rollback uses the previous review ZIP/installer with its matching separate
data snapshot; do not run an old server against newly published private drafts.
