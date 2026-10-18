# Executed website integration checks — 2026-10-18 UTC

| Check | Actual result |
| --- | --- |
| Complete existing Python suite, `python -m unittest discover -v` | **111 passed, 0 failed**, 14.920 seconds; includes the eight new public-translation regressions |
| Node browser workflow regressions | **15 passed, 0 failed**; also run through the complete suite |
| Actual Chromium browser acceptance | **65 passed, 0 failed**, no application JavaScript errors; see [browser-results.json](browser-results.json) |
| Python compilation | Passed for changed server/service/test/browser-check Python files |
| JavaScript syntax | Passed for app, classroom, i18n/catalog, public-content, translation manager, teacher page and diagnostic modules |
| Catalog consistency | **841 identical, nonempty EN/ZH keys**; placeholder parity and referenced canonical keys checked |
| Source package manifest | 85 allowlisted OWNER source/evidence files, exact hashes; no runtime data or unlisted files |
| Installer integrity | Existing 15,979,616-byte MathStudio.exe SHA-256 unchanged: `c05b5e9f160d0c9dddb428128dab1ddd3d87527d5fb6ed7e97094f494d8990cc` |

Full suite: Linux CPython 3.12.14, existing pinned Pillow 12.3.0, pypdf 6.20.1 and tzdata 2026.4 (IANA 2026d). No production dependencies were changed. Real browser: Playwright 1.62.0 and Chromium 154.0.8037.57, 1440×1100 viewport. All accounts, files, public descriptions, messages, math and attempted HTML content are synthetic. An initial sandbox restriction on loopback tests was resolved by running the synthetic tests with the required execution permission. Test-development issues were corrected before the reported final runs.

API regressions cover teacher authorization/CSRF, private-source rejection, disabled/explicit opt-in behavior, original preservation, draft/edit/approval separation, publication, persistent cache/restart, stale-source and stale-tab conflicts, concurrent source edit/opt-out, provider failure, protected math/names/URLs, additive course descriptions and native build ID compatibility. Provider calls were mocked; no real external provider was used.

Browser acceptance visits Home, Booking, Login, Signup, Join, Resources, Teacher instructions, My lessons, Messages and Classroom in EN and ZH, plus the teacher translation editor. It exercises EN→ZH→EN without reloading, persistence, polling, localized login errors, typed names/chat drafts, original messages/filenames/resource labels, download retention, an actual joined room with camera/microphone off, accessibility labels, manual translation save/approval, unchanged original, HTML displayed as text, stale translation fallback and a deliberately blocked app module's Chinese startup diagnostic.

The screenshots below were opened and visually inspected; the corrected classroom placeholder and participant status wrapping are visible in the final joined-room image. Public originals intentionally remain unchanged when no approved translation exists. “Home” and “Teacher” are deliberately used as synthetic user content to exercise boundaries. Browser permission errors in prejoin screenshots reflect the headless browser, not a device acceptance result.

- [English home](screenshots/home-en.png) and [Chinese home](screenshots/home-zh.png)
- [English booking](screenshots/booking-en.png) and [Chinese booking](screenshots/booking-zh.png)
- [Chinese login](screenshots/login-zh.png), [teacher instructions](screenshots/teacher-zh.png)
- [Joined classroom, Chinese](screenshots/classroom-joined-zh.png)
- [English approval editor](screenshots/translation-manager-en.png) and [Chinese approval editor](screenshots/translation-manager-zh.png)
- [Chinese startup diagnostic](screenshots/startup-diagnostic-zh.png)

Screenshots are repository review attachments, not part of the OWNER runtime archive. The archive includes this report and the structured browser results.

Not executed: a real translation-provider request, live Cloudflare/TURN connectivity, new Windows installation/signing or physical Windows/iPhone/Android camera/audio/screenshare/annotation acceptance. Prior installer Windows evidence remains in `installer-review/`. OS/browser-native permission/validation dialogs use the OS/browser language. Proper names beyond protected patterns require teacher-supplied terms and review. Technical exception details and user-created titles/names/prices/files/messages remain literal. No claim of universal translation quality or physical-device media acceptance is made.
