"""Optional per-Windows-user remembered login. No password storage or fallback."""
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import secrets
import tempfile
from runtime_paths import state_directory


def available():
    return os.name=='nt'


def path_for(origin):
    return state_directory()/'remembered'/('owner-'+hashlib.sha256(origin.encode()).hexdigest()+'.bin')


def crypt(data, origin, decrypt=False):
    if not available():raise RuntimeError('Remember Me requires Windows DPAPI.')
    class Blob(ctypes.Structure):
        _fields_=[('length',wintypes.DWORD),('data',ctypes.POINTER(ctypes.c_ubyte))]
    def blob(value):
        buffer=ctypes.create_string_buffer(value)
        return buffer,Blob(len(value),ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte)))
    buffer,source=blob(data)
    salt,entropy=blob(('MathStudio desktop v1|'+str(state_directory())+'|'+origin).encode('utf-8'))
    result=Blob();library=ctypes.WinDLL('crypt32',use_last_error=True)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.LocalFree.argtypes=[ctypes.c_void_p];kernel.LocalFree.restype=ctypes.c_void_p
    # CRYPTPROTECT_UI_FORBIDDEN; current Windows user, never local-machine scope.
    if decrypt:
        method=library.CryptUnprotectData
        method.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
        args=(ctypes.byref(source),None,ctypes.byref(entropy),None,None,1,ctypes.byref(result))
    else:
        method=library.CryptProtectData
        method.argtypes=[ctypes.POINTER(Blob),wintypes.LPCWSTR,ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
        args=(ctypes.byref(source),'MathStudio remembered device',ctypes.byref(entropy),None,None,1,ctypes.byref(result))
    method.restype=wintypes.BOOL
    if not method(*args):raise RuntimeError('Windows could not protect or restore this device credential. Sign in again.')
    try:return ctypes.string_at(result.data,result.length)
    finally:kernel.LocalFree(result.data)


def save(origin, refresh, device):
    payload=json.dumps({'schema':1,'origin':origin,'refresh':refresh,'device':device}).encode('utf-8')
    encrypted=crypt(payload,origin)
    path=path_for(origin);path.parent.mkdir(parents=True,exist_ok=True)
    fd,temporary=tempfile.mkstemp(prefix='.credential-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as output:output.write(encrypted)
        os.replace(temporary,path)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)


def load(origin):
    path=path_for(origin)
    if not path.exists():return None
    if path.is_symlink() or path.stat().st_size>16384:raise RuntimeError('Invalid remembered credential. Sign in again.')
    value=json.loads(crypt(path.read_bytes(),origin,decrypt=True).decode('utf-8'))
    if (not isinstance(value,dict) or value.get('schema')!=1 or value.get('origin')!=origin
        or not isinstance(value.get('refresh'),str) or not 50<=len(value['refresh'])<=150
        or not isinstance(value.get('device'),str) or len(value['device'])!=64):
        raise RuntimeError('Invalid remembered credential. Sign in again.')
    return value


def forget(origin):
    path_for(origin).unlink(missing_ok=True)


def new_device():
    return secrets.token_hex(32)
