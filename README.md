# MathStudio v41.6.6 — hardened release candidate

Python backend on port 5051, Windows Teacher App, and bilingual student website. This branch includes the approved Phase 2A, Phase 2B Parts 1/2, and Phase 2C fixes. Current build/asset identity is in `version.json`.

For normal Windows use, follow **[INSTALL_WINDOWS.md](INSTALL_WINDOWS.md)**: install supported x64 Python with Tcl/Tk, double-click **SETUP MATHSTUDIO.bat**, then **OPEN MATHSTUDIO TEACHER.bat**. No VS Code is needed. The Teacher App creates the first teacher account on a fresh install and starts or reuses a matching website. Remote media requires an HTTPS student link and working TURN configuration.

Private credentials and new installation data live outside the application folder. Legacy in-folder data remains in place; back up and migrate deliberately. Do not send databases, student files, logs, TURN tokens or configuration files with a package. Old configuration batch files are not discovered or executed. See the explicit import instructions.

Release inputs and provenance are documented in [BUILD_RELEASE.md](BUILD_RELEASE.md) and [release_manifest.json](release_manifest.json). The undocumented historical EXE is removed. No signed installer or replacement executable has been built in this Cloud environment.

Validate dependencies and run tests in an isolated environment:

```text
python -m venv .venv
# Activate that environment, then:
python -m pip install --require-hashes --only-binary=:all: -r requirements.txt
python -m unittest discover -v
node test_browser_workflows.mjs
python release_package.py --kind teacher
```

Tests use temporary databases and synthetic accounts. Node is needed only for development tests. Windows installation and physical Windows/iPhone/Android media acceptance remain required: [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md). No unit-test result certifies bidirectional media on physical devices.
