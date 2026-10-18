# Free offline English ↔ Simplified Chinese translation (OWNER only)

Argos runs on OWNER, with no OpenAI key, subscription or translation account. Teacher Ready / MathStudio.exe remains a client and is unchanged. Public descriptions use the existing draft → preview/edit → approval workflow. Private lessons, student accounts, messages, resource files and private notes are never accepted as translation sources.

**Current verification limit:** the Cloud policy blocks the official model host `argos-net.com`. The real Python 3.13 dependency stack imports and focused tests pass, but real-model translations have NOT been executed in this environment. There are no claimed successful model examples yet. The installer below refuses to mark models ready until its own actual offline English→Chinese and Chinese→English tests succeed. Windows 11 acceptance also remains pending; Windows CI, if reported separately, uses Windows Server 2025 rather than Windows 11.

## One-time setup on OWNER (Windows 11 x64)

1. Finish lessons and stop OWNER/tunnel normally. Do not run dependency/model installation during lessons. Keep a private backup of OWNER data/configuration outside application/release folders. Install current **64-bit CPython 3.13** from python.org with pip and the `py` launcher. No VS Code is needed. Argos is optional: the existing application environment stays unchanged.
2. Double-click **SETUP OFFLINE TRANSLATION.bat** in the OWNER source folder. Setup refuses to proceed if port 5051 is occupied. It creates a separate CPU runtime, installs hash-pinned wheels, downloads the two official Argos 1.9 model packages once, checks archive paths/size/language metadata, then tests both real translation directions with networking disabled before activating the models. Installation may take several minutes and needs roughly 2–4 GB of disk space. No Windows protection should be disabled. Missing-DLL errors require checking the supported Microsoft Visual C++ x64 runtime and rerunning setup, not bypassing security warnings.
3. Default permanent storage is `%LOCALAPPDATA%\MathStudio\translation` (runtime, packages, cache, installation receipt). Linux defaults to the existing MathStudio per-user state directory’s `translation` subdirectory. `MATH_ARGOS_HOME` may select another **absolute, private directory outside the application tree**; pass the same value to setup and OWNER. Models/caches are not bundled into ZIPs, source control or the teacher installer.
4. Translation drafts/approvals remain in the existing OWNER database, normally `%LOCALAPPDATA%\MathStudio\data`, or the explicit `MATH_DATA` directory. Setup does not move user data. If an old installation uses `bulletin_data` inside its application folder, setup stops: back it up, explicitly move/select the data directory outside versioned folders, set `MATH_DATA`, and verify normal OWNER access before proceeding. Never create a replacement account database or discard the original.
5. Start OWNER normally. A verified local Argos installation is selected automatically only when `MATH_PUBLIC_TRANSLATION_PROVIDER` is unset. To select it explicitly set `MATH_PUBLIC_TRANSLATION_PROVIDER=argos` in the OWNER process environment. An existing explicit external-provider selection is preserved; set an empty value to disable automatic provider selection. No provider credential is needed.
6. Sign in as teacher/admin at `/teacher/translations`, review Protected terms, check **Enable free offline automatic translation**, and Save. Generate a draft, inspect/edit it, then explicitly Approve. Regenerate uses the local model. This opt-in is separate from one-time model installation; neither installation nor generation automatically publishes text. The student sees an approved translation or the original fallback. Missing/failed models cannot generate a new draft and never trigger a paid/online fallback. Existing approved translations are retained.

## Disconnected installation and verification

A machine with Internet access may prepare the exact wheels and the two official versioned model archives. Keep their recorded SHA-256 values with your private installation receipt and verify copies before transfer; do not source models from untrusted folders or execute any configuration script found there. Model SHA-256 values are recorded from the official HTTPS download during setup; this candidate does not contain independently verified model hashes because Cloud downloading was blocked.

Use the matching lock and Python 3.13 x64 when collecting wheels:

```
py -3.13 -m pip download --require-hashes --only-binary=:all: --extra-index-url https://download.pytorch.org/whl/cpu -r packaging/argos/requirements-windows-py313.txt -d D:\TrustedArgos\wheels
```

Official model URLs (upstream index: `argosopentech/argospm-index`, package version 1.9):

- `https://argos-net.com/v1/translate-en_zh-1_9.argosmodel`
- `https://argos-net.com/v1/translate-zh_en-1_9.argosmodel`

Place those two filenames in `D:\TrustedArgos\models`. With OWNER stopped:

```
py -3.13 argos_setup.py install --wheelhouse D:\TrustedArgos\wheels --model-files D:\TrustedArgos\models
py -3.13 argos_setup.py status
```

Setup never downloads additional sentence/tokenizer models at inference time: it uses packaged Stanza data with Stanza downloads disabled. Every inference child rejects network connections, forces the local OpenNMT/CPU backend, and receives no provider keys/TURN secrets. OpenCC converts model output to Simplified Chinese before protected values are restored. Missing resources fail safely rather than downloading them.

After setup, this explicit acceptance command uses synthetic public descriptions in a temporary database, tests actual models, protected text, HTTP generation, cache reuse, approval, original preservation and invalidation, and records real output:

```
py -3.13 verify_argos_models.py --output D:\MathStudioChecks\argos-model-results.json
```

The command requires the existing application test dependencies plus access to the installed external Argos runtime; it never downloads models itself. If models are missing, it exits with a blocked result and no examples. Simple real setup examples are also recorded under `offline_examples` in `installation.json` only after actual success. Inspect both model quality and math/name preservation before approving public content. Do not substitute mocked unit outputs for real examples.

## Isolation, cache and protection

One low-priority CPU worker runs at a time with one inference thread. Concurrent generation gets a retry message. Each child is terminated/reaped on its 30-second deadline; only the translation editor has a 45-second HTTP deadline. Classroom polling and native/browser media requests use independent server threads and retain their existing timeouts. Argos is never imported into the HTTP or teacher process. The website shows progress while awaiting the asynchronous request.

Protected tokens are split out before model processing and rejoined exactly. Existing protection covers names supplied in Protected terms, public studio/teacher names, URLs, fenced/inline code, delimited LaTeX, standalone commands and common arithmetic expressions. Supply **all additional proper nouns**, especially Chinese/single-word names, and delimit complex formulas with `$...$`, `\(...\)` or `\[...\]`; text-pattern detection cannot identify every possible name or notation. Human approval remains required. User-supplied text is escaped when rendered. Originals, draft edits, approvals and source-hash invalidation retain the existing semantics.

## Dependencies and rollback

Optional locks are `packaging/argos/requirements-{windows,linux}-py313.txt`, with 65 Linux / 66 Windows fully pinned, hashed CPU dependencies (wheels only). Principal versions: Argos 1.11.0, CTranslate2 4.8.3, SentencePiece 0.2.2, Stanza 1.10.1, spaCy 3.8.16, MiniSBD 0.9.5, PyTorch 2.14.1+cpu, OpenCC Python reimplementation 0.1.7. All are local/free software; check their upstream model/software license notices when distributing copies. Existing MathStudio runtime pins and installer bytes remain unchanged. English/Chinese model quality is not equivalent to human mathematical editing.

To disable new generation, uncheck the teacher setting or explicitly clear/change the OWNER provider selection. Restore the PR #7 OWNER source tree for code rollback; keep the private database and external model directory intact. Added model/cache files do not require an installer rebuild. Before reinstalling or removing optional dependencies, stop OWNER. A crashed setup may leave `.setup.lock`; remove it only after confirming no setup or OWNER process is running. Never delete the account database to repair translation.
