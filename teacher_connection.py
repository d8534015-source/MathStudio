"""Teacher-only connection settings. No backend hosting or credential storage."""
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
from runtime_paths import state_directory

ROOT=Path(__file__).resolve().parent


def teacher_only():
    marker=ROOT/'package_role.json'
    return marker.is_file() and json.loads(marker.read_text())['role']=='teacher-remote'


def validate_origin(value):
    value=value.strip().rstrip('/')
    parts=urlsplit(value)
    try:port=parts.port
    except ValueError:raise ValueError('Invalid OWNER server port.') from None
    if (parts.scheme!='https' or not parts.hostname or parts.username is not None or parts.password is not None
        or parts.path or parts.query or parts.fragment or any(ord(ch)<33 for ch in value)):
        raise ValueError('Enter the OWNER HTTPS origin only, for example https://mathstudio.example.org (no password, path or query).')
    return value


def connection_path():
    return state_directory()/'teacher_connection.json'


def configured_origin():
    if os.environ.get('MATHSTUDIO_SERVER_URL'):return validate_origin(os.environ['MATHSTUDIO_SERVER_URL'])
    path=connection_path()
    if path.is_file():return validate_origin(json.loads(path.read_text())['server_url'])
    return ''


def check_connection(origin):
    """Verify TLS, origin and the matching OWNER build before persisting a URL."""
    from urllib.request import Request,urlopen
    from build_info import BUILD_ID
    try:
        with urlopen(Request(origin+'/api/desktop-info',headers={'Accept':'application/json'}),timeout=6) as response:
            final=urlsplit(response.geturl())
            if final.scheme!='https' or final.netloc!=urlsplit(origin).netloc:
                raise ValueError('OWNER redirected to a different origin.')
            data=response.read(65537)
            if len(data)>65536 or json.loads(data).get('build')!=BUILD_ID:
                raise ValueError('OWNER build mismatch.')
    except Exception:
        raise ValueError('Cannot connect to the matching OWNER HTTPS backend. Check the address, trusted certificate and OWNER version. / 无法连接对应版本的 OWNER HTTPS 服务器，请检查地址、可信证书及版本。') from None
    return origin


def select_origin(force=False):
    current=configured_origin()
    if current and not force:return current
    import tkinter as tk
    from tkinter import simpledialog,messagebox
    root=tk.Tk();root.withdraw()
    try:
        while True:
            value=simpledialog.askstring('MathStudio OWNER / 服务器',
                'Enter the OWNER HTTPS address / 输入 OWNER HTTPS 地址：',initialvalue=current,parent=root)
            if value is None:return ''
            try:origin=check_connection(validate_origin(value))
            except ValueError as ex:messagebox.showerror('MathStudio',str(ex),parent=root);continue
            path=connection_path();path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps({'server_url':origin})+'\n',encoding='utf-8')
            return origin
    finally:root.destroy()
