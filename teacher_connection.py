"""Teacher-only connection settings. No backend hosting or credential storage."""
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
from runtime_paths import state_directory

ROOT=Path(__file__).resolve().parent


def teacher_only():
    if getattr(__import__('sys'),'frozen',False):return True
    marker=ROOT/'package_role.json'
    return marker.is_file() and json.loads(marker.read_text(encoding='utf-8'))['role']=='teacher-remote'


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
    if path.is_file():return validate_origin(json.loads(path.read_text(encoding='utf-8'))['server_url'])
    return ''


class ConnectionProblem(ValueError):
    def __init__(self, code, message):
        self.code=code
        super().__init__(message)


def check_connection(origin):
    """TLS-verified, credential-free OWNER health check; never probe local ports."""
    import socket
    import ssl
    from urllib.error import HTTPError, URLError
    from urllib.request import Request,urlopen
    from build_info import BUILD_ID
    origin=validate_origin(origin)
    try:
        with urlopen(Request(origin+'/api/desktop-info',headers={'Accept':'application/json'}),timeout=6) as response:
            final=urlsplit(response.geturl())
            expected=urlsplit(origin)
            if final.scheme!='https' or final.netloc.lower()!=expected.netloc.lower():
                raise ConnectionProblem('redirect','OWNER redirected to another address. Enter the current OWNER HTTPS address.')
            data=response.read(65537)
            try:
                if len(data)>65536:raise ValueError()
                info=json.loads(data)
                if not isinstance(info,dict) or not info.get('build'):raise ValueError()
            except (ValueError,TypeError):
                raise ConnectionProblem('response','This address did not return a MathStudio OWNER response. Check the tunnel and address.') from None
            if info['build']!=BUILD_ID:
                raise ConnectionProblem('build','OWNER and Teacher Ready builds do not match. Ask the owner to install the matching package.')
    except HTTPError as ex:
        if ex.code in (401,403):
            raise ConnectionProblem('auth','The OWNER gateway requires authentication. Ask the owner to check gateway access; teacher login is separate.') from None
        if ex.code in (502,503,504,530):
            raise ConnectionProblem('owner','The HTTPS gateway is reachable, but OWNER is unavailable. Ask the owner to check the backend and tunnel.') from None
        raise ConnectionProblem('http','The OWNER address returned an HTTP error. Check the current server address.') from None
    except (URLError,OSError) as ex:
        reason=getattr(ex,'reason',ex)
        if isinstance(reason,ssl.SSLCertVerificationError):
            raise ConnectionProblem('tls','The OWNER TLS certificate could not be verified. Ask the owner to repair HTTPS; do not disable certificate checks.') from None
        if isinstance(reason,(socket.timeout,TimeoutError)):
            raise ConnectionProblem('timeout','The OWNER connection timed out. Check your Internet connection, then retry or update the tunnel address.') from None
        raise ConnectionProblem('network','The OWNER address could not be reached. Check Internet access and the current tunnel address, then retry.') from None
    return origin


def select_origin(force=False):
    invalid_saved=False
    try:current=configured_origin()
    except (ValueError,KeyError,TypeError,OSError):current='';invalid_saved=True
    if current and not force:return current
    import tkinter as tk
    from tkinter import simpledialog,messagebox
    root=tk.Tk();root.withdraw()
    try:
        if invalid_saved:
            messagebox.showerror('MathStudio', 'Saved OWNER settings are invalid or unreadable. Enter the current OWNER HTTPS address. / 已保存的 OWNER 设置无效或无法读取，请输入当前 OWNER HTTPS 地址。',parent=root)
        while True:
            value=simpledialog.askstring('MathStudio OWNER / 服务器',
                'Enter the OWNER HTTPS address / 输入 OWNER HTTPS 地址：',initialvalue=current,parent=root)
            if value is None:return ''
            try:origin=check_connection(validate_origin(value))
            except ValueError as ex:messagebox.showerror('MathStudio',str(ex)+'\n\n'+__import__('teacher_localization').translate(str(ex),'zh'),parent=root);continue
            path=connection_path();path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps({'server_url':origin})+'\n',encoding='utf-8')
            return origin
    finally:root.destroy()
