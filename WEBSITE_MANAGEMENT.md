# Website Management review candidate — v41.6.6

Download the **unsigned, isolated review installer** from [MathStudio-Website-Management-Review.exe](website-management-review/MathStudio-Website-Management-Review.exe?raw=true). See [verified results and checksums](website-management-review/TEST_RESULTS.md). Windows Server CI has passed; Windows 11/mobile acceptance remains manual.

Stacked on Draft PR #8, commit `cd09b99483abf1c2260bcf9c91183280df1b4f4b`. No deployment, DNS changes, production records, installed EXE or paid infrastructure is changed by this PR.

## Teacher workflow

Open **MathStudio → Website Management**. The **Public content** tab manages homepage/studio text, announcements, active lesson descriptions and confirmed public group descriptions. Names and titles remain original text. Existing **Files & codes** and **Schedule** buttons open their established desktop workflows; private file contents, messages, attendance and student records are not translation sources.

1. Select an item, edit its source text (and announcement title), then **Save draft**. A new announcement is also initially private.
2. In **Translation settings**, enable OWNER offline translation and specify protected names/terms if needed. Only OWNER needs the existing PR #8 Argos installation.
3. In **Translations**, choose `zh` for English → Simplified Chinese or `en` for Chinese → English. Compare original and draft, edit the result, and save it. Generate reuses cached work; Regenerate explicitly creates another draft. Previously approved text remains available as a reference and is never automatically replaced.
4. Return to Public content and use **Preview English / Preview Chinese**. These are private, plain-text previews of the selected description/announcement, not a pixel-identical embedded browser view. Missing translations show the source. Previewing never approves or publishes anything.
5. Explicitly **Approve & publish translation**, then **Publish content** when the source is ready. A translation approved for an unpublished source remains private until that source is published. For an already published source, explicit translation approval updates that language immediately.
6. **Unpublish content** hides the announcement or public text, including its translations, without deleting the original/draft. Unpublishing a lesson/group description does not cancel classes, change bookings or hide the lesson booking option.

Unsaved edits survive English ↔ Chinese switching. Changes must be saved or reloaded before changing editor tabs. Failed requests preserve editor text. Requests run on a dedicated background client; a slow translation does not run on the Tk event loop. If a connection drops after a mutation was sent, reload and inspect publication status before retrying: network failure alone cannot prove whether the server committed it.

`/teacher/translations` redirects to bilingual desktop-app guidance. Student/parent navigation continues to offer home, bookings, resources, messages, accounts and joining. Authentication-protected backend APIs remain available to the desktop client. Unrelated teacher classroom/account workflows remain intact.

## OWNER, privacy and upgrade safety

The teacher sends authenticated HTTPS requests using its existing session and CSRF checks. Every management API requires a current admin/teacher session; hiding web controls is not authorization. Stale revision/source hashes return conflicts. All inference runs on OWNER in the existing bounded, CPU/offline subprocess, using the strict UTF-8 request and private-file response protocol. No new translation provider, key, model download or dependency version is introduced. The desktop requests offline-only generation; external providers are rejected for that request.

The user confirms PR #8 real Windows 11/Python 3.13.7 acceptance: ready=true, verify_argos_models.py passed, official 1.9 models translated both directions, protected math/URL checks passed and inference networking was disabled. This is user-supplied acceptance evidence; this feature's Cloud checks use synthetic content/translation fixtures and genuine sentence models, not complete official translation weights.

Update the review OWNER source and review client together. New clients talking to older OWNER code cannot use the new content API; they must not be pointed at production for acceptance. Start with a disposable COPY of OWNER data after backing up the stopped server. The additive migration adds `posts.published` (existing posts default to published) and `website_drafts`; it does not replace/delete existing tables or accounts. New translation previews use draft source hashes while public responses use the actual published hashes.

**Rollback:** stop the review server, retain a copy of its data and restore the matching pre-feature database snapshot before running older source. Older servers do not understand `posts.published` and can expose newly unpublished announcements if used against the new database. Never roll older code back over this database blindly. Do not uninstall the working Argos runtime or overwrite production data to test this feature.

## Windows review build and installation

Use a disposable Windows 11/x64 build machine and the existing hash-locked build toolchain:

```powershell
py -3.13 --version  # Build script requires exactly x64 CPython 3.13.12.
py -3.13 packaging/windows/build.py --review
```

The build creates a fresh build-only venv with the pinned base requirements and PyInstaller tools. It never installs Argos or models on the teacher PC. It compiles a real Windows onedir client and an Inno Setup installer; Linux cannot cross-build this EXE.

Output: `work\windows-build\installer\MathStudio-Website-Management-Review.exe`, SHA256SUMS.txt, build-manifest.json and client-isolation.json. The latter inspects the **actual frozen PYZ module archive and files** and fails if OWNER modules, Argos/MiniSBD/SentencePiece/CTranslate2/ONNX/PyTorch/Stanza/SpaCy or model/database files are present. The source spec also excludes these modules. The artifact is unsigned: do not disable Windows security protections; use signing through an authorized publisher before production distribution.

Run the review installer on a test PC. It has a separate App ID, `%LOCALAPPDATA%\Programs\MathStudio Review` directory and **MathStudio Review** shortcut. Its bundled role marker selects `%LOCALAPPDATA%\MathStudioReview` for connection/language state. It does not reuse the installed teacher app's settings or registration. Keep the default review directory; never select the existing application's directory. The normal build path remains available without --review but is not the delivered review artifact.

On first launch, enter the **test OWNER HTTPS origin** and sign in with a synthetic teacher account. No Python, VS Code, translation account or model installation is required on the teacher PC. Change the origin later under **Connection & studio**. Never enter production credentials during these tests.

## Domain and future hosting boundary

Intended production origin is `https://hongmaths.com`, with `https://www.hongmaths.com` eventually routed to the same deployment and redirected to the apex. A future OWNER configuration example is `PUBLIC_ORIGIN=https://hongmaths.com`; the teacher stores that origin locally, never in its executable. Configure the www → apex HTTPS redirect at the edge when infrastructure is separately approved. Both hostnames need certificates and routing at that time; no DNS/tunnel/Render changes are made here. Existing OWNER canonical navigation also prefers its configured HTTPS origin. Keep strict origin/CSRF checks; do not add permissive cross-origin credential forwarding.

Initially the website, content APIs and Argos stay together on the verified Windows OWNER. The desktop talks only to the OWNER content/translation API, so moving inference behind that API later does not require a different teacher app. No separate public translation service or credentials are added. Render free/Starter suitability is **not established**; do not move the working model environment there based on this PR.

Resource evidence (separate from hosting recommendations):

- Disk: existing Cloud optional runtime is approximately **1.30 GiB**, excluding official translation weights; cached genuine English/Chinese MiniSBD files total approximately **0.77 MiB**. OWNER reports an approximately **4 GB** working Windows translation environment. Windows wheels/model totals differ; that report is not a measured Render footprint. Budget for runtime + model archives + installed/staged model copies + a complete backup and free-space margin.
- CPU: one inference subprocess at a time, CPU-only, bounded by the existing 30-second deadline, with Argos inter/intra threads set to one. Genuine translation throughput on a hosted CPU has not been benchmarked here; the 30-second deadline remains an acceptance constraint.
- RAM: the isolated Linux sentence-splitter/synthetic-tokenizer test peaked at **387448 KiB (~378 MiB)** in **1.840 seconds**. This excludes CTranslate2 translation weights and is NOT a full translation RAM requirement. Measure peak working set with both real directions on the intended OWNER/host before sizing RAM. Teacher client memory is separate.
- Hosting: needs persistent writable model/cache/data storage outside versioned folders, a subprocess-capable x64/Python 3.13 environment matching the locked wheels, sufficient measured RAM/disk/CPU and outbound access only during explicit installation. Stateless or ephemeral disk must not hold the sole model/data copy. No paid service or migration was provisioned.

## Acceptance checklist

- Windows test OWNER: back up first, use copied data/synthetic accounts; preserve ready Argos installation; verify both real directions twice, math/LaTeX/URLs/names, missing-model fallback and network isolation.
- Review teacher EXE: confirm separate app ID/install/settings/shortcut; no local port 5051 listener; no Python/Argos installation; first-launch HTTPS health validation; teacher login and expired-session rejection.
- Draft homepage/announcement/course text; preview both languages; confirm anonymous/student responses contain neither unpublished source nor unapproved draft translations. Approve, publish, edit source, regenerate and unpublish; check retained approved references and stale-edit rejection with two teacher clients.
- Disconnect OWNER during save/generation; verify responsive UI, preserved edits, clear error, and reload before retrying uncertain writes. Switch English ↔ Chinese while editing; confirm names/content remain byte-for-byte unchanged.
- Windows/iPhone/Android browsers: login/signup, DST-aware bookings, resources/downloads, messaging, scheduled and instant joins, simultaneous bidirectional audio/video, screen sharing, annotations and mobile sleep/reconnect. Automated DOM/signaling tests are not physical-device media acceptance.
- Validate artifact hashes and client-isolation report before distributing. No merge/deployment/production installation until explicitly approved.
