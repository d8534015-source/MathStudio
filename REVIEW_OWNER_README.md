# Classroom recording / pen review

Read `CLASSROOM_REVIEW.md` first for the new isolated installer, private-cloud recording configuration and manual acceptance gates. Earlier PR9 review installations remain separate.

# PR #9 Windows OWNER server review

This is complete OWNER source for PR #9's paired-login review, including PR #8's Argos/MiniSBD,
UTF-8 input and private-file worker-response fixes. It is a review candidate,
not a production upgrade or a teacher-only package. No EXE, accounts,
databases, credentials, Python environments or language models are bundled.

## Extract and set up without changing the working OWNER

1. Keep your existing OWNER folder unchanged. Extract the entire ZIP into a
   **new** folder, for example `C:\MathStudioTests\Classroom`. Keep its single
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
   receipt into `%LOCALAPPDATA%\MathStudioOwnerClassroomReview\translation`.
   Allow several GB of free disk space. No original files are changed, no
   archives are needed, and **no language models are downloaded**.
5. Setup creates a separate OWNER Python environment and installs only the
   hash-pinned base packages in `requirements.txt` from PyPI (Internet needed
   for these base wheels only). It does not install/upgrade Argos dependencies.
   It verifies the copied interpreter uses the copied packages, checks model
   readiness and runs two offline translations in **each direction**. Success
   is reported only after all these checks pass.
6. Install official Cloudflare `cloudflared` if not already present:
   `winget install --id Cloudflare.cloudflared --exact`. Open a new console
   afterwards and check `cloudflared --version`. No tunnel executable is
   bundled, no DNS changes are needed, and no security settings are disabled.
7. Double-click **REVIEW OWNER START.bat**. OWNER opens a local pairing
   window if it has never been initialized, and prints a temporary
   **https://...trycloudflare.com** address. It never requests a teacher
   password in the console. Port 5061 remains loopback; the existing OWNER
   on 5051 is neither reused nor stopped. If 5061 is busy, startup refuses it.
   A failed tunnel startup never calls backend initialization. Ctrl+C stops
   only this review OWNER and its own tunnel/pairing window.
8. Install the matching **MathStudio Review** teacher installer into its
   default separate folder. Enter the HTTPS address in the app. In
   **First-Time Teacher Setup**, explicitly enter the code from the local
   OWNER window and create a new synthetic teacher account. The code expires
   in 15 minutes, is consumed once, and is never put in URLs or console logs.
   If lost or expired, stop/restart only the review OWNER to issue a new code.
   An initialized OWNER never offers account creation again, even on restart.
9. Optionally check **Remember me on this device** (initially unchecked).
   Windows DPAPI protects a rotating, revocable credential; no password is
   stored. Idle expiration is 7 days and absolute expiration is 30 days.
   Password/role changes or revocation require login again. Settings can
   disable Remember Me; **Sign out** revokes it. Network failures do not
   count as confirmed logout: reconnect and retry.

Only use synthetic public descriptions/accounts/files. The review server binds
loopback behind an owned **temporary test tunnel**, and inherits no TURN/R2
credentials. Do not share the pairing code or use private student information.
It has no configured TURN relay; cross-network media may need separately
configured test TURN credentials. No production media acceptance is claimed.
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
py -3.13 .\owner_review.py setup --state "$env:LOCALAPPDATA\MathStudioOwnerClassroomReview2" --argos-home "D:\ExistingArgosHome"
py -3.13 .\owner_review.py start --state "$env:LOCALAPPDATA\MathStudioOwnerClassroomReview2"
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
Get-FileHash .\MathStudio_v41_6_6_OWNER_Classroom_Review.zip -Algorithm SHA256
```

The matching delivery report records final local and Windows CI results.
Physical Windows 11/mobile media acceptance and live Quick Tunnel reachability
must be distinguished from mocked lifecycle tests. Actual translations with
your installed models must pass the local setup checks. Quick Tunnel addresses
change after restart: use Connection settings to select the new address;
remembered credentials are scoped to the exact origin and review profile.

See `PR9_PAIRING_REVIEW.md` for security boundaries, signing/SmartScreen,
regression coverage, changed-file purposes and remaining manual acceptance.

Use only the two **REVIEW OWNER** launchers for this isolated test. Other
legacy/production setup scripts are included for source completeness and are
not needed for review. No merge, deployment or production migration is done.
