# PR #9 Windows OWNER server review

This is complete OWNER source for PR #9, including PR #8's Argos/MiniSBD,
UTF-8 input and private-file worker-response fixes. It is a review candidate,
not a production upgrade or a teacher-only package. No EXE, accounts,
databases, credentials, Python environments or language models are bundled.

## Extract and set up without changing the working OWNER

1. Keep your existing OWNER folder unchanged. Extract the entire ZIP into a
   **new** folder, for example `C:\MathStudioTests\PR9`. Keep its single
   `MathStudio_v41_6_6_OWNER_Website_Management_Review` subfolder intact.
2. On the **same Windows PC** where Argos already works, confirm
   `py -3.13 --version` works. Keep the original 64-bit Python 3.13 installation:
   the locally copied Argos environment still depends on that base interpreter.
   Do not reinstall Argos, upgrade pip, or run `SETUP OFFLINE TRANSLATION.bat`.
3. Double-click **REVIEW OWNER SETUP.bat**. Enter your existing Argos home:
   the folder containing `installation.json`, `runtime` and `packages`.
   The normal location is `%LOCALAPPDATA%\MathStudio\translation`; use your
   actual custom `MATH_ARGOS_HOME` location if different. Do not select the
   downloaded archive folder or an individual `.argosmodel` file.
4. Setup copies only the installed runtime, installed packages and readiness
   receipt into `%LOCALAPPDATA%\MathStudioOwnerPR9Review\translation`.
   Allow several GB of free disk space. No original files are changed, no
   archives are needed, and **no language models are downloaded**.
5. Setup creates a separate OWNER Python environment and installs only the
   hash-pinned base packages in `requirements.txt` from PyPI (Internet needed
   for these base wheels only). It does not install/upgrade Argos dependencies.
   It verifies the copied interpreter uses the copied packages, checks model
   readiness and runs two offline translations in **each direction**. Success
   is reported only after all these checks pass.
6. Double-click **REVIEW OWNER START.bat**. Create a **new test-only** admin
   using the console prompts. Open **http://127.0.0.1:5059**. The existing
   OWNER on port 5051 is neither reused nor stopped. If 5059 is busy, startup
   refuses it. Ctrl+C stops only the review server.

Only use synthetic public descriptions/accounts/files. The review server binds
loopback, starts no tunnel, and inherits no TURN/R2 credentials. This is not a
public HTTPS or physical-device classroom deployment. It has no configured
TURN relay; do not treat this package as a production media acceptance test.
The Teacher Website Management desktop UI is source-included; its separately
delivered PR #9 review teacher installer is **not** included in this OWNER ZIP.
See `WEBSITE_MANAGEMENT.md` for its content/translation review workflow.

## Equivalent PowerShell commands

Run from the extracted versioned source folder (no administrator required):

```powershell
py -3.13 .\owner_review.py setup --argos-home "$env:LOCALAPPDATA\MathStudio\translation"
py -3.13 .\owner_review.py start
```

For an existing custom Argos home, replace that argument with its full path.
For **fully offline base dependency setup**, first obtain compatible verified
base dependency wheels in a local wheelhouse, then use:

```powershell
py -3.13 .\owner_review.py setup --argos-home "D:\ExistingArgosHome" --wheelhouse "D:\OwnerBaseWheels"
```

For a retry after a failed setup, choose a **new** review-only state directory;
setup refuses to overwrite existing directories. Pass the same `--state` to
both setup and start. Never select your existing OWNER state or Argos home.

```powershell
py -3.13 .\owner_review.py setup --state "$env:LOCALAPPDATA\MathStudioOwnerPR9Review2" --argos-home "D:\ExistingArgosHome"
py -3.13 .\owner_review.py start --state "$env:LOCALAPPDATA\MathStudioOwnerPR9Review2"
```

If copying/verification fails, leave the working OWNER untouched. A copied
environment cannot be moved to a different PC or used after removing its
original base Python installation. Do not force readiness or edit receipts.
The setup self-test uses the existing bounded, CPU-only, network-blocked
worker; it never activates new models in your original installation.

## State, provenance and verification

All review databases, accounts, caches, configuration and copied models stay
under the selected review state directory, outside the extracted application.
No existing private configuration or account database is imported. Removing
the extracted folder and this **review-only** state directory removes the
review installation; it does not uninstall Python or alter the working OWNER.

`release_manifest.json` identifies every included source file and its SHA-256.
The delivery checksum file covers the ZIP itself. In PowerShell:

```powershell
Get-FileHash .\MathStudio_v41_6_6_OWNER_PR9_Review.zip -Algorithm SHA256
```

The inherited source passed 155 Linux regression tests; Windows CI ran 155
tests (151 passed, 4 optional OWNER-stack skips). Packaging isolation tests
are recorded in the adjacent delivery verification report. The new review
setup/start scripts have not been executed on physical Windows in this Cloud
session. Actual translations with your installed models must pass the local
setup checks; no Windows/model success is inferred from synthetic tests.

Use only the two **REVIEW OWNER** launchers for this isolated test. Other
legacy/production setup scripts are included for source completeness and are
not needed for review. No merge, deployment or production migration is done.
