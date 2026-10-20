# Stop/input repair OWNER review

Read **STOP_INPUT_REVIEW.md** for this candidate's complete recording, restricted Resources sharing, legal draft, guardian, student Remember Me, R2 and rollback instructions.

Extract into a new folder. Production, PR9, PR10 and PR11 review installations/data must remain separate. This candidate uses OWNER **5065**, `%LOCALAPPDATA%\MathStudioOwnerStopInputReview`, its own Quick Tunnel, and the matching **MathStudio-Stop-Input-Review.exe** client with a distinct AppID/profile.

Install/retain x64 Python 3.13. Double-click **REVIEW OWNER SETUP.bat** and select your already installed, ready Argos home. It copies the runtime, packages and verified receipt to the new review state, checks the local copy and performs offline bidirectional self-tests; translation models are neither bundled nor downloaded. Keep the original Python installation used by the copied Windows venv installed. Setup installs only the pinned OWNER dependencies, not new Argos dependencies.

Alternatively, from PowerShell in the extracted folder:

```powershell
py -3.13 .\owner_review.py setup --argos-home 'D:\YourExistingInstalledArgosHome'
py -3.13 .\owner_review.py start
```

For a wheelhouse containing the pinned OWNER wheels:

```powershell
py -3.13 .\owner_review.py setup --argos-home 'D:\YourExistingInstalledArgosHome' --wheelhouse 'D:\TrustedOwnerWheels'
```

Then double-click **REVIEW OWNER START.bat**. Startup refuses reuse of an occupied 5065; it does not stop or reuse the earlier OWNER. Use only synthetic accounts. Enter this review's HTTPS origin in the matching teacher client and use the OWNER's local first-time pairing window. Ctrl+C stops this review and its owned tunnel. No credentials or account database are supplied.

Recording is disabled until OWNER's approved policy is configured. New sharing/local/standing scopes require independently verified guardian evidence plus separate student agreement; draft policies require business-owner and qualified Alberta review before real use. **Seekable absentee playback additionally needs an explicitly selected, trusted FFmpeg on OWNER**; no FFmpeg binary is downloaded/bundled automatically. The detailed guide provides configuration and verification commands. Teacher remains client-only and never needs FFmpeg or Argos.

Do not disable Windows protections. The genuine Windows review build's signature, malware scan and install results are reported with the delivery; unsigned is not signed. Check the supplied SHA256SUMS.txt before extracting/installing. No deployment, merge, DNS/TURN change, paid resource creation or automatic policy/recording publication is authorized.
