# MathStudio v41.6.6 — hardened release candidate

Canonical identity: `version.json` (`v41.6.6-release-candidate-hardening1`). This source candidate includes approved security/session/TURN stability repairs, teaching/chat/resource/timezone corrections, annotation/localization fixes, and Phase 2C release hardening.

Phase 2C adds explicit hash-checked dependency setup, a first-account/start-or-reuse Teacher App path, external private configuration with data-only migration, an explicit source package manifest, launcher source/build/signing instructions, version-matched web diagnostics/assets and supported teacher navigation. Unknown/executable uploaded types download as attachments; validated raster images/PDF signatures may preview under a restrictive sandbox policy. PyPDF2 fallback is removed and PDF extraction runs in a bounded child.

Pillow 12.3.0, pypdf 6.20.1 and tzdata 2026.4 are pinned and hash checked. Pinned IANA 2026d is authoritative on all OSes; Edmonton stays UTC−6 in November 2026. No stored booking timestamps are rewritten. Review future local-time expectations during upgrades.

The user reported working bidirectional media on v41.6.5. Subsequent approved changes retain its WebRTC negotiation/track behavior; this is not a new physical-device certification. Windows clean installation, actual cmd/PowerShell execution, native GUI/device media, code signing and final distribution assembly remain pending.

Read INSTALL_WINDOWS.md before upgrade, BUILD_RELEASE.md for exact remaining build steps, and RELEASE_CHECKLIST.md for acceptance. No signed executable/installer is included, no release is published, and production credentials/student data must never enter a source package.
