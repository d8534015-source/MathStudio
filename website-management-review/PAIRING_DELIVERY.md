# PR #9 — paired-login review delivery

Both packages use build **v41.6.6-pr9-pairing-review1**, source head
`10b80c72a648532167ed163aeb76d3ea0bff40b3`, and the identical source-manifest
SHA-256 `9fbdcc40fdf096c708ddef633c5b134b5d5e151e54d75f959298275e0a0114fe`.
The Windows checkout `f74bf97f349f04ed4a7f19ff276936d6a3ae81cb` is GitHub's
synthetic PR test-merge, not a branch merge. Later delivery commits contain
only artifacts/reports; they do not require another teacher rebuild.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `MathStudio_v41_6_6_OWNER_PR9_Review.zip` | 574,373 | `1010fca831cff8bb7c1ee936a34d959746ee1c10f083edcbfd689c88b6292e8b` |
| `MathStudio-Website-Management-Review.exe` | 16,284,377 | `cb88d5022491570aec61c16ffb78175d02095486aa29038de657123373a066e0` |

This delivery supersedes the older ZIP/installer linked in historical
`TEST_RESULTS.md`. [OWNER verification](OWNER_REVIEW_VERIFICATION.json),
[Windows verification](windows-verification.json),
[build provenance](build-manifest.json), [client isolation](client-isolation.json),
[Defender/signature result](distribution-security.json),
[Windows smoke checks](windows-smoke-results.json), [checksums](SHA256SUMS.txt).

## Windows startup and pairing

1. Extract the complete OWNER ZIP into a **new test folder**. Keep the single
   versioned subfolder intact. Do not extract over the working OWNER.
2. From that extracted source folder, use installed 64-bit Python 3.13:

   ```powershell
   py -3.13 .\owner_review.py setup --argos-home "$env:LOCALAPPDATA\MathStudio\translation"
   ```

   Replace the Argos path if yours is custom. Select the existing folder with
   `installation.json`, `runtime` and `packages`, not the archive folder.
   This copies only the installed runtime/models/receipt locally into isolated
   review storage. **No models or Argos dependencies are downloaded/reinstalled.**
   The original base Python must remain installed on this same PC. Allow
   several GB for the copy. A new review-only OWNER environment installs the
   pinned base wheels, then the existing worker must pass two real translations
   per direction before review setup succeeds. A local base-wheel `--wheelhouse`
   option is documented in the ZIP for fully offline setup.
3. If the previous isolated OWNER review is already successfully set up,
   **do not run setup over it**: start this extracted source with its existing
   state to preserve your synthetic accounts/models. To demonstrate first-run
   pairing from scratch, choose a new review-only directory using the same
   `--state` argument for both setup and start. For example:

   ```powershell
   py -3.13 .\owner_review.py setup --state "$env:LOCALAPPDATA\MathStudioOwnerPairingReview" --argos-home "$env:LOCALAPPDATA\MathStudio\translation"
   ```

4. Install official cloudflared if needed, then reopen the console so PATH is
   refreshed. No DNS or hosting changes are needed:

   ```powershell
   winget install --id Cloudflare.cloudflared --exact
   cloudflared --version
   py -3.13 .\owner_review.py start
   ```

   Or double-click `REVIEW OWNER START.bat`. If you selected the alternate
   state in step 3, launch it explicitly instead:

   ```powershell
   py -3.13 .\owner_review.py start --state "$env:LOCALAPPDATA\MathStudioOwnerPairingReview"
   ```

   OWNER uses loopback port **5059**, displays the temporary HTTPS URL, and
   opens a **local pairing window** only if uninitialized. It never requests
   an initial account/password in the console. No process on 5051 is adopted
   or stopped. Ctrl+C in this review OWNER console stops only its own server,
   tunnel and pairing window. Tunnel startup failure does not initialize DBs.
5. Run the downloaded teacher installer and keep its **MathStudio Review**
   destination/shortcut. It has its own App ID and settings profile, bundles
   Python/Tcl/Tk, requires no VS Code or separate Python, and remains client-only.
   Do not choose the production application's folder.
6. Open MathStudio Review and enter the exact OWNER HTTPS origin. If OWNER is
   uninitialized, explicitly enter the local pairing window's one-time code
   in **First-Time Teacher Setup**, create a synthetic teacher account and sign
   in. The code expires after 15 minutes and is consumed once. A lost/expired
   code requires restarting only the uninitialized review OWNER; no accounts
   are reset. An initialized OWNER uses normal login and is never reclaimed.
7. **Remember me on this device** defaults off. If enabled, Windows DPAPI
   protects rotating refresh credentials (7-day inactivity / 30-day absolute
   limit). No password is saved. Restart restoration, replay, password/role
   revocation and logout were tested. Settings can disable it without ending
   an active native classroom; Sign out revokes it. Failed remote logout is
   reported, not treated as success. A changed Quick Tunnel origin needs login
   again; Connection settings allow updating an offline old address and clearly
   warn if the old remote credential could not be revoked. Sign out before
   uninstalling if you want to revoke remembered access; uninstall preserves
   this review profile and does not touch production settings.
8. Use only synthetic public content/student accounts. Verify the student site
   through the same HTTPS address. No production TURN/R2 configuration is
   imported. Cross-network media may need separately configured **test** TURN
   credentials; no media success is inferred from mocked signaling tests.

For a **review-only** forgotten-password recovery, stop the review server and
run this from the extracted source folder. This explicitly scopes the existing
local reset command to the review data/config; never run bare `server.py`
against a working OWNER's default state. Adjust the review directory if you
used a custom `--state`:

```powershell
py -3.13 -c "import os; from pathlib import Path; from owner_review import run,python_at; s=Path(os.environ['LOCALAPPDATA'])/'MathStudioOwnerPR9Review'; assert (s/'review-ready.json').is_file(); run(s,[str(python_at(s/'owner-runtime')),'server.py','reset-password'])"
```

No recovery command was run on an existing installation during this work.

## Executed verification

- Final Linux / Python 3.13.5 full suite: **185 run, 183 passed, 2 Windows-only
  DPAPI tests skipped, zero failures**, 29.556 seconds. Cached official MiniSBD
  English/Chinese sentence models were exercised; full translation weights
  were unavailable here. PR #8's user-confirmed real Windows translation
  acceptance is preserved; no new Cloud real-model translation is claimed.
- [Final Windows Server 2025 / Python 3.13.12 x64 CI](https://github.com/d8534015-source/MathStudio/actions/runs/39200969026):
  **185 run, 181 passed, 4 optional OWNER-stack tests skipped, zero failures**,
  280.539 seconds. Those four Argos/SentencePiece/MiniSBD tests ran successfully
  locally. Actual Windows DPAPI encryption, origin/review isolation and
  authenticated restoration/logout across **new processes** passed in CI.
- **9 Chinese-codepage regressions**, **15 install/import/DPAPI/uninstall/reinstall
  smoke checks**, and actual Windows job ownership/cleanup passed.
- **15 Node browser workflow tests** passed. Existing security, booking/DST,
  annotation, Website Management, draft/edit/approval/cache/publication and
  media-signaling compatibility regressions passed in the full suites.
- ZIP CRC, single versioned root, exact 118-file allowlist plus manifest, every
  source byte/hash, launchers, extracted Python compilation, isolated schema
  startup, missing-model fallback and inherited PR #8 protected-source identity
  passed. No environment, model/archive, credential, DB, user file or EXE payload.
- Actual frozen teacher inspected: **388 modules / 1,636 files**, no OWNER/auth
  backend, Argos dependency, model or account DB. PE header, x64 bundled runtime,
  GUI launch without Python on PATH, review profile and matching manifest verified.
- **Microsoft Defender scan completed: zero build detections.** This is an
  observed scan result, not a guarantee that every future scanner agrees.
- **Authenticode: NotSigned.** No authorized signing certificate/environment
  was supplied. No self-signing, purchase, security exclusions or protection
  changes were made. New code signing and SmartScreen reputation are different:
  signing proves identity/integrity; even a newly signed app may still receive
  warnings. See [signing options/indicative costs and changed-file purposes](../PR9_PAIRING_REVIEW.md).

Earlier development failures (outdated bootstrap/build-ID assertions and a
packaging-test import) were corrected before the final gate. Earlier Windows
runs were superseded/cancelled when the final authorization edge fixes landed;
no test failure was bypassed to produce this delivery.

## Unverified acceptance / stop point

Live Quick Tunnel HTTPS reachability was **not** exercised in this Cloud
session. Physical Windows 11 installation/SmartScreen UX and iPhone/Android
bidirectional audio/video, screen share, annotations, sleep/resume and reconnect
still require real-device acceptance. Windows CI is **Server 2025**, not a
physical Windows 11 test. Reusing your actual installed Argos model copy must
pass the local setup's real both-direction gate. No production data, existing
OWNER/teacher installation, DNS, deployment, main branch or release was changed.

This is a draft-PR review distribution. Stop for approval before any merge or
deployment. Roll back using the prior review distribution and its matching
separate review-state snapshot; keep all production data untouched.
