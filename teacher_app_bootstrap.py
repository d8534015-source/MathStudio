"""Reliable Windows bootstrap for the MathStudio Teacher App.

Starts teacher_meeting_app.py without hiding startup failures. If the child exits
quickly, the traceback is written to teacher_app_error.log and shown in a native
Windows message box so a double-click can never fail silently.
"""
from __future__ import annotations

import argparse
import ctypes
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
LOG = ROOT / "teacher_app_error.log"
APP = ROOT / "teacher_meeting_app.py"


def message(title: str, body: str, flags: int = 0x10) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(None, body, title, flags)
    except Exception:
        pass


def parse_args():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--server", default="http://127.0.0.1:5051")
    p.add_argument("--token", default="")
    p.add_argument("--public-origin", default="")
    p.add_argument("--skip-auto-media", action="store_true")
    return p.parse_args()


def main() -> int:
    if sys.platform != "win32":
        print("MathStudio Teacher App currently supports Windows only.")
        return 2

    args = parse_args()
    # Native desktop screen sharing uses Pillow for efficient JPEG capture.
    # Install it once automatically so the teacher does not have to manage
    # Python packages by hand.
    try:
        import PIL  # noqa: F401
    except Exception:
        try:
            subprocess.run([sys.executable,"-m","pip","install","--disable-pip-version-check","--quiet","Pillow>=10"],
                           cwd=str(ROOT),timeout=180,check=True,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        except Exception as ex:
            message("MathStudio Teacher App setup",
                    "Could not install the screen-sharing component (Pillow).\n\n"+str(ex)+
                    "\n\nCamera/microphone can still use the video panel, but native screen sharing will be unavailable.")
    # If this bootstrap itself is running through pythonw.exe, prefer the paired
    # pythonw child so no console flashes. Otherwise python.exe is fine.
    exe = Path(sys.executable)
    if exe.name.lower() == "python.exe":
        candidate = exe.with_name("pythonw.exe")
        child_python = candidate if candidate.exists() else exe
    else:
        child_python = exe

    cmd = [str(child_python), str(APP), "--server", args.server]
    if args.token:
        cmd += ["--token", args.token]
    if args.public_origin:
        cmd += ["--public-origin", args.public_origin]
    if args.skip_auto_media:
        cmd += ["--skip-auto-media"]

    try:
        LOG.write_text(
            "MathStudio Teacher App startup log\n"
            f"Python: {child_python}\n"
            f"Server: {args.server}\n"
            f"Token supplied: {'yes' if args.token else 'no'}\n\n",
            encoding="utf-8",
        )
        with LOG.open("a", encoding="utf-8") as log:
            proc = subprocess.Popen(
                cmd,
                cwd=str(ROOT),
                stdout=log,
                stderr=log,
                close_fds=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                if child_python.name.lower() == "pythonw.exe" else 0,
            )
        # Most import/Tk startup failures happen immediately. Give them time to
        # surface before declaring the launch successful.
        for _ in range(16):
            time.sleep(0.125)
            rc = proc.poll()
            if rc is not None:
                break
        else:
            return 0

        if rc == 0:
            return 0
        try:
            details = LOG.read_text(encoding="utf-8", errors="replace")[-5000:]
        except Exception:
            details = f"Teacher app exited with code {rc}."
        message(
            "MathStudio Teacher App could not start",
            "The Teacher App closed during startup.\n\n"
            + details
            + "\n\nA copy of this error is saved as teacher_app_error.log.",
        )
        return int(rc or 1)
    except Exception as ex:
        text = f"Could not launch the Teacher App:\n\n{type(ex).__name__}: {ex}"
        try:
            LOG.write_text(text, encoding="utf-8")
        except Exception:
            pass
        message("MathStudio Teacher App could not start", text)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
