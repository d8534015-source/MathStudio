# Cookie Policy — DRAFT
Version: 2026-10-review-1

**OWNER and Alberta privacy/legal review required.** Operator/contact/effective date: [OWNER TO SUPPLY AND APPROVE]. This inventory describes first-party application behavior, not unverified hosting or browser extensions.

## Essential session and security state
`mathstudio_5051` is an HttpOnly, SameSite=Strict session cookie used by this application even when a review server uses another port. Cookies are hostname-based, not port-isolated: keep production and review on distinct HTTPS hostnames/browser profiles. Public HTTPS responses mark it Secure. It normally has no persistent Max-Age; browser session-restoration settings can affect whether a session cookie survives closing. Server-side authenticated sessions roll forward to an eight-hour idle expiry; anonymous sessions have shorter bounded lifetimes. Closing a browser is not a substitute for Sign Out. CSRF tokens are server-side session values delivered in JSON and sent in request headers; there is no separate first-party CSRF cookie. Resource/playback grants are authenticated, short-lived server-side authorizations, not public storage links.

## Optional student Remember Me
`mathstudio_student_remember` is issued only after an explicit, initially unchecked choice at student login. It is Secure, HttpOnly, SameSite=Strict, Path=/, with no Domain attribute. It holds a random selector/secret; OWNER stores only a secret verifier, account/password binding, idle and absolute expirations. It rotates on restoration, expires after at most 30 days absolute or seven days idle, and is revoked by Sign Out, password/role/security changes or replay detection. Server revocation can make a still-visible cookie unusable. Never choose Remember Me on a public/shared device. No password or long-lived authentication token is stored in localStorage. Browser settings may clear/prevent persistent cookies; if so, sign in again.

## Preferences and the separate teacher app
`mathstudio_lang` in localStorage preserves English/Chinese preference until cleared. The application also uses temporary in-memory page/session state for classroom controls; this is not advertising tracking. The Windows teacher app's optional persistent credentials use Windows DPAPI and its own server-side credential family, not the student website Remember Me cookie.

## Tracking, choices and changes
This application introduces no analytics or advertising cookies. Cloudflare/hosting security controls can vary with deployment; OWNER must verify and disclose any additional deployed cookies before publication. Browser extensions and external sites are outside this inventory. A blanket tracking-consent banner has not been introduced for these essential/explicitly requested functions. Whether any additional consent is legally required must be reviewed for the actual deployment.

Sign Out revokes the current persistent credential and clears its cookie; password/security changes invalidate affected remembered sessions. Clearing cookies removes browser login state but does not itself delete an account, enrollment, recording or server audit record. Clearing localStorage resets language preference. Policy versions and acknowledgment timestamps are retained server-side; these acknowledgments do not grant optional recording authorization. Questions: [OWNER TO SUPPLY privacy contact].
