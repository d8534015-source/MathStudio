MathStudio v38 — Full Teacher Meeting

# MathStudio v36 — Modern Bilingual Teacher + Instant Meetings

## Start

- `START STUDENT WEBSITE.bat` starts the student website/backend on port 5051.
- `START TEACHER APP.bat` starts the desktop teacher application.
- `MathStudioTeacher.exe` is the teacher app launcher.

Keep the website server running while using the Teacher App.

## v36 changes

- Teacher App detects the available screen/window size and scales its sidebar and calendar to fit.
- The weekly teacher calendar keeps all seven days visible without horizontal scrolling.
- Schedule forms moved into separate dialogs so the calendar does not get squeezed vertically.
- Student website uses responsive grids and viewport-based calendar columns.
- Home-page feature labels no longer inherit the old fixed-width number badge styling.
- New **Join meeting** page for 10-digit instant meeting codes.
- Teachers can start an **Instant Meeting** without selecting a scheduled class.
- Instant meetings generate a unique 10-digit numeric share code.
- Students may join instant meetings while signed in or as a guest with only a display name.
- Guest users are not added to the permanent student account list.
- Instant-meeting chat is live-session chat rather than persistent account chat.

## Instant meeting workflow

1. Open Teacher App → Meetings.
2. Click **Start instant meeting**.
3. Enter an optional meeting title.
4. MathStudio copies the 10-digit code to the clipboard and opens the native teacher meeting window.
5. Students open the student website → **Join meeting**, enter the code, and join either with their account or as a guest.

The code remains valid while the meeting is active and is deactivated when the teacher ends or cancels the meeting.

### v36 additions
- Modernized Teacher App booking/actions layout and fixed invisible action-button labels.
- Instant meeting codes are live as soon as the teacher creates them.
- Closing the native Teacher Meeting window ends the classroom and removes it from active classes.
- English / 中文 mode on the student website and Teacher App.
- Resource access codes can opt into automatic English/Chinese document translation. Translation is off by default and uses an online translation service only when the teacher enables it for that code.
- Chat: Enter sends; Shift+Enter inserts a new line in multiline chat boxes.


## v37 direct teacher instant meeting
Creating an Instant Meeting from the Teacher App launches the native host immediately. The camera/audio browser panel uses a one-time admin handoff and goes straight to the classroom; only students use the 10-digit join code.
