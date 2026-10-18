MathStudio v41.6.6 — OWNER release candidate

Use INSTALL_WINDOWS.md for setup without VS Code.
Run SETUP MATHSTUDIO.bat, then START STUDENT WEBSITE.bat to host the OWNER backend.
Use the separately supplied, verified MathStudio.exe installer for the client-only teacher app.
Use BUILD_RELEASE.md and release_manifest.json for provenance and source-package validation.

This OWNER source archive contains no teacher executable or bundled Python runtime.
The separately supplied MathStudio.exe is unchanged; see installer-review in the review repository.
See WEBSITE_INTEGRATION.md and PUBLIC_TRANSLATION_SETUP.md for website upgrades and opt-in translations.
The old undocumented MathStudioTeacher.exe has been removed.
Never distribute private_config.json, media_config.bat, cloud_storage.bat,
bulletin_data, student files, logs, account databases or signing keys.
Import one explicitly selected trusted legacy configuration as data; never execute it.

Finish all classes and make a private backup before upgrading or recreating dependencies.
Do not run two builds against the same data. Review the pinned timezone-data changes.
Windows, iPhone and Android acceptance remains pending; do not publish without approval.
