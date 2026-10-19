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
