# Recording Stop and native input repair review

Stacked on Draft PR #11 delivery `336d744c0680183832ac499ddaa4a1e93ea47721`. This is a separate synthetic-test candidate, not a production release. See `stop-input-review/DELIVERY.md` in the draft PR for immutable source/build revisions, checksums and executed results.

## Separate Windows installation

1. Extract the complete OWNER ZIP into a **new folder**, e.g. `C:\MathStudioTests\StopInput`. Do not extract over production, PR9, PR10 or PR11. The archive has one application root, not nested older releases.
2. Keep x64 Python 3.13 installed. Run **REVIEW OWNER SETUP.bat**, selecting the existing ready Argos home when prompted. It copies and verifies the installed runtime/packages/receipt into this review, without downloading models or modifying the original.
3. Run **REVIEW OWNER START.bat**. OWNER uses **5065**, `%LOCALAPPDATA%\MathStudioOwnerStopInputReview` and its own HTTPS Quick Tunnel. An occupied port is refused, never reused. Production5051, PR9 5059, PR10 5061 and PR11 5063 are unchanged.
4. Install the matching **MathStudio-Stop-Input-Review.exe**. It is client-only, with a new AppID, install directory and `%LOCALAPPDATA%\MathStudioStopInputReview` profile. It does not host OWNER. Enter the new review HTTPS origin and use OWNER pairing. Keep Windows protections enabled; this review executable is unsigned unless its actual signature report says otherwise.
5. Use synthetic accounts and authorized development participants only. The review contains no accounts, credentials, private databases/files, virtual environments, Argos models or recordings. New state starts empty; existing account databases are not automatically migrated.

PowerShell from the new extracted application folder:

```powershell
py -3.13 .\owner_review.py setup --argos-home 'D:\YourExistingReadyArgosHome'
py -3.13 .\owner_review.py start
```

`--wheelhouse 'D:\TrustedOwnerWheels'` can reuse pinned OWNER dependency wheels. The teacher installer bundles Python; the teacher PC needs neither a separate Python installation nor FFmpeg/Argos.

## Recording configuration and prior protections

Configure this review's own private test R2/policy/guardian settings deliberately. Do not copy production secrets or student data into development. See the inherited `RECORDING_UPGRADE_REVIEW.md` for the private bucket checks, consent scopes, quotas, policies, cost estimates and explicit guardian process, substituting **5065**, **MathStudioOwnerStopInputReview**, **MathStudioStopInputReview** and the new installer name wherever that historical PR11 guide names its older profile. Do not enable recording merely to bypass consent requirements. R2 credentials belong in the new state's private config, never command arguments/Git/chat. No bucket or paid service is created by this repair.

Configure a trusted, explicitly selected FFmpeg on the **new OWNER state**:

```powershell
py -3.13 .\recording_media.py configure --data "$env:LOCALAPPDATA\MathStudioOwnerStopInputReview\data" --path 'C:\Tools\FFmpeg\bin\ffmpeg.exe'
py -3.13 .\recording_media.py status --data "$env:LOCALAPPDATA\MathStudioOwnerStopInputReview\data"
```

No FFmpeg binary is automatically downloaded/executed. Existing pinned dependencies and Argos translation code/models are unchanged. Retention, 3h/5decimalGB limits, 2h30m/4GB warnings, conservative guardian/participant consent, withdrawal, private R2, authenticated Range access, policy drafts, student Remember Me and teacher DPAPI remain. Scheduled absentee sharing still requires explicit creating-teacher selection of named, verified absent enrollees of the exact scheduled class; expiry/revocation and manual Messages delivery remain. Instant meetings remain private. There is **no automatic sending**.

## Root causes and repair boundaries

**Confirmed in the Cloud browser against authenticated OWNER:** when no enabled audio source was connected, Chromium's MediaStreamAudioDestinationNode did not supply samples. MediaRecorder produced zero chunks, including on Stop; OWNER correctly stored `failed` but the browser unconditionally announced queued success. A zero-valued ConstantSource supplies an audio clock without enabling any microphone or inventing received speech/video. Empty captures are failures; successful Stop drains the final event and acknowledged chunks before finalization. Cloud and local paths are independently tested.

**Confirmed server/client ordering defects:** native End Class removed the room before browser Stop/drain; browser End also called remote end first. Native end now explicitly requests browser Stop and returns pending until capture/finalization has ended, then confirms remote closure. Cloud upload/indexing remains asynchronous and does not require the teacher PC after completion. A stopped encoder has a separate bounded120-second final-chunk drain state; its capture lease cannot be renewed. A crash/expired lease/withdrawal remains interruption, never promoted to successful capture. With a configured processor, Ready waits for original private R2 acknowledgment and the completed private seekable playback copy. Missing processor behavior remains private original access with absentee sharing blocked.

**Native control/input mechanism:** the prior full-screen input HWND covered the toolbar's coordinates and relied on `lift/topmost` ordering alone. A raised input surface can receive toolbar clicks. The input HWND now has an actual window region excluding the toolbar and mapped native control panels, refreshed on mapping/movement. Ink coordinates and the pen rendering pipeline are unchanged. Failure to install protection hides the input surface and restores Interact. Win32 handle signatures are explicit; Escape in MathStudio releases its owned implicit capture. This is an input-area fix, not removal of Pen mode. Hosted Win32 tests are distinct from physical pen acceptance below.

**Confirmed UI blocking:** End Class, close/screen cleanup and Video-panel authentication used synchronous HTTP on Tk's UI thread (up to eight seconds per request). They now use owned daemon workers and the existing main-thread dispatch queue. Closing locally never waits for OWNER; unconfirmed remote end is reported honestly. Pending finalization responses are not treated as successful End Class. No global browser/task/process kill or new input hook is introduced.

## Physical Windows11 acceptance — required

Keep production/earlier reviews closed or unchanged and use only this isolated state/client. Record the build ID shown in diagnostics and check supplied hashes first.

- Create an Instant math meeting with one authorized teacher. With mic/camera disabled, record at least a few seconds, Stop and wait through Finalizing/Processing/Uploading/indexing until Ready. Play and seek in the teacher library, then download and play the original. Repeat with mic/camera enabled. Confirm no failed/interrupted flag for a normal Stop.
- Repeat with multiple properly authorized participants and actually received remote audio/video. Test screen share on/off, whiteboard changes and rapid teacher/student annotations while stopping. Confirm aligned readable math, audible intended tracks, sync and sustained quality; no unreceived feed is claimed.
- Stop while uploads are active; temporarily delay/disconnect the network. Check honest retry/error diagnostics and recovery. Never mark Ready before cloud acknowledgment/seek indexing. An actual crash/consent withdrawal must remain interrupted. Verify R2 object sizes and seekable playback privately; do not publish recordings.
- Choose Local Recording in desktop Chrome/Edge, select Save As, Stop and verify the saved file independently. Check Windows disk-full/permission/save failure reporting. Confirm **no cloud media upload**. Later explicit authorized upload must verify original chunk hashes. The automated picker/writer test is mocked, not physical Save As acceptance.
- Rapidly switch Pen → Interact → Pen at least20 times. Click every toolbar tool/color/width, undo/clear, Recording, Video panel and End Class; drag the toolbar and native control panels while in Pen mode. Draw outside controls and check accurate strokes. Clicks inside controls must never draw on the overlay.
- Move focus between toolbar, desktop and Video panel; test Escape while MathStudio has focus and Alt+F4. Do not assume a global keyboard shortcut when a different application owns keyboard focus. Click Interact as the recovery control. Test actual stylus pressure/buttons where supported; no synthetic test establishes physical stylus behavior.
- During Draw, Interact and recording finalization, choose Close App/End Class. A pending end should keep UI responsive and await Stop. Close locally while confirmation is pending; it must release overlays/capture/windows promptly and state that the remote class may still be open. Retry remote end from an authenticated teacher/OWNER after recovery; never infer success from local window disappearance.
- Repeat with OWNER stopped, slow and returning an error. Confirm no Task Manager escape is needed. Check Task Manager for this review's native meeting process/owned workers after multiple cycles. The external browser may reuse a user's existing browser process; unrelated browser processes must not be killed. A recorder browser abandoned before finalization can lose unacknowledged chunks and must not be represented as completed.
- Verify scheduled Resources still refuse unrelated/present/unenrolled accounts, expired/revoked codes and unauthorized Range requests; Instant recordings remain unshareable. Check policies, Remember Me and offline Argos in the copied review runtime.

## Limits, rollback and future hosting

Cloud tests use synthetic media/in-memory R2 and a real encoder/FFmpeg. Hosted Windows CI is Windows Server2025, not a physical Windows11 PC. No live R2, actual mobile camera receipt, physical pen, long-duration/5GB or real disk-full acceptance is claimed. Privacy-safe diagnostics expose fixed processing stages, HTTP/exit categories and encoder-empty state, never arbitrary FFmpeg output, tokens, paths or media content. A network failure can still interrupt a recording; recoverable acknowledged data/checkpoints are retained.

Completed private R2 media is independent of teacher-PC/local-OWNER uptime; future Render still needs one OWNER instance with persistent protected metadata/spools/index checkpoints and trusted FFmpeg. No Render/DNS/TURN change is made. Legal policies remain drafts requiring owner/qualified review before real use.

Rollback: stop/uninstall **MathStudio Stop Input Review** only. Retain/dispose its separate state and private test R2 objects under the approved retention rules. Existing production/PR9/PR10/PR11 installations remain unchanged. Stop for acceptance: no merge, deployment, paid resources or recording publication.
