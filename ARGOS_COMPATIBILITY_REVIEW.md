# Argos compatibility review — 2026-10-19

Scope: optional OWNER translation only, based on Draft PR #8. Teacher EXE, WebRTC, authentication, scheduling and all previous MathStudio fixes are unchanged.

## Sources and version checks

Read the official [Argos repository/README](https://github.com/argosopentech/argos-translate), [documentation](https://github.com/argosopentech/argos-translate/tree/master/docs), [official index](https://github.com/argosopentech/argospm-index/blob/main/index.json), and [Argos 1.11.0 PyPI metadata](https://pypi.org/pypi/argostranslate/1.11.0/json). Compared these with the actual hash-locked Argos 1.11.0, Stanza 1.10.1 and CTranslate2 4.8.3 installed sources/docstrings. Also inspected official Stanza 1.1.1 source to compare legacy formats, and [official MiniSBD usage](https://github.com/LibreTranslate/MiniSBD) with installed 0.9.5 source. No downloaded dependency source was installed or executed.

Current master documentation differs from 1.11: it calls Stanza optional and describes MiniSBD as default; pinned 1.11 metadata requires `stanza==1.10.1` and its default chooses the packaged Stanza path for legacy packages. Master also describes `NONE`, but 1.11 has no implemented sentencizer for it. The repair explicitly selects the supported `MINISBD` enum/environment setting confirmed in pinned source. Locks need no changes. CTranslate2 4.8.3 supports the existing `Translator` CPU/int8/inter_threads/intra_threads arguments; actual CPU compute-type inspection passed.

## Root causes and APIs

| Finding | Evidence and status | Resolution |
|---|---|---|
| Forced old tokenizer through new Stanza | Windows resource `add_mwt` failure; new Stanza expects `packages`, old data declares `default_processors`. Reproduced with installed Stanza. | Stop using Stanza for sentence boundaries; supported explicit MiniSBD choice. |
| Checkpoint generations differ | New loader requires feature dropout and lexicon; old loader/save format did not contain them. Reproduced earlier with strict tensor fixtures. | Remove checkpoint adaptation entirely. Legacy PyTorch checkpoints are not loaded for translation. |
| Data-processing generations also differ | Stanza 1.10.1 `para_to_sentences:134` rejects unsupported feature functions. Legacy source supports `all_caps`; pinned new source no longer does. This reproduces the latest error path. | Use genuine supported MiniSBD ONNX tokenizers, rather than adding further exception-specific patches. Actual archived feature list is reported by the Windows diagnostic; it could not be inspected here. |
| Latest documentation is not pinned behavior | Optional Stanza/default/NONE discrepancies above. | Check actual 1.11 source and verify profile versions, rather than follow unversioned examples blindly. |
| Hidden downloads in alternative tokenizers | Argos SpaCy cache can fetch on import; MiniSBD fetches when no local model exists. | Use one known local MiniSBD model per package; validate files/hashes before constructing translation engines. Downloads exist only in explicit stopped-OWNER setup. |
| Readiness previously certified an older path | Earlier receipts only identify Argos and a verified flag. | Schema 2 + runtime profile + pinned sentence-model presence/hash; repeat two distinct translations in each direction before activation. Old receipts fail safely until revalidated. |
| Diagnostics unavailable when ready is false | Prior acceptance harness exited early and could not inspect staged failed installations. | `diagnose_argos.py` safely inspects existing archives/runtime, tests staged models, never downloads or activates, and writes failure JSON. Post-install harness now tests edits and emits safe phase-specific failures. |

The translation calls retain documented `get_installed_languages()`, `get_translation()` and `translate()`. Safe staging extraction is retained because upstream `install_from_path()` extracts directly into the configured package directory; our extra archive checks and pre-activation rollback boundary must remain. No inference request installs models or mutates library APIs. There are **no Stanza/torch monkey patches** in the repaired runtime.

## Model/runtime contract

The official index currently identifies en→zh and zh→en archives as package 1.9 / Argos 1.9.0, hosted at argos-net.com. The Cloud policy does not permit that host; no retry, mirror or policy change was attempted. No genuine translation archives are present here, so their actual metadata/resources/checkpoints and CTranslate2 loading have not been independently accepted. The staged Windows diagnostic reads them on OWNER, reporting only public pair/version/hash, legacy resource flags, known feature labels, safe exception locations and principal versions. It uses `torch.load(weights_only=True)` only for optional legacy inspection, never to repair or translate.

The alternative sentence models are **official MiniSBD v0.0.1 assets referenced by pinned MiniSBD 0.9.5**, not replacement/unofficial translation models. They were downloaded once from the upstream project and SHA-256 pinned in `packaging/argos/profile.json`:

- en.onnx: 188,043 bytes; `6fa9f3a3b201687bd43e329b2b0736789efc97b37883b5b759b31988dca9f353`
- zh-hans.onnx: 616,442 bytes; `b2a6e45ebb43df44ac3c8e4100ea1cb30ec8319c5698b678ed3f203e5edc5d0e`

Actual Argos MiniSBD selection and repeated real ONNX sentence inference passed for both languages on Python 3.13. This proves the replacement sentence stage, **not the complete translation model**. New fixtures forbid Stanza pipeline/checkpoint calls while exercising that stage. The obsolete compatibility tests/patches are replaced by the legacy-feature failure reproduction and tests of the selected supported API.

## Security, acceptance and delivery

CPU-only model sessions, ONNX telemetry disabled, scrubbed child environment, Python network block, one low-priority child, 30-second worker deadline and 45-second editor deadline remain. CTranslate2 is limited to one inter/intra thread; ONNX uses its normal CPU pool. Public-content allowlist, original preservation, protected notation/names, teacher review/edit/approval and source invalidation remain. The diagnostic does not read private accounts/messages or the production DB. Model maintenance remains outside lessons and versioned source folders.

`--skip-dependencies --model-files` reuses installed dependencies and original archives; only two new official sentence models may be downloaded in explicit setup. `--sbd-files` makes installation fully disconnected. Both directions must translate two different synthetic strings per worker before model/receipt activation. Failed stages preserve the previous installation; successful staging diagnostics alone never activate. Post-install acceptance also verifies actual protected mathematical descriptions, names, LaTeX/URLs, edits, approval, cache and invalidation against a temporary HTTP backend/database.

See [setup/Windows commands](ARGOS_OFFLINE_SETUP.md) and [current executed results](argos-review/TEST_RESULTS.md). The updated OWNER ZIP includes source, profile, diagnostic, acceptance harness, existing pins and manifests, excluding all model data, environments, private data and credentials. The teacher EXE is unchanged. Real translation/Windows 11 acceptance remains a release limitation until OWNER reports success with actual examples; human mathematical review is still required.
