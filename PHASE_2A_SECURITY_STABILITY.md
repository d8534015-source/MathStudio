# Phase 2A: security and stability

Scope: SEC-01, SEC-02, SEC-03, SEC-04, SES-01, REL-01 and PERF-01 only.
Baseline: `d0c53c78771ed0a49cdc77c7661b3b19f8f37e82` (v41.6.6).

## Behavior changes

- `/api/classes` exposes the upcoming public group catalog, the signed-in
  student's bookings, and instant meetings admitted to the current session.
  Administrators retain full visibility. Public records exclude ownership and
  internal series/chat identifiers; booked group members retain their chat link.
- Generic participant signaling accepts descriptions, candidates, renegotiation
  and camera-retry controls. Host mute events originate only from the authorized
  moderation endpoint. Browser media negotiation code is unchanged.
- Native and overlay tokens are bound to their issuing session, current role,
  current password version and class access. Logout/rotation revokes tokens from
  that session; role changes revoke that account's tokens. Password changes and
  expired sessions invalidate their tokens on use. Tokens have absolute existing
  lifetimes (12 hours native, 4 hours overlay, 90 seconds one-use handoff).
  Authorized same-browser handoff transfers the issuing token bindings when its
  cookie rotates. Logout remains per session; it does not sign out all devices.
- Anonymous sessions are created only by GET `/api/me`. Static/public/health,
  invalid-path and independently token-authorized native requests do not create
  anonymous sessions. Cookie reuse, CSRF bootstrap, login rotation and guests
  remain supported. Expired sessions and idle anonymous capacity are reclaimed;
  authenticated and guest sessions are not evicted to admit new anonymous users.
- Failed port binding leaves live-class flags unchanged. Successful startup
  retains the existing stale-live-state reset.
- TURN provider failures are cached for 60 seconds. Provider lookup is outside
  the global room/session lock, and joining rechecks authorization/class state
  afterward. Existing successful-cache lifetime and ICE response format remain.

## Proxy configuration and rate limits

Default: forwarded addresses are ignored. `MATH_TRUSTED_PROXIES` is an optional
comma-separated list of trusted connector IPs/CIDRs. Only a direct peer in that
list may supply a valid single `CF-Connecting-IP`; `X-Forwarded-For` is ignored.
Do not trust client/LAN address ranges or arbitrary public proxies. Local
processes on a trusted connector host are part of that trust boundary.

`start_https.ps1` owns the local cloudflared process and sets this value to
`127.0.0.1/32,::1/128`. Other deployment methods must configure their actual
connector addresses explicitly. A request lacking a valid forwarded address
uses its TCP peer address, so unconfigured tunnels share a client budget.

| Operation | Fixed-window budgets |
|---|---|
| Login/signup | 10/account, 60/client, 600/global per 5 minutes |
| Signup additionally | 10/client per 5 minutes |
| Resource-code redemption | 30/client, 600/global per 5 minutes |
| Meeting-code info/join | 30/client, 300/global per minute |
| New anonymous session | 30/client, 300/global per minute |

A successful login clears only that account's budget, preserving client/global
and other-account history. Limits return HTTP 429. Anonymous capacity is 500
within the existing 3,000 total-session cap. Established sessions continue to
work at admission limits; a completely full protected pool still rejects new
sessions. These small-studio defaults need monitoring before larger deployments.

## Verification and limits

Run `python -B -m unittest discover -v` or
`python -B -m pytest -q -p no:cacheprovider`. The existing suite and new
`test_security_stability.py` use temporary databases and synthetic accounts.
The new tests include privacy/admission, valid media message shapes, moderation,
token revocation/handoff, guest drawing, proxy trust/throttling, session pressure,
native JPEG requests, duplicate startup, mocked TURN cooldown and concurrent
request responsiveness. They never call a live TURN provider.

No browser media or localization source was changed. Physical Windows/iPhone/
Android media tests and Windows PowerShell launcher execution remain manual
acceptance requirements. Other audit findings, including the separate native
Video panel CSRF caller mismatch, localization gaps and scheduling bugs, remain
outside Phase 2A. This patch does not make the overall release production-ready.

## Rollback

No schema migration or dependency change is introduced. Before deployment,
back up and verify the database/resources and retain the matching application
package. To roll back, restore the previous application files (including the
HTTPS launcher) while the server is stopped, then restart and reauthenticate.
In-memory sessions/tokens are intentionally lost on restart. The existing
`attempts` table contains only expiring rate-limit counters; no student records
are rewritten by these changes. No deployment, merge or Phase 2B is authorized.
