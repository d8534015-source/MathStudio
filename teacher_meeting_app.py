"""MathStudio Teacher Meeting App (Windows, standard library only).

Launched automatically by the local MathStudio server when an admin starts a class.
The native transparent overlay is intentionally separate from the browser so teacher
and student annotations remain visible over PowerPoint, PDFs, Chrome, or other apps.
"""
from __future__ import annotations

import argparse
import ctypes
import io
import queue
import shutil
import subprocess
from ctypes import wintypes
import json
import math
import os
import sys
import threading
import time
import tkinter as tk
from teacher_localization import translate as translate_ui, read_language, save_language
from tkinter import messagebox, simpledialog
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
import uuid
import webbrowser

if sys.platform != "win32":
    raise SystemExit("MathStudio Teacher Meeting App currently supports Windows only.")

APP_NAME = "MathStudio Teacher Meeting"
TRANSPARENT = "#010203"
POLL_MS = 350
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
LWA_COLORKEY = 0x00000001
GA_ROOT = 2
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
HWND_TOPMOST = -1
SM_CXSCREEN = 0
SM_CYSCREEN = 1
user32 = ctypes.windll.user32
# Explicit Win32 signatures are important on 64-bit Python.  Without them,
# ctypes may treat HWND values as 32-bit integers and target the wrong window.
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND
user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowLongW.restype = wintypes.LONG
user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.LONG]
user32.SetWindowLongW.restype = wintypes.LONG
user32.SetLayeredWindowAttributes.argtypes = [wintypes.HWND, wintypes.DWORD, wintypes.BYTE, wintypes.DWORD]
user32.SetLayeredWindowAttributes.restype = wintypes.BOOL


def http_json(url: str, method: str = "GET", payload=None, timeout: float = 8.0):
    data = None
    headers = {"Accept": "application/json", "User-Agent": "MathStudio-Teacher-App/26"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except HTTPError as ex:
        try:
            body = json.loads(ex.read().decode("utf-8", "replace"))
            msg = body.get("error") or str(ex)
        except Exception:
            msg = str(ex)
        raise RuntimeError(msg) from ex
    except URLError as ex:
        raise RuntimeError(f"Could not reach MathStudio: {ex.reason}") from ex


def http_bytes_post(url: str, token: str, payload: bytes, timeout: float = 5.0):
    req = Request(url, data=payload, headers={
        "Content-Type": "image/jpeg", "X-Teacher-Token": token,
        "User-Agent": "MathStudio-Teacher-App/27"
    }, method="POST")
    try:
        with urlopen(req, timeout=timeout) as response:
            raw=response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except HTTPError as ex:
        try: msg=json.loads(ex.read().decode("utf-8","replace")).get("error") or str(ex)
        except Exception: msg=str(ex)
        raise RuntimeError(msg) from ex
    except URLError as ex:
        raise RuntimeError(f"Could not reach MathStudio: {ex.reason}") from ex


class TeacherMeetingApp:
    BG = "#0f1720"
    PANEL = "#16212c"
    PANEL_2 = "#1d2b37"
    TEXT = "#f4f7f8"
    MUTED = "#a9bac2"
    ACCENT = "#22a699"
    ACCENT_DARK = "#157d74"
    DANGER = "#c84242"
    BORDER = "#2c3e49"

    def __init__(self, server: str, token: str, public_origin: str = "", auto_media: bool = True):
        self.server = server.rstrip("/")
        self.public_origin = (public_origin or server).rstrip("/")
        self.token = token
        self.class_id = 0
        self.title = "MathStudio meeting"
        self.connected = False
        self.closed = False
        self.polling = False
        self.saving = False
        self.board = {"background": "blank", "shapes": []}
        self.version = 0
        self.tool = "pen"
        self.color = "#e53935"
        self.width = 4
        self.draft = None
        self.my_shapes: list[str] = []
        self.draw_mode = False
        self.ink_visible = True
        self.students_can_draw = False
        self.attendees = []
        self.connected_people = []
        self.input_overlay = None
        self.input_canvas = None
        self.share_overlay = None
        self.share_canvas = None
        self.screen_sharing = False
        self.screen_stop = threading.Event()
        self.media_helper_started = False
        self.media_command_busy = False
        self.auto_media = bool(auto_media)
        self.lang = read_language()

        # Use the Tk root itself as the visible teacher control window.  The old
        # build hid the root and put the controls in a Toplevel; on some Windows
        # systems that window was difficult to find and could disappear behind
        # the full-screen annotation overlay.  A real root window gets a normal
        # taskbar/Alt+Tab entry and is much more reliable.
        self.root = tk.Tk()
        self.toolbar = self.root
        self.toolbar.title(APP_NAME)
        self.toolbar.configure(bg=self.BG)
        self.toolbar.attributes("-topmost", True)
        self.toolbar.protocol("WM_DELETE_WINDOW", self.on_close)
        self.toolbar.geometry("1260x176+24+24")
        self.toolbar.minsize(1040, 160)
        self.toolbar.bind("<Escape>", lambda _e: self.set_mode(False))
        self.toolbar.bind("<Control-z>", lambda _e: self.undo())
        # Bring the app to the foreground after Windows has created the native
        # window, and repeat after the overlay is created.
        self.toolbar.after(120, self.bring_toolbar_forward)

        self.overlay = None
        self.canvas = None
        self.tool_buttons = {}
        self.color_buttons = {}
        self.width_buttons = {}
        self.status_var = self._LocalizedVar(self.root, self, "Connecting to classroom…")
        self.people_var = self._LocalizedVar(self.root, self, "Students: loading…")
        self.mode_var = self._LocalizedVar(self.root, self, "Interact")
        self.student_var = self._LocalizedVar(self.root, self, "Students: view only")
        self.build_toolbar()
        self.apply_toolbar_language()
        self.connect()

    # ---------- UI ----------
    class _LocalizedVar(tk.StringVar):
        def __init__(self, master, owner, value):
            self.owner=owner
            self.original=str(value)
            super().__init__(master=master, value=owner.tr(self.original))

        def set(self, value):
            self.original=str(value)
            super().set(self.owner.tr(self.original))

        def refresh(self):
            super().set(self.owner.tr(self.original))

    def tr(self, text):
        return translate_ui(text, self.lang)

    def make_button(self, parent, text, command, *, bg=None, fg=None, padx=12, width=None):
        btn = tk.Button(
            parent, text=self.tr(text), command=command, bg=bg or self.PANEL_2, fg=fg or self.TEXT,
            activebackground=self.ACCENT_DARK, activeforeground="white", relief="flat",
            bd=0, padx=padx, pady=7, width=width, cursor="hand2", highlightthickness=0,
            font=("Segoe UI", 9, "bold")
        )
        btn._mathstudio_en_text = text
        return btn

    def set_button_label(self, widget, text):
        widget._mathstudio_en_text = text
        widget.configure(text=self.tr(text))

    def apply_toolbar_language(self, widget=None):
        widget = widget or self.toolbar
        try:
            source = getattr(widget, '_mathstudio_en_text', None)
            if source is None and isinstance(widget, tk.Label):
                if not widget.cget('textvariable'):
                    source = widget.cget('text')
                    widget._mathstudio_en_text = source
            if source is not None:
                widget.configure(text=self.tr(source))
        except (AttributeError, tk.TclError):
            pass
        try:
            for child in widget.winfo_children():
                self.apply_toolbar_language(child)
        except (AttributeError, tk.TclError):
            pass

    def toggle_language(self):
        self.lang = 'zh' if self.lang == 'en' else 'en'
        save_language(self.lang)
        self.apply_toolbar_language()
        for var in (self.status_var, self.people_var, self.mode_var, self.student_var):
            var.refresh()
        self.refresh_button_states()
        self.refresh_people()
        self.lang_button.configure(text='EN' if self.lang == 'zh' else '中文')

    def build_toolbar(self):
        top = tk.Frame(self.toolbar, bg=self.BG, padx=14, pady=10)
        top.pack(fill="x")
        left = tk.Frame(top, bg=self.BG)
        left.pack(side="left", fill="x", expand=True)
        self.title_label = tk.Label(left, text="Teacher meeting", bg=self.BG, fg=self.TEXT,
                                    font=("Segoe UI", 14, "bold"), anchor="w")
        self.title_label.pack(anchor="w")
        tk.Label(left, textvariable=self.status_var, bg=self.BG, fg=self.MUTED,
                 font=("Segoe UI", 9), anchor="w").pack(anchor="w", pady=(2, 0))
        right = tk.Frame(top, bg=self.BG)
        right.pack(side="right")
        self.mic_btn = self.make_button(right, "Unmute", lambda: self.send_media_command("mic-toggle"), bg="#25445a")
        self.mic_btn.pack(side="left", padx=3)
        self.camera_btn = self.make_button(right, "Start camera", lambda: self.send_media_command("camera-toggle"), bg="#25445a")
        self.camera_btn.pack(side="left", padx=3)
        self.share_btn = self.make_button(right, "Share screen", self.toggle_native_screen_share, bg="#25445a")
        self.share_btn.pack(side="left", padx=3)
        self.media_btn = self.make_button(right, "Video panel", self.open_media, bg="#31505f")
        self.media_btn.pack(side="left", padx=3)
        self.end_btn = self.make_button(right, "End class", self.end_class, bg=self.DANGER)
        self.end_btn.pack(side="left", padx=4)
        self.close_btn = self.make_button(right, "Close app", self.on_close)
        self.close_btn.pack(side="left", padx=4)
        self.lang_button = self.make_button(right, 'EN' if self.lang == 'zh' else '中文', self.toggle_language, padx=7)
        self.lang_button.pack(side='left', padx=3)

        row = tk.Frame(self.toolbar, bg=self.PANEL, padx=12, pady=9, highlightbackground=self.BORDER,
                       highlightthickness=1)
        row.pack(fill="x", padx=12, pady=(0, 8))

        mode_box = tk.Frame(row, bg=self.PANEL)
        mode_box.pack(side="left", padx=(0, 12))
        self.mode_btn = self.make_button(mode_box, "Interact", self.toggle_mode, bg="#31505f", width=10)
        self.mode_btn.pack(side="left")
        self.student_btn = self.make_button(mode_box, "Students: view only", self.toggle_student_drawing,
                                            bg="#384650", width=18)
        self.student_btn.pack(side="left", padx=(6, 0))

        divider = tk.Frame(row, width=1, height=34, bg=self.BORDER)
        divider.pack(side="left", padx=10)

        tools = [("pen", "Pen"), ("line", "Line"), ("rect", "Rectangle"),
                 ("circle", "Circle"), ("text", "Text"), ("eraser", "Eraser")]
        for key, label in tools:
            btn = self.make_button(row, label, lambda k=key: self.select_tool(k), width=8)
            btn.pack(side="left", padx=2)
            self.tool_buttons[key] = btn

        divider2 = tk.Frame(row, width=1, height=34, bg=self.BORDER)
        divider2.pack(side="left", padx=10)

        for color in ("#e53935", "#1565c0", "#09695f", "#6a1b9a", "#111111", "#f9a825"):
            btn = tk.Button(row, bg=color, activebackground=color, width=2, height=1, relief="flat",
                            bd=0, cursor="hand2", command=lambda c=color: self.select_color(c),
                            highlightthickness=2, highlightbackground=self.PANEL, highlightcolor=self.TEXT)
            btn.pack(side="left", padx=2, pady=3)
            self.color_buttons[color] = btn

        for size, label in ((2, "S"), (4, "M"), (8, "L")):
            btn = self.make_button(row, label, lambda n=size: self.select_width(n), padx=8, width=2)
            btn.pack(side="left", padx=2)
            self.width_buttons[size] = btn

        divider3 = tk.Frame(row, width=1, height=34, bg=self.BORDER)
        divider3.pack(side="left", padx=10)
        self.make_button(row, "Undo", self.undo, width=6).pack(side="left", padx=2)
        self.make_button(row, "Clear", self.clear_all, bg="#5c3f42", width=6).pack(side="left", padx=2)
        self.ink_btn = self.make_button(row, "Hide ink", self.toggle_ink, width=7)
        self.ink_btn.pack(side="left", padx=2)

        footer = tk.Frame(self.toolbar, bg=self.BG, padx=14)
        footer.pack(fill="x")
        tk.Label(footer, textvariable=self.people_var, bg=self.BG, fg=self.MUTED,
                 font=("Segoe UI", 9)).pack(side="left")
        tk.Label(footer, text="Interact = click through to apps · Draw = annotate desktop · Esc returns to Interact",
                 bg=self.BG, fg="#7f959e", font=("Segoe UI", 8)).pack(side="right")
        self.refresh_button_states()

    def bring_toolbar_forward(self):
        try:
            self.toolbar.deiconify()
            self.toolbar.attributes("-topmost", True)
            self.toolbar.lift()
            self.toolbar.focus_force()
            # Drop and restore topmost once so Windows gives the control window
            # its own foreground/taskbar presence rather than burying it below
            # the transparent overlay.
            self.toolbar.after(250, lambda: self.toolbar.attributes("-topmost", True))
        except Exception:
            pass

    def refresh_button_states(self):
        self.set_button_label(self.mode_btn, "Draw on desktop" if not self.draw_mode else "Interact with apps")
        self.mode_btn.configure(bg=self.ACCENT if self.draw_mode else "#31505f")
        self.set_button_label(self.student_btn, "Students: can draw" if self.students_can_draw else "Students: view only")
        self.student_btn.configure(bg=self.ACCENT_DARK if self.students_can_draw else "#384650")
        for key, btn in self.tool_buttons.items():
            btn.configure(bg=self.ACCENT_DARK if key == self.tool else self.PANEL_2)
        for color, btn in self.color_buttons.items():
            btn.configure(relief="sunken" if color == self.color else "flat")
        for size, btn in self.width_buttons.items():
            btn.configure(bg=self.ACCENT_DARK if size == self.width else self.PANEL_2)
        self.set_button_label(self.ink_btn, "Show ink" if not self.ink_visible else "Hide ink")

    # ---------- Connection ----------
    def connect(self):
        try:
            state = http_json(self.server + "/api/teacher-app/state?" + urlencode({"token": self.token}))
        except Exception as ex:
            messagebox.showerror(APP_NAME, f"Could not open the teacher meeting app.\n\n{ex}", parent=self.toolbar)
            self.closed = True
            self.root.after(50, self.root.destroy)
            return
        cl = state.get("class") or {}
        self.class_id = int(cl.get("id") or 0)
        self.title = cl.get("title") or "MathStudio meeting"
        self.title_label.configure(text=self.title)
        self.connected = bool(cl.get("live"))
        self.board = state.get("board") or {"background": "blank", "shapes": []}
        self.version = int(state.get("version") or 0)
        self.students_can_draw = bool(state.get("drawing"))
        self.attendees = state.get("attendees") or []
        self.connected_people = state.get("connected") or []
        self.status_var.set("Live classroom open · native desktop annotations active")
        self.refresh_people()
        self.open_overlay()
        self.open_input_capture()
        self.set_mode(False)
        self.redraw()
        if self.auto_media:
            self.root.after(650, self.launch_media_helper)
        self.schedule_poll()

    def state_url(self):
        return self.server + "/api/teacher-app/state?" + urlencode({"token": self.token})

    def refresh_people(self):
        online = [p for p in self.connected_people if p.get("role") != "admin"]
        booked = len(self.attendees)
        names = ", ".join(p.get("name", "Student") for p in online[:4])
        extra = f" +{len(online)-4}" if len(online) > 4 else ""
        self.people_var.set(f"Booked students: {booked} · Online now: {len(online)}" + (f" · {names}{extra}" if names else ""))
        teacher_peer=next((p for p in self.connected_people if p.get("role")=="admin"),None)
        if hasattr(self,"mic_btn"):
            self.set_button_label(self.mic_btn, "Mute" if teacher_peer and teacher_peer.get("mic_on") else "Unmute")
            self.mic_btn.configure(bg=self.ACCENT_DARK if teacher_peer and teacher_peer.get("mic_on") else "#25445a")
            self.set_button_label(self.camera_btn, "Stop camera" if teacher_peer and teacher_peer.get("camera_on") else "Start camera")
            self.camera_btn.configure(bg=self.ACCENT_DARK if teacher_peer and teacher_peer.get("camera_on") else "#25445a")
        if hasattr(self,"share_btn"):
            self.set_button_label(self.share_btn, "Stop sharing" if self.screen_sharing else "Share screen")
            self.share_btn.configure(bg=self.DANGER if self.screen_sharing else "#25445a")

    # ---------- Overlay ----------
    def overlay_hwnd(self):
        """Return the real top-level HWND for the Tk overlay.

        Tk can expose an inner child HWND through winfo_id().  Layered-window and
        click-through styles must be applied to the Windows root HWND or some
        Windows 11/Tk builds render the transparent area as opaque black.
        """
        if not self.overlay:
            return 0
        self.overlay.update_idletasks()
        child = int(self.overlay.winfo_id())
        root = int(user32.GetAncestor(child, GA_ROOT) or 0)
        return root or child

    @staticmethod
    def _colorref(hex_color: str) -> int:
        value = hex_color.lstrip("#")
        r, g, b = int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
        return r | (g << 8) | (b << 16)

    def apply_overlay_transparency(self):
        """Force Windows color-key transparency on the actual overlay HWND."""
        if not self.overlay:
            return
        self.overlay.update_idletasks()
        hwnd = self.overlay_hwnd()
        if not hwnd:
            return
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style |= WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
        # The visible ink surface is always click-through. Draw-mode input is
        # captured by a separate nearly-invisible input window, which avoids the
        # Windows layered-window hit-testing bug on transparent pixels.
        style |= WS_EX_TRANSPARENT
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        # Tk's -transparentcolor works on many systems, but call the Win32 API
        # directly too so Python/Tk version differences cannot leave a black
        # layered surface behind.  The transparent key is a near-black color
        # that the annotation tools never use.
        ok = user32.SetLayeredWindowAttributes(
            hwnd, self._colorref(TRANSPARENT), 255, LWA_COLORKEY
        )
        if not ok:
            err = ctypes.get_last_error()
            self.status_var.set(f"Overlay transparency warning (Windows error {err})")
        user32.SetWindowPos(
            hwnd, HWND_TOPMOST, 0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
        )

    def open_overlay(self):
        w = user32.GetSystemMetrics(SM_CXSCREEN)
        h = user32.GetSystemMetrics(SM_CYSCREEN)
        self.overlay = tk.Toplevel(self.root)
        self.overlay.withdraw()
        self.overlay.overrideredirect(True)
        self.overlay.geometry(f"{w}x{h}+0+0")
        self.overlay.configure(bg=TRANSPARENT)
        try:
            # Keep the Tk setting as a first layer of compatibility.
            self.overlay.wm_attributes("-transparentcolor", TRANSPARENT)
        except tk.TclError:
            pass
        self.overlay.attributes("-topmost", True)
        self.canvas = tk.Canvas(
            self.overlay, bg=TRANSPARENT, highlightthickness=0, bd=0,
            relief="flat", cursor="arrow"
        )
        self.canvas.pack(fill="both", expand=True)
        self.overlay.deiconify()
        self.overlay.update()
        self.apply_overlay_transparency()
        # Windows can recreate/update the layered surface just after mapping, so
        # repeat the color-key once after the first frame is on screen.
        self.overlay.after(120, self.apply_overlay_transparency)
        self.overlay.after(500, self.apply_overlay_transparency)
        self.set_clickthrough(True)
        self.bring_toolbar_forward()
        self.toolbar.after(300, self.bring_toolbar_forward)

    def open_input_capture(self):
        """Create an input-only fullscreen surface for Draw mode.

        Tk/Windows color-key transparent pixels often do not receive mouse
        events.  Keeping visual ink and input capture on separate windows makes
        desktop drawing reliable while the visible overlay stays truly clear.
        """
        w=user32.GetSystemMetrics(SM_CXSCREEN); h=user32.GetSystemMetrics(SM_CYSCREEN)
        self.input_overlay=tk.Toplevel(self.root)
        self.input_overlay.withdraw(); self.input_overlay.overrideredirect(True)
        self.input_overlay.geometry(f"{w}x{h}+0+0"); self.input_overlay.configure(bg="#000000")
        self.input_overlay.attributes("-topmost",True)
        try: self.input_overlay.attributes("-alpha",0.01)
        except tk.TclError: pass
        self.input_canvas=tk.Canvas(self.input_overlay,bg="#000000",highlightthickness=0,bd=0,cursor="crosshair")
        self.input_canvas.pack(fill="both",expand=True)
        self.input_canvas.bind("<ButtonPress-1>",self.pointer_down)
        self.input_canvas.bind("<B1-Motion>",self.pointer_move)
        self.input_canvas.bind("<ButtonRelease-1>",self.pointer_up)

    def _show_input_capture(self, show: bool):
        if not self.input_overlay: return
        if show:
            self.input_overlay.deiconify(); self.input_overlay.lift()
            self.toolbar.lift(); self.toolbar.attributes("-topmost",True)
        else:
            self.input_overlay.withdraw()

    def set_clickthrough(self, enabled: bool):
        if not self.overlay:
            return
        self.draw_mode = not bool(enabled)
        self.apply_overlay_transparency()
        self._show_input_capture(self.draw_mode)
        if self.canvas:
            self.canvas.configure(cursor="arrow")

    def set_mode(self, draw: bool):
        self.draw_mode = bool(draw)
        self.set_clickthrough(not self.draw_mode)
        self.refresh_button_states()
        self.status_var.set("Draw mode · drag anywhere on the desktop to annotate" if self.draw_mode
                            else "Interact mode · annotations stay visible while clicks pass through to your apps")
        self.toolbar.lift()

    def toggle_mode(self):
        self.set_mode(not self.draw_mode)

    def toggle_ink(self):
        self.ink_visible = not self.ink_visible
        self.refresh_button_states()
        self.redraw()

    def select_tool(self, tool: str):
        self.tool = tool
        if not self.draw_mode:
            self.set_mode(True)
        self.refresh_button_states()

    def select_color(self, color: str):
        self.color = color
        self.refresh_button_states()

    def select_width(self, width: int):
        self.width = int(width)
        self.refresh_button_states()

    def normalized(self, event):
        source=getattr(event,"widget",None) or self.input_canvas or self.canvas
        w=max(1,source.winfo_width()); h=max(1,source.winfo_height())
        return max(0.0,min(1.0,event.x/w)),max(0.0,min(1.0,event.y/h))

    def new_shape(self, kind: str):
        return {"id": str(uuid.uuid4()), "type": kind, "color": self.color, "width": self.width}

    def pointer_down(self, event):
        if not self.draw_mode or self.saving:
            return
        x, y = self.normalized(event)
        if self.tool == "eraser":
            self.erase_at(x, y)
            return
        if self.tool == "text":
            text = simpledialog.askstring("MathStudio annotation", "Text or math symbols:", parent=self.toolbar)
            if text and text.strip():
                self.commit_shape({**self.new_shape("text"), "x": x, "y": y, "text": text.strip()[:300]})
            return
        if self.tool == "pen":
            self.draft = {**self.new_shape("pen"), "points": [[x, y]]}
        else:
            self.draft = {**self.new_shape(self.tool), "x": x, "y": y, "x2": x, "y2": y}
        self.redraw()

    def pointer_move(self, event):
        if not self.draft:
            return
        x, y = self.normalized(event)
        if self.draft["type"] == "pen":
            pts = self.draft["points"]
            if len(pts) < 1500:
                if not pts or math.hypot(x - pts[-1][0], y - pts[-1][1]) > 0.001:
                    pts.append([x, y])
        else:
            self.draft["x2"], self.draft["y2"] = x, y
        self.redraw()

    def pointer_up(self, _event):
        if not self.draft:
            return
        shape, self.draft = self.draft, None
        self.commit_shape(shape)

    @staticmethod
    def point_segment_distance(px, py, x1, y1, x2, y2):
        vx, vy = x2 - x1, y2 - y1
        wx, wy = px - x1, py - y1
        c1 = vx * wx + vy * wy
        if c1 <= 0:
            return math.hypot(px - x1, py - y1)
        c2 = vx * vx + vy * vy
        if c2 <= c1:
            return math.hypot(px - x2, py - y2)
        b = c1 / c2
        bx, by = x1 + b * vx, y1 + b * vy
        return math.hypot(px - bx, py - by)

    def shape_distance(self, s, x, y):
        kind = s.get("type")
        if kind == "pen":
            pts = s.get("points") or []
            if not pts:
                return 99
            return min(math.hypot(x - p[0], y - p[1]) for p in pts[::max(1, len(pts)//80)])
        if kind == "line":
            return self.point_segment_distance(x, y, s.get("x", 0), s.get("y", 0), s.get("x2", 0), s.get("y2", 0))
        if kind == "rect":
            x1, x2 = sorted((s.get("x", 0), s.get("x2", 0)))
            y1, y2 = sorted((s.get("y", 0), s.get("y2", 0)))
            if x1 <= x <= x2 and y1 <= y <= y2:
                return min(abs(x-x1), abs(x-x2), abs(y-y1), abs(y-y2))
            return min(math.hypot(x-x1, y-y1), math.hypot(x-x2, y-y1), math.hypot(x-x1, y-y2), math.hypot(x-x2, y-y2))
        if kind == "circle":
            cx, cy = s.get("x", 0), s.get("y", 0)
            r = math.hypot(s.get("x2", cx)-cx, s.get("y2", cy)-cy)
            return abs(math.hypot(x-cx, y-cy)-r)
        if kind == "text":
            return math.hypot(x-s.get("x", 0), y-s.get("y", 0))
        return 99

    def erase_at(self, x, y):
        shapes = self.board.get("shapes") or []
        if not shapes:
            return
        candidate = min(reversed(shapes), key=lambda s: self.shape_distance(s, x, y), default=None)
        if candidate is None or self.shape_distance(candidate, x, y) > 0.035:
            return
        self.save_board({**self.board, "shapes": [s for s in shapes if s.get("id") != candidate.get("id")]})

    def draw_shape(self, s):
        if not self.canvas:
            return
        w, h = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        color = s.get("color", "#e53935")
        width = max(1, int(s.get("width", 4)) * 2)
        kind = s.get("type")
        if kind == "pen":
            pts = s.get("points") or []
            coords = []
            for p in pts:
                coords.extend([p[0] * w, p[1] * h])
            if len(coords) >= 4:
                self.canvas.create_line(*coords, fill=color, width=width, capstyle="round", joinstyle="round")
            elif len(coords) == 2:
                self.canvas.create_oval(coords[0]-width/2, coords[1]-width/2, coords[0]+width/2, coords[1]+width/2,
                                        fill=color, outline="")
        elif kind == "line":
            self.canvas.create_line(s["x"]*w, s["y"]*h, s["x2"]*w, s["y2"]*h, fill=color, width=width)
        elif kind == "rect":
            self.canvas.create_rectangle(s["x"]*w, s["y"]*h, s["x2"]*w, s["y2"]*h, outline=color, width=width)
        elif kind == "circle":
            cx, cy = s["x"]*w, s["y"]*h
            r = math.hypot((s["x2"]-s["x"])*w, (s["y2"]-s["y"])*h)
            self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline=color, width=width)
        elif kind == "text":
            self.canvas.create_text(s["x"]*w, s["y"]*h, text=s.get("text", ""), fill=color,
                                    font=("Segoe UI", 20 + int(s.get("width", 4))*2, "bold"), anchor="sw")
        elif kind == "graph":
            pts = []
            fn = s.get("fn", "linear")
            a, hh, k = s.get("a", 1), s.get("h", 0), s.get("k", 0)
            for px in range(0, int(w)+1, 3):
                xv = (px-w/2)/(w/20 if w else 1)
                v = xv-hh
                yv = a*((v*v) if fn == "quadratic" else math.sin(v) if fn == "sine" else abs(v) if fn == "absolute" else v)+k
                py = h/2-yv*(h/11.25 if h else 1)
                if -2*h <= py <= 3*h:
                    pts.extend([px, py])
            if len(pts) >= 4:
                self.canvas.create_line(*pts, fill=color, width=width)

    def redraw(self):
        if not self.canvas:
            return
        self.canvas.delete("all")
        if self.ink_visible:
            for shape in self.board.get("shapes", []):
                try:
                    self.draw_shape(shape)
                except Exception:
                    pass
            if self.draft:
                try:
                    self.draw_shape(self.draft)
                except Exception:
                    pass
        self.toolbar.lift()

    # ---------- Sync ----------
    def save_board(self, next_board, own_id=None):
        if self.saving or not self.connected:
            return
        self.saving = True
        version = self.version
        self.status_var.set("Saving annotation…")

        def work():
            nonlocal version, next_board
            try:
                for attempt in range(3):
                    try:
                        response = http_json(self.server + "/api/teacher-app/board", "POST",
                                             {"token": self.token, "version": version, "board": next_board})
                        return ("ok", response, next_board)
                    except RuntimeError as ex:
                        if attempt < 2 and "changed" in str(ex).lower():
                            state = http_json(self.state_url())
                            version = int(state.get("version") or 0)
                            current = state.get("board") or {"background": "blank", "shapes": []}
                            if own_id:
                                own = next((x for x in next_board.get("shapes", []) if x.get("id") == own_id), None)
                                if own and not any(x.get("id") == own_id for x in current.get("shapes", [])):
                                    next_board = {**current, "shapes": [*(current.get("shapes") or []), own]}
                                else:
                                    next_board = current
                            else:
                                next_board = current
                            continue
                        raise
            except Exception as ex:
                return ("err", ex, None)

        def done(result):
            self.saving = False
            if self.closed:
                return
            if result[0] == "ok":
                self.version = int(result[1].get("version") or self.version)
                self.board = result[2]
                if own_id:
                    self.my_shapes.append(own_id)
                self.status_var.set("Annotation synced · student drawings appear here automatically")
            else:
                self.status_var.set("Could not sync annotation: " + str(result[1]))
            self.redraw()

        threading.Thread(target=lambda: self.root.after(0, done, work()), daemon=True).start()

    def commit_shape(self, shape):
        next_board = {**self.board, "shapes": [*(self.board.get("shapes") or []), shape]}
        self.save_board(next_board, shape.get("id"))

    def undo(self):
        if self.saving:
            return
        ids = set(self.my_shapes)
        target = next((s for s in reversed(self.board.get("shapes", [])) if s.get("id") in ids), None)
        if not target:
            self.status_var.set("Nothing from this teacher session to undo.")
            return
        self.my_shapes = [x for x in self.my_shapes if x != target.get("id")]
        self.save_board({**self.board, "shapes": [s for s in self.board.get("shapes", []) if s.get("id") != target.get("id")]})

    def clear_all(self):
        if self.saving:
            return
        if messagebox.askyesno(APP_NAME, "Clear every shared annotation for everyone?", parent=self.toolbar):
            self.my_shapes.clear()
            self.save_board({**self.board, "shapes": []})

    def toggle_student_drawing(self):
        desired = not self.students_can_draw
        self.student_btn.configure(state="disabled")

        def work():
            try:
                return ("ok", http_json(self.server + "/api/teacher-app/permissions", "POST",
                                        {"token": self.token, "drawing": desired}))
            except Exception as ex:
                return ("err", ex)

        def done(result):
            self.student_btn.configure(state="normal")
            if result[0] == "ok":
                self.students_can_draw = bool(result[1].get("drawing"))
                self.status_var.set("Student annotation enabled." if self.students_can_draw else "Students are view-only.")
            else:
                self.status_var.set(str(result[1]))
            self.refresh_button_states()

        threading.Thread(target=lambda: self.root.after(0, done, work()), daemon=True).start()

    def schedule_poll(self):
        if self.closed or self.polling:
            return
        self.polling = True

        def work():
            try:
                return ("ok", http_json(self.state_url()))
            except Exception as ex:
                return ("err", ex)

        def done(result):
            self.polling = False
            if self.closed:
                return
            if result[0] == "ok":
                state = result[1]
                cl = state.get("class") or {}
                if not cl.get("live") or cl.get("status") != "scheduled":
                    self.status_var.set("This classroom has ended.")
                    self.connected = False
                    self.set_clickthrough(True)
                    return
                self.students_can_draw = bool(state.get("drawing"))
                self.attendees = state.get("attendees") or []
                self.connected_people = state.get("connected") or []
                remote_version = int(state.get("version") or 0)
                if remote_version != self.version and not self.saving and self.draft is None:
                    self.version = remote_version
                    self.board = state.get("board") or {"background": "blank", "shapes": []}
                    self.redraw()
                self.refresh_people()
                self.refresh_button_states()
            else:
                self.status_var.set("Sync reconnecting… " + str(result[1]))
            self.root.after(POLL_MS, self.schedule_poll)

        threading.Thread(target=lambda: self.root.after(0, done, work()), daemon=True).start()

    # ---------- Meeting controls ----------
    def classroom_url(self):
        return f"{self.public_origin}/classroom?id={self.class_id}&teacherhost=1&autojoin=1"

    def launch_media_helper(self):
        if not self.class_id:
            return
        # Request a short-lived, single-use browser bootstrap token from the
        # local server. The browser consumes it on the public origin, receives
        # the admin session cookie there, then redirects straight into this
        # classroom. The teacher never enters the student's 10-digit code.
        try:
            handoff=http_json(self.server+"/api/teacher-app/media-login-token","POST",{"token":self.token})
            media_token=str(handoff.get("media_token") or "")
            if not media_token:
                raise RuntimeError("MathStudio did not return a teacher media token.")
            url=f"{self.public_origin}/teacher-media-login?token={quote(media_token)}"
        except Exception as ex:
            self.status_var.set("Could not authenticate meeting window: "+str(ex))
            return
        # Chrome app mode gives the teacher a clean camera/participant panel
        # without browser tabs/address bars. The one-time handoff above signs
        # this browser window in as the same admin automatically.
        candidates=[
            os.path.join(os.environ.get("PROGRAMFILES", ""),"Google","Chrome","Application","chrome.exe"),
            os.path.join(os.environ.get("PROGRAMFILES(X86)", ""),"Google","Chrome","Application","chrome.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""),"Google","Chrome","Application","chrome.exe"),
            os.path.join(os.environ.get("PROGRAMFILES", ""),"Microsoft","Edge","Application","msedge.exe"),
        ]
        browser=next((x for x in candidates if x and os.path.exists(x)),None)
        try:
            if browser:
                subprocess.Popen([browser,f"--app={url}","--window-size=1280,850"],close_fds=True)
            else:
                webbrowser.open(url,new=1,autoraise=True)
            self.media_helper_started=True
            self.status_var.set("Full meeting window opened · camera, microphone, participants, chat, and annotations are available there")
        except Exception as ex:
            self.status_var.set("Could not open meeting window: "+str(ex))

    def open_media(self):
        self.launch_media_helper()

    def send_media_command(self, command: str):
        if self.media_command_busy or not self.connected:
            return
        self.media_command_busy=True
        def work():
            try:
                return ("ok",http_json(self.server+"/api/teacher-app/media-command","POST",{"token":self.token,"command":command}))
            except Exception as ex:
                return ("err",ex)
        def done(result):
            self.media_command_busy=False
            if result[0]=="ok":
                self.status_var.set("Media command sent · allow browser permission if prompted in the video panel")
            else:
                self.status_var.set("Media control failed: "+str(result[1]))
        threading.Thread(target=lambda:self.root.after(0,done,work()),daemon=True).start()

    def toggle_native_screen_share(self):
        if self.screen_sharing:
            self.stop_native_screen_share()
        else:
            self.start_native_screen_share()

    def start_native_screen_share(self):
        if not self.connected or self.screen_sharing:
            return
        try:
            from PIL import ImageGrab, Image
        except Exception:
            messagebox.showerror(APP_NAME,"Screen sharing needs Pillow. Restart the Teacher App; its launcher will install it automatically.",parent=self.toolbar)
            return
        try:
            http_json(self.server+"/api/teacher-app/screen","POST",{"token":self.token,"active":True})
        except Exception as ex:
            messagebox.showerror(APP_NAME,str(ex),parent=self.toolbar); return
        self.screen_sharing=True; self.screen_stop.clear(); self.open_share_indicator(); self.refresh_people()
        self.status_var.set("Sharing your desktop · students see this screen and the shared annotation layer")
        def capture_loop():
            failures=0
            while not self.screen_stop.is_set() and self.connected:
                try:
                    img=ImageGrab.grab(all_screens=False)
                    maxw,maxh=1280,720
                    scale=min(1.0,maxw/max(1,img.width),maxh/max(1,img.height))
                    if scale<1:
                        img=img.resize((max(1,int(img.width*scale)),max(1,int(img.height*scale))),Image.Resampling.LANCZOS)
                    buf=io.BytesIO(); img.convert("RGB").save(buf,"JPEG",quality=62,optimize=False)
                    http_bytes_post(self.server+"/api/teacher-app/screen-frame",self.token,buf.getvalue(),timeout=4)
                    failures=0
                except Exception as ex:
                    failures+=1
                    if failures>=5:
                        self.root.after(0,lambda e=str(ex):self.status_var.set("Screen share reconnecting… "+e))
                self.screen_stop.wait(0.18)
        threading.Thread(target=capture_loop,daemon=True).start()

    def stop_native_screen_share(self):
        if not self.screen_sharing:
            return
        self.screen_sharing=False; self.screen_stop.set()
        try: http_json(self.server+"/api/teacher-app/screen","POST",{"token":self.token,"active":False})
        except Exception: pass
        self.close_share_indicator(); self.refresh_people()
        self.status_var.set("Screen sharing stopped")

    def _style_clickthrough(self, win):
        try:
            win.update_idletasks(); child=int(win.winfo_id()); hwnd=int(user32.GetAncestor(child,GA_ROOT) or child)
            style=user32.GetWindowLongW(hwnd,GWL_EXSTYLE)|WS_EX_LAYERED|WS_EX_TRANSPARENT|WS_EX_TOOLWINDOW|WS_EX_NOACTIVATE
            user32.SetWindowLongW(hwnd,GWL_EXSTYLE,style)
            user32.SetLayeredWindowAttributes(hwnd,self._colorref(TRANSPARENT),255,LWA_COLORKEY)
            user32.SetWindowPos(hwnd,HWND_TOPMOST,0,0,0,0,SWP_NOMOVE|SWP_NOSIZE|SWP_NOACTIVATE)
        except Exception: pass

    def open_share_indicator(self):
        if self.share_overlay:
            return
        w=user32.GetSystemMetrics(SM_CXSCREEN); h=user32.GetSystemMetrics(SM_CYSCREEN)
        win=tk.Toplevel(self.root); self.share_overlay=win
        win.withdraw(); win.overrideredirect(True); win.geometry(f"{w}x{h}+0+0"); win.configure(bg=TRANSPARENT)
        try: win.wm_attributes("-transparentcolor",TRANSPARENT)
        except tk.TclError: pass
        win.attributes("-topmost",True)
        c=tk.Canvas(win,bg=TRANSPARENT,highlightthickness=0,bd=0); self.share_canvas=c; c.pack(fill="both",expand=True)
        c.create_rectangle(3,3,w-4,h-4,outline="#ef4444",width=5)
        c.create_rectangle(w/2-170,8,w/2+170,48,fill="#b91c1c",outline="")
        c.create_text(w/2,28,text="MathStudio · You are sharing this screen",fill="white",font=("Segoe UI",11,"bold"))
        win.deiconify(); win.update(); self._style_clickthrough(win); self.toolbar.lift()

    def close_share_indicator(self):
        try:
            if self.share_overlay:self.share_overlay.destroy()
        except Exception: pass
        self.share_overlay=None; self.share_canvas=None

    def end_class(self):
        if not messagebox.askyesno(APP_NAME, "End this class for the teacher and all students?", parent=self.toolbar):
            return
        self.end_btn.configure(state="disabled")
        try:
            http_json(self.server + "/api/teacher-app/end", "POST", {"token": self.token})
        except Exception as ex:
            self.end_btn.configure(state="normal")
            messagebox.showerror(APP_NAME, str(ex), parent=self.toolbar)
            return
        self.connected = False
        self.status_var.set("Class ended.")
        messagebox.showinfo(APP_NAME, "The classroom is now closed.", parent=self.toolbar)
        self.close(force=True)

    def on_close(self):
        if self.connected:
            choice = messagebox.askyesno(APP_NAME, "Exit this meeting?\n\nClosing the Teacher Meeting window will end the classroom for students and remove it from the active class list.", parent=self.toolbar)
            if not choice:
                return
            try:
                http_json(self.server + "/api/teacher-app/end", "POST", {"token": self.token})
            except Exception as ex:
                if not messagebox.askyesno(APP_NAME, "MathStudio could not confirm that the class ended:\n\n"+str(ex)+"\n\nClose the app anyway?", parent=self.toolbar):
                    return
        self.close(force=True)

    def close(self, force=False):
        self.closed = True
        self.connected = False
        self.screen_stop.set()
        if self.screen_sharing:
            try: http_json(self.server+"/api/teacher-app/screen","POST",{"token":self.token,"active":False})
            except Exception: pass
        self.close_share_indicator()
        try:
            if self.overlay:
                self.overlay.destroy()
            if self.input_overlay:
                self.input_overlay.destroy()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def run(self):
        self.root.mainloop()


def parse_args():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--server", default="http://127.0.0.1:5051")
    parser.add_argument("--token", default="")
    parser.add_argument("--public-origin", default="")
    parser.add_argument("--skip-auto-media", action="store_true")
    return parser.parse_args()


def show_launcher(server: str):
    root = tk.Tk()
    root.title("MathStudio Teacher App")
    root.geometry("620x430+120+100")
    root.minsize(560, 390)
    root.configure(bg="#0f1720")

    wrap = tk.Frame(root, bg="#0f1720", padx=28, pady=24)
    wrap.pack(fill="both", expand=True)
    tk.Label(wrap, text="MathStudio Teacher App", bg="#0f1720", fg="#f4f7f8",
             font=("Segoe UI", 21, "bold"), anchor="w").pack(fill="x")
    tk.Label(wrap, text="Desktop meeting controls & system-wide annotations", bg="#0f1720",
             fg="#9fb2bc", font=("Segoe UI", 10), anchor="w").pack(fill="x", pady=(2, 20))

    card = tk.Frame(wrap, bg="#16212c", padx=20, pady=18, highlightbackground="#2c3e49", highlightthickness=1)
    card.pack(fill="x")
    tk.Label(card, text="How to start a class", bg="#16212c", fg="#f4f7f8",
             font=("Segoe UI", 13, "bold"), anchor="w").pack(fill="x")
    tk.Label(card, text=("1. Keep the MathStudio server running.\n"
                         "2. Open Admin in the website.\n"
                         "3. Under Confirmed classes, press Start teacher app.\n"
                         "4. This window becomes the live meeting toolbar and the desktop overlay opens automatically."),
             bg="#16212c", fg="#c5d1d6", justify="left", anchor="w",
             font=("Segoe UI", 10)).pack(fill="x", pady=(8, 14))

    status = tk.StringVar(value=f"Server: {server}")
    tk.Label(card, textvariable=status, bg="#16212c", fg="#9fb2bc", anchor="w").pack(fill="x", pady=(0, 12))

    buttons = tk.Frame(card, bg="#16212c")
    buttons.pack(fill="x")

    def check_server():
        try:
            http_json(server.rstrip('/') + "/api/public", timeout=3)
            status.set("Server connected ✓  ·  Start a confirmed class from Admin.")
        except Exception as ex:
            status.set("Server not reachable · " + str(ex))

    def open_admin():
        webbrowser.open(server.rstrip('/') + "/admin", new=1, autoraise=True)

    def button(text, command, bg):
        return tk.Button(buttons, text=text, command=command, bg=bg, fg="white",
                         activebackground="#157d74", activeforeground="white", relief="flat",
                         bd=0, padx=16, pady=10, cursor="hand2", font=("Segoe UI", 10, "bold"))

    button("Open MathStudio Admin", open_admin, "#157d74").pack(side="left", padx=(0, 8))
    button("Check server", check_server, "#31505f").pack(side="left")

    helpbox = tk.Frame(wrap, bg="#0f1720", pady=18)
    helpbox.pack(fill="x")
    tk.Label(helpbox, text="If the Admin button says the app opened but no toolbar appears, leave this window open and try Start teacher app again. The live toolbar now has a normal Windows taskbar/Alt+Tab entry.",
             bg="#0f1720", fg="#9fb2bc", justify="left", wraplength=550, anchor="w").pack(fill="x")

    root.after(250, check_server)
    root.mainloop()


def main():
    args = parse_args()
    if not args.token:
        show_launcher(args.server)
        return
    TeacherMeetingApp(args.server, args.token, args.public_origin, auto_media=not args.skip_auto_media).run()


if __name__ == "__main__":
    main()
