"""OWNER-only first pairing and revocable desktop credentials. No model imports."""
import hashlib
import hmac
import secrets
import time

PAIRING = None
LIFETIME = 30*86400
IDLE = 7*86400


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


class Pairing:
    def __init__(self):
        self.code = secrets.token_hex(16)
        self.verifier = digest(self.code)
        self.expires = time.time()+900

    def valid(self, code):
        return (isinstance(code, str) and len(code) == 32 and self.expires > time.time()
                and hmac.compare_digest(self.verifier, digest(code.strip())))

    def consume(self):
        self.verifier = ''
        self.code = ''
        self.expires = 0


def schema(connection):
    connection.execute('''CREATE TABLE IF NOT EXISTS desktop_credentials(
        selector TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        verifier TEXT NOT NULL, device TEXT NOT NULL, password_stamp TEXT NOT NULL,
        expires REAL NOT NULL, idle REAL NOT NULL)''')
    if connection.execute("SELECT 1 FROM users WHERE role='admin'").fetchone():
        connection.execute("INSERT OR REPLACE INTO settings VALUES ('owner_initialized','1')")


def initialized(connection):
    return bool(connection.execute("SELECT 1 FROM settings WHERE key='owner_initialized' AND value='1'").fetchone()
                or connection.execute("SELECT 1 FROM users WHERE role='admin'").fetchone())


def issue(connection, user, device):
    now = time.time()
    connection.execute('DELETE FROM desktop_credentials WHERE expires<=? OR idle<=?', (now, now))
    count = connection.execute('SELECT COUNT(*) FROM desktop_credentials WHERE user_id=?', (user['id'],)).fetchone()[0]
    if count >= 10:
        raise ValueError('Too many remembered devices. Sign out on another device first.')
    selector = secrets.token_hex(16); secret = secrets.token_urlsafe(32)
    connection.execute('INSERT INTO desktop_credentials VALUES (?,?,?,?,?,?,?)',
                       (selector, user['id'], digest(secret), digest(device), digest(user['password']), now+LIFETIME, now+IDLE))
    return selector+'.'+secret


def rotate(connection, token, device):
    """Caller holds BEGIN IMMEDIATE. Commit revocation even on replay/failure."""
    selector, separator, secret = token.partition('.')
    row = connection.execute('SELECT * FROM desktop_credentials WHERE selector=?', (selector,)).fetchone()
    if not row:return None
    user = connection.execute('SELECT * FROM users WHERE id=?', (row['user_id'],)).fetchone()
    now = time.time()
    valid = (separator and user and user['role']=='admin' and row['expires']>now and row['idle']>now
             and hmac.compare_digest(row['verifier'], digest(secret))
             and hmac.compare_digest(row['device'], digest(device))
             and hmac.compare_digest(row['password_stamp'], digest(user['password'])))
    if not valid:
        connection.execute('DELETE FROM desktop_credentials WHERE selector=?', (selector,))
        return None
    secret = secrets.token_urlsafe(32)
    connection.execute('UPDATE desktop_credentials SET verifier=?,idle=? WHERE selector=?',
                       (digest(secret), min(row['expires'], now+IDLE), selector))
    return user, selector+'.'+secret


def session_valid(connection, selector, user):
    row=connection.execute('SELECT * FROM desktop_credentials WHERE selector=?', (selector,)).fetchone()
    now=time.time()
    return bool(row and user and row['user_id']==user['id'] and user['role']=='admin'
                and row['expires']>now and row['idle']>now
                and hmac.compare_digest(row['password_stamp'],digest(user['password'])))


def pairing_window(code):
    """GUI only: never put the pairing code in command lines, URLs or logs."""
    import json
    import queue
    import subprocess
    import sys
    import threading
    from pathlib import Path
    from owner_launcher import OwnedProcess
    child=OwnedProcess([sys.executable,str(Path(__file__).resolve()),'--pairing-window'],
                       stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                       creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        child.proc.stdin.write(json.dumps({'code':code}).encode('utf-8'))
        child.proc.stdin.close()
        result=queue.Queue()
        threading.Thread(target=lambda:result.put(child.proc.stdout.readline(16)),daemon=True).start()
        if result.get(timeout=8)!=b'READY\n':raise RuntimeError()
        return child
    except Exception:
        child.close()
        raise RuntimeError('Could not open local OWNER pairing window. Install Python with Tcl/Tk and retry; no account was created.') from None


if __name__=='__main__':
    import json
    import sys
    import tkinter as tk
    request=json.loads(sys.stdin.buffer.read(256))
    code=request['code']
    if not isinstance(code,str) or len(code)!=32:raise SystemExit(1)
    root=tk.Tk();root.title('MathStudio OWNER pairing / 教师配对')
    tk.Label(root,text='Enter this one-time code in the Teacher App only.\n仅在教师应用中输入此一次性配对码。\nExpires in 15 minutes; restart OWNER to renew. / 15 分钟有效。',padx=24,pady=20).pack()
    entry=tk.Entry(root,width=36,font=('Consolas',16));entry.insert(0,code);entry.configure(state='readonly');entry.pack(padx=24,pady=12)
    tk.Label(root,text='Do not share it with visitors. No password is requested here.\n请勿与访客分享；此处不要求输入密码。',padx=20,pady=20).pack()
    root.update();sys.stdout.buffer.write(b'READY\n');sys.stdout.buffer.flush()
    root.mainloop()
