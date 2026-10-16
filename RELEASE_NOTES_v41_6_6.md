# MathStudio v41.6.6 — Release candidate

Built from the v41.6.5 WebRTC transceiver fix that the user tested on PC, iPhone and Android.
This update focuses on Chinese localization of the native Teacher desktop interface.

Improvements:
- Dashboard cards, quick actions, empty states, student-portal panel and connection statuses translated.
- All seven other teacher app views have expanded headings, controls, table labels and statuses in Chinese.
- Calendar weekday, availability labels, and date/time formatting adapted in Chinese mode.
- Native Windows meeting / annotation toolbar shares the language preference and has its own language switch.
- Language preference persists across teacher app restarts (APPDATA\MathStudio\teacher_ui_preferences.json, language only).
- Both packages report build v41.6.6-release-candidate on port 5051 and use version-matched folders.
- Browser WebRTC source code is unchanged from working v41.6.5 (no media regression intended).

How to run:
1. Back up your currently working v41.6.5 OWNER database/resources.
2. Stop old servers and teacher windows; extract both packages to separate folders.
3. Start OWNER/START STUDENT WEBSITE.bat. Check the terminal build label.
4. Run TEACHER READY/OPEN MATHSTUDIO TEACHER.bat. It should reuse the OWNER server.
5. Test 中文/EN; open an instant class and test two-way media again.

Do not distribute TURN secrets, private student data, or real credentials.
Unknown Publisher prompts on Windows may remain until a digitally signed installer is created.
Temporary trycloudflare.com URLs are for development, not permanent published links.

**Not production-certified**: static checks and tests cannot substitute for a real 30–60 minute classroom and clean Windows install.
See RELEASE_CHECKLIST.md before sending the project to the teacher.
