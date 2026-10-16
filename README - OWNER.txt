MathStudio v41.6.6 — OWNER release candidate

Use INSTALL_WINDOWS.md for setup without VS Code.
Run SETUP MATHSTUDIO.bat, then OPEN MATHSTUDIO TEACHER.bat.
Use BUILD_RELEASE.md and release_manifest.json for provenance and source-package validation.

No signed executable, bundled Python runtime or complete Windows installer is supplied.
The old undocumented MathStudioTeacher.exe has been removed.
Never distribute private_config.json, media_config.bat, cloud_storage.bat,
bulletin_data, student files, logs, account databases or signing keys.
Import one explicitly selected trusted legacy configuration as data; never execute it.

Finish all classes and make a private backup before upgrading or recreating dependencies.
Do not run two builds against the same data. Review the pinned timezone-data changes.
Windows, iPhone and Android acceptance remains pending; do not publish without approval.
