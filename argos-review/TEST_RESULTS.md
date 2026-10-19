# Argos offline review candidate

Base: PR #7, `cffa6c8f9fce828c6530b3ce123c688b386b54c1`. Branch: `codex/argos-offline-v4166`, draft PR #8. All earlier changes remain inherited. MathStudio.exe, teacher/native sources, WebRTC classroom module, scheduling/timezone code, runtime dependency pins and build IDs are unchanged.

## Executed checks

- Final focused Python 3.12 tests after the Windows archive fix: **19 passed** (2.059 seconds), including the eight existing public-translation tests and 11 new Argos tests. Tests use synthetic public content and mocked model output; they do not claim model quality.
- Python 3.13.5 Linux: the actual Argos CPU dependency stack imports successfully and `uv pip check` reports 65 compatible optional packages. All **19 final focused tests passed** on this real Python 3.13 runtime after the Windows archive fix (4.624 seconds); no real model was installed or invoked.
- Node browser workflow regressions: **15 passed**; keyed EN/ZH catalogs and previous browser state protections remain valid.
- Actual Chromium EN/ZH offline-editor checks: passed, no JavaScript errors. Inspected screenshots: [English](offline-editor-en.png), [Chinese](offline-editor-zh.png). Missing models disable generation, show an honest setup hint and leave the default opt-in unchecked.
- Windows Server 2025 x64 / CPython **3.13.16**: hash-locked optional stack and application dependencies installed, pip check passed, actual dependency imports passed, and **19 focused tests passed** (17.927 seconds). [Successful CI run](https://github.com/d8534015-source/MathStudio/actions/runs/39177916641), code commit `f82a97d4d9316eeae705e9e05dfccddeaaa16731`. Earlier CI failures exposed a missing worker profile and Windows path/ZIP normalization assumptions; the final fix passed this run. This CI does not install real translation models.
- The complete suite was run once at the end of this resumed task, after the final code fix: **122 passed, 0 failed**, in 16.068 seconds. The earlier 122-test run also passed before that fix. This includes all previous **111** regressions plus 11 new Argos regressions.

## Blocking acceptance gaps

**Real Argos models were not downloaded or executed.** The Cloud proxy denies the official host `argos-net.com` (CONNECT 403). No successful real English→Chinese/Chinese→English examples or model hashes are supplied. [real-model-results.json](real-model-results.json) explicitly records `blocked_missing_models`; fake unit translations are not actual examples. On Windows OWNER with access to the official source, run explicit setup, then `verify_argos_models.py` before considering this feature accepted. No blocked download was retried and no Cloud allowlist was changed during this resumed task. The setup itself requires real offline translations in both directions before it marks a model installation ready.

Windows 11 installation/model acceptance remains unexecuted. Windows Server 2025 CI is a separate compatibility check, not Windows 11 acceptance. No physical-device media tests, deployment, merge, release publication or teacher installer rebuild occurred.

## Focused coverage and implementation

New regressions exercise missing models/maintenance readiness, external stable storage, scrubbed child credentials, CPU/deadline/one-worker limits, timeout cleanup, invalid output, safe ZIP paths/metadata, stopped-OWNER setup, no-network inference, plain arithmetic/LaTeX/name/URL protection, both target languages in the existing draft/edit/approval/cache/invalidation flow, private-source rejection and concurrent classroom polling/login during slow generation.

Only allowlisted public descriptions reach the local adapter. Original values are untouched, student rendering remains escaped, and stale source/approval races keep their existing guards. Protected placeholders are kept out of the model and rejoined exactly; additional proper nouns/complex formulas require the existing teacher review and Protected terms. One low-priority, single-thread CPU child runs at a time, with a 30-second deadline; only the editor request has a longer 45-second deadline. No requests install dependencies or models.

## Changed files and delivery

- `argos_runtime.py`, `argos_worker.py`: lightweight provider bridge, isolated CPU/network-disabled child, bounded execution and stable model/cache paths.
- `argos_setup.py`, `SETUP OFFLINE TRANSLATION.bat`: explicit maintenance installation, pinned wheel workflow, safe staged model archives and real bidirectional pre-activation self-tests.
- `public_translations.py`: Argos adapter/readiness, existing cache and approval reuse, conservative arithmetic/LaTeX protection.
- `app.js`, `translation_manager.js`, `locales.js`: generation-only HTTP deadline and EN/ZH offline/progress/missing-model UI.
- `packaging/argos/`: optional Windows/Linux Python 3.13 CPU dependency locks, all hashes pinned; existing `requirements.txt` unchanged.
- `test_argos_offline.py`, `verify_argos_models.py`, `.github/workflows/argos-runtime.yml`: synthetic regressions, explicit real-model acceptance and Windows compatibility checks without model downloads or installer rebuilding.
- `ARGOS_OFFLINE_SETUP.md`, `PUBLIC_TRANSLATION_SETUP.md`, `release_manifest.json`, `argos-review/`: setup, limitations, refreshed OWNER source allowlist and review evidence.

The new OWNER archive excludes model files, wheels, environments, private configuration, account/student databases, personal data, resource files and credentials. Models/cache live in the stable MathStudio per-user directory; existing OWNER database storage is reused and legacy in-tree data requires explicit migration before model setup. See [ARGOS_OFFLINE_SETUP.md](../ARGOS_OFFLINE_SETUP.md) for dependency details, installation/verification and rollback instructions. This is an **unverified-model review candidate**, not a production-ready offline translation release.

## Delivery checklist

- [x] PR #7 commit is an ancestor of the Argos branch; earlier phase fixes are inherited.
- [x] Final focused regressions on Python 3.12 and 3.13 and one final complete suite passed.
- [x] Existing teacher executable bytes and WebRTC classroom module, timezone code, application pins and version identifiers are unchanged.
- [ ] Real official models: install and pass both offline directions on OWNER before enabling automatic generation.
- [ ] Windows 11: clean setup, upgrade, teacher connection and live-class acceptance remain manual checks.
- [ ] Human review of actual bilingual mathematical output, Protected terms and approval before publishing descriptions.

The archive is delivered for review via draft PR #8, not a GitHub release. Stop OWNER, extract the new OWNER folder, retain the existing external data/configuration paths, use the existing OWNER setup/start instructions, and run **SETUP OFFLINE TRANSLATION.bat** for optional models. Teacher Ready connects to OWNER and does not install or host Argos. Do not replace or reset the account database. Run `Get-FileHash .\MathStudio_v41_6_6_OWNER_Argos_Review_Candidate.zip -Algorithm SHA256` and compare against the accompanying `SHA256SUMS.txt` before use.

## Windows self-test diagnostic repair — 2026-10-19

The worker's blanket exception handler previously exited with code 2 and empty stderr. This was reproduced with the existing Python 3.13 dependency runtime and missing models. It now emits sanitized exception type/code locations/OS error numbers, without exception messages, paths, input or local variables. Setup names the language direction and separates worker errors, startup errors, timeouts and response-validation failures. No actual Windows model exception was supplied, so its underlying cause remains unconfirmed; model loading and verification requirements are unchanged.

Added `--skip-dependencies` for retry with an existing runtime and the original official archives: no pip invocation or model download is needed. Both staged offline direction checks must still pass. Three new regressions cover safe diagnostics, invalid/unchanged outputs, timeouts/startup failures, no activation after second-direction failure, and activation only after both checks pass.

Targeted tests after this repair: **22 passed** on Python 3.12 (2.220 seconds) and **22 passed** on the existing Linux Python 3.13 runtime (4.401 seconds). The actual missing-model worker now returns a safe `ValueError` location rather than empty stderr. No dependency installation, pip upgrade, full audit, full-suite rerun, model download, Windows execution or media change was performed for this repair. Earlier full-suite/Windows CI evidence above applies to the earlier code commit, not this follow-up.

This follow-up is a source repair: update `argos_setup.py` and `argos_worker.py` together using the current PR #8 source, then follow the retry section in `ARGOS_OFFLINE_SETUP.md`. The earlier immutable OWNER ZIP and its checksum are retained unchanged and **do not include this follow-up repair**.

## Confirmed Stanza processor/resource compatibility repair — 2026-10-19

The supplied Windows stack points to Stanza 1.10.1 `add_mwt` indexing the missing `packages` key. Argos requests `processors="tokenize"` with the default package, while legacy bundled resources declare `default_processors`. The inference worker now supplies the equivalent `packages.default` map in memory only during pipeline initialization, restoring the original loader even if initialization fails. Modern maps are preserved; there are no guessed tokenizer names, missing-model substitutions, dependency changes or disk-resource rewrites.

A new regression uses the actual installed Stanza code and synthetic legacy English/Chinese resource JSON: without the adapter it reproduces `KeyError('packages')` at the reported initialization path; with the adapter it resolves the declared tokenizer model for both languages. Only tensor loading is mocked. It asserts no resource/model downloads, `DownloadMethod.NONE`, unchanged resource bytes, normal tokenization (not pretokenized input), and loader restoration including failure. A separate regression covers modern and unknown metadata without modifying source dictionaries.

Final targeted verification: **24 passed** on the existing Linux Python 3.13/Argos/Stanza runtime (5.671 seconds); Python 3.12: **23 passed, 1 skipped** because optional Stanza is not installed (2.200 seconds). The previous no-network, bounded-worker, privacy, approval/cache/invalidation and both-direction activation-gate regressions remain passing. No dependencies were installed, pip was not upgraded, no full audit/suite was repeated and no teacher executable was rebuilt. Actual Windows 11 translation with the user's installed models still requires retry. The earlier OWNER ZIP remains unchanged; use the latest PR #8 worker source and the existing `--skip-dependencies` retry workflow.

## Legacy tokenizer checkpoint compatibility repair — 2026-10-19

The second Windows trace ends at Stanza 1.10.1 `tokenization/trainer.py:93`, which requires `config.feat_dropout` when constructing the tokenizer. Comparison with the official Stanza 1.1.1 source confirms its loader required the other four configuration keys on that line but had no feature-dropout argument; its saved checkpoint contains only `model`, `vocab`, `config`, with no lexicon. The source was read from the official PyPI wheel (SHA-256 `281e9f47623790e2770cf42f837346724c45a16a767302ec538287c54767eed7`) without installing it or downloading any model. The legacy model always used its feature vectors directly. Stanza 1.10.1 additionally reads top-level `lexicon` at line 96.

The child-only adapter recognizes exactly the legacy three-field checkpoint with the original required dimensions and absent `feat_dropout`. It supplies `feat_dropout=0.0` and `lexicon=None` in memory, leaving tensors/vocabulary/dimensions untouched. It intercepts only the tokenizer module's checkpoint load during pipeline initialization and restores the module afterward, including on errors. Stanza still calls `torch.load(weights_only=True)` and its original strict `load_state_dict`. Modern/unknown checkpoint formats are left unchanged. Sanitized KeyError diagnostics expose only fixed known schema key names, never arbitrary exception text.

The regression uses real Stanza/PyTorch and synthetic small tensor checkpoints for English and Chinese. It reproduces `KeyError('feat_dropout')` before adaptation, then initializes the real tokenizer through the existing resource adapter, verifies every loaded tensor is identical, confirms model-file bytes are unchanged and restricted deserialization remains enabled. Deliberately missing weights still fail strict loading; no model parameters or dimensions are synthesized by production code. Tests also cover malformed modern schemas and private-key redaction. These fixtures are not real Argos model acceptance or translation-quality examples.

Final focused results: **26 passed** on the existing Linux Python 3.13 dependency runtime (6.508 seconds); Python 3.12: **24 passed / 2 optional-Stanza tests skipped** (2.384 seconds). Existing bounded/offline inference, privacy, cache/approval/invalidation and both-direction activation tests remain passing. No dependency installation, pip upgrade, model download, full audit/suite run, teacher EXE rebuild, merge or deployment. Actual Windows 11 translation requires retry with the latest worker. The original OWNER ZIP is unchanged and predates this repair; keep the repaired setup script and use the existing local official archives with `--skip-dependencies`.
