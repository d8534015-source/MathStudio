# MathStudio installer review delivery

Teacher-facing download: **MathStudio.exe** (15,979,616 bytes). This is the single installer; the JSON/log/Markdown files beside it are owner/reviewer evidence, not teacher prerequisites.

SHA-256: `c05b5e9f160d0c9dddb428128dab1ddd3d87527d5fb6ed7e97094f494d8990cc`.

[Install/uninstall instructions](INSTALL_AND_UNINSTALL.md) · [Complete test report](../WINDOWS_INSTALLER_TEST_RESULTS.md) · [Pinned Windows rebuild and signing instructions](../packaging/windows/README.md)

[Successful Windows Actions run](https://github.com/d8534015-source/MathStudio/actions/runs/39165705626). Built from source head b76e32cd38c4325770781598fdd97d0829c724af and its PR merge snapshot recorded in build-manifest.json. The installer passed per-user installation with 5051 occupied, Unicode paths/shortcut validation, bundled windowless GUI/native imports without Python on PATH, uninstall and reinstall. All 103 Windows regressions and nine Chinese-codepage checks passed.

**Unsigned review candidate.** Real Windows 11/Search/reboot, actual Chinese Windows display locale, live remote OWNER login/native lessons and physical-device media remain acceptance steps. No signing certificate was available. Nothing has been merged, deployed or published as a GitHub Release.
