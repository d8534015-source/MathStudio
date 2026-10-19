# Website Management review evidence

**Final review delivery verified:** 155/155 local tests; Windows 151 passed + 4 optional skips; 9 Chinese-codepage tests; 14 installer smoke checks. The unsigned review installer and its SHA256SUMS.txt are in this folder. See the final Windows section for immutable build provenance and remaining manual acceptance.

Base: PR #8 commit cd09b99483abf1c2260bcf9c91183280df1b4f4b. Source branch: codex/teacher-website-management-v4166.

- Initial API/security draft/publication tests: 8 passed.
- Focused native full-app + API/translation tests: 19 passed at that checkpoint; subsequent final CMS/profile/concurrency tests: 14 passed.
- Actual teacher-app shell tested under Linux Tk 8.6/Xvfb: unsaved content survives English/Chinese switching, request errors preserve text and the event loop responds while a synthetic OWNER translation is blocked. This is not Windows 11 acceptance.
- Headless Chromium: 66 checks passed, zero JavaScript errors, using synthetic accounts/content and manual translation fixtures. Includes anonymous/student/teacher pages, both languages, draft isolation, public approval/fallback, retired translation UI, downloads/messages/classroom DOM. No physical camera/microphone or real-device claim.
- Node direct runner: 15 browser workflow tests passed. JavaScript module syntax checks passed.
- Actual Windows frozen-payload verification passed after the lifecycle repair: 387 modules/1636 files inspected, zero prohibited runtime/model/database files. See final evidence below; the spec alone was not treated as proof.
- Complete local suite before the Windows lifecycle finding: **154 passed, zero failures/skips**, Python 3.13.5 Linux/Tk 8.6 with cached genuine sentence models, **25.664 seconds**. An initial full run found one existing localization fixture error (the new page guard assumed current_page was initialized); the guard was repaired, its focused retest passed, then the final full suite passed. Windows CI validates the platform-specific installer separately; artifact results will be recorded after execution.

The existing user-confirmed real PR #8 Windows 11/Python 3.13.7 Argos acceptance is preserved. No full real translation weights are available in Cloud, so new automated translations are fixtures. The genuine sentence-model/tokenizer tests prove sentence/transport handling, not translation quality. No models or private records were downloaded/accessed.

See [workflow, hosting evidence, rollback and manual checklist](../WEBSITE_MANAGEMENT.md). The working teacher EXE is not replaced. The separate unsigned review installer, when verified, uses a distinct app ID/install directory/shortcut/settings profile. Do not merge, deploy, publish or test against production without approval.


## Changed files

- website_content.py: additive draft/publication storage, allowlisted public fields, revision/source conflicts, visibility and Unicode validation.
- public_translations.py: authoring-draft vs published-source separation, retained previous approved versions, offline-only generation request enforcement. Original provider/inference architecture remains.
- server.py: authenticated CMS route; published-only projections; retired translation page/script; canonical apex navigation remains the existing behavior.
- teacher_website.py: background authenticated OWNER client, public-content editing/publication, private bilingual text previews, translation/configuration/review UI, retained edits on failure/language switches, scrollable panels.
- teacher_desktop_app.py: Website Management section, preserved editor during language changes, connection/timezone settings, old immediate-publication desktop forms migrated.
- teacher_localization.py: fixed English/Chinese manager/error labels only.
- app.js, teacher.html, locales.js: retire web translation navigation/editor in favor of bilingual desktop guidance; student workflows/layout retained.
- runtime_paths.py: frozen review-role marker selects an isolated settings profile; source OWNER and production client paths unchanged.
- windows_teacher.py: frozen self-test imports new client UI and records client-only capability.
- packaging/windows/MathStudio.spec, build.py, MathStudio.iss, smoke.ps1, check_client_payload.py: explicit exclusions, actual frozen-PYZ/file inspection, distinct review identity/install/settings/shortcut, build evidence and Windows smoke adaptation.
- .github/workflows/windows-installer.yml: review build/test on PRs stacked onto PR #8.
- test_website_management.py: 15 CMS/native UI/session/concurrency/profile/isolation regressions; verify_website_browser.py: migrated navigation and API/public-render checks.
- WEBSITE_MANAGEMENT.md, this evidence, release_manifest.json and argos-review/SHA256SUMS.txt: workflow, measured resource limits, manual acceptance/rollback/build guide and refreshed allowlisted source hashes. Historical ZIP/EXE artifacts remain unchanged.

Protected source comparison against PR #8 is identical for classroom.js, teacher_meeting_app.py, argos_worker.py, argos_runtime.py, argos_setup.py and packaging/argos. No WebRTC, native annotation, model/dependency version or inference-worker changes were made.


## Windows review build and lifecycle follow-up

The first disposable Windows Server 2025 / Python 3.13.12 build (run 39195077723, source 119d9446e902a397913ef7188d3e1dcab27131e0) produced a genuine unsigned review EXE. Actual frozen-payload inspection passed: **387 Python modules, 1636 files, zero prohibited translation dependencies/model files**. The separate review registration/profile and **14 install/import/uninstall/reinstall smoke checks** passed, including port 5051 already occupied and Unicode/long paths. This is Windows Server evidence, not Windows 11 physical acceptance.

The workflow nevertheless correctly FAILED its regression gate: after native UI fixtures closed, a later HTTP test triggered garbage collection of Tk-owned objects on another thread (Variable.__del__ / Tcl_AsyncDelete). The incomplete Windows full run is NOT a passed suite, and that first installer is superseded for delivery. No readiness check was weakened.

Repair: background callables now bind only WebsiteService and plain request data, never the Tk editor. Destroying the editor cancels its UI polling, releases Tk variables/widget cycles and app callbacks on their creating thread. GUI exception handling drops only the retained Python traceback reference after preserving its error feedback, preventing a completed Future from keeping the GUI tree alive. Native test teardown explicitly collects closed interpreters on the main thread before subsequent HTTP concurrency tests. No worker/inference error validation was changed.

A regression closes the editor during background work, verifies release of Tk references/callbacks and confirms the task can finish. Error preservation also verifies that the Future does not retain a GUI traceback. Focused lifecycle/API tests passed; the complete local suite after this confirmed fix: **155 passed, zero failures/skips**, **25.585 seconds**, Python 3.13.5 Linux/Tk. At that checkpoint the Windows rebuild was pending; the successful final run recorded below supersedes that pending status.


## Final Windows artifact verification

The repaired candidate passed the complete Windows Server 2025 / CPython 3.13.12 x64 job: [run 39195878856](https://github.com/d8534015-source/MathStudio/actions/runs/39195878856), PR head `84f3b9c4713f60f4e9609c921b8217a42a243241`. GitHub checked out its temporary PR test-merge ref `c7d35cfab19fc64a3b6dba73f757784e49f73bab`; this is CI's synthetic merge commit, not a merge of branches performed by this task. The built source-manifest SHA matches the recorded 84f3b9c inputs exactly. Later documentation/artifact commits do not rebuild or change the client source.

- Windows full suite: **155 run: 151 passed, 4 explicitly skipped, zero failures**, **134.696 seconds**. The four skips are optional Stanza, genuine MiniSBD and two SentencePiece checks; this clean client build environment deliberately has no Argos stack/models. Those four checks ran in the 155/155 local OWNER-stack suite instead. No skipped test is counted as passed.
- **9 Chinese-codepage startup tests** passed; owned Windows child/tunnel cleanup passed.
- **14 actual installer smoke checks** passed, including separate review registry/profile, bundled Python without Python on PATH, GUI/native/Website Management import self-test, port 5051 occupied, Unicode/space/long install path, shortcut targets, uninstall and reinstall.
- Actual frozen-client inspection: **387 Python modules and 1636 files**, no prohibited server translation dependencies or model/database files. Verified the embedded role-marker hash using its Windows CRLF bytes, not only build settings. Review profile is separate from production.
- Downloaded artifact ZIP digest and CRC, installer checksum/PE header, review flag, unsigned flag, source manifest, runtime self-test and regression outcome were independently checked. Installer is a genuine Windows GUI Inno bootstrap (machine 0x014c) with x64 CPython payload; it was not cross-built on Linux.

Deliverable: [MathStudio-Website-Management-Review.exe](MathStudio-Website-Management-Review.exe), **16272464 bytes**. SHA-256: `f531b475f50823558501abc13a52bb7997649900d6eed99cf3f3901ee2a4d068`. This supersedes the first lifecycle-defective candidate, which is not copied into the delivery folder. See SHA256SUMS.txt, build-manifest.json, client-isolation.json, runtime-self-test.json, windows-smoke-results.json and windows-verification.json for evidence. The complete CI log/artifact is linked from the verification JSON; CI artifact retention ends 2026-11-02, while this reviewed EXE copy is retained with the draft PR.

Remaining limits: unsigned review binary; Windows 11 physical OWNER/teacher end-to-end acceptance, genuine translation quality through the new desktop workflow, mobile physical WebRTC/annotation tests and production upgrade/rollback acceptance remain manual. Cloud full real translation weights are unavailable. The user-confirmed PR #8 model acceptance remains the engine baseline. No production installation, DNS/Render change, paid service, merge, deployment or release publication occurred.
