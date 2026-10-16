# MathStudio v41.6.6 — provenance and release procedure

Status: **unsigned source candidate only**. A manifest or passing Python test is not proof of a signed executable, working Windows installer, or physical-device WebRTC. No release is published by these steps.

## Reviewed inputs and integrity

`version.json` is the single runtime build/asset identity. `release_manifest.json` records package folder names, the Phase 2B Part 2 parent commit, exact dependencies, and SHA-256 for each explicit first-party file. `/api/desktop-info`, generated `/build_info.js`, the HTML cache URLs and desktop checks consume the same identity. The hardening suffix distinguishes this candidate from older v41.6.6 servers. All application responses use no-store; a fresh page reload is required after an upgrade.

`release_package.py` reads only manifest-listed files, rejects symlinks, unsafe/private paths and binaries, checks hashes, uses one versioned root folder, and creates deterministic ZIP bytes. It excludes `.venv`, credentials/configuration, databases, uploaded resources, logs, cloudflared, and executables. Unlisted files are never scanned or read. Obtain the source/manifest/checksum through a trusted reviewed commit/channel: hashes supplied by an attacker alongside altered files do not establish provenance.

The old checked-in 3,072-byte `MathStudioTeacher.exe` has been removed. Its historical SHA-256 was `7da338987db99aa587630b596936242ef4306fb3859a6623ea0d3b46486e4154`; it lacked an embedded Authenticode signature and a supplied build recipe. This is a provenance gap, not a malware finding. Do not redistribute it as the new launcher.

Validate source candidates without creating an artifact:

```text
python release_package.py --kind owner
python release_package.py --kind teacher
```

After a release reviewer authorizes artifact assembly, create a **new** output path with `--output`; it refuses overwrites. Source candidate folders are `MathStudio_v41_6_6_OWNER_Release_Candidate` and `MathStudio_v41_6_6_TEACHER_READY_Release_Candidate`. They include no Python runtime; Teacher Ready needs the documented setup and connects only to a separately hosted OWNER backend; package_role.json enforces that role. This phase validates assembly using synthetic fixtures; it does not claim complete Windows distribution artifacts.

## Dependencies and environment

Runtime: CPython 3.12–3.14, x64; Tcl/Tk and pip included by the official Windows installer. Tested here: CPython 3.12.14 Linux x86-64. Windows x64 binary wheels for CPython 3.12, 3.13 and 3.14 resolved and downloaded with required hashes in Cloud; those wheels were not executed. Windows Python/Tk versions must be recorded in acceptance evidence; update to current supported vendor security releases.

| Dependency | Exact version | Purpose |
| --- | --- | --- |
| Pillow | 12.3.0 | Native JPEG capture; raster preview validation |
| pypdf | 6.20.1 | Supported PDF extraction in a child process |
| tzdata | 2026.4 (IANA 2026d) | Identical authoritative scheduling rules across OSes |

`requirements.txt` pins all three, with SHA-256 from their exact PyPI release metadata. Setup accepts matching binary wheels only and checks exact installed versions/imports, timezone data, Tk on Windows, and `pip check`. Pillow's hashes cover published platform wheels, including CPython Windows x64; installing a different version or a source build is not an accepted fallback. No runtime third-party transitive dependencies were reported for these distributions. pip/ensurepip come from the selected interpreter and are not separately bundled; record their actual versions at the Windows build. No automatic dependency install occurs during native meeting launch. Recreate `.venv` only through explicit setup outside live lessons.

PyPDF2 fallback is removed. PDF translation has a 32 MB input limit, 80-page/30,000-character output bounds, and a 15-second child-process timeout; Unix also caps worker address space at 512 MiB. A Windows Job Object memory cap is **not implemented**. A hostile PDF may temporarily consume substantial memory before timeout on Windows; document this limitation and test malicious/large documents before broad release. DOCX/ZIP processing budgets remain outside this focused change.

On 2026-10-16, a fresh hash-checked installation and `pip check` passed. pip-audit 2.10.1 using PyPI advisory data reported **no known vulnerabilities** for these three exact versions. That result is a dated advisory observation, not a future guarantee; rerun at the actual release build. The test tools are external to the distributed runtime.

## Optional Windows executable build — NOT performed in Cloud

`launcher/teacher_launcher.c` is a small Unicode launcher: it locates its own directory, starts only the adjacent `.venv\Scripts\python.exe` with `runtime_setup.py --launch teacher`, uses an absolute executable path and working directory, and never invokes cmd.exe or searches/imports configuration scripts. Missing setup opens a visible instruction dialog. It is optional; normal installation uses the BAT launcher. No compiled replacement executable is included in the manifest.

Required Windows steps:

1. Check out the reviewed PR commit in a clean Windows x64 build VM. Respect .gitattributes (LF text bytes) so Git checkout does not invalidate the manifest hashes. Record commit ID, `version.json`, Windows build, exact Python installer SHA-256/signature, Python/Tk/pip versions, MSVC `cl /Bv` output and Windows SDK version. Ensure no credentials, private account database or student resources enter the workspace/artifact.
2. Use an x64 Native Tools Command Prompt for a supported Visual Studio Build Tools installation. Build into an empty private staging directory:

   ```bat
   cl /nologo /W4 /O2 /MT /utf-8 /Brepro launcher\teacher_launcher.c /Fe:staging\MathStudioTeacher.exe /link /SUBSYSTEM:WINDOWS /DYNAMICBASE /NXCOMPAT /Brepro user32.lib
   ```

   MSVC/SDK are absent here; this recipe and executable have **not** been compiled or executed in Cloud. Build twice in independent clean directories with the same toolchain and compare unsigned hashes; `/Brepro` is an input to that check, not a claim of bit-for-bit reproducibility across toolchains.
3. Test the BAT/source path and optional EXE as a standard Windows user: clean setup, Unicode/space paths, missing Python/Tk, missing/old packages, offline wheels, healthy/mismatched/occupied port, upgrade backup/rollback, and read-only/nonwritable folders. Verify there is no dependency installation during a live meeting and that errors remain visible.
4. Obtain a legitimate Authenticode code-signing certificate through the owner's signing process. Use the certificate store or approved hardware/signing service; never put private keys/passwords/PFX in the repo or ZIP. Sign the EXE with SHA-256 and an RFC3161 timestamp at the CA-approved URL, e.g. `signtool sign /sha1 <certificate-thumbprint> /fd SHA256 /tr <CA-timestamp-URL> /td SHA256 staging\MathStudioTeacher.exe`. Verify using `signtool verify /pa /all /v` and `Get-AuthenticodeSignature`. Record expected signer, timestamp and SHA-256 **after** signing. Timestamped signatures need not be byte-reproducible.
5. A signed installer, if required, also needs a reviewed installer definition, bundled-runtime licensing/update policy, supported prerequisites, uninstall/upgrade behavior that preserves data, clean-VM install tests, its own signature, and after-signing hashes. These inputs/artifacts do not exist in this Cloud phase. Do not label a source ZIP as a self-contained signed Teacher Ready installer.
6. Create a separately reviewed manifest for the signed artifact. The source-only packager deliberately rejects EXE files. Never weaken that guard merely to fit a binary. Validate downloaded files with Mark-of-the-Web and normal Defender/SmartScreen protections enabled; investigate warnings rather than recommending global bypasses.
7. Recheck the dependency advisories, manifest, every package member, folder version and after-signing checksums. Run the physical-device checklist in `RELEASE_CHECKLIST.md`, including simultaneous bidirectional media, permission revocation and annotation conflicts. Obtain explicit release approval before publishing.

Cloud also lacks Windows PowerShell/cmd execution, code-signing credentials/service, an official selected cloudflared Windows binary, and physical camera/audio/mobile devices. No Windows installer or signed EXE is claimed, no production credentials/data were used, and no deployment, merge or release publication was performed.
