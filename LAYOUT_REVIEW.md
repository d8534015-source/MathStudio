# Responsive teacher toolbar and recording layout review

Stacked on Draft PR #12 delivery `4b9c04c862377befb4dd926ea5fad922cc8443e2`. This is a separate synthetic-test candidate, not a production release. See `layout-review/DELIVERY.md` in the draft PR for immutable source/build revisions, checksums and executed results.

## Separate Windows installation

1. Extract the complete OWNER ZIP into a **new folder**, e.g. `C:\MathStudioTests\Layout`. Do not extract over production, PR9, PR10, PR11 or PR12. The archive has one application root, not nested older releases.
2. Keep x64 Python 3.13 installed. Run **REVIEW OWNER SETUP.bat**, selecting the existing ready Argos home when prompted. It copies and verifies the installed runtime/packages/receipt into this review, without downloading models or modifying the original.
3. Run **REVIEW OWNER START.bat**. OWNER uses **5067**, `%LOCALAPPDATA%\MathStudioOwnerLayoutReview` and its own HTTPS Quick Tunnel. An occupied port is refused, never reused. Production5051, PR9 5059, PR10 5061 and PR11 5063 and PR12 5065 are unchanged.
4. Install the matching **MathStudio-Layout-Review.exe**. It is client-only, with a new AppID, install directory and `%LOCALAPPDATA%\MathStudioLayoutReview` profile. It does not host OWNER. Enter the new review HTTPS origin and use OWNER pairing. Keep Windows protections enabled; this review executable is unsigned unless its actual signature report says otherwise.
5. Use synthetic accounts and authorized development participants only. The review contains no accounts, credentials, private databases/files, virtual environments, Argos models or recordings. New state starts empty; existing account databases are not automatically migrated.

PowerShell from the new extracted application folder:

```powershell
py -3.13 .\owner_review.py setup --argos-home 'D:\YourExistingReadyArgosHome'
py -3.13 .\owner_review.py start
```

`--wheelhouse 'D:\TrustedOwnerWheels'` can reuse pinned OWNER dependency wheels. The teacher installer bundles Python; the teacher PC needs neither a separate Python installation nor FFmpeg/Argos.

## Recording configuration and prior protections

Configure this review's own private test R2/policy/guardian settings deliberately. Do not copy production secrets or student data into development. See the inherited `RECORDING_UPGRADE_REVIEW.md` for the private bucket checks, consent scopes, quotas, policies, cost estimates and explicit guardian process, substituting **5067**, **MathStudioOwnerLayoutReview**, **MathStudioLayoutReview** and the new installer name wherever that historical PR11 guide names its older profile. Do not enable recording merely to bypass consent requirements. R2 credentials belong in the new state's private config, never command arguments/Git/chat. No bucket or paid service is created by this repair.

Configure a trusted, explicitly selected FFmpeg on the **new OWNER state**:

```powershell
py -3.13 .\recording_media.py configure --data "$env:LOCALAPPDATA\MathStudioOwnerLayoutReview\data" --path 'C:\Tools\FFmpeg\bin\ffmpeg.exe'
py -3.13 .\recording_media.py status --data "$env:LOCALAPPDATA\MathStudioOwnerLayoutReview\data"
```

No FFmpeg binary is automatically downloaded/executed. Existing pinned dependencies and Argos translation code/models are unchanged. Retention, 3h/5decimalGB limits, 2h30m/4GB warnings, conservative guardian/participant consent, withdrawal, private R2, authenticated Range access, policy drafts, student Remember Me and teacher DPAPI remain. Scheduled absentee sharing still requires explicit creating-teacher selection of named, verified absent enrollees of the exact scheduled class; expiry/revocation and manual Messages delivery remain. Instant meetings remain private. There is **no automatic sending**.

## Changes in this review

Stacked on PR #12, preserving its recording Stop/drain, nonblocking shutdown and native input exclusions. Fixed-width native controls previously extended outside the initial window; the toolbar now measures Tk requested dimensions at the active font/DPI and wraps independent rows to the monitor work area, including negative monitor coordinates. Resizing, movement and translated labels schedule geometry and input-region refreshes. Existing larger user dimensions are retained during the session; there is no persisted geometry to migrate.

The encoded canvas previously always reserved a 1024×576 board area and placed cameras in a fixed six-slot strip. The recording now uses the same actual classroom presenter/native-share/whiteboard state as the live stage. Without a received screen or active whiteboard, consenting participants fill a balanced grid; disabled, missing, muted or ended video tracks produce display-name/initial tiles. A received screen or active board retains the existing 1024×576 annotation coordinate mapping and uses the side strip for participants. Transitions occur within the existing encoder; no negotiation or media tracks are changed. Audio mixing, consent leases, private-file handling, uploads/indexing and authorization are unchanged.

## Windows 11 acceptance checklist

- Extract OWNER into a new folder; run setup/start above. Check port **5067**, new Layout Review build and isolated data profile. Prior review/production installations must remain unchanged.
- Install **MathStudio-Layout-Review.exe**, a separate per-user client-only install. Enter this review OWNER's HTTPS origin and sign in. Do not disable Windows protections for this unsigned review build.
- At 100%, 125%, 150%, 175% and 200% DPI: verify first-launch rows, Undo/Clear/Hide Ink, mode/student controls, media/meeting buttons and language switch. Toggle EN/中文 repeatedly; move across monitors with different DPI, taskbars and negative origins. Resize narrow/wide; verify all controls remain reachable.
- Pen/Interact/Escape, moved/resized toolbar and recording dialogs must remain clickable with the input overlay raised. Draw coordinates and responsiveness must remain correct; Close/Alt+F4 must work during unreachable OWNER or pending recording Stop.
- With consent/guardian policy satisfied, record teacher alone with camera on/off; two, three and several people with mixed camera/mic states. Check safe initials for Chinese, single names, whitespace and absent display names. No account IDs should appear.
- During one continuous recording: camera on→off→disconnected→on; joins/leaves; screen share start/stop/unavailable; whiteboard open/close and equations/annotations. Play the actual saved video; verify camera-only coverage, balanced tiles, aspect ratios, no stale white stage and readable board coordinates.
- Check actual received remote cameras/audio, sync, 720p target and measured capture FPS near30 under realistic load. Synthetic/browser CI is not physical-device acceptance.
- Verify private cloud and local Save As Stop/final chunks, End Class sequencing, indexing/seek, authenticated playback, consent withdrawal, policy notices and restricted absentee sharing. No actual private recordings are published by this review.

## Rollback and limits

Stop only the new review server and uninstall only MathStudio Layout Review. Keep prior installations/state and external Argos models. No production migration or deployment is required. Windows CI and synthetic browser results are listed in the delivery report; actual Windows11/mixed-DPI/pen/mobile/live-R2 acceptance, long-session performance, real Save As dialogs and low-disk behavior remain manual. Tiny displays that cannot physically fit the largest individual control still need Windows display scaling adjustment; test normal supported desktop work areas before acceptance.
