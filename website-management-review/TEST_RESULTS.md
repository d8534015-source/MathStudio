# Website Management review evidence

Base: PR #8 commit cd09b99483abf1c2260bcf9c91183280df1b4f4b. Source branch: codex/teacher-website-management-v4166.

- Initial API/security draft/publication tests: 8 passed.
- Focused native full-app + API/translation tests: 19 passed at that checkpoint; subsequent final CMS/profile/concurrency tests: 14 passed.
- Actual teacher-app shell tested under Linux Tk 8.6/Xvfb: unsaved content survives English/Chinese switching, request errors preserve text and the event loop responds while a synthetic OWNER translation is blocked. This is not Windows 11 acceptance.
- Headless Chromium: 66 checks passed, zero JavaScript errors, using synthetic accounts/content and manual translation fixtures. Includes anonymous/student/teacher pages, both languages, draft isolation, public approval/fallback, retired translation UI, downloads/messages/classroom DOM. No physical camera/microphone or real-device claim.
- Node direct runner: 15 browser workflow tests passed. JavaScript module syntax checks passed.
- New packaging guards have tests for OWNER/runtime/model/database exclusion. Inspection of an actual frozen Windows artifact is pending the Windows review build; no exclusion success is claimed solely from the spec.
- Complete final local suite: **154 passed, zero failures/skips**, Python 3.13.5 Linux/Tk 8.6 with cached genuine sentence models, **25.664 seconds**. An initial full run found one existing localization fixture error (the new page guard assumed current_page was initialized); the guard was repaired, its focused retest passed, then the final full suite passed. Windows CI validates the platform-specific installer separately; artifact results will be recorded after execution.

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
- test_website_management.py: 14 CMS/native UI/session/concurrency/profile/isolation regressions; verify_website_browser.py: migrated navigation and API/public-render checks.
- WEBSITE_MANAGEMENT.md, this evidence, release_manifest.json and argos-review/SHA256SUMS.txt: workflow, measured resource limits, manual acceptance/rollback/build guide and refreshed allowlisted source hashes. Historical ZIP/EXE artifacts remain unchanged.

Protected source comparison against PR #8 is identical for classroom.js, teacher_meeting_app.py, argos_worker.py, argos_runtime.py, argos_setup.py and packaging/argos. No WebRTC, native annotation, model/dependency version or inference-worker changes were made.
