import json
import os
from pathlib import Path
import re
import socket
import sqlite3
import subprocess
import sys
import threading
import traceback
import ctypes
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
import http.cookiejar
import queue
from functools import partial
import desktop_credentials
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from teacher_localization import translate as translate_ui, read_language, save_language, content_label, localize_value
from studio_time import studio_zone, parse_local
from build_info import BUILD_ID
from runtime_paths import data_directory, state_directory
from private_config import apply_config
from teacher_connection import teacher_only, select_origin, check_connection

ROOT = Path(__file__).resolve().parent
PORT = 5051
LOCAL_ORIGIN = os.environ.get("MATHSTUDIO_SERVER_URL", "" if teacher_only() else f"http://127.0.0.1:{PORT}").rstrip("/")
DATA = data_directory(ROOT)
APP_TITLE = "MathStudio Teacher"


class APIError(RuntimeError):
    pass


class APIClient:
    def __init__(self, base=LOCAL_ORIGIN):
        self.base = base.rstrip('/')
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.csrf = ''
        self.user = None

    def _decode(self, response):
        data = response.read()
        try:
            return json.loads(data.decode('utf-8'))
        except Exception:
            return {}

    def _refresh_session_token(self, timeout=15):
        """Establish/refresh the server session and its CSRF token."""
        req = urllib.request.Request(
            self.base + '/api/me',
            headers={'Accept': 'application/json'},
            method='GET',
        )
        try:
            with self.opener.open(req, timeout=timeout) as r:
                out = self._decode(r)
        except urllib.error.HTTPError as ex:
            try:
                msg = json.loads(ex.read().decode('utf-8')).get('error') or f'HTTP {ex.code}'
            except Exception:
                msg = f'HTTP {ex.code}'
            raise APIError(msg) from None
        except urllib.error.URLError as ex:
            raise APIError(f'Cannot reach MathStudio server: {ex.reason}') from None
        if not isinstance(out, dict) or not out.get('csrf'):
            raise APIError('MathStudio could not establish a secure session. Please retry.')
        self.csrf = out['csrf']
        self.user = out.get('user')
        return out

    def json(self, path, data=None, timeout=15, _retried=False):
        url = self.base + path
        headers = {'Accept': 'application/json'}
        body = None
        method = 'GET'
        if data is not None:
            # The native app does not load a web page first, so unlike the student
            # site it must explicitly fetch the anonymous session/CSRF token before
            # its first POST (including /api/login).
            if not self.csrf:
                self._refresh_session_token(timeout=timeout)
            method = 'POST'
            body = json.dumps(data).encode('utf-8')
            headers['Content-Type'] = 'application/json'
            headers['X-CSRF-Token'] = self.csrf
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with self.opener.open(req, timeout=timeout) as r:
                out = self._decode(r)
        except urllib.error.HTTPError as ex:
            try:
                out = json.loads(ex.read().decode('utf-8'))
                msg = out.get('error') or f'HTTP {ex.code}'
            except Exception:
                msg = f'HTTP {ex.code}'
            # Sessions are stored in memory by the development server. If the
            # server restarted, refresh the session token and transparently retry
            # one POST instead of surfacing a misleading "Form expired" error.
            if data is not None and ex.code == 403 and 'Form expired' in msg and not _retried:
                self.csrf = ''
                self._refresh_session_token(timeout=timeout)
                return self.json(path, data, timeout=timeout, _retried=True)
            raise APIError(msg) from None
        except urllib.error.URLError as ex:
            raise APIError(f'Cannot reach MathStudio server: {ex.reason}') from None
        if isinstance(out, dict) and out.get('csrf'):
            self.csrf = out['csrf']
        return out

    def login(self, username, password, remember=False):
        out = self.json('/api/login', {'username': username, 'password': password})
        self.user = out.get('user')
        self.csrf = out.get('csrf', self.csrf)
        if not self.user or self.user.get('role') != 'admin':
            try:
                self.json('/api/logout', {})
            except Exception:
                pass
            self.user = None
            raise APIError('This account is not an admin/teacher account.')
        self.forget_remembered()
        if remember:self.enable_remember(password)
        return self.user

    def enable_remember(self,password):
        device=desktop_credentials.new_device()
        out=self.json('/api/desktop/remember',{'password':password,'device':device})
        try:desktop_credentials.save(self.base,out['refresh'],device)
        except Exception:
            self.json('/api/desktop/forget',{})
            raise APIError('Windows could not save Remember Me. Sign in without it.') from None

    def forget_remembered(self):
        try:stored=desktop_credentials.load(self.base)
        except Exception:stored=None
        self.json('/api/desktop/forget',{'refresh':stored['refresh']} if stored else {})
        desktop_credentials.forget(self.base)

    def startup_auth(self):
        try:stored=desktop_credentials.load(self.base)
        except Exception:
            desktop_credentials.forget(self.base);stored=None
        if stored:
            try:
                out=self.json('/api/desktop/refresh',{'refresh':stored['refresh'],'device':stored['device']})
                self.user=out.get('user')
                if not self.user or self.user.get('role')!='admin':raise APIError('Remembered login was revoked. Sign in again.')
                desktop_credentials.save(self.base,out['refresh'],stored['device'])
                return 'authenticated'
            except Exception:
                # A failed rotation is never treated as a restored session.
                try:self.json('/api/logout',{})
                except Exception:pass
                desktop_credentials.forget(self.base);self.user=None
        return 'login' if self.json('/api/desktop/setup-status')['initialized'] else 'setup'

    def setup_teacher(self,username,name,password,pairing,remember=False):
        out=self.json('/api/desktop/setup',{'username':username,'name':name,'password':password,'pairing':pairing})
        self.user=out.get('user')
        if not self.user or self.user.get('role')!='admin':raise APIError('Teacher setup did not complete.')
        if remember:self.enable_remember(password)
        return self.user

    def logout(self):
        self.json('/api/logout',{})
        desktop_credentials.forget(self.base)
        self.jar.clear();self.user=None;self.csrf=''

    def me(self):
        out = self.json('/api/me')
        self.user = out.get('user')
        self.csrf = out.get('csrf', self.csrf)
        return self.user

    def upload_file(self, path: Path):
        data = path.read_bytes()
        headers = {
            'Content-Type': 'application/octet-stream',
            'X-CSRF-Token': self.csrf,
            'X-File-Name': urllib.parse.quote(path.name),
            'X-File-Type': urllib.parse.quote('application/octet-stream'),
            'Accept': 'application/json',
        }
        req = urllib.request.Request(self.base + '/api/admin/files/upload', data=data, headers=headers, method='POST')
        try:
            with self.opener.open(req, timeout=120) as r:
                return self._decode(r)
        except urllib.error.HTTPError as ex:
            try:
                msg = json.loads(ex.read().decode('utf-8')).get('error', f'HTTP {ex.code}')
            except Exception:
                msg = f'HTTP {ex.code}'
            raise APIError(msg) from None


class CloudflareTunnel:
    def __init__(self, on_url, on_status):
        self.on_url = on_url
        self.on_status = on_status
        self.proc = None
        self.url = ''
        self._stop = False

    @staticmethod
    def find_exe():
        candidates = []
        for name in ('cloudflared.exe', 'cloudflared'):
            from shutil import which
            p = which(name)
            if p:
                candidates.append(p)
        local = os.environ.get('LOCALAPPDATA', '')
        candidates += [
            r'C:\Program Files (x86)\cloudflared\cloudflared.exe',
            r'C:\Program Files\cloudflared\cloudflared.exe',
            str(Path(local) / 'cloudflared' / 'cloudflared.exe') if local else '',
        ]
        for p in candidates:
            if p and Path(p).exists():
                return p
        return None

    def start(self):
        if self.proc and self.proc.poll() is None:
            return
        exe = self.find_exe()
        if not exe:
            self.on_status('Cloudflared not found. LAN student link is still available.')
            return
        self._stop = False
        try:
            self.proc = subprocess.Popen(
                [exe, 'tunnel', '--url', LOCAL_ORIGIN],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding='utf-8',
                errors='replace',
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
        except Exception as ex:
            self.on_status(f'Could not start secure link: {ex}')
            return
        self.on_status('Starting secure student link…')
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self):
        pattern = re.compile(r'https://[a-z0-9-]+\.trycloudflare\.com', re.I)
        deadline = time.time() + 40
        try:
            while self.proc and self.proc.poll() is None and not self._stop and time.time() < deadline:
                line = self.proc.stdout.readline() if self.proc.stdout else ''
                if not line:
                    time.sleep(.1)
                    continue
                m = pattern.search(line)
                if m:
                    self.url = m.group(0)
                    try:
                        DATA.mkdir(parents=True, exist_ok=True)
                        (DATA / 'public_origin.txt').write_text(self.url, encoding='utf-8')
                    except Exception:
                        pass
                    self.on_url(self.url)
                    self.on_status('Secure student link is ready.')
                    return
        finally:
            if not self.url and not self._stop:
                self.on_status('Secure link did not start. Use the LAN link for now.')

    def stop(self):
        self._stop = True
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except Exception:
                pass
        self.proc = None
        self.url = ''
        try:
            (DATA / 'public_origin.txt').unlink(missing_ok=True)
        except Exception:
            pass


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return '127.0.0.1'


def can_connect():
    if os.environ.get('MATHSTUDIO_REMOTE'):
        return bool(server_build())
    try:
        with socket.create_connection(('127.0.0.1', PORT), timeout=.6):
            return True
    except OSError:
        return False


def server_build():
    try:
        with urllib.request.urlopen(LOCAL_ORIGIN + '/api/desktop-info', timeout=1.2) as r:
            data=json.loads(r.read().decode('utf-8'))
            return data.get('build','')
    except Exception:
        return ''


def ensure_admin_account(parent):
    sys.path.insert(0, str(ROOT))
    import server
    server.init()
    with server.db() as c:
        if c.execute("SELECT 1 FROM users WHERE role='admin'").fetchone():
            return True
    setup = tk.Toplevel(parent)
    setup.title('Create teacher account')
    setup.transient(parent)
    setup.grab_set()
    setup.resizable(False, False)
    result = {'ok': False}
    frm = ttk.Frame(setup, padding=22)
    frm.pack(fill='both', expand=True)
    ttk.Label(frm, text='Create the first teacher account', font=('Segoe UI', 16, 'bold')).grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 6))
    ttk.Label(frm, text='This account controls the MathStudio Teacher app.', foreground='#5d6b78').grid(row=1, column=0, columnspan=2, sticky='w', pady=(0, 14))
    fields = {}
    for i, (key, label, show) in enumerate([
        ('name', 'Teacher name', ''), ('username', 'Username', ''), ('password', 'Password', '•'), ('confirm', 'Confirm password', '•')
    ], start=2):
        ttk.Label(frm, text=label).grid(row=i, column=0, sticky='w', padx=(0, 12), pady=5)
        e = ttk.Entry(frm, width=34, show=show)
        e.grid(row=i, column=1, sticky='ew', pady=5)
        fields[key] = e
    err = ttk.Label(frm, text='', foreground='#b42318')
    err.grid(row=6, column=0, columnspan=2, sticky='w', pady=(8, 2))

    def save():
        name = fields['name'].get().strip()
        username = fields['username'].get().strip().lower()
        password = fields['password'].get()
        confirm = fields['confirm'].get()
        if not name or not re.fullmatch(r'[a-z0-9_]{3,40}', username):
            err.config(text='Enter a name and a username using letters, numbers, and underscores.')
            return
        if len(password) < 12:
            err.config(text='Use a password with at least 12 characters.')
            return
        if password != confirm:
            err.config(text='Passwords do not match.')
            return
        try:
            with server.db() as c:
                c.execute("INSERT INTO users(username,name,password,role) VALUES (?,?,?,'admin')",
                          (username, name, server.hash_password(password)))
            result['ok'] = True
            setup.destroy()
        except sqlite3.IntegrityError:
            err.config(text='That username is already in use.')
        except Exception as ex:
            err.config(text=str(ex))

    ttk.Button(frm, text='Create teacher account', command=save).grid(row=7, column=0, columnspan=2, sticky='ew', pady=(10, 0))
    fields['name'].focus_set()
    parent.wait_window(setup)
    return result['ok']


def start_server_process():
    if can_connect():
        if server_build()==BUILD_ID:
            return None
        raise RuntimeError(f'Port {PORT} is already being used by another/older MathStudio. Stop that version first, then run OPEN MATHSTUDIO TEACHER.bat.')
    env = os.environ.copy()
    apply_config(env)
    env['BIND_HOST'] = '0.0.0.0'
    env['PORT'] = str(PORT)
    env['MATH_DESKTOP_MODE'] = '1'
    # The dashboard owns a local Cloudflare connector; only loopback may supply CF client IPs.
    env.setdefault('MATH_TRUSTED_PROXIES','127.0.0.1/32,::1/128')
    cmd = [sys.executable, str(ROOT / 'server.py')]
    log_path=state_directory()/'server_startup.log'
    log_path.parent.mkdir(parents=True,exist_ok=True)
    log=log_path.open('a',encoding='utf-8')
    try:
        proc = subprocess.Popen(
            cmd, cwd=str(ROOT), env=env, stdout=log, stderr=log,
            stdin=subprocess.DEVNULL,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
    finally:
        log.close()
    deadline = time.time() + 12
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError('The MathStudio student server closed during startup.')
        if can_connect() and server_build()==BUILD_ID:
            return proc
        time.sleep(.15)
    raise RuntimeError(f'MathStudio could not start on port {PORT}.')


def quarter_values():
    out = []
    for h in range(24):
        for m in (0, 15, 30, 45):
            out.append(f'{h:02d}:{m:02d}')
    return out


def fmt_time(ts, zone='America/Edmonton'):
    return datetime.fromtimestamp(float(ts),studio_zone(zone)).strftime('%a, %b %d · %I:%M %p').replace(' 0', ' ')


def fmt_day(ts):
    d = datetime.fromtimestamp(float(ts))
    today = datetime.now().date()
    if d.date() == today:
        prefix = 'Today'
    elif d.date() == today + timedelta(days=1):
        prefix = 'Tomorrow'
    else:
        prefix = d.strftime('%A')
    return f'{prefix} · {d.strftime("%b %d")}'


class TeacherDesktopApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        sw=max(800,self.root.winfo_screenwidth()); sh=max(600,self.root.winfo_screenheight())
        width=max(760,min(sw-28,int(sw*0.965))); height=max(560,min(sh-64,int(sh*0.93)))
        x=max(0,(sw-width)//2); y=max(0,min(24,(sh-height)//2))
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        self.root.minsize(760,560)
        # Start maximized on normal desktop displays; smaller displays keep the fitted geometry.
        if sw>=1100 and sh>=700:
            try:self.root.state('zoomed')
            except tk.TclError:pass
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)
        self.remote = teacher_only() or bool(os.environ.get('MATHSTUDIO_REMOTE'))
        self.client = APIClient()
        self.student_origin = self.client.base if self.remote else f'http://{lan_ip()}:{PORT}'
        self.secure_origin = ''
        self.admin = {}
        self.schedule = {}
        self.file_info = {}
        self.public = {}
        self.classes = []
        self.week_offset = 0
        self.active_group_id = None
        self.active_chat_type = None
        self.active_chat_id = None
        self.message_poll_job = None
        self.sidebar_buttons = {}
        self.current_page = ''
        self.sidebar = None
        self._sidebar_width = None
        self._resize_job = None
        self._active_poll_job = None
        self._active_signature = None
        self.lang = read_language()
        self._style()
        self._bootstrap()

    def _style(self):
        s = ttk.Style(self.root)
        try:
            s.theme_use('clam')
        except tk.TclError:
            pass
        bg = '#f2f5f7'
        ink = '#13272f'
        muted = '#6b7c84'
        teal = '#0f766e'
        s.configure('.', font=('Segoe UI', 10), background=bg, foreground=ink)
        s.configure('TFrame', background=bg)
        s.configure('Content.TFrame', background=bg)
        s.configure('Card.TFrame', background='white', relief='solid', borderwidth=1, bordercolor='#dbe5e8')
        s.configure('Soft.TFrame', background='#edf6f4')
        s.configure('TLabel', background=bg, foreground=ink)
        s.configure('Card.TLabel', background='white', foreground=ink)
        s.configure('Soft.TLabel', background='#edf6f4', foreground=ink)
        s.configure('Title.TLabel', font=('Segoe UI', 23, 'bold'), foreground=ink)
        s.configure('PageSub.TLabel', font=('Segoe UI', 9), foreground=muted)
        s.configure('H2.TLabel', font=('Segoe UI', 14, 'bold'), foreground=ink)
        s.configure('Muted.TLabel', foreground=muted)
        s.configure('TButton', font=('Segoe UI', 9, 'bold'), foreground=ink, background='white', bordercolor='#cfdadd', padding=(11, 7))
        s.map('TButton', foreground=[('disabled','#91a0a6')], background=[('active','#f0f5f6'),('pressed','#e8eff1')])
        s.configure('Accent.TButton', font=('Segoe UI', 10, 'bold'), foreground='white', background=teal, bordercolor=teal, padding=(13, 8))
        s.map('Accent.TButton', background=[('active','#0b625c'),('pressed','#09544f')])
        s.configure('Quiet.TButton', foreground='#28434b', background='white', bordercolor='#d8e2e5', padding=(11, 7))
        s.map('Quiet.TButton', background=[('active','#f2f6f7')])
        s.configure('Danger.TButton', foreground='#9a2732', background='#fff4f4', bordercolor='#f0ced2', padding=(11, 7))
        s.configure('Treeview', rowheight=38, background='white', fieldbackground='white', bordercolor='#dbe5e8', lightcolor='#dbe5e8', darkcolor='#dbe5e8', font=('Segoe UI',10))
        s.map('Treeview', background=[('selected','#dff2ed')], foreground=[('selected',ink)])
        s.configure('Treeview.Heading', font=('Segoe UI', 9, 'bold'), foreground='#5d7078', background='#f4f7f8', relief='flat', padding=(10, 10))
        s.configure('TNotebook', background=bg, borderwidth=0)
        s.configure('TNotebook.Tab', padding=(14, 8))
        s.configure('TEntry', padding=8)
        s.configure('TCombobox', padding=7)
        s.configure('TSpinbox', padding=7)
        self.root.configure(bg=bg)

    def _bootstrap(self):
        # Reuse a healthy matching server; create an account/start only when absent.
        self.root.deiconify()
        if getattr(self,'remote',False):
            try:
                check_connection(self.client.base)
            except Exception as ex:
                self.show_server_offline(str(ex));return
            self.open_auth();return
        if not can_connect():
            try:
                self.server_process=start_server_process()
            except Exception as ex:
                self.show_server_offline(str(ex));return
        build = server_build()
        if build != BUILD_ID:
            self.show_server_offline(
                'Port 5051 is running a different MathStudio build. Stop that server and start the v41.6.6 student website.'
            )
            return
        self.open_auth()

    def auth_task(self,operation,success,failure):
        """Only plain API calls run on the worker; every Tk callback stays here."""
        if getattr(self,'_auth_busy',False):return
        self._auth_busy=True
        client=self.client;results=queue.Queue()
        def work():
            try:results.put((True,operation()))
            except Exception as error:results.put((False,str(error)))
        threading.Thread(target=work,daemon=True).start()
        def poll():
            try:ok,value=results.get_nowait()
            except queue.Empty:
                self.root.after(75,poll);return
            self._auth_busy=False
            if self.client is not client:return
            (success if ok else failure)(value)
        self.root.after(75,poll)

    def open_auth(self):
        def ready(mode):
            if mode=='authenticated':self.build_main();self.refresh_all()
            elif mode=='setup':self.show_setup()
            else:self.show_login()
        self.auth_task(self.client.startup_auth,ready,lambda error:self.show_server_offline(error))

    def show_setup(self,values=None,remember_choice=False):
        if getattr(self,'_auth_busy',False):return
        self.current_page=''
        for widget in self.root.winfo_children():widget.destroy()
        shell=ttk.Frame(self.root,padding=20);shell.pack(expand=True)
        ttk.Label(shell,text=self.tr('First-Time Teacher Setup'),font=('Segoe UI',20,'bold')).pack(anchor='w')
        ttk.Label(shell,text=self.tr('Enter the one-time authorization from the local OWNER pairing window.'),wraplength=470).pack(anchor='w',pady=8)
        entries={}
        for key,label in [('username','Username'),('name','Teacher name'),('password','Password'),('confirm','Repeat password'),('pairing','OWNER pairing code')]:
            ttk.Label(shell,text=self.tr(label)).pack(anchor='w')
            entry=ttk.Entry(shell,width=46,show='•' if key in ('password','confirm','pairing') else '')
            entry.pack(fill='x',pady=(1,5));entries[key]=entry
            if values:entry.insert(0,values.get(key,''))
        remember=tk.BooleanVar(value=remember_choice)
        ttk.Checkbutton(shell,text=self.tr('Remember me on this device'),variable=remember,state='normal' if desktop_credentials.available() else 'disabled').pack(anchor='w')
        status=ttk.Label(shell,text='',wraplength=470);status.pack(anchor='w',pady=5)
        def submit():
            password=entries['password'].get()
            if password!=entries['confirm'].get():status.configure(text=self.tr('Passwords did not match.'));return
            status.configure(text=self.tr('Connecting…'))
            operation=partial(self.client.setup_teacher,entries['username'].get().strip(),entries['name'].get().strip(),password,entries['pairing'].get().strip(),remember.get())
            def done(_):self.build_main();self.refresh_all()
            self.auth_task(operation,done,lambda error:status.configure(text=self.tr(error)))
        ttk.Button(shell,text=self.tr('Create teacher account'),command=submit).pack(fill='x',pady=4)
        ttk.Button(shell,text=self.tr('Sign in instead'),command=self.show_login).pack(fill='x')
        def switch():
            if getattr(self,'_auth_busy',False):return
            saved={key:entry.get() for key,entry in entries.items()};choice=remember.get()
            self.lang='en' if self.lang=='zh' else 'zh';save_language(self.lang)
            self.show_setup(saved,choice)
        ttk.Button(shell,text='中文 / EN',command=switch).pack(fill='x',pady=4)

    def show_server_offline(self, detail='The student website server is not running.'):
        for w in self.root.winfo_children():
            w.destroy()
        shell = ttk.Frame(self.root, padding=30)
        shell.pack(fill='both', expand=True)
        card = ttk.Frame(shell, style='Card.TFrame', padding=30)
        card.place(relx=.5, rely=.44, anchor='center', width=560)
        ttk.Label(card, text='MathStudio Teacher', style='Title.TLabel', background='white').pack(anchor='w')
        ttk.Label(card, text='Teacher desktop application', style='Card.TLabel', foreground='#66767d').pack(anchor='w', pady=(3, 18))
        ttk.Label(card, text=self.tr('OWNER connection needs attention' if getattr(self,'remote',False) else 'Student website is offline'), style='Card.TLabel', font=('Segoe UI', 13, 'bold'), foreground='#b42318').pack(anchor='w')
        ttk.Label(card, text=self.tr(detail), style='Card.TLabel', foreground='#66767d', wraplength=490).pack(anchor='w', pady=(5, 14))
        ttk.Label(card, text=('Check the OWNER HTTPS address and ask the owner to keep its backend running. Teacher Ready never starts a local backend.' if getattr(self,'remote',False) else 'First double-click START STUDENT WEBSITE.bat, leave that window open, then click Retry below.'), style='Card.TLabel', wraplength=490).pack(anchor='w', pady=(0, 16))
        row = ttk.Frame(card, style='Card.TFrame')
        row.pack(fill='x')
        ttk.Button(row, text='Retry connection', style='Accent.TButton', command=self.retry_server_connection).pack(side='left')
        if getattr(self,'remote',False):
            ttk.Button(row,text=self.tr('Change OWNER server'),command=self.change_owner_server).pack(side='left',padx=8)
        ttk.Button(row, text='Close', command=self.root.destroy).pack(side='left', padx=8)
        ttk.Label(card, text=self.tr('Connected to OWNER HTTPS server' if getattr(self,'remote',False) else 'Website: port 5051  •  Teacher app: separate process'), style='Card.TLabel', foreground='#839097').pack(anchor='w', pady=(18, 0))

    def retry_server_connection(self):
        if getattr(self,'remote',False):
            self._bootstrap();return
        if not can_connect():
            return messagebox.showwarning(APP_TITLE,self.tr('The website server is still offline. Start START STUDENT WEBSITE.bat first.'), parent=self.root)
        build = server_build()
        if build != BUILD_ID:
            return messagebox.showwarning(APP_TITLE,self.tr('Port 5051 belongs to another MathStudio build. Stop it and start the v41.6.6 website.'), parent=self.root)
        self.show_login()

    def show_login(self):
        if getattr(self,'_auth_busy',False):return
        self.current_page=''
        for w in self.root.winfo_children():
            w.destroy()
        shell = tk.Frame(self.root, bg='#f2f5f7')
        shell.pack(fill='both', expand=True)
        shell.grid_columnconfigure(0, weight=1)
        shell.grid_columnconfigure(1, weight=1)
        shell.grid_rowconfigure(0, weight=1)

        brand = tk.Frame(shell, bg='#0d2f34', padx=54, pady=48)
        brand.grid(row=0, column=0, sticky='nsew')
        logo = tk.Label(brand, text='M', bg='#dff5ed', fg='#0f766e', font=('Segoe UI', 19, 'bold'), width=2, height=1)
        logo.pack(anchor='w', pady=(12, 22))
        tk.Label(brand, text='MathStudio', bg='#0d2f34', fg='white', font=('Segoe UI', 27, 'bold')).pack(anchor='w')
        tk.Label(brand, text='Teacher workspace', bg='#0d2f34', fg='#a9cfca', font=('Segoe UI', 11)).pack(anchor='w', pady=(2, 34))
        tk.Label(brand, text='Manage lessons without opening the admin website.', bg='#0d2f34', fg='white', font=('Segoe UI', 15, 'bold'), wraplength=410, justify='left').pack(anchor='w')
        tk.Label(brand, text='Schedule classes, confirm bookings, message students, share files, and launch meetings from one desktop app.', bg='#0d2f34', fg='#bcd4d2', font=('Segoe UI', 10), wraplength=410, justify='left').pack(anchor='w', pady=(10, 0))

        area = tk.Frame(shell, bg='#f2f5f7', padx=60, pady=48)
        area.grid(row=0, column=1, sticky='nsew')
        card = tk.Frame(area, bg='white', highlightbackground='#dfe7ea', highlightthickness=1, padx=34, pady=34)
        card.place(relx=.5, rely=.48, anchor='center', width=430)
        tk.Label(card, text='Welcome back', bg='white', fg='#172a33', font=('Segoe UI', 21, 'bold')).pack(anchor='w')
        tk.Label(card, text='Sign in with a teacher/admin account.', bg='white', fg='#6a7b83', font=('Segoe UI', 10)).pack(anchor='w', pady=(4, 24))
        tk.Label(card, text='Username', bg='white', fg='#354b54', font=('Segoe UI', 9, 'bold')).pack(anchor='w')
        user = ttk.Entry(card)
        user.pack(fill='x', pady=(6, 15), ipady=4)
        tk.Label(card, text='Password', bg='white', fg='#354b54', font=('Segoe UI', 9, 'bold')).pack(anchor='w')
        pw = ttk.Entry(card, show='•')
        pw.pack(fill='x', pady=(6, 12), ipady=4)
        remember=tk.BooleanVar(value=False)
        ttk.Checkbutton(card,text='Remember me on this device',variable=remember,
                        state='normal' if desktop_credentials.available() else 'disabled').pack(anchor='w',pady=(0,8))
        status = tk.Label(card, text='', bg='white', fg='#b42318', font=('Segoe UI', 9), wraplength=350, justify='left')
        status.pack(anchor='w', pady=(0, 8))

        def login(*_):
            status.config(text=self.tr('Connecting…'))
            operation=partial(self.client.login,user.get().strip(),pw.get(),remember.get())
            def done(_):self.build_main();self.refresh_all()
            self.auth_task(operation,done,lambda error:status.config(text=self.tr(error)))
        if self.remote:
            ttk.Button(card,text=self.tr('Change OWNER server'),command=self.change_owner_server).pack(fill='x',pady=6)
        ttk.Button(card, text='Sign in to Teacher', style='Accent.TButton', command=login).pack(fill='x', ipady=3, pady=(2,0))
        ttk.Button(card, text='中文 / EN', style='Quiet.TButton', command=self.toggle_language).pack(fill='x', pady=(9,0))
        tk.Label(card, text=('Connected to OWNER HTTPS server' if self.remote else f'Connected to student website server · port {PORT}'), bg='white', fg='#8a989e', font=('Segoe UI', 8)).pack(anchor='w', pady=(18,0))
        self.apply_language(shell)
        user.focus_set()
        pw.bind('<Return>', login)

    def build_main(self):
        for w in self.root.winfo_children():
            w.destroy()
        outer = tk.Frame(self.root, bg='#f2f5f7')
        outer.pack(fill='both', expand=True)

        side = tk.Frame(outer, bg='#0d2f34', width=218)
        self.sidebar = side
        side.pack(side='left', fill='y')
        side.pack_propagate(False)
        brand = tk.Frame(side, bg='#0d2f34')
        brand.pack(fill='x', padx=20, pady=(22, 22))
        tk.Label(brand, text='M', bg='#dff5ed', fg='#0f766e', font=('Segoe UI', 15, 'bold'), width=2).pack(side='left')
        bt = tk.Frame(brand, bg='#0d2f34')
        bt.pack(side='left', padx=(10,0))
        tk.Label(bt, text='MathStudio', bg='#0d2f34', fg='white', font=('Segoe UI', 15, 'bold')).pack(anchor='w')
        tk.Label(bt, text='Teacher workspace', bg='#0d2f34', fg='#9fc7c3', font=('Segoe UI', 8)).pack(anchor='w')

        tk.Label(side, text='WORKSPACE', bg='#0d2f34', fg='#7fa7a4', font=('Segoe UI', 8, 'bold')).pack(anchor='w', padx=22, pady=(2,8))
        items = [
            ('dashboard', '⌂', 'Dashboard'), ('schedule', '▦', 'Schedule'), ('bookings', '✓', 'Bookings'),
            ('students', '◎', 'Students'), ('groups', '◫', 'Groups & chats'), ('files', '⇩', 'Files & codes'),
            ('meetings', '◉', 'Meetings'), ('recordings','●','Recordings'), ('website', '▤', 'Website Management'), ('settings', '⚙', 'Connection & studio')
        ]
        for key, icon, label in items:
            b = tk.Button(side, text=f'  {icon}   {label}', anchor='w', relief='flat', bd=0, padx=14, pady=11,
                          bg='#0d2f34', fg='#dcebea', activebackground='#165158', activeforeground='white',
                          font=('Segoe UI', 10), cursor='hand2', command=lambda k=key: self.show_page(k))
            b.pack(fill='x', padx=10, pady=1)
            self.sidebar_buttons[key] = b

        tk.Frame(side, bg='#0d2f34').pack(fill='both', expand=True)
        userbox = tk.Frame(side, bg='#154149', padx=13, pady=11)
        userbox.pack(fill='x', padx=10, pady=(8,10))
        initials = ''.join(x[0] for x in (self.client.user or {}).get('name','Teacher').split()[:2]).upper() or 'T'
        content_label(tk.Label, userbox, text=initials, bg='#dff5ed', fg='#0f766e', font=('Segoe UI', 9, 'bold'), width=3, height=1).pack(side='left')
        ui = tk.Frame(userbox, bg='#154149')
        ui.pack(side='left', padx=(9,0), fill='x', expand=True)
        content_label(tk.Label, ui, text=(self.client.user or {}).get('name','Teacher'), bg='#154149', fg='white', font=('Segoe UI', 9, 'bold')).pack(anchor='w')
        tk.Label(ui, text='Administrator', bg='#154149', fg='#9fc7c3', font=('Segoe UI', 8)).pack(anchor='w')
        tk.Button(side, text='↻  Refresh data', anchor='w', relief='flat', bd=0, padx=20, pady=9, bg='#0d2f34', fg='#a9c9c6', activebackground='#165158', activeforeground='white', command=self.refresh_all).pack(fill='x')
        tk.Button(side, text='↪  Sign out', anchor='w', relief='flat', bd=0, padx=20, pady=9, bg='#0d2f34', fg='#f0b9bd', activebackground='#165158', activeforeground='white', command=self.sign_out).pack(fill='x', pady=(0,14))

        workspace = tk.Frame(outer, bg='#f2f5f7')
        workspace.pack(side='left', fill='both', expand=True)
        topbar = tk.Frame(workspace, bg='white', height=88, highlightbackground='#e1e8eb', highlightthickness=0)
        topbar.pack(fill='x')
        topbar.pack_propagate(False)
        titlebox = tk.Frame(topbar, bg='white')
        titlebox.pack(side='left', padx=28, pady=16)
        self.page_title = tk.Label(titlebox, text='', bg='white', fg='#172a33', font=('Segoe UI', 20, 'bold'))
        self.page_title.pack(anchor='w')
        self.page_subtitle = tk.Label(titlebox, text='', bg='white', fg='#718188', font=('Segoe UI', 9))
        self.page_subtitle.pack(anchor='w', pady=(2,0))
        right = tk.Frame(topbar, bg='white')
        right.pack(side='right', padx=28)
        self.status_label = tk.Label(right, text='● Connected', bg='#edf7f4', fg='#0f766e', font=('Segoe UI', 9, 'bold'), padx=12, pady=7)
        self.status_label.pack(side='right')
        self.lang_button=ttk.Button(right, text='中文', style='Quiet.TButton', command=self.toggle_language)
        self.lang_button.pack(side='right', padx=(0,8))
        self.action_button(right,'New meeting',self.start_instant_meeting,'primary').pack(side='right',padx=(0,8))
        ttk.Button(right, text='Refresh', style='Quiet.TButton', command=self.refresh_all).pack(side='right', padx=(0,10))

        self.main = ttk.Frame(workspace, style='Content.TFrame', padding=(26, 22))
        self.main.pack(fill='both', expand=True)
        self.content = ttk.Frame(self.main, style='Content.TFrame')
        self.content.pack(fill='both', expand=True)
        self.root.bind('<Configure>', self._on_window_resize, add='+')
        self._apply_window_layout()
        self.show_page('dashboard')
        self.apply_language(self.root)
        if hasattr(self, 'lang_button'): self.lang_button.config(text='EN' if self.lang == 'zh' else '中文')
        self._schedule_active_poll()

    def _schedule_active_poll(self):
        if self._active_poll_job:
            try: self.root.after_cancel(self._active_poll_job)
            except Exception: pass
        self._active_poll_job=self.root.after(2000,self._poll_active_classes)

    def _poll_active_classes(self):
        """Background refresh for the desktop app without requiring Refresh clicks."""
        self._active_poll_job=None
        try:
            if self.client.user:
                latest=self.client.json('/api/admin')
                # Include all teacher-facing collections in the signature, not only live classes.
                sig=json.dumps({
                    'classes':latest.get('calendar_classes',[]),
                    'bookings':latest.get('bookings',[]),
                    'users':latest.get('users',[]),
                    'groups':latest.get('groups',[]),
                },sort_keys=True,default=str,separators=(',',':'))
                changed=(self._active_signature is not None and sig!=self._active_signature)
                self._active_signature=sig
                self.admin=latest
                # Schedule and file state can change independently of /api/admin.
                if self.current_page=='schedule':
                    self.schedule=self.client.json('/api/schedule')
                    if hasattr(self,'calendar_canvas') and self.calendar_canvas.winfo_exists():
                        self.draw_calendar()
                elif changed and self.current_page in ('dashboard','bookings','meetings','students'):
                    self.show_page(self.current_page)
                if self.current_page=='files':
                    newest_files=self.client.json('/api/admin/files')
                    fsig=json.dumps(newest_files,sort_keys=True,default=str,separators=(',',':'))
                    if fsig!=getattr(self,'_files_signature',None):
                        self._files_signature=fsig; self.file_info=newest_files; self.show_page('files')
                self.status_label.config(text='● Connected · auto-updated '+datetime.now().strftime('%I:%M:%S %p'),bg='#edf7f4',fg='#0f766e')
                self.apply_language(self.root)
        except Exception:
            try:
                self.status_label.config(text='● Reconnecting automatically…',bg='#fff7e8',fg='#9a6412')
                self.apply_language(self.status_label)
            except Exception: pass
        if self.root.winfo_exists(): self._schedule_active_poll()

    UI_ZH = {
        'Dashboard':'主页','Schedule':'课表','Bookings':'预约','Students':'学生','Groups & chats':'群组与聊天','WORKSPACE':'工作台','Teacher workspace':'教师工作台','Administrator':'管理员','Refresh data':'刷新数据','Sign out':'退出登录',
        '  ⌂   Dashboard':'  ⌂   主页','  ▦   Schedule':'  ▦   课表','  ✓   Bookings':'  ✓   预约','  ◎   Students':'  ◎   学生','  ◫   Groups & chats':'  ◫   群组与聊天','  ⇩   Files & codes':'  ⇩   文件与分享码','  ◉   Meetings':'  ◉   在线课堂','  ⚙   Student site':'  ⚙   学生网站',
        'Files & codes':'文件与分享码','Meetings':'在线课堂','Student site':'学生网站','Refresh':'刷新','Refresh data':'刷新数据','Sign out':'退出登录',
        'Recordings':'录制','Private cloud recordings':'私有云录制','Play':'播放','Download':'下载','Delete':'删除','Date':'日期','Meeting':'会议','Duration':'时长','Status':'状态','Recording is not ready.':'录制尚未就绪。','Permanently delete this private recording?':'永久删除此私有录制？','capturing':'正在录制','uploading':'正在上传','ready':'就绪','empty':'无内容','Interrupted':'已中断',
        'Today’s classes, requests, and student website status':'今天的课程、预约和学生网站状态',
        'Set availability, post group lessons, and review the week':'设置可预约时间、发布小班课并查看本周课表',
        'Confirm requests and manage scheduled classes':'确认预约并管理已安排课程',
        'Accounts, roles, and group membership':'账号、权限和群组成员',
        'Persistent class conversations and lesson messages':'长期群聊与课程消息',
        'Upload resources and create student download codes':'上传资料并创建学生下载码',
        'Start the native teacher classroom and annotation tools':'启动教师课堂、音视频与标注工具',
        'Public website details and announcements':'学生网站信息与公告',
        'Pending private requests':'待确认的一对一预约','Confirmed classes to handle':'已确认课程',
        'Confirm':'确认','Confirm weekly…':'按周重复确认…','Decline':'拒绝','Start teacher meeting':'开始课堂','End class':'结束课程','Cancel class':'取消课程',
        'Start an instant meeting':'立即开始课堂','Start instant meeting':'创建即时课堂',
        'No scheduled class is required. MathStudio creates a 10-digit code that students can use with an account or as a guest.':'无需先安排课程。MathStudio 会生成 10 位课堂码，学生可登录账号或以访客身份加入。',
        'Scheduled meetings':'已安排课堂','Select a confirmed class below, or use Instant Meeting above.':'选择下方已确认课程，或使用上方即时课堂。',
        'Start selected meeting':'开始所选课堂','Copy share code':'复制课堂码',
        'File library':'文件库','Access codes':'分享码','Upload files…':'上传文件…','Generate code from selected':'为所选文件生成分享码','Delete selected file':'删除所选文件',
        'Revoke':'停用','Restore':'恢复','Translation on':'翻译已开启','Translation off':'翻译已关闭','Enable translation':'开启翻译','Disable translation':'关闭翻译',
        'Persistent group chat':'长期群聊','Send':'发送','Message':'消息','Create group chat from selection':'用所选学生创建群聊',
        'Student':'学生','Lesson':'课程','Date':'日期','Length':'时长','Class':'课程','Booked by':'预约学生','Scheduled':'时间','Type':'类型','Meeting':'课堂',
        'Code':'分享码','Label':'名称','Files':'文件','Status':'状态','Translation':'翻译','File':'文件','Size':'大小','Codes':'分享码',
        'Active':'启用','Revoked':'已停用','On':'开启','Off':'关闭','Private':'一对一','Group':'小班课','Open':'已开启','Closed':'未开启',
        'Weekly calendar':'每周课表','Add private availability':'添加一对一可预约时间','Post group lesson':'发布小班课','Previous':'上一周','Next':'下一周',
        'Retry connection':'重新连接','Close':'关闭','Student website is offline':'学生网站未启动','Welcome back':'欢迎回来','Username':'用户名','Password':'密码','Sign in to Teacher':'登录教师端',
        'Teacher workspace':'教师工作台','Administrator':'管理员','Connected':'已连接','Connection problem':'连接异常',
        'New meeting':'新建课堂','Pending requests':'待确认预约','Needs your review':'需要处理','Confirmed classes':'已确认课程','Ready to teach':'可开始上课',
        'No pending requests':'暂无待确认预约','New private booking requests will appear here.':'新的预约申请会显示在这里。','Select a request, then choose an action below.':'选择预约后，在下方选择操作。',
        'Select a class to launch the teacher meeting, finish it, or cancel it.':'选择课程后，可开始课堂、结束课程或取消课程。','No students yet':'暂无学生','Join by code':'通过课堂码加入',
        'Instant':'即时课堂','Ready':'就绪','Late — ready to start':'已过开始时间，可立即开始','LIVE':'进行中','Share code':'课堂码','Students':'学生'
    }

    def studio_zone_name(self):
        return self.public.get('settings',{}).get('timezone','America/Edmonton')

    def fmt_time(self, ts):
        if self.lang == 'zh':
            return datetime.fromtimestamp(float(ts),studio_zone(self.studio_zone_name())).strftime('%Y年%m月%d日 %H:%M')
        return fmt_time(ts,self.studio_zone_name())

    def tr(self, value):
        translated = translate_ui(value, self.lang)
        if self.lang == 'zh' and translated == value:
            return self.UI_ZH.get(value, value)
        return translated

    def toggle_language(self):
        if getattr(self,'_auth_busy',False):return
        self.lang = 'zh' if self.lang == 'en' else 'en'
        save_language(self.lang)
        if self.current_page=='website' and getattr(self,'website_editor',None) and self.website_editor.winfo_exists():
            self.website_editor.set_language()
        elif self.current_page:
            self.show_page(self.current_page)
        self.apply_language(self.root)
        if hasattr(self, 'lang_button') and self.lang_button.winfo_exists():
            self.lang_button.config(text='EN' if self.lang == 'zh' else '中文')
        if hasattr(self, 'calendar_canvas') and self.calendar_canvas.winfo_exists():
            self.draw_calendar()

    def apply_language(self, widget):
        """Reapply translations after Tk refreshes without freezing live status text.

        Never modify entry fields, chat bodies or arbitrary user-supplied content.
        Widget text and known enum/status columns are UI strings only.
        """
        if getattr(widget, '_mathstudio_no_translate', False):
            return
        if hasattr(widget, '_mathstudio_title'):
            widget.title(self.tr(widget._mathstudio_title))
        try:
            if hasattr(widget, 'cget'):
                current = widget.cget('text')
                if isinstance(current, str) and current:
                    original = getattr(widget, '_mathstudio_en_text', None)
                    previous = getattr(widget, '_mathstudio_display_text', None)
                    # A fresh status update in English must supersede any cached label.
                    if original is None or (previous is not None and current != previous and current != original):
                        original = current
                        widget._mathstudio_en_text = original
                    displayed = self.tr(original)
                    if current != displayed:
                        widget.configure(text=displayed)
                    widget._mathstudio_display_text = displayed
        except (tk.TclError, AttributeError, TypeError):
            pass
        if isinstance(widget, ttk.Treeview):
            cols = list(widget['columns'])
            for col in cols + (['#0'] if widget['show'] and 'tree' in str(widget['show']) else []):
                try:
                    source = widget.heading(col, 'text')
                    widget.heading(col, text=localize_value(widget, ('heading', col), source, self.tr))
                except tk.TclError:
                    pass
            # Only translate controlled status/role columns, never usernames,
            # chat content, lesson names, or resource filenames.
            fixed_indices = {
                'confirmed_tree': (3,4), 'meeting_tree': (4,),
                'users_tree': (2,), 'codes_tree': (3,4),
            }
            indices = fixed_indices.get(next((k for k,v in self.__dict__.items() if v is widget),''), ())
            if indices:
                for iid in widget.get_children(''):
                    try:
                        original = list(widget.item(iid,'values'))
                        for i in indices:
                            if i < len(original):
                                original[i] = localize_value(widget, ('value', iid, i), original[i], self.tr)
                        widget.item(iid,values=original)
                    except tk.TclError:
                        pass
            if widget is getattr(self, 'groups_tree', None):
                for iid in ('section-groups','section-lessons'):
                    if widget.exists(iid):
                        widget.item(iid,text=localize_value(widget, ('section', iid), widget.item(iid,'text'), self.tr))
        try:
            for child in widget.winfo_children():
                self.apply_language(child)
        except (tk.TclError, AttributeError):
            pass

    def _on_window_resize(self,event=None):
        if event is not None and event.widget is not self.root:
            return
        if self._resize_job:
            try: self.root.after_cancel(self._resize_job)
            except Exception: pass
        self._resize_job=self.root.after(90,self._apply_window_layout)

    def _apply_window_layout(self):
        self._resize_job=None
        if not self.sidebar or not self.sidebar.winfo_exists():
            return
        width=max(1,self.root.winfo_width())
        desired=154 if width<900 else 176 if width<1100 else 198 if width<1320 else 220
        if desired!=self._sidebar_width:
            self._sidebar_width=desired
            self.sidebar.configure(width=desired)
        if hasattr(self,'calendar_canvas') and self.calendar_canvas.winfo_exists():
            self.draw_calendar()

    def clear_content(self):
        self.active_chat_id = None
        self._chat_key = None
        for w in self.content.winfo_children():
            w.destroy()
        if self.message_poll_job:
            try: self.root.after_cancel(self.message_poll_job)
            except Exception: pass
            self.message_poll_job = None

    def show_page(self, key):
        editor=getattr(self,'website_editor',None)
        if getattr(self,'current_page','')=='website' and editor and editor.winfo_exists() and editor.dirty:
            if not messagebox.askyesno(APP_TITLE,self.tr('Discard unsaved editor changes?'),parent=self.root):return
        self.current_page = key
        self.clear_content()
        meta = {
            'dashboard':('Dashboard','Today’s classes, requests, and student website status'),
            'schedule':('Schedule','Set availability, post group lessons, and review the week'),
            'bookings':('Bookings','Confirm requests and manage scheduled classes'),
            'students':('Students','Accounts, roles, and group membership'),
            'groups':('Groups & chats','Persistent class conversations and lesson messages'),
            'files':('Files & access codes','Upload resources and create student download codes'),
            'meetings':('Meetings','Start the native teacher classroom and annotation tools'),
            'recordings':('Recordings','Private cloud recordings'),
            'website':('Website Management','Draft, review and publish student-facing content'),
            'settings':('Connection & studio','OWNER server connection and studio timezone')
        }
        title, subtitle = meta[key]
        self.page_title._mathstudio_en_text = title
        self.page_title.config(text=self.tr(title))
        self.page_title._mathstudio_display_text = self.tr(title)
        self.page_subtitle._mathstudio_en_text = subtitle
        self.page_subtitle.config(text=self.tr(subtitle))
        self.page_subtitle._mathstudio_display_text = self.tr(subtitle)
        for k,b in self.sidebar_buttons.items():
            active = k == key
            b.config(bg='#176c67' if active else '#0d2f34', fg='white' if active else '#dcebea')
        getattr(self, f'page_{key}')()
        self.apply_language(self.content)

    def refresh_all(self):
        try:
            info = self.client.json('/api/desktop-info')
            self.secure_origin = (info.get('public_origin') or '').strip()
            self.student_origin = self.client.base if self.remote else f'http://{lan_ip()}:{PORT}'
            self.admin = self.client.json('/api/admin')
            self._active_signature=json.dumps({'classes':self.admin.get('calendar_classes',[]),'bookings':self.admin.get('bookings',[]),'users':self.admin.get('users',[]),'groups':self.admin.get('groups',[])},sort_keys=True,default=str,separators=(',',':'))
            self.schedule = self.client.json('/api/schedule')
            self.file_info = self.client.json('/api/admin/files')
            self.public = self.client.json('/api/public')
            self.classes = self.client.json('/api/classes').get('classes', [])
            self.status_label.config(text='● Connected · ' + datetime.now().strftime('%I:%M %p'), bg='#edf7f4', fg='#0f766e')
            self.apply_language(self.status_label)
            if self.current_page=='website' and getattr(self,'website_editor',None) and self.website_editor.winfo_exists():self.website_editor.reload()
            else:self.show_page(self.current_page or 'dashboard')
        except Exception as ex:
            self.status_label.config(text='● Connection problem', bg='#fff0f0', fg='#a52b37')
            self.apply_language(self.status_label)
            messagebox.showerror(APP_TITLE, self.tr('Request failed.')+"\n\n"+str(ex), parent=self.root)

    def card(self, parent, title, value, note='', accent='#0f766e'):
        f = tk.Frame(parent, bg='white', highlightbackground='#dfe7ea', highlightthickness=1, padx=18, pady=16)
        tk.Frame(f, bg=accent, width=4, height=42).pack(side='left', fill='y', padx=(0,13))
        body = tk.Frame(f, bg='white')
        body.pack(side='left', fill='both', expand=True)
        tk.Label(body, text=title.upper(), bg='white', fg='#6b7c84', font=('Segoe UI', 8, 'bold')).pack(anchor='w')
        content_label(tk.Label, body, text=str(value), bg='white', fg='#172a33', font=('Segoe UI', 23, 'bold')).pack(anchor='w', pady=(2,0))
        if note:
            tk.Label(body, text=note, bg='white', fg='#7c8b91', font=('Segoe UI', 8)).pack(anchor='w')
        return f


    def action_button(self, parent, text, command, kind='primary'):
        palette={
            'primary':('#0f766e','white','#0b625c'),
            'secondary':('#ffffff','#223840','#eef4f5'),
            'danger':('#fff1f2','#a52b37','#ffe4e6')
        }
        bg,fg,active=palette.get(kind,palette['secondary'])
        b=tk.Button(parent,text=self.tr(text),command=command,relief='flat',bd=0,
                    bg=bg,fg=fg,activebackground=active,activeforeground=fg,
                    padx=16,pady=9,font=('Segoe UI',9,'bold'),cursor='hand2',
                    highlightthickness=1,highlightbackground='#d9e3e6')
        b._mathstudio_en_text=text
        return b

    # ----- Dashboard -----
    def page_dashboard(self):
        users = self.admin.get('users', [])
        pending = [b for b in self.admin.get('bookings', []) if b.get('approval')=='pending' and b.get('status')=='scheduled']
        upcoming = [c for c in self.admin.get('calendar_classes', []) if c.get('status')=='scheduled' and c.get('approval')=='confirmed']
        groups = self.admin.get('groups', [])

        top = tk.Frame(self.content, bg='#f2f5f7')
        top.pack(fill='x')
        stats = [
            ('Students', len([u for u in users if u.get('role')=='student']), 'registered', '#0f766e'),
            ('Pending', len(pending), 'need a response', '#e3982e'),
            ('Classes', len(upcoming), 'confirmed', '#5570c0'),
            ('Groups', len(groups), 'active chats', '#8756a7'),
        ]
        for i,(t,v,n,a) in enumerate(stats):
            c=self.card(top,t,v,n,a); c.grid(row=0,column=i,sticky='nsew',padx=(0 if i==0 else 10,0))
            top.columnconfigure(i,weight=1)

        quick = tk.Frame(self.content, bg='#f2f5f7')
        quick.pack(fill='x', pady=(16,0))
        tk.Label(quick, text='Quick actions', bg='#f2f5f7', fg='#172a33', font=('Segoe UI', 11, 'bold')).pack(side='left')
        for label,key in [('Open schedule','schedule'),('Review requests','bookings'),('Start a meeting','meetings')]:
            ttk.Button(quick, text=label, style='Quiet.TButton', command=lambda k=key:self.show_page(k)).pack(side='right', padx=(7,0))

        body = tk.Frame(self.content, bg='#f2f5f7')
        body.pack(fill='both', expand=True, pady=(14,0))
        body.grid_columnconfigure(0,weight=3); body.grid_columnconfigure(1,weight=2); body.grid_rowconfigure(0,weight=1)
        left = tk.Frame(body, bg='white', highlightbackground='#dfe7ea', highlightthickness=1, padx=20, pady=18)
        left.grid(row=0,column=0,sticky='nsew',padx=(0,10))
        tk.Label(left,text='Upcoming classes',bg='white',fg='#172a33',font=('Segoe UI',13,'bold')).pack(anchor='w')
        tk.Label(left,text='Confirmed classes remain here until you end or cancel them.',bg='white',fg='#718188',font=('Segoe UI',9)).pack(anchor='w',pady=(3,12))
        nexts = sorted(upcoming,key=lambda x:x.get('start',0))[:8]
        if not nexts:
            empty=tk.Frame(left,bg='#f7faf9',padx=18,pady=24)
            empty.pack(fill='x',pady=(8,0))
            tk.Label(empty,text='No confirmed classes yet',bg='#f7faf9',fg='#445a63',font=('Segoe UI',10,'bold')).pack(anchor='w')
            tk.Label(empty,text='Confirmed bookings and group lessons will appear here.',bg='#f7faf9',fg='#7a8a91',font=('Segoe UI',9)).pack(anchor='w',pady=(3,0))
        for c in nexts:
            row=tk.Frame(left,bg='white',highlightbackground='#edf1f3',highlightthickness=1,padx=13,pady=11)
            row.pack(fill='x',pady=4)
            info=f"{self.fmt_time(c['start'])} · {c.get('minutes',0)} min"
            names=', '.join(a.get('name','') for a in c.get('attendees',[])) or self.tr('No students booked yet')
            dot=tk.Label(row,text='●',bg='white',fg='#0f766e',font=('Segoe UI',9))
            dot.pack(side='left',anchor='n',padx=(0,9),pady=1)
            text=tk.Frame(row,bg='white'); text.pack(side='left',fill='x',expand=True)
            content_label(tk.Label, text,text=c.get('title','Class'),bg='white',fg='#172a33',font=('Segoe UI',10,'bold')).pack(anchor='w')
            tk.Label(text,text=info,bg='white',fg='#60727a',font=('Segoe UI',9)).pack(anchor='w',pady=(1,0))
            content_label(tk.Label, text,text=names,bg='white',fg='#829096',font=('Segoe UI',8)).pack(anchor='w')

        right = tk.Frame(body, bg='white', highlightbackground='#dfe7ea', highlightthickness=1, padx=20, pady=18)
        right.grid(row=0,column=1,sticky='nsew')
        badge=tk.Label(right,text='STUDENT WEBSITE',bg='#e8f5f1',fg='#0f766e',font=('Segoe UI',8,'bold'),padx=8,pady=4)
        badge.pack(anchor='w')
        tk.Label(right,text='Share the student portal',bg='white',fg='#172a33',font=('Segoe UI',13,'bold')).pack(anchor='w',pady=(12,3))
        tk.Label(right,text='Students use this site for booking, resources, messages, and joining lessons.',bg='white',fg='#718188',font=('Segoe UI',9),wraplength=360,justify='left').pack(anchor='w')
        linkbox=tk.Frame(right,bg='#f5f8f8',highlightbackground='#dce6e7',highlightthickness=1,padx=12,pady=11)
        linkbox.pack(fill='x',pady=(16,10))
        self.student_link_label=content_label(tk.Label, linkbox,text=self.secure_origin or self.student_origin,bg='#f5f8f8',fg='#0f766e',font=('Consolas',9),wraplength=340,justify='left')
        self.student_link_label.pack(anchor='w')
        ttk.Button(right,text='Copy student link',style='Accent.TButton',command=self.copy_student_link).pack(fill='x',pady=(2,6))
        ttk.Button(right,text='Refresh website link',style='Quiet.TButton',command=self.refresh_student_link).pack(fill='x')

    def copy_student_link(self):
        link=self.secure_origin or self.student_origin
        self.root.clipboard_clear(); self.root.clipboard_append(link)
        self.status_label.config(text='Student link copied')
        self.apply_language(self.status_label)

    def refresh_student_link(self):
        try:
            info = self.client.json('/api/desktop-info')
            self.secure_origin = (info.get('public_origin') or '').strip()
            self.student_origin = self.client.base if self.remote else f'http://{lan_ip()}:{PORT}'
            if hasattr(self,'student_link_label') and self.student_link_label.winfo_exists():
                self.student_link_label.config(text=self.secure_origin or self.student_origin)
            self.status_label.config(text='Website link refreshed')
            self.apply_language(self.status_label)
        except Exception as ex:
            messagebox.showerror(APP_TITLE, self.tr('Request failed.')+"\n\n"+str(ex), parent=self.root)

    # ----- Schedule -----
    def page_schedule(self):
        actions=ttk.Frame(self.content,style='Soft.TFrame',padding=12); actions.pack(fill='x',pady=(0,10))
        ttk.Label(actions,text='Teaching schedule',style='Soft.TLabel',font=('Segoe UI',11,'bold')).pack(side='left')
        ttk.Label(actions,text='Timezone: '+self.studio_zone_name(),style='Soft.TLabel',foreground='#667982').pack(side='left',padx=(10,0))
        ttk.Button(actions,text='Add availability',style='Quiet.TButton',command=self.open_availability_dialog).pack(side='right')
        ttk.Button(actions,text='Post group lesson',style='Quiet.TButton',command=self.open_group_class_dialog).pack(side='right',padx=(0,8))
        cal=ttk.Frame(self.content,style='Card.TFrame',padding=12); cal.pack(fill='both',expand=True)
        bar=ttk.Frame(cal,style='Card.TFrame'); bar.pack(fill='x')
        ttk.Label(bar,text='Weekly calendar',style='Card.TLabel',font=('Segoe UI',13,'bold')).pack(side='left')
        ttk.Button(bar,text='← Previous',command=lambda:self.shift_week(-1)).pack(side='right',padx=(5,0))
        ttk.Button(bar,text='Next →',command=lambda:self.shift_week(1)).pack(side='right')
        self.week_label=ttk.Label(bar,text='',style='Card.TLabel',foreground='#66767d'); self.week_label.pack(side='right',padx=12)
        cwrap=ttk.Frame(cal,style='Card.TFrame'); cwrap.pack(fill='both',expand=True,pady=(10,0))
        self.calendar_canvas=tk.Canvas(cwrap,bg='white',highlightthickness=0,bd=0)
        sy=ttk.Scrollbar(cwrap,orient='vertical',command=self.calendar_canvas.yview)
        self.calendar_canvas.configure(yscrollcommand=sy.set)
        sy.pack(side='right',fill='y'); self.calendar_canvas.pack(fill='both',expand=True)
        self._calendar_resize_after=None
        def _queue_redraw(event=None):
            if self._calendar_resize_after:
                try: self.root.after_cancel(self._calendar_resize_after)
                except Exception: pass
            self._calendar_resize_after=self.root.after(80,self.draw_calendar)
        cwrap.bind('<Configure>', _queue_redraw)
        self.draw_calendar()

    def open_availability_dialog(self):
        win=tk.Toplevel(self.root);win.title(self.tr('Add private availability'));win._mathstudio_title='Add private availability';win.transient(self.root)
        w=min(760,max(520,int(self.root.winfo_width()*0.62)));h=420
        win.geometry(f'{w}x{h}')
        frame=self._availability_card(win);frame.pack(fill='both',expand=True,padx=16,pady=16)
        ttk.Label(win,text='Timezone: '+self.studio_zone_name()).pack(pady=(0,6))
        ttk.Button(win,text='Close',command=win.destroy).pack(pady=(0,14))
        self.apply_language(win)

    def open_group_class_dialog(self):
        win=tk.Toplevel(self.root);win.title(self.tr('Post group lesson'));win._mathstudio_title='Post group lesson';win.transient(self.root)
        w=min(820,max(560,int(self.root.winfo_width()*0.68)));h=600
        win.geometry(f'{w}x{h}')
        frame=self._group_class_card(win);frame.pack(fill='both',expand=True,padx=16,pady=16)
        ttk.Label(win,text='Timezone: '+self.studio_zone_name()).pack(pady=(0,6))
        ttk.Button(win,text='Close',command=win.destroy).pack(pady=(0,14))
        self.apply_language(win)

    def _availability_card(self,parent):
        f=ttk.Frame(parent,style='Card.TFrame',padding=16)
        ttk.Label(f,text='Add private availability',style='Card.TLabel',font=('Segoe UI',12,'bold')).grid(row=0,column=0,columnspan=4,sticky='w')
        ttk.Label(f,text='Students can fit a 60/90-minute lesson inside this open block.',style='Card.TLabel',foreground='#66767d').grid(row=1,column=0,columnspan=4,sticky='w',pady=(2,10))
        today=datetime.now(studio_zone(self.studio_zone_name()))+timedelta(minutes=30); m=((today.minute+14)//15)*15
        if m>=60: today=today.replace(minute=0)+timedelta(hours=1)
        else: today=today.replace(minute=m,second=0,microsecond=0)
        end=today+timedelta(hours=2)
        date_var=tk.StringVar(value=today.strftime('%Y-%m-%d')); start_var=tk.StringVar(value=today.strftime('%H:%M')); end_date=tk.StringVar(value=end.strftime('%Y-%m-%d')); end_var=tk.StringVar(value=end.strftime('%H:%M')); weeks=tk.IntVar(value=1)
        vals=quarter_values()
        for col,(label,var) in enumerate([('Date',date_var),('From',start_var),('Until date',end_date),('Until',end_var)]):
            ttk.Label(f,text=label,style='Card.TLabel').grid(row=2,column=col,sticky='w',padx=(0,6))
            if 'date' in label.lower() or label=='Date': w=ttk.Entry(f,textvariable=var,width=12)
            else: w=ttk.Combobox(f,textvariable=var,values=vals,state='readonly',width=9)
            w.grid(row=3,column=col,sticky='ew',padx=(0,6),pady=(2,8))
        ttk.Label(f,text='Repeat weeks',style='Card.TLabel').grid(row=4,column=0,sticky='w')
        ttk.Spinbox(f,from_=1,to=24,textvariable=weeks,width=8).grid(row=5,column=0,sticky='w',pady=(2,8))
        def add():
            try:
                st=parse_local(date_var.get(),start_var.get(),self.studio_zone_name()); en=parse_local(end_date.get(),end_var.get(),self.studio_zone_name())
                self.client.json('/api/admin/availability',{'start':st,'end':en,'repeat_weekly':weeks.get()>1,'weeks':weeks.get()})
                self.refresh_all(); messagebox.showinfo(APP_TITLE,self.tr('Availability added.'),parent=self.root)
            except Exception as ex: messagebox.showerror(APP_TITLE,self.tr('Request failed.')+"\n\n"+str(ex),parent=self.root)
        ttk.Button(f,text='Add to schedule',command=add).grid(row=5,column=1,columnspan=3,sticky='e')
        for i in range(4):f.columnconfigure(i,weight=1)
        return f

    def _group_class_card(self,parent):
        f=ttk.Frame(parent,style='Card.TFrame',padding=16)
        ttk.Label(f,text='Post a group lesson',style='Card.TLabel',font=('Segoe UI',12,'bold')).grid(row=0,column=0,columnspan=4,sticky='w')
        ttk.Label(f,text='Students reserve seats; everyone is added to the lesson group chat.',style='Card.TLabel',foreground='#66767d').grid(row=1,column=0,columnspan=4,sticky='w',pady=(2,10))
        title=tk.StringVar(value=''); datev=tk.StringVar(value=(datetime.now(studio_zone(self.studio_zone_name()))+timedelta(days=1)).strftime('%Y-%m-%d')); timev=tk.StringVar(value='16:00'); cap=tk.IntVar(value=4); price=tk.StringVar(value='Price TBD'); weeks=tk.IntVar(value=1)
        lessons=self.schedule.get('lesson_types',[])
        lesson_labels=[f"{x['name']} — {x['minutes']} min" for x in lessons]
        lessonvar=tk.StringVar(value=lesson_labels[0] if lesson_labels else '')
        ttk.Label(f,text='Class name',style='Card.TLabel').grid(row=2,column=0,sticky='w'); ttk.Entry(f,textvariable=title).grid(row=3,column=0,columnspan=2,sticky='ew',padx=(0,6),pady=(2,7))
        ttk.Label(f,text='Lesson type',style='Card.TLabel').grid(row=2,column=2,sticky='w'); ttk.Combobox(f,textvariable=lessonvar,values=lesson_labels,state='readonly').grid(row=3,column=2,columnspan=2,sticky='ew',pady=(2,7))
        for col,(lab,var,kind) in enumerate([('Date',datev,'entry'),('Time',timev,'time'),('Seats',cap,'spin'),('Repeat weeks',weeks,'spin')]):
            ttk.Label(f,text=lab,style='Card.TLabel').grid(row=4,column=col,sticky='w')
            if kind=='entry': w=ttk.Entry(f,textvariable=var,width=12)
            elif kind=='time': w=ttk.Combobox(f,textvariable=var,values=quarter_values(),state='readonly',width=9)
            else: w=ttk.Spinbox(f,from_=2 if lab=='Seats' else 1,to=5 if lab=='Seats' else 24,textvariable=var,width=8)
            w.grid(row=5,column=col,sticky='ew',padx=(0,6),pady=(2,7))
        ttk.Label(f,text='Price label',style='Card.TLabel').grid(row=6,column=0,sticky='w'); ttk.Entry(f,textvariable=price).grid(row=7,column=0,columnspan=2,sticky='ew',padx=(0,6))
        desc=tk.StringVar(value='Small-group lesson'); ttk.Label(f,text='Description',style='Card.TLabel').grid(row=6,column=2,sticky='w'); ttk.Entry(f,textvariable=desc).grid(row=7,column=2,columnspan=2,sticky='ew')
        def post():
            try:
                idx=lesson_labels.index(lessonvar.get()); lesson=lessons[idx]
                payload={'title':title.get().strip(),'lesson_type_id':lesson['id'],'start':parse_local(datev.get(),timev.get(),self.studio_zone_name()),'capacity':cap.get(),'price_label':price.get().strip() or 'Price TBD','description':desc.get().strip() or 'Small-group lesson','repeat_weekly':weeks.get()>1,'weeks':weeks.get()}
                out=self.client.json('/api/admin/group-class',payload); self.refresh_all(); messagebox.showinfo(APP_TITLE,self.tr('Posted {0} group lesson(s).').format(out.get('created', 1)),parent=self.root)
            except Exception as ex: messagebox.showerror(APP_TITLE,self.tr('Request failed.')+"\n\n"+str(ex),parent=self.root)
        ttk.Button(f,text='Post group lesson',command=post).grid(row=8,column=0,columnspan=4,sticky='e',pady=(10,0))
        for i in range(4):f.columnconfigure(i,weight=1)
        return f

    def shift_week(self,delta): self.week_offset+=delta; self.draw_calendar()
    def draw_calendar(self):
        c=self.calendar_canvas; c.delete('all')
        zone=studio_zone(self.studio_zone_name())
        now=datetime.now(zone); monday=(now-timedelta(days=now.weekday())).replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(weeks=self.week_offset)
        self.week_label.config(text=(f"{monday.strftime('%Y年%m月%d日')} – {(monday+timedelta(days=6)).strftime('%Y年%m月%d日')}" if self.lang=='zh' else f"{monday.strftime('%b %d')} – {(monday+timedelta(days=6)).strftime('%b %d, %Y')}"))

        def round_rect(x1,y1,x2,y2,r=10,**kwargs):
            r=max(0,min(r,(x2-x1)/2,(y2-y1)/2))
            points=[x1+r,y1, x2-r,y1, x2,y1, x2,y1+r, x2,y2-r, x2,y2, x2-r,y2, x1+r,y2, x1,y2, x1,y2-r, x1,y1+r, x1,y1]
            return c.create_polygon(points, smooth=True, splinesteps=24, **kwargs)

        head=62; rowh=24; start_hour=7; end_hour=22; rows=(end_hour-start_hour)*4
        left=86
        available_width=max(560, c.winfo_width() or 0)
        usable=max(455, available_width-left-8)
        colw=max(65, int(usable/7))
        totalw=left+7*colw+2; totalh=head+rows*rowh+2
        c.configure(scrollregion=(0,0,totalw,totalh))
        c.create_rectangle(0,0,totalw,totalh,fill='#f7fafb',outline='')
        round_rect(4,4,totalw-4,totalh-4,r=16,fill='white',outline='#dbe4e7')
        c.create_text(16,head/2,text=self.tr('TIME'),anchor='w',fill='#718087',font=('Segoe UI',8,'bold'))
        for d in range(7):
            x=left+d*colw; day=monday+timedelta(days=d)
            fill='#eef8f6' if day.date()==now.date() else '#f7f9fa'
            round_rect(x+2,6,x+colw-2,head-4,r=12,fill=fill,outline='#d9e2e4')
            c.create_text(x+colw/2,20,text=(('周一','周二','周三','周四','周五','周六','周日')[d] if self.lang=='zh' else day.strftime('%a').upper()),fill='#52646b',font=('Segoe UI',8,'bold'))
            c.create_text(x+colw/2,40,text=(day.strftime('%m月%d日') if self.lang=='zh' else day.strftime('%d %b')),fill='#102a2e',font=('Segoe UI',10,'bold'))
        for r in range(rows+1):
            y=head+r*rowh; mins=start_hour*60+r*15
            strong=(mins%60==0); c.create_line(left,y,totalw-2,y,fill='#d7e1e3' if strong else '#edf1f2')
            if strong and r<rows:
                h=mins//60; label=(f'{h:02d}:00' if self.lang=='zh' else datetime(2000,1,1,h,0).strftime('%I:%M %p').lstrip('0'))
                c.create_text(14,y+4,text=label,anchor='nw',fill='#627279',font=('Segoe UI',8))
        for d in range(8): c.create_line(left+d*colw,head,left+d*colw,totalh-2,fill='#dce4e6')
        week_start=monday.timestamp(); week_end=(monday+timedelta(days=7)).timestamp()
        for a in self.schedule.get('availability',[]):
            st=float(a['start']); en=float(a['end'])
            if en<=week_start or st>=week_end: continue
            ds=datetime.fromtimestamp(st,zone); de=datetime.fromtimestamp(en,zone); day=(ds.date()-monday.date()).days
            if not 0<=day<7: continue
            sm=ds.hour*60+ds.minute; em=de.hour*60+de.minute
            y1=head+((sm-start_hour*60)/15)*rowh; y2=head+((em-start_hour*60)/15)*rowh
            x1=left+day*colw+5; x2=x1+colw-10
            round_rect(x1,y1,x2,y2,r=11,fill='#e9f7f3',outline='#95cfc2')
            c.create_text(x1+8,y1+7,text=self.tr('Available'),anchor='nw',fill='#287d70',font=('Segoe UI',8,'bold'))
        for cl in self.admin.get('calendar_classes',[]):
            st=float(cl['start'])
            if not week_start<=st<week_end or cl.get('status')!='scheduled': continue
            ds=datetime.fromtimestamp(st,zone); day=(ds.date()-monday.date()).days
            if not 0<=day<7: continue
            sm=ds.hour*60+ds.minute; y1=head+((sm-start_hour*60)/15)*rowh; y2=y1+(float(cl.get('minutes',60))/15)*rowh
            x1=left+day*colw+6; x2=x1+colw-12
            pending=cl.get('approval')=='pending'; group=cl.get('class_kind')=='group'
            fill='#fff5df' if pending else '#e7efff' if not group else '#f0e9ff'; outline='#d8a746' if pending else '#86a9e8' if not group else '#b69ae9'
            round_rect(x1,y1,x2,y2,r=11,fill=fill,outline=outline,width=1)
            names=', '.join(a.get('name','') for a in cl.get('attendees',[])) or self.tr('No student yet')
            text=f"{cl.get('title','Class')}\n{names}"
            c.create_text(x1+8,y1+7,text=text,anchor='nw',width=colw-26,fill='#1b2f34',font=('Segoe UI',8,'bold'))

    # ----- Bookings -----
    def page_bookings(self):
        pending=[b for b in self.admin.get('bookings',[]) if b.get('approval')=='pending' and b.get('status')=='scheduled']
        confirmed=[cl for cl in sorted(self.admin.get('calendar_classes',[]),key=lambda x:x.get('start',0)) if cl.get('status')=='scheduled' and cl.get('approval')=='confirmed']

        shell=tk.Frame(self.content,bg='#f2f5f7');shell.pack(fill='both',expand=True)
        canvas=tk.Canvas(shell,bg='#f2f5f7',highlightthickness=0,bd=0)
        scroll=ttk.Scrollbar(shell,orient='vertical',command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
        body=tk.Frame(canvas,bg='#f2f5f7')
        win=canvas.create_window((0,0),window=body,anchor='nw')
        body.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(win,width=e.width))
        canvas.bind('<MouseWheel>',lambda e:canvas.yview_scroll(int(-1*(e.delta/120)),'units'))

        summary=tk.Frame(body,bg='#f2f5f7');summary.pack(fill='x',pady=(0,16))
        summary.columnconfigure(0,weight=1);summary.columnconfigure(1,weight=1)
        for col,(title,value,note,color) in enumerate([
            ('Pending requests',len(pending),'Needs your review','#d9912b'),
            ('Confirmed classes',len(confirmed),'Ready to teach','#0f766e')]):
            card=self.card(summary,title,value,note,color);card.grid(row=0,column=col,sticky='nsew',padx=(0,8) if col==0 else (8,0))

        pending_frame=ttk.Frame(body,style='Card.TFrame',padding=20);pending_frame.pack(fill='x',pady=(0,16))
        ph=ttk.Frame(pending_frame,style='Card.TFrame');ph.pack(fill='x')
        ttk.Label(ph,text='Pending private requests',style='Card.TLabel',font=('Segoe UI',13,'bold')).pack(side='left')
        tk.Label(ph,text=f'{len(pending)} waiting',bg='white',fg='#8a641d',font=('Segoe UI',9,'bold')).pack(side='right')
        if pending:
            ttk.Label(pending_frame,text='Select a request, then choose an action below.',style='Card.TLabel',foreground='#6a7b83').pack(anchor='w',pady=(3,10))
            cols=('student','class','date','minutes')
            self.pending_tree=ttk.Treeview(pending_frame,columns=cols,show='headings',height=max(2,min(5,len(pending))))
            for col,title,w in [('student','Student',170),('class','Lesson',280),('date','Date',210),('minutes','Length',90)]:
                self.pending_tree.heading(col,text=title); self.pending_tree.column(col,width=w,anchor='w',stretch=True)
            self.pending_tree.pack(fill='x',pady=(0,12))
            for b in pending:self.pending_tree.insert('', 'end', iid=str(b['class_id']), values=(b['name'],b['title'],self.fmt_time(b['start']),f"{b['minutes']} min"))
            actions=tk.Frame(pending_frame,bg='white');actions.pack(fill='x')
            self.action_button(actions,'Confirm',lambda:self.booking_action('confirm'),'primary').pack(side='left')
            self.action_button(actions,'Confirm weekly…',lambda:self.booking_action('confirm_weekly'),'secondary').pack(side='left',padx=8)
            self.action_button(actions,'Decline',lambda:self.booking_action('reject'),'danger').pack(side='left')
        else:
            empty=tk.Frame(pending_frame,bg='#f7fafb',highlightbackground='#e2e9eb',highlightthickness=1,padx=16,pady=14)
            empty.pack(fill='x',pady=(12,0))
            tk.Label(empty,text='✓',bg='#dff5ed',fg='#0f766e',font=('Segoe UI',11,'bold'),width=3).pack(side='left')
            copy=tk.Frame(empty,bg='#f7fafb');copy.pack(side='left',padx=(12,0))
            tk.Label(copy,text='No pending requests',bg='#f7fafb',fg='#20343c',font=('Segoe UI',10,'bold')).pack(anchor='w')
            tk.Label(copy,text='New private booking requests will appear here.',bg='#f7fafb',fg='#74858c',font=('Segoe UI',9)).pack(anchor='w')

        confirmed_frame=ttk.Frame(body,style='Card.TFrame',padding=20);confirmed_frame.pack(fill='x',pady=(0,8))
        ch=ttk.Frame(confirmed_frame,style='Card.TFrame');ch.pack(fill='x')
        ttk.Label(ch,text='Confirmed classes to handle',style='Card.TLabel',font=('Segoe UI',13,'bold')).pack(side='left')
        tk.Label(ch,text=f'{len(confirmed)} active',bg='white',fg='#0f766e',font=('Segoe UI',9,'bold')).pack(side='right')
        ttk.Label(confirmed_frame,text='Select a class to launch the teacher meeting, finish it, or cancel it.',style='Card.TLabel',foreground='#6a7b83').pack(anchor='w',pady=(3,10))
        ca=tk.Frame(confirmed_frame,bg='white');ca.pack(fill='x',pady=(0,12))
        self.action_button(ca,'Start teacher meeting',self.start_selected_meeting,'primary').pack(side='left')
        self.action_button(ca,'End class',lambda:self.class_action('end'),'secondary').pack(side='left',padx=8)
        self.action_button(ca,'Cancel class',lambda:self.class_action('cancel'),'danger').pack(side='left')
        self.confirmed_tree=ttk.Treeview(confirmed_frame,columns=('class','students','date','kind','status'),show='headings',height=max(4,min(9,len(confirmed)+1)))
        for col,title,w in [('class','Class',260),('students','Booked by',260),('date','Scheduled',205),('kind','Type',90),('status','Meeting',105)]:
            self.confirmed_tree.heading(col,text=title); self.confirmed_tree.column(col,width=w,anchor='w',stretch=True)
        self.confirmed_tree.pack(fill='x')
        for cl in confirmed:
            names=', '.join(a.get('name','') for a in cl.get('attendees',[])) or ('Join by code' if cl.get('class_kind')=='instant' else 'No students yet')
            self.confirmed_tree.insert('', 'end', iid=str(cl['id']), values=(cl['title'],names,self.fmt_time(cl['start']),'Instant' if cl.get('class_kind')=='instant' else 'Group' if cl.get('class_kind')=='group' else 'Private','Open' if cl.get('live') else 'Closed'))

    def booking_action(self,action):
        tree=getattr(self,'pending_tree',None); sel=tree.selection() if tree else []
        if not sel: return messagebox.showinfo(APP_TITLE,self.tr('Select a pending request first.'),parent=self.root)
        weeks=1
        if action=='confirm_weekly':
            weeks=simpledialog.askinteger(self.tr('Weekly confirmation'),self.tr('How many weeks total?'),parent=self.root,minvalue=2,maxvalue=24,initialvalue=8)
            if not weeks:return
        if action=='reject' and not messagebox.askyesno(APP_TITLE,self.tr('Decline this booking request?'),parent=self.root):return
        try:
            self.client.json('/api/admin/booking-action',{'class_id':int(sel[0]),'action':action,'weeks':weeks}); self.refresh_all()
        except Exception as ex: messagebox.showerror(APP_TITLE,self.tr('Request failed.')+"\n\n"+str(ex),parent=self.root)

    def class_action(self,action):
        sel=self.confirmed_tree.selection()
        if not sel:return messagebox.showinfo(APP_TITLE,self.tr('Select a class first.'),parent=self.root)
        if action=='cancel' and not messagebox.askyesno(APP_TITLE,self.tr('Cancel this class?'),parent=self.root):return
        try:self.client.json('/api/admin/class-action',{'class_id':int(sel[0]),'action':action});self.refresh_all()
        except Exception as ex:messagebox.showerror(APP_TITLE,self.tr('Request failed.')+"\n\n"+str(ex),parent=self.root)

    # ----- Students -----
    def page_students(self):
        ttk.Label(self.content,text='Registered accounts',style='H2.TLabel').pack(anchor='w')
        ttk.Label(self.content,text='Select several students to create a persistent group chat.',style='Muted.TLabel').pack(anchor='w',pady=(2,10))
        self.users_tree=ttk.Treeview(self.content,columns=('name','username','role','bookings','groups'),show='headings',selectmode='extended')
        for col,title,w in [('name','Name',220),('username','Username',170),('role','Role',100),('bookings','Bookings',90),('groups','Groups',90)]: self.users_tree.heading(col,text=title);self.users_tree.column(col,width=w,anchor='w')
        self.users_tree.pack(fill='both',expand=True)
        for u in self.admin.get('users',[]): self.users_tree.insert('', 'end', iid=str(u['id']), values=(u['name'],u['username'],u['role'],u.get('booking_count',0),u.get('group_count',0)))
        a=ttk.Frame(self.content);a.pack(fill='x',pady=(8,0))
        ttk.Button(a,text='Create group chat from selection',command=self.create_group_from_users).pack(side='left')
        ttk.Button(a,text='Make admin',command=lambda:self.change_role('admin')).pack(side='left',padx=6)
        ttk.Button(a,text='Make student',command=lambda:self.change_role('student')).pack(side='left')

    def selected_user_ids(self):
        return [int(x) for x in self.users_tree.selection()]
    def create_group_from_users(self):
        ids=self.selected_user_ids()
        if not ids:return messagebox.showinfo(APP_TITLE,self.tr('Select at least one student.'),parent=self.root)
        name=simpledialog.askstring(self.tr('Create group chat'),self.tr('Group name:'),parent=self.root)
        if not name:return
        try:self.client.json('/api/admin/groups/create',{'name':name.strip(),'user_ids':ids});self.refresh_all();self.show_page('groups')
        except Exception as ex:messagebox.showerror(APP_TITLE,self.tr('Request failed.')+"\n\n"+str(ex),parent=self.root)
    def change_role(self,role):
        sel=self.users_tree.selection()
        if len(sel)!=1:return messagebox.showinfo(APP_TITLE,self.tr('Select exactly one account.'),parent=self.root)
        try:self.client.json('/api/admin/role',{'user_id':int(sel[0]),'role':role});self.refresh_all()
        except Exception as ex:messagebox.showerror(APP_TITLE,self.tr('Request failed.')+"\n\n"+str(ex),parent=self.root)

    # ----- Groups & messages -----
    def page_groups(self):
        paned=ttk.Panedwindow(self.content,orient='horizontal');paned.pack(fill='both',expand=True)
        left=ttk.Frame(paned,style='Card.TFrame',padding=10);right=ttk.Frame(paned,style='Card.TFrame',padding=12)
        paned.add(left,weight=1);paned.add(right,weight=3)
        ttk.Label(left,text='Groups',style='Card.TLabel',font=('Segoe UI',12,'bold')).pack(anchor='w',pady=(0,8))
        self.groups_tree=ttk.Treeview(left,columns=('members',),show='tree headings',height=20)
        self.groups_tree.heading('#0',text='Conversation');self.groups_tree.heading('members',text='People');self.groups_tree.column('#0',width=220);self.groups_tree.column('members',width=70)
        self.groups_tree.pack(fill='both',expand=True)
        group_parent=self.groups_tree.insert('', 'end', iid='section-groups', text='GROUP CHATS', open=True, values=('',))
        for g in self.admin.get('groups',[]):self.groups_tree.insert(group_parent, 'end', iid='g-'+str(g['id']), text=g['name'], values=(g.get('member_count',len(g.get('members',[]))),))
        lesson_parent=self.groups_tree.insert('', 'end', iid='section-lessons', text='LESSON CHATS', open=True, values=('',))
        seen=set()
        for cl in sorted(self.admin.get('calendar_classes',[]),key=lambda x:x.get('start',0),reverse=True):
            if cl['id'] in seen: continue
            seen.add(cl['id']); count=len(cl.get('attendees',[]))
            if count: self.groups_tree.insert(lesson_parent,'end',iid='c-'+str(cl['id']),text=f"{cl['title']} · {datetime.fromtimestamp(cl['start'],studio_zone(self.studio_zone_name())).strftime('%b %d')}",values=(count,))
        self.groups_tree.bind('<<TreeviewSelect>>',lambda e:self.load_group_chat())
        ttk.Button(left,text='Delete selected custom group',command=self.delete_group).pack(fill='x',pady=(8,0))
        ttk.Label(right,text='Persistent group chat',style='Card.TLabel',font=('Segoe UI',12,'bold')).pack(anchor='w')
        self.group_members=ttk.Label(right,text='Select a group',style='Card.TLabel',foreground='#66767d');self.group_members.pack(anchor='w',pady=(2,8))
        self.chat_text=tk.Text(right,state='disabled',wrap='word',bg='white',relief='flat',font=('Segoe UI',10));self.chat_text.pack(fill='both',expand=True)
        send=ttk.Frame(right,style='Card.TFrame');send.pack(fill='x',pady=(8,0))
        self.chat_entry=ttk.Entry(send);self.chat_entry.pack(side='left',fill='x',expand=True,padx=(0,6));self.chat_entry.bind('<Return>',lambda e:(self.send_group_message(),'break')[1])
        ttk.Button(send,text='Send',command=self.send_group_message).pack(side='right')

    def load_group_chat(self):
        sel=self.groups_tree.selection()
        if not sel or sel[0].startswith('section-'):return
        key=sel[0]
        self.active_chat_type='group' if key.startswith('g-') else 'class'
        self.active_chat_id=int(key.split('-',1)[1])
        self.active_group_id=self.active_chat_id if self.active_chat_type=='group' else None
        if self.active_chat_type=='group':
            group=next((g for g in self.admin.get('groups',[]) if g['id']==self.active_chat_id),None)
            if group:self.group_members.config(text=self.tr('Members: ')+', '.join(m['name'] for m in group.get('members',[])))
        else:
            cl=next((c for c in self.admin.get('calendar_classes',[]) if c['id']==self.active_chat_id),None)
            if cl:self.group_members.config(text=self.tr('Lesson: ')+cl['title']+' · '+', '.join(a.get('name','') for a in cl.get('attendees',[])))
        self.refresh_group_messages()
    def refresh_group_messages(self):
        if self.message_poll_job:
            try: self.root.after_cancel(self.message_poll_job)
            except Exception: pass
            self.message_poll_job=None
        if not self.active_chat_id:return
        key=(self.active_chat_type,self.active_chat_id)
        changed=key!=getattr(self,'_chat_key',None)
        since=0 if changed else self._chat_seq
        if changed:
            self.chat_text.config(state='normal');self.chat_text.delete('1.0','end')
            self.chat_text.config(state='disabled')
            self._chat_key=key;self._chat_seq=0
        delay=4000
        try:
            if self.active_chat_type=='group':
                out=self.client.json(f'/api/group-messages?group={self.active_chat_id}&since={since}')
            else:
                out=self.client.json(f'/api/messages?class={self.active_chat_id}&since={since}')
            messages=out.get('messages',[]); next_seq=out.get('seq',since)
            if messages and next_seq<=since: raise ValueError('Message cursor did not advance')
            rendered=[]
            for m in messages:
                stamp=datetime.fromtimestamp(float(m['at']),studio_zone(self.studio_zone_name())).strftime('%b %d %I:%M %p')
                codes='  [resource: '+', '.join(x['code'] for x in m['codes'])+']' if m.get('codes') else ''
                rendered.append(f"{m['name']} · {stamp}{codes}\n{m['text']}\n\n")
            self.chat_text.config(state='normal')
            if rendered:
                self.chat_text.insert('end',''.join(rendered));self.chat_text.see('end')
            self._chat_key=key;self._chat_seq=next_seq
            if len(messages)==300: delay=10
        except Exception:
            self.status_label.config(text=self.tr('● Connection problem'))
        finally:
            self.chat_text.config(state='disabled')
        self.message_poll_job=self.root.after(delay,self.refresh_group_messages)
    def send_group_message(self):
        if not self.active_chat_id:return
        text=self.chat_entry.get().strip()
        if not text:return
        try:
            if self.active_chat_type=='group':self.client.json('/api/group-messages/send',{'group_id':self.active_chat_id,'text':text})
            else:self.client.json('/api/messages/send',{'class_id':self.active_chat_id,'text':text})
            self.chat_entry.delete(0,'end');self.refresh_group_messages()
        except Exception as ex:messagebox.showerror(APP_TITLE,self.tr('Request failed.')+"\n\n"+str(ex),parent=self.root)
    def delete_group(self):
        sel=self.groups_tree.selection()
        if not sel or not sel[0].startswith('g-'):
            return messagebox.showinfo(APP_TITLE,self.tr('Select a custom group chat. Lesson chats are tied to their class and cannot be deleted here.'),parent=self.root)
        gid=int(sel[0].split('-',1)[1])
        if not messagebox.askyesno(APP_TITLE,self.tr('Delete this group and its chat history?'),parent=self.root):return
        try:self.client.json('/api/admin/groups/delete',{'group_id':gid});self.refresh_all()
        except Exception as ex:messagebox.showerror(APP_TITLE,self.tr('Request failed.')+"\n\n"+str(ex),parent=self.root)

    # ----- Files -----
    def page_files(self):
        toolbar=ttk.Frame(self.content);toolbar.pack(fill='x',pady=(0,8))
        ttk.Button(toolbar,text='Upload files…',command=self.upload_files).pack(side='left')
        ttk.Button(toolbar,text='Generate code from selected',command=self.generate_code).pack(side='left',padx=6)
        ttk.Button(toolbar,text='Delete selected file',command=self.delete_file).pack(side='left')
        storage=self.file_info.get('storage',{});content_label(ttk.Label, toolbar,text=f"Storage: {storage.get('label','Local')} ",style='Muted.TLabel').pack(side='right')
        paned=ttk.Panedwindow(self.content,orient='vertical');paned.pack(fill='both',expand=True)
        ff=ttk.Frame(paned,style='Card.TFrame',padding=10);cf=ttk.Frame(paned,style='Card.TFrame',padding=10);paned.add(ff,weight=3);paned.add(cf,weight=2)
        ttk.Label(ff,text='File library',style='Card.TLabel',font=('Segoe UI',12,'bold')).pack(anchor='w')
        self.files_tree=ttk.Treeview(ff,columns=('name','size','codes'),show='headings',selectmode='extended')
        for col,title,w in [('name','File',520),('size','Size',100),('codes','Codes',70)]:self.files_tree.heading(col,text=title);self.files_tree.column(col,width=w,anchor='w')
        self.files_tree.pack(fill='both',expand=True,pady=(8,0))
        for f in self.file_info.get('files',[]):self.files_tree.insert('', 'end',iid=str(f['id']),values=(f['name'],self.human_size(f.get('size',0)),f.get('code_count',0)))
        ttk.Label(cf,text='Access codes',style='Card.TLabel',font=('Segoe UI',12,'bold')).pack(anchor='w')
        self.codes_tree=ttk.Treeview(cf,columns=('code','label','files','status','translation'),show='headings')
        for col,title,w in [('code','Code',105),('label','Label',300),('files','Files',65),('status','Status',85),('translation','Translation',95)]:self.codes_tree.heading(col,text=title);self.codes_tree.column(col,width=w,anchor='w')
        self.codes_tree.pack(fill='both',expand=True,pady=(8,8))
        for code in self.file_info.get('codes',[]):self.codes_tree.insert('', 'end',iid=str(code['id']),values=(code['code'],code['label'],len(code.get('files',[])),'Active' if code.get('active') else 'Revoked','On' if code.get('translate_enabled') else 'Off'))
        ca=ttk.Frame(cf,style='Card.TFrame');ca.pack(fill='x')
        ttk.Button(ca,text='Revoke',style='Danger.TButton',command=lambda:self.code_action('revoke')).pack(side='left')
        ttk.Button(ca,text='Restore',style='Quiet.TButton',command=lambda:self.code_action('restore')).pack(side='left',padx=6)
        ttk.Button(ca,text='Enable translation',style='Quiet.TButton',command=lambda:self.code_action('enable_translate')).pack(side='left',padx=(8,4))
        ttk.Button(ca,text='Disable translation',style='Quiet.TButton',command=lambda:self.code_action('disable_translate')).pack(side='left')

    @staticmethod
    def human_size(n):
        n=float(n or 0)
        for unit in ('B','KB','MB','GB'):
            if n<1024 or unit=='GB':return f'{n:.0f} {unit}' if unit=='B' else f'{n:.1f} {unit}'
            n/=1024
    def upload_files(self):
        paths=filedialog.askopenfilenames(parent=self.root,title=self.tr('Upload teacher files'))
        if not paths:return
        try:
            for p in paths:
                self.status_label.config(text='Uploading '+Path(p).name);self.root.update_idletasks();self.client.upload_file(Path(p))
            self.refresh_all();messagebox.showinfo(APP_TITLE,self.tr('Uploaded {0} file(s).').format(len(paths)),parent=self.root)
        except Exception as ex:messagebox.showerror(APP_TITLE,self.tr('Request failed.')+"\n\n"+str(ex),parent=self.root)
    def generate_code(self):
        ids=[int(x) for x in self.files_tree.selection()]
        if not ids:return messagebox.showinfo(APP_TITLE,self.tr('Select one or more files.'),parent=self.root)
        label=simpledialog.askstring(self.tr('Generate access code'),self.tr('Label for this file bundle:'),parent=self.root,initialvalue='Shared files')
        if label is None:return
        translate_enabled=messagebox.askyesno(self.tr('Document translation'),self.tr('Enable automatic English/Chinese document translation for this share code?\n\nStudents will see a translated reading view when the file type is supported. Translation uses an online translation service.'),parent=self.root)
        try:
            out=self.client.json('/api/admin/files/code',{'file_ids':ids,'label':label,'translate_enabled':translate_enabled});self.refresh_all();
            self.root.clipboard_clear();self.root.clipboard_append(out['code']);messagebox.showinfo(APP_TITLE,self.tr('Access code: {0}\n\nTranslation: {1}\nThe code was copied to the clipboard.').format(out['code'], self.tr('On' if translate_enabled else 'Off')),parent=self.root)
        except Exception as ex:messagebox.showerror(APP_TITLE,self.tr('Request failed.')+"\n\n"+str(ex),parent=self.root)
    def code_action(self,action):
        sel=self.codes_tree.selection()
        if not sel:return
        try:self.client.json('/api/admin/files/code-action',{'code_id':int(sel[0]),'action':action});self.refresh_all()
        except Exception as ex:messagebox.showerror(APP_TITLE,self.tr('Request failed.')+"\n\n"+str(ex),parent=self.root)
    def delete_file(self):
        sel=self.files_tree.selection()
        if len(sel)!=1:return messagebox.showinfo(APP_TITLE,self.tr('Select one file.'),parent=self.root)
        if not messagebox.askyesno(APP_TITLE,self.tr('Delete this file from storage?'),parent=self.root):return
        try:self.client.json('/api/admin/files/delete',{'file_id':int(sel[0])});self.refresh_all()
        except Exception as ex:messagebox.showerror(APP_TITLE,self.tr('Request failed.')+"\n\n"+str(ex),parent=self.root)

    # ----- Meetings -----
    def page_meetings(self):
        instant=tk.Frame(self.content,bg='#eaf7f4',highlightbackground='#b9ddd5',highlightthickness=1,padx=22,pady=18);instant.pack(fill='x',pady=(0,16))
        top=tk.Frame(instant,bg='#eaf7f4');top.pack(fill='x')
        tk.Label(top,text='Start an instant meeting',bg='#eaf7f4',fg='#14343a',font=('Segoe UI',14,'bold')).pack(side='left')
        self.action_button(top,'Start instant meeting',self.start_instant_meeting,'primary').pack(side='right')
        tk.Label(instant,text='No scheduled class is required. MathStudio creates a 10-digit code that students can use with an account or as a guest.',bg='#eaf7f4',fg='#60757b',font=('Segoe UI',9),wraplength=900,justify='left').pack(anchor='w',pady=(6,0))
        ttk.Label(self.content,text='Scheduled meetings',style='H2.TLabel').pack(anchor='w')
        ttk.Label(self.content,text='Select a confirmed class below, or use Instant Meeting above.',style='Muted.TLabel').pack(anchor='w',pady=(2,10))
        a=tk.Frame(self.content,bg='#f2f5f7');a.pack(fill='x',pady=(0,12))
        self.action_button(a,'Start selected meeting',self.start_selected_meeting,'primary').pack(side='left')
        self.action_button(a,'Copy share code',self.copy_selected_share_code,'secondary').pack(side='left',padx=8)
        self.action_button(a,'End class',lambda:self.meeting_class_action('end'),'secondary').pack(side='left',padx=(0,8))
        self.action_button(a,'Cancel class',lambda:self.meeting_class_action('cancel'),'danger').pack(side='left')
        self.meeting_tree=ttk.Treeview(self.content,columns=('title','students','code','date','status'),show='headings')
        for col,title,w in [('title','Class',260),('students','Students',260),('code','Share code',120),('date','Scheduled',190),('status','Status',105)]:self.meeting_tree.heading(col,text=title);self.meeting_tree.column(col,width=w,anchor='w',stretch=True)
        self.meeting_tree.pack(fill='both',expand=True)
        for cl in sorted(self.admin.get('calendar_classes',[]),key=lambda x:x.get('start',0)):
            if cl.get('status')=='scheduled' and cl.get('approval')=='confirmed':
                names=', '.join(a.get('name','') for a in cl.get('attendees',[])) or ('Join by code' if cl.get('class_kind')=='instant' else 'No students yet')
                late=time.time()>float(cl['start']);status='LIVE' if cl.get('live') else ('Late — ready to start' if late else 'Ready')
                self.meeting_tree.insert('', 'end',iid=str(cl['id']),values=(cl['title'],names,cl.get('share_code',''),self.fmt_time(cl['start']),status))

    def _launch_teacher_meeting(self, cid):
        remote=getattr(self,'remote',False)
        payload={'class_id':cid}
        if remote:payload['client_launch']=True
        out=self.client.json('/api/admin/teacher-app-launch',payload)
        if remote:
            # Native overlay runs on the teacher PC, never the separately hosted OWNER.
            command=[sys.executable,('--meeting-bootstrap' if getattr(sys,'frozen',False) else str(ROOT/'teacher_app_bootstrap.py')),'--server',self.client.base,
                '--token',out['token'],'--public-origin',self.client.base,'--skip-auto-media']
            try:
                subprocess.Popen(command,cwd=str(ROOT),close_fds=True,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                out.update(launched=True,already_running=False,launch_error='')
            except OSError:
                out.update(launched=False,already_running=False,launch_error=self.tr('Could not start the local teacher meeting. Check setup and diagnostics.'))
        return out

    def _open_full_classroom(self, url):
        """Open the same full classroom UI for instant and scheduled teacher meetings."""
        if not url:return
        candidates=[
            os.path.join(os.environ.get('PROGRAMFILES',''),'Google','Chrome','Application','chrome.exe'),
            os.path.join(os.environ.get('PROGRAMFILES(X86)',''),'Google','Chrome','Application','chrome.exe'),
            os.path.join(os.environ.get('LOCALAPPDATA',''),'Google','Chrome','Application','chrome.exe'),
            os.path.join(os.environ.get('PROGRAMFILES',''),'Microsoft','Edge','Application','msedge.exe'),
        ]
        browser=next((x for x in candidates if x and os.path.exists(x)),None)
        try:
            if browser:
                subprocess.Popen([browser,f'--app={url}','--window-size=1400,900'],close_fds=True)
            else:
                webbrowser.open(url,new=1,autoraise=True)
            self.status_label.config(text='Full classroom opened · updates automatically')
            self.apply_language(self.status_label)
        except Exception as ex:
            messagebox.showwarning(APP_TITLE,self.tr('The meeting started, but the classroom window could not open automatically.\n') + str(ex),parent=self.root)

    def start_instant_meeting(self):
        title=simpledialog.askstring(self.tr('Instant meeting'),self.tr('Meeting title:'),parent=self.root,initialvalue='Instant math meeting')
        if title is None:return
        try:
            instant=self.client.json('/api/admin/instant-meeting',{'title':title.strip() or 'Instant math meeting'})
            out=self._launch_teacher_meeting(instant['class_id'])
            self._open_full_classroom(out.get('browser_url',''))
            code=instant['code']
            self.root.clipboard_clear();self.root.clipboard_append(code)
            self.refresh_all()
            detail=self.tr('Your teacher meeting is opening now.\n\nShare code: {0}\n\nOnly students need this code. They can choose Join meeting and enter it signed in or as a guest.\n\nThe code was copied to your clipboard.').format(code)
            if not out.get('launched') and not out.get('already_running'):
                detail += self.tr('\n\nThe meeting was created, but the native meeting window did not open automatically: ')+out.get('launch_error','')
            messagebox.showinfo(self.tr('Instant meeting'),detail,parent=self.root)
        except Exception as ex:messagebox.showerror(APP_TITLE,self.tr('Request failed.')+"\n\n"+str(ex),parent=self.root)

    def copy_selected_share_code(self):
        tree=getattr(self,'meeting_tree',None);sel=tree.selection() if tree else []
        if not sel:return messagebox.showinfo(APP_TITLE,self.tr('Select an instant meeting first.'),parent=self.root)
        values=tree.item(sel[0],'values');code=str(values[2]) if len(values)>2 else ''
        if not code:return messagebox.showinfo(APP_TITLE,self.tr('That scheduled class does not use a share code.'),parent=self.root)
        self.root.clipboard_clear();self.root.clipboard_append(code);self.status_label.config(text='Share code copied')
        self.apply_language(self.status_label)

    def _selected_class_id(self):
        tree=getattr(self,'meeting_tree',None) if self.current_page=='meetings' else getattr(self,'confirmed_tree',None)
        sel=tree.selection() if tree else []
        return int(sel[0]) if sel else None
    def start_selected_meeting(self):
        cid=self._selected_class_id()
        if not cid:return messagebox.showinfo(APP_TITLE,self.tr('Select a confirmed class first.'),parent=self.root)
        try:
            out=self._launch_teacher_meeting(cid)
            self._open_full_classroom(out.get('browser_url',''))
            if not out.get('launched') and not out.get('already_running'):
                messagebox.showwarning(APP_TITLE,self.tr('The classroom opened, but the native meeting window could not be launched automatically.\n') + out.get('launch_error', ''),parent=self.root)
            else:self.status_label.config(text='Teacher meeting started')
            self.apply_language(self.status_label)
            self.refresh_all()
        except Exception as ex:messagebox.showerror(APP_TITLE,self.tr('Request failed.')+"\n\n"+str(ex),parent=self.root)
    def meeting_class_action(self,action):
        cid=self._selected_class_id()
        if not cid:return
        if action=='cancel' and not messagebox.askyesno(APP_TITLE,self.tr('Cancel this class?'),parent=self.root):return
        try:self.client.json('/api/admin/class-action',{'class_id':cid,'action':action});self.refresh_all()
        except Exception as ex:messagebox.showerror(APP_TITLE,self.tr('Request failed.')+"\n\n"+str(ex),parent=self.root)

    # ----- Settings -----
    def page_recordings(self):
        from teacher_recordings import Recordings
        Recordings(self.content,self.client,self.tr,self.fmt_time).pack(fill='both',expand=True)

    def page_website(self):
        from teacher_website import WebsiteManagement
        self.website_editor=WebsiteManagement(self.content,self.client,self.tr,self.show_page)
        self.website_editor.pack(fill='both',expand=True)

    def page_settings(self):
        if getattr(self,'remote',False):
            connection=ttk.Frame(self.content,style='Card.TFrame',padding=12)
            connection.pack(fill='x',pady=(0,12))
            ttk.Label(connection,text='OWNER server connection',style='Card.TLabel').pack(side='left')
            content_label(ttk.Label,connection,text=self.client.base,style='Card.TLabel').pack(side='left',padx=12)
            ttk.Button(connection,text='Change OWNER server',command=self.change_owner_server).pack(side='right')
        timezone=tk.StringVar(value=self.public.get('settings',{}).get('timezone','America/Edmonton'))
        ttk.Label(self.content,text=self.tr('Timezone')).pack(anchor='w',pady=(8,2))
        ttk.Combobox(self.content,textvariable=timezone,values=['America/Edmonton','America/Vancouver','America/Toronto','UTC'],state='readonly').pack(anchor='w')
        def save():
            try:
                self.client.json('/api/admin/settings',{'timezone':timezone.get()});self.refresh_all()
            except Exception as ex:messagebox.showerror(APP_TITLE,self.tr('Request failed.')+'\n\n'+str(ex),parent=self.root)
        ttk.Button(self.content,text=self.tr('Save studio timezone'),command=save).pack(anchor='w',pady=12)
        ttk.Button(self.content,text=self.tr('Website Management'),command=lambda:self.show_page('website')).pack(anchor='w')
        ttk.Button(self.content,text=self.tr('Disable Remember Me on this device'),command=self.disable_remember).pack(anchor='w',pady=8)

    def disable_remember(self):
        self.auth_task(self.client.forget_remembered,
                       lambda _:messagebox.showinfo(APP_TITLE,self.tr('Remember Me disabled. Your next app restart will require login.'),parent=self.root),
                       lambda error:messagebox.showerror(APP_TITLE,self.tr(error),parent=self.root))

    def change_owner_server(self):
        if getattr(self,'_auth_busy',False):return
        if not messagebox.askyesno(APP_TITLE,self.tr('Change OWNER server? Finish active lessons first. This signs you out of the dashboard.'),parent=self.root):return
        try:self.client.logout()
        except Exception:
            # A changed Quick Tunnel address must remain recoverable offline.
            desktop_credentials.forget(self.client.base)
            self.client.jar.clear();self.client.user=None;self.client.csrf=''
            messagebox.showwarning(APP_TITLE,self.tr('Previous OWNER is unreachable. Local Remember Me was cleared; remote logout is unconfirmed. Reset the OWNER password to revoke old devices if needed.'),parent=self.root)
        origin=select_origin(force=True)
        if not origin or origin==self.client.base:self.show_login();return
        for name in ('message_poll_job','_active_poll_job'):
            job=getattr(self,name,None)
            if job:
                try:self.root.after_cancel(job)
                except Exception:pass
                setattr(self,name,None)
        os.environ['MATHSTUDIO_SERVER_URL']=origin
        self.client=APIClient(origin)
        self.student_origin=origin;self.secure_origin=''
        self.current_page='';self.active_chat_id=None;self.active_group_id=None;self._active_signature=None
        self.admin={};self.schedule={};self.file_info={};self.public={};self.classes=[]
        self._bootstrap()

    def sign_out(self):
        def done(_):
            for name in ('message_poll_job','_active_poll_job'):
                job=getattr(self,name,None)
                if job:
                    try:self.root.after_cancel(job)
                    except Exception:pass
                    setattr(self,name,None)
            self.show_login()
        self.auth_task(self.client.logout,done,lambda error:messagebox.showerror(APP_TITLE,self.tr('Could not confirm logout. Check your connection and retry.'),parent=self.root))
    def on_close(self):
        if messagebox.askokcancel(self.tr('Exit MathStudio Teacher'),self.tr('Close the Teacher App? The student website will keep running separately.'),parent=self.root):
            self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    try:
        TeacherDesktopApp().run()
    except Exception:
        details = traceback.format_exc()
        try:
            log=state_directory()/'teacher_app_error.log';log.parent.mkdir(parents=True,exist_ok=True)
            log.write_text(details, encoding='utf-8')
        except Exception:
            pass
        try:
            ctypes.windll.user32.MessageBoxW(None, 'MathStudio Teacher App could not start.\n\n' + details[-5000:] + '\n\nA copy was saved to teacher_app_error.log.', 'MathStudio Teacher App', 0x10)
        except Exception:
            print(details)
        raise
