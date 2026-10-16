# MathStudio v41.6.6 — Pre-release acceptance checklist

**Status:** RELEASE CANDIDATE — not production-verified. This build changes teacher-interface localization, not the established v41.6.5 browser WebRTC implementation. Record actual results; do not mark anything passed without observing it.

**Test setup:** Teacher on Windows; one iPhone student, one Android student; two separate networks (Wi-Fi and cellular); a second Windows user or clean Windows environment; test English and 中文. Do not use real student personal data during the initial test.

## 1. Installation, build consistency and recovery
- [ ] OWNER ZIP extracts into exactly `MathStudio_v41_6_6_OWNER_Release_Candidate/` (no nested outdated folder).
- [ ] TEACHER READY ZIP extracts into exactly `MathStudio_v41_6_6_TEACHER_READY_Release_Candidate/`.
- [ ] The server terminal says `MathStudio v41.6.6 is running on port 5051` and shows the matching build ID.
- [ ] The Teacher App connects to OWNER when OWNER already listens on 5051; it does not create a second server or claim the site is offline.
- [ ] On a separate clean Windows environment, TEACHER READY sets up required dependencies and starts with one launcher.
- [ ] If the port belongs to a different application, show an actionable error; do not stop another process.
- [ ] Restart server and Teacher App; database/accounts/classes/resources persist.
- [ ] Existing TURN credentials load if present; fresh installs can configure TURN without exposing secrets.
- [ ] Downloaded unsigned launchers may show Windows Unknown Publisher / SmartScreen. Do not bypass protections globally; sign a packaged installer before wide distribution.

## 2. Live classroom: camera/audio/network (release blocker)
- [ ] Windows camera and microphone reach iPhone.
- [ ] iPhone camera and microphone reach Windows.
- [ ] Windows camera and microphone reach Android.
- [ ] Android camera and microphone reach Windows.
- [ ] Both cameras and microphones stay active simultaneously; mute/unmute switches work independently.
- [ ] 3 participants (teacher + iPhone + Android) remain connected for 30 minutes, with no audio/video freezing and no `Too many sessions` error.
- [ ] A 60-minute mock lesson runs acceptably with two-way audio/video, screen sharing and chat.
- [ ] Test same Wi-Fi; test iPhone on cellular to validate remote WebRTC/TURN path.
- [ ] Rejoin after leaving; teacher can end class for all; no ghost participants remain.
- [ ] Test device sleep/return, page refresh, Wi-Fi↔cellular change and AirPlay/Bluetooth route change. Video should recover or show a clear rejoin instruction.
- [ ] Watch for high CPU load, disconnected/failed ICE, recurrent offers/answers, and rapidly growing sessions.

## 3. Tutoring and collaboration
- [ ] Instant meeting generates a 10-digit code; teacher enters as host automatically; a guest can join by code.
- [ ] Scheduled and instant meetings use the same full classroom layout and teacher permissions.
- [ ] Screen share from Windows is legible for math notation, drawing, a PDF and slides; screen-share switching/stopping works.
- [ ] Native desktop overlay correctly draws over other windows; interact mode clicks through; erase/undo/clear work.
- [ ] Student drawing is off by default and only works after teacher permits it; student cannot control teacher-only options.
- [ ] Participants appear and disappear accurately with an expected meeting limit of approximately six.
- [ ] Live chat sends with Enter and newlines with Shift+Enter; no duplicated messages after reconnect.
- [ ] Voice echo/mute and screen-sharing permission handling are acceptable.

## 4. Student website and bookings
- [ ] Signup, login, logout, reset/recovery (if present), and guest participation work on desktop and mobile.
- [ ] Teacher availability blocks show correct available 15-minute start increments for 60/90-minute lessons.
- [ ] Pending booking reserves its slot, teacher can confirm/decline, and confirm-weekly works.
- [ ] Late scheduled classes remain available to start until explicitly ended/cancelled.
- [ ] Group sessions have expected 2–5 seats and block overlapping private bookings.
- [ ] My Lessons, booking status, room Join button and dashboard refresh automatically without losing form contents.
- [ ] Resource codes can be generated/revoked; individual and bundle downloads work on PC/iPhone/Android.
- [ ] Persistent messages and lesson/group chats behave correctly across logouts, refreshes and server restarts.
- [ ] Document translation is opt-in per code; originals stay unchanged; the privacy explanation is visible.

## 5. Language and accessibility
- [ ] Switch Teacher Dashboard EN ↔ 中文; dashboard cards, Quick actions, empty states, student website panel and connection status translate.
- [ ] Visit Schedule, Bookings, Students, Groups/Chats, Files/Codes, Meetings and Student Site in Chinese; headings, buttons and relevant statuses translate.
- [ ] Teacher's native desktop annotation toolbar follows the chosen language and can switch independently.
- [ ] Student browser: homepage, login/signup, booking, resources, messages, My Lessons, Join Meeting and classroom translate.
- [ ] Switch back to English: there are no leftover Chinese UI labels, duplicated translated text or broken controls.
- [ ] Dynamic data refresh doesn't revert UI translations; user names, student-generated content and uploaded documents are not silently modified.
- [ ] Phone viewport is readable without clipped primary actions; keyboard/focus and color contrast remain usable.

## 6. Privacy, security and release operations (release blocker)
- [ ] No `media_config.bat`, permanent TURN API token, passwords, payment/API secrets, session cookies or private student databases in either distributed ZIP.
- [ ] Revoke/rotate any secret previously exposed; temporary TURN ICE credentials alone are not the permanent API secret.
- [ ] Teacher-only API endpoints require admin sessions; a guest/student cannot impersonate the teacher, mute other students without permission or access private classes/files.
- [ ] Verify session cookie Secure/HttpOnly/SameSite behavior over HTTPS, CSRF protections, role checks and session expiration/reuse.
- [ ] Verify user messages and uploaded filenames display safely (no stored HTML/JS injection).
- [ ] Rate-limit or otherwise guard authentication, join-code guessing, uploads and guest-session creation.
- [ ] Define backup/restore process and retention/deletion policy for student accounts, chat and class resources.
- [ ] Obtain appropriate privacy/parental consent for student data and audio/video; inform participants what is shared and whether anything is recorded.
- [ ] Use a stable HTTPS domain and supported tunnel arrangement for delivery rather than relying on a changing `trycloudflare.com` test URL.
- [ ] Run a realistic install on the tutor's PC using their credentials, Wi-Fi and peripherals. Explain how to start/stop a server, troubleshoot permissions and recover after a restart.

## Decision
- **GO (limited tutor pilot):** all release-blocking items and core lesson workflows pass; any noncritical limitation is documented.
- **NO-GO:** one-way media, session exhaustion, incorrect teacher permissions, broken login/booking, exposed secrets, data loss, or a teacher package that cannot start on the tutor's PC.
- **Wider public release:** additionally requires security/privacy review, stable hosting, monitoring, reliable backups and code signing.

**Record:** test date __________  teacher device __________  student devices __________  failures __________  reviewer __________
