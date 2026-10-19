# Current Argos compatibility verification

Based on PR #7; Draft PR #8 source `c945f6e0f31078a73e3d4f8df502aab61dd63602`. This supersedes the earlier synthetic-only Stanza patch evidence. See [compatibility review](../ARGOS_COMPATIBILITY_REVIEW.md) and [Windows instructions](../ARGOS_OFFLINE_SETUP.md).

- Final focused Python 3.13 tests: **27 passed**, zero skipped/failures (6.452 seconds), including genuine official MiniSBD English/Chinese models.
- Actual CPU sentence splitting repeated successfully through Argos 1.11's selected MiniSBD implementation, with Stanza pipeline and checkpoint loading forbidden. Two sentences per example remained consistent. This is **not complete translation verification**.
- Runtime inspection: Python 3.13.5, all principal pinned versions matched; device CPU, provider OPENNMT, chunk type MINISBD. Existing locks unchanged.
- New diagnostics/acceptance harness regressions passed using synthetic HTTP/databases and mocked translation. Those test fixtures do not provide genuine translation examples.
- Complete suite, run once after the final code changes: **130 passed, zero failures/skips** on Python 3.13.5 (22.092 seconds). Includes all previous 111 regressions.
- Node browser workflow checks: **15 passed**, zero failures/skips.
- Existing teacher EXE SHA-256 remains `c05b5e9f160d0c9dddb428128dab1ddd3d87527d5fb6ed7e97094f494d8990cc`; no rebuild.
- Windows Server 2025 x64 / Python **3.13.16**: **27 focused tests passed**, zero failures/skips (53.570 seconds); hashed dependency installation/pip check/imports and genuine MiniSBD models passed. [Successful run](https://github.com/d8534015-source/MathStudio/actions/runs/39185599841), code commit `c945f6e0f31078a73e3d4f8df502aab61dd63602`. This CI does not download full translation packages and is not Windows 11 acceptance.

## Acceptance blockers

No original Argos English/Chinese translation archives are available here, and argos-net.com is outside the Cloud allowlist. No blocked download was retried, no unofficial mirror used and no policy changed. Actual CTranslate2 model loading, translation quality, mathematical/proper-name translation and full offline generation remain unverified until OWNER runs the supplied diagnostic/acceptance commands. Model metadata/resources can be inspected safely by that diagnostic on the Windows PC.

Windows 11 physical-machine installation and end-to-end media/manual workflows remain unexecuted. Do not infer those from Linux tests or Windows Server CI. Source originals, cache/edit/approval/invalidation and both-direction activation guards have automated regression coverage.

## Changed files and delivery

- `argos_worker.py`: use the supported MiniSBD setting, principal-version/local-model validation, no Stanza/torch mutation, explicit native telemetry disable, safe model inspection.
- `argos_runtime.py`, `packaging/argos/profile.json`: schema-2/profile readiness, pinned sentence hashes, CPU/MiniSBD child environment and safe handling of incomplete optional source updates.
- `argos_setup.py`: official auxiliary models only during explicit setup, safe staging, hash verification, repeated real translations in both directions before activation, existing runtime/archive reuse.
- `diagnose_argos.py`, `verify_argos_models.py`: safe staged real-model diagnostics without activation/download/pip, actual protected math and edited approval/cache/source checks after installation.
- `test_argos_offline.py`, `.github/workflows/argos-runtime.yml`: relevant compatibility/security tests and Windows genuine-sentence-model checks.
- Setup/review/results/manifest/checksum files: current commands, evidence, blockers and allowlisted OWNER delivery.

All previous MathStudio fixes are inherited. No teacher/native source, teacher EXE, WebRTC, scheduling, authentication, main, deployment or release publication was changed. No private accounts/databases/resources/credentials, model data, wheels or environments are included in the updated source archive. The new ZIP supersedes the older Argos review ZIP for source updates; never mix the intermediate Stanza worker with the new profile/runtime.

## Windows subprocess encoding repair — focused follow-up

Text-mode `subprocess.run(encoding="utf-8")` decoded both pipes inside Windows reader threads, although native libraries can emit locale-encoded diagnostic bytes. `redirect_stdout` only changes Python output and does not isolate fd 1/Win32 STD_OUTPUT_HANDLE. The repair captures raw bytes in setup, runtime generation and staged inspection. JSON is decoded strictly as UTF-8 on the parent thread; invalid bytes or malformed responses fail validation. Diagnostic stderr alone uses replacement decoding, then only the existing sanitized ASCII exception record is retained. No arbitrary native logs are exposed.

The worker duplicates its original stdout pipe for explicit UTF-8 JSON, redirects native fd 1 and Windows STD_OUTPUT_HANDLE to stderr before optional imports, and retains exception exit codes/safe diagnostics. The exact native library that emitted the PC's byte cannot be identified from the supplied traceback; the fix handles native output independently of its producer/codepage.

New real subprocess regressions emit CP936 `0xCE 0xD2` diagnostic bytes on stdout/stderr and, on Windows, through Win32 WriteFile. They exercise both setup directions, assert no reader-thread exception, and preserve exact Chinese strings in valid JSON. Malformed UTF-8/JSON and unsafe diagnostics are rejected; a second-direction malformed response leaves previous models/receipt untouched. Fixtures represent transport, not genuine translation quality.

Focused Linux Python 3.13 verification: **29 passed**, no failures/skips (6.418 seconds), using the existing dependencies and cached genuine MiniSBD sentence models. Windows-specific Win32 branches are included but were not executed locally; prior Windows CI/full-suite results above predate this repair. No dependency installation, pip change, download, full-suite rerun, teacher EXE rebuild, merge or deployment. The previous OWNER ZIP is unchanged; replace `argos_runtime.py`, `argos_setup.py`, `argos_worker.py` and `diagnose_argos.py` together from the current draft PR. Retry with existing local original archives and `--sbd-files` pointing to the already downloaded cache.


## Invalid worker response — private protocol follow-up

The reported generic validation failure did not distinguish malformed JSON, missing fields or incorrect types. Its exact Windows response is unavailable here; no particular native library or response shape is claimed as confirmed. A real subprocess regression confirms a remaining protocol defect: startup output (before worker.main redirects stdout), including locale bytes, still occupies the inherited pipe and makes strict JSON parsing fail. Cached native stdout handles can likewise bypass later redirection.

All three parent launch paths now share a raw-byte subprocess helper and a unique private temporary response file. The worker opens that file exclusively and writes explicit UTF-8 JSON; native stdout/stderr remain diagnostic channels. Response files are bounded when read and cleaned up on completion/failure. Missing files never fall back to accepting stdout; malformed JSON, unexpected piece counts/types, empty/unchanged translations and failed processes still prevent activation. The old direct-invocation stdout fallback is not used by OWNER callers.

Self-test errors and diagnostic reports include only exit code, response presence/transport, JSON parse status, JSON-object presence, pieces presence/type/count, aggregate piece types and unexpected stdout/non-JSON flags. Embedded JSON objects can be detected for classification only; they are never salvaged for validation. No arbitrary output, paths or translation text appears in protocol summaries. Existing sanitized worker exception records remain available. Offline network guards, MINISBD, bounded execution and both-direction checks are unchanged.

Final focused verification: **31 passed**, zero failures/skips, Python 3.13.5 Linux, **6.366 seconds**, existing dependencies and cached genuine MiniSBD sentence models. Tests cover startup/native CP936 bytes, exact Chinese output, strict JSON, missing private responses despite valid stdout, missing fields, non-list/wrong-count/mixed-type pieces, both-direction activation refusal, and existing editor/cache/security workflows. The initial unprivileged run could not create the synthetic localhost server under the sandbox; the final authorized run passed. Windows-specific Win32 execution and complete real translation remain unverified locally. No dependencies installed, models downloaded, full suite rerun, teacher EXE rebuilt, merge or deployment.

Source-only follow-up: replace **argos_runtime.py, argos_setup.py, argos_worker.py and diagnose_argos.py together** from the latest Draft PR #8. The historical ZIP above is unchanged and predates this repair. Tests, this results file, release manifest hashes and checksum index accompany the four runtime files. Use existing translation archives and cached sentence models with --skip-dependencies and --sbd-files; neither input needs downloading.
