# Phase 2B, part 1 — teaching workflows

Based on Phase 2A commit `89fbccd4dedd63952f51e9545b1184e8ffe93883`.
Scope: MEDIA-01, UI-01, UI-02, BOOK-01 and BOOK-02 only.

## Repairs

- Native Video panel requests use their existing scoped app token instead of
  requiring a browser cookie/CSRF token they do not possess. Phase 2A issuer,
  current-role, password-version, class-access and expiry checks still apply.
  Browser handoffs remain single-use; ordinary mutations retain CSRF checks.
- Teacher lesson/group chat uses the API cursor, drains full 300-message pages,
  renders resource-code dictionaries, and keeps one polling timer. Failed polls
  retain existing text and its readonly state; switching conversations resets
  the cursor and clears content from the previous conversation.
- Resource-page background refresh preserves the redeemed download/translation
  DOM. Expiry and revocation remain enforced by every server resource operation.
- Weekly availability, group lessons and weekly booking confirmation preserve
  studio-local start times instead of adding 604,800 seconds. Availability ends
  also preserve their local wall time; lesson duration remains elapsed minutes.
  Existing transaction and overlap/capacity checks remain in place.
- Browser and desktop calendars/inputs use the configured studio timezone.
  Browser scheduling receives compact, cached backend timezone rules to avoid
  differing IANA versions in browser engines (including Vancouver's 2026 rules).
  The supplied rules run from the prior calendar year until January 1 three years ahead,
  encompassing the supported booking/recurrence horizon. Outside that range,
  browser display falls back to the browser's own timezone database.

## Timezone dependency and policy

Install application requirements before running this update:

```text
py -m pip install -r requirements.txt
```

`zoneinfo` is part of supported Python versions; `tzdata` supplies IANA data on
Windows and systems lacking a system database. Unix uses its system database
when available. Keep that database current. Missing data produces an actionable
installation error rather than silently scheduling in the device timezone.

New wall-clock inputs/recurrences reject nonexistent spring-forward times.
Repeated fall-back times choose the earlier occurrence. Existing stored timestamps
are not rewritten; previously shifted bookings need separate owner review.
If any recurrence is invalid or conflicts, the transaction leaves the whole
operation uncommitted. A studio-timezone setting change affects future recurrence
calculations; existing lesson instants remain unchanged.

## Verification and rollback

`test_teaching_workflows.py` reuses the Phase 2A temporary-backend fixture and
executes the actual native HTTP helper and desktop methods with UI doubles.
`test_browser_workflows.mjs` exercises the actual app scheduling/refresh functions
and timezone module under multiple device zones. Its Node checks run from the
Python suite as well as directly with `node test_browser_workflows.mjs`.

Run the complete suite with `python -B -m pytest -q -p no:cacheprovider`.
Final verification: 48 tests and four subtests passed (11.14 seconds), including
all Phase 2A regressions. All five Node checks passed, along with Python
compilation, JavaScript syntax validation and `git diff --check`.
No production database, student information or provider credentials are used.
Physical Windows UI and Windows/iPhone/Android classroom/media acceptance remain
manual requirements. WebRTC negotiation, camera/microphone/screen-share code and
the localization dictionary are unchanged. No release-readiness certification,
merge or deployment is implied.

No schema migration is introduced. Roll back to the matching Phase 2A application
files while the server is stopped, then restart/re-authenticate. Retain a verified
data/resource backup before any deployment. New lessons created by this update
have valid absolute timestamps and are not moved by rollback.
