# OWNER offline English ↔ Simplified Chinese translation

Use the **complete updated OWNER ZIP**, not individual files from the earlier Stanza patches. Teacher Ready/MathStudio.exe is unchanged and remains client-only. No paid API, OpenAI key, translation account or subscription is required.

**Acceptance status:** genuine official MiniSBD sentence models have been tested, but the official Argos translation host is blocked in Cloud and neither complete translation direction has been executed here. Windows 11 real-model acceptance remains pending. See [compatibility review](ARGOS_COMPATIBILITY_REVIEW.md) and [results](argos-review/TEST_RESULTS.md). Successful sentence splitting is not successful translation.

## Existing Windows OWNER installation — reuse downloaded models and dependencies

1. Finish lessons and stop OWNER/tunnel. Back up existing private data/configuration outside application folders. Extract the updated OWNER folder and keep the same external `MATH_DATA` and optional `MATH_ARGOS_HOME` settings. Do not replace/reset account databases. Legacy in-application data must first be explicitly backed up and selected outside the versioned application folder.
2. Open PowerShell in the extracted OWNER folder. Use the already installed x64 CPython 3.13 and existing optional runtime:

```powershell
$env:PYTHONUTF8 = '1'
$models = Read-Host 'Folder containing translate-en_zh-1_9.argosmodel and translate-zh_en-1_9.argosmodel'
py -3.13 argos_setup.py install --skip-dependencies --model-files "$models"
```

This does **not** run pip or redownload the two Argos archives. It obtains only two new official MiniSBD sentence models (about 188 KB and 616 KB) once, verifies their pinned SHA-256 hashes, and caches them externally. It safely stages the original translation archives with these sentence models, then requires two genuine translations **per direction, within one worker process per direction**, with network access disabled. Only then are both model directories and the verified receipt activated. Failure leaves the old directories/receipt intact. `ready: false` is intentional until successful verification; never edit the receipt to bypass it.

3. If setup fails, generate a safe report with the same archives and the sentence models cached by setup:

```powershell
$checks = Join-Path $env:LOCALAPPDATA 'MathStudio\translation\checks'
py -3.13 diagnose_argos.py --model-files "$models" --output "$checks\compatibility.json"
```

The diagnostic never runs pip, downloads, activates models or touches accounts. It inspects public package metadata, legacy resource flags/checkpoint feature names using restricted deserialization, installed versions and CPU/MiniSBD selection, then runs the staged real-model self-tests. Failure reports contain direction, safe code locations and fixed schema keys, without private paths, input, credentials or arbitrary exception messages. Return code 1 means failed/blocked. Keep the JSON for review.

4. After successful installation, keep OWNER stopped and run the acceptance harness:

```powershell
$checks = Join-Path $env:LOCALAPPDATA 'MathStudio\translation\checks'
py -3.13 verify_argos_models.py --output "$checks\acceptance.json"
py -3.13 argos_setup.py status
```

The harness uses synthetic public descriptions and a temporary database/server. It checks real English→Chinese/Chinese→English mathematical translation, protected names, URLs, arithmetic, LaTeX, draft editing, approval, source preservation, cache reuse and source invalidation. It does not use real accounts or student data. It never downloads models. Exit 0 plus `status: passed` is the automated acceptance result; inspect actual translations for quality before enabling generation. Missing models produce a blocked result, not a pass. Check the exit code of each command; `status` alone does not certify quality or physical-device workflows.

5. Start OWNER normally. A verified local installation is selected when `MATH_PUBLIC_TRANSLATION_PROVIDER` is unset; explicitly set it to `argos` if needed. Existing explicit external-provider choices are preserved; an empty value disables automatic selection. At `/teacher/translations`, review Protected terms, enable free offline generation, Save, generate/edit a draft, then explicitly Approve. Nothing is automatically published.

## Fresh setup / fully disconnected setup

For a fresh Windows 11 x64 OWNER, install 64-bit CPython 3.13 with pip and the `py` launcher from python.org, then double-click **SETUP OFFLINE TRANSLATION.bat** while OWNER is stopped. No VS Code is needed. It installs the existing hash-locked optional CPU environment and official model data. Do not upgrade pip or change dependency versions to fix a model error. DLL failures need the supported Microsoft Visual C++ x64 runtime, not disabled Windows protections.

For a disconnected PC, collect the matching wheels on a connected trusted machine:

```powershell
py -3.13 -m pip download --require-hashes --only-binary=:all: --extra-index-url https://download.pytorch.org/whl/cpu -r packaging/argos/requirements-windows-py313.txt -d D:\TrustedArgos\wheels
```

Obtain the two existing translation archives only from the official index URLs:

- https://argos-net.com/v1/translate-en_zh-1_9.argosmodel
- https://argos-net.com/v1/translate-zh_en-1_9.argosmodel

Additional sentence models are the official models used by pinned MiniSBD 0.9.5:

- https://github.com/LibreTranslate/MiniSBD/releases/download/v0.0.1/en.onnx — SHA-256 `6fa9f3a3b201687bd43e329b2b0736789efc97b37883b5b759b31988dca9f353`
- https://github.com/LibreTranslate/MiniSBD/releases/download/v0.0.1/zh-hans.onnx — SHA-256 `b2a6e45ebb43df44ac3c8e4100ea1cb30ec8319c5698b678ed3f203e5edc5d0e`

Put the ONNX files in a trusted folder. With OWNER stopped:

```powershell
# Existing optional dependencies; no pip or downloads:
py -3.13 argos_setup.py install --skip-dependencies --model-files D:\TrustedArgos\models --sbd-files D:\TrustedArgos\sentence-models
# Fresh disconnected optional runtime:
py -3.13 argos_setup.py install --wheelhouse D:\TrustedArgos\wheels --model-files D:\TrustedArgos\models --sbd-files D:\TrustedArgos\sentence-models
# Diagnostic can use the same local sentence-model folder:
py -3.13 diagnose_argos.py --model-files D:\TrustedArgos\models --sbd-files D:\TrustedArgos\sentence-models --output D:\MathStudioChecks\compatibility.json
```

Translation archive hashes are recorded in the installation receipt; independent pinned hashes could not be established here because that official host is blocked. Never use unofficial model mirrors or discovered configuration scripts. All inference paths are local; missing/corrupt sentence models fail before Argos can attempt a cache download.

## Runtime, storage and security

The supported Argos 1.11 setting `ARGOS_CHUNK_TYPE=MINISBD` replaces all custom Stanza resource/checkpoint patches. Each installed package has exactly one hash-pinned local MiniSBD model; Argos uses its normal package, language and translation APIs. Stanza remains installed because Argos 1.11 requires it, but its legacy tokenizer path is unused. ONNX telemetry is explicitly disabled before sessions start.

Default persistent Windows storage: `%LOCALAPPDATA%\MathStudio\translation` (runtime, models, auxiliary download cache, receipt). Linux uses the MathStudio per-user state directory. `MATH_ARGOS_HOME` may specify another absolute private directory outside the application tree; use it consistently for setup, verification and OWNER. Drafts/approvals stay in the existing external OWNER database, normally `%LOCALAPPDATA%\MathStudio\data` or `MATH_DATA`. Upgrades must preserve these directories. No models, environments, wheels or private data are bundled in OWNER ZIPs.

One low-priority child runs at a time, with a 30-second deadline and CPU-only execution. CTranslate2 inter/intra threads are 1; MiniSBD uses its upstream ONNX CPU pool. Only generation has a 45-second HTTP deadline. No Argos import, model inference or download runs in the teacher application or classroom request thread. Concurrent generation gets a retry response. ONNX telemetry and Python network connections are disabled. Provider credentials are absent from the child environment.

Only allowlisted public descriptions are translated. Messages, accounts, private lessons, resource contents and private notes are rejected. Existing approved translations/edits and original descriptions are retained. Models do not receive protected placeholders: parent-side splitting/restoration preserves URLs, delimited LaTeX, common notation and configured terms. Add all extra names/proper nouns to Protected terms and delimit complex mathematics; automatic pattern detection cannot identify every name or formula. Regenerate explicitly when desired; changing the runtime does not erase teacher-approved content.

Dependency locks are unchanged: 65 Linux / 66 Windows pinned, hashed packages, wheels only. Key versions: Argos 1.11.0, CTranslate2 4.8.3, MiniSBD 0.9.5, ONNX Runtime 1.31.0, SentencePiece 0.2.2, Stanza 1.10.1, spaCy 3.8.16, CPU PyTorch 2.14.1+cpu, OpenCC 0.1.7. The source-controlled runtime profile verifies these principal versions before translation. Keep upstream license notices when redistributing software/models.

To disable, uncheck offline generation or explicitly clear the provider selection. For source rollback use the PR #7 OWNER baseline and retain all private data; do not restore intermediate broken Stanza patches. Stop OWNER before optional runtime maintenance. A crashed setup may leave `.setup.lock`; remove it only after confirming setup/OWNER are stopped. Never delete the account database to repair translation.
