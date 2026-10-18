# Website integration review — MathStudio 41.6.6

## Baseline and compatibility

Branch: `codex/website-integration-v4166`, based on `58590f9903dc7fca01b759e6f764c703a7f4d40f` (combined Windows installer delivery, draft PR #6). Verified ancestry includes Phase 2A `89fbccd`, Phase 2B part 1 `157d21c`, part 2 `1857869`, Phase 2C `b8fc294`, delivery `2249e4c`, and WIN-01–06 source `b76e32c`. Main is unchanged. This PR is based on `codex/windows-installer-v4166`; nothing was merged or deployed.

The existing `installer-review/MathStudio.exe` is preserved byte-for-byte (15,979,616 bytes), SHA-256 `c05b5e9f160d0c9dddb428128dab1ddd3d87527d5fb6ed7e97094f494d8990cc`. No installer rebuild is necessary: teacher payload sources are unchanged, the existing native APIs remain compatible, and `version.json` / desktop build ID remain `v41.6.6-delivery-candidate1`. Server/static responses use `Cache-Control: no-store`. The refreshed OWNER source package includes the new server module and website modules; Teacher Ready remains a client of the separately hosted OWNER backend.

## Confirmed defects addressed

- The website previously used overlapping translation mappings and an unrestricted DOM text walker. It missed mixed booking descriptions and could not reliably bind dynamic text to a canonical key. Localization now touches only marked UI elements/attributes or explicit UI calls. EN/ZH catalogs have 841 identical nonempty keys and checked placeholder parity. UI labels, loading/empty states, dialogs, server errors and accessibility attributes are keyed; English/Chinese switching persists and updates existing forms and active classrooms without reloading the document or replacing message/resource state.
- Booking seat counts, duration labels and request confirmations now use keyed templates with original course/title values kept separate. Calendar dates rerender in the selected language using the existing studio timezone rules.
- Teacher landing instructions referenced source BAT setup despite the verified installer. They now describe MathStudio.exe, Start menu/desktop launch, the separate OWNER and first-run HTTPS configuration, with a link to the protected public-content editor.
- Public descriptions previously had no persistent translation/approval path. The new opt-in provider adapters and teacher editor store drafts/approvals separately, enforce public-source isolation, preserve protected text, reject stale edits/results and show approved translations or visible original fallback. See [PUBLIC_TRANSLATION_SETUP.md](PUBLIC_TRANSLATION_SETUP.md).

No unrelated functional defect was reopened. RTC offer/answer, transceiver, ICE restart, track attachment/replacement, native media and annotation permission/board conflict algorithms are preserved. Classroom changes are UI text/bindings and a language-event UI refresh; this is not proof of physical-device media acceptance.

## Changed files

| Files | Purpose |
| --- | --- |
| `app.js`, `classroom.js` | Keyed visible UI; live switch; separately escaped public descriptions; room state retained |
| `locales.js`, `web_i18n.js` | Canonical EN/ZH catalogs and scoped localization engine |
| `public_translations.py`, `server.py` | Additive database migration, allowlisted public sources, adapters, cache, draft/approval APIs, static routes |
| `public_content.js`, `translation_manager.js` | Approved-content rendering, visible fallback and protected teacher editor |
| `teacher.html`, `teacher_page.js`, `index.html`, `diagnostics.js`, `style.css` | Installer instructions, localization startup labels and translation-editor presentation |
| `test_public_translations.py`, `test_browser_workflows.mjs`, `verify_website_browser.py` | Synthetic API, scoped localization and real Chromium regressions |
| `PUBLIC_TRANSLATION_SETUP.md`, `WEBSITE_INTEGRATION.md`, `README - OWNER.txt` | Provider setup, evidence, limitations and correct OWNER/installer roles |
| `release_manifest.json` | Updated allowlist and source hashes; unchanged runtime versions/dependencies |
| `website-review/` | Synthetic screenshots, check results, updated OWNER ZIP and SHA-256 list |

## Reproduce checks

Use the existing pinned `requirements.txt` in an isolated CPython environment. Run focused tests while editing:

```
python -m unittest test_public_translations -v
node test_browser_workflows.mjs
```

Run the full existing suite once after changes:

```
python -m unittest discover -v
```

Optional real-browser acceptance requires a separate test-only environment with `playwright==1.62.0` and Chromium. This delivery used system Chromium `154.0.8037.57` on Linux. Do not add browser tooling to the teacher application's production dependencies:

```
python verify_website_browser.py --chromium /path/to/chromium --output /temporary/synthetic-screenshots
```

The script creates isolated synthetic accounts/data, never reads the production database or provider credentials, and tests rendered routes, persistent/live EN→ZH→EN, errors, input/message preservation, resource/download retention, room continuity, public draft approval, original preservation, stale invalidation and XSS escaping. Screenshot content uses synthetic public descriptions/names. Review `website-review/TEST_RESULTS.md` for actual executed outcomes; these commands alone are not claims of success.

## Upgrade and rollback

Finish classes and stop the OWNER/tunnel cleanly before upgrading. Make a private backup of the existing OWNER data directory and configuration outside any delivery folder. Extract the new OWNER source archive into a clean directory; reuse the explicitly selected existing private data/configuration through the supported paths. Never ship that data, run two server builds against it or place private files into a package. Follow INSTALL_WINDOWS.md for pinned dependency setup, then `START STUDENT WEBSITE.bat` for OWNER hosting. The teacher keeps the existing MathStudio.exe installation and configured OWNER HTTPS address. No Windows security protection should be disabled.

Migrations add two translation tables and a default-empty course description column; they do not rewrite existing originals, accounts, bookings or media state. For rollback, stop this OWNER and restore the previous source tree (including all pre-existing approved repairs). Existing code ignores the extra tables/column. Keep the private backup for recovery; if restoring it, account for all changes made after its creation. Do not remove or reset the working teacher installation.

## Remaining acceptance

- No real provider request was executed; configure and explicitly opt in only after authorized public test text succeeds.
- Proper-name protection needs teacher-supplied terms and human review; it is not a universal named-entity detector. Original course names/titles/prices and technical diagnostics are intentionally preserved.
- Real Windows installation/Search/shortcuts/reboot and live native handoff were not rerun in Linux. The existing installer has prior Windows Server 2025 build/smoke evidence; Windows 11 and signing remain pending.
- Physical Windows/iPhone/Android camera/audio, simultaneous bidirectional media, AirPlay/sleep, screen share/annotations, permission prompts and network/TURN recovery require manual acceptance on the actual deployment. Joining a loopback room or passing tests is insufficient.
- Complete the real OWNER HTTPS/TURN setup and run authorized teacher login, guest join, booking/recurrence/timezone, messaging/download, native/browser annotations and server/tunnel shutdown checks. This task does not deploy, merge, publish, sign the executable or disable OS protections.
