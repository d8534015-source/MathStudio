"""OWNER console launcher: no PowerShell, no adopted or unrelated processes."""
import json
import os
from pathlib import Path
import queue
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parent


def find_cloudflared():
    for name in ('cloudflared.exe','cloudflared'):
        found=shutil.which(name)
        if found:return found
    for key in ('ProgramFiles','ProgramFiles(x86)','LOCALAPPDATA'):
        if os.environ.get(key):
            p=Path(os.environ[key])/'cloudflared'/'cloudflared.exe'
            if p.is_file():return str(p)
    raise RuntimeError('Install official cloudflared, or use the LAN-only launcher.')


def existing_server(port=5051,allow_reuse=True):
    """Check before database initialization; never stop or change a running server."""
    try:
        with socket.create_connection(('127.0.0.1',port),timeout=.5):pass
    except OSError:return False
    if not allow_reuse:
        raise RuntimeError(f'Port {port} is occupied. No process or live lesson was changed.')
    from build_info import BUILD_ID
    try:
        with urlopen(f'http://127.0.0.1:{port}/api/desktop-info',timeout=3) as r:
            info=json.loads(r.read(65536))
        if info.get('build')==BUILD_ID and info.get('public_origin','').startswith('https://'):
            print('Reusing the running MathStudio OWNER: '+info['public_origin'],flush=True)
            return True
    except (OSError,ValueError):pass
    raise RuntimeError('Port 5051 is occupied. No process or live lesson was changed. Use the running OWNER or finish lessons and stop it first.')


class OwnedProcess:
    """Only the Popen child is stopped. Windows job handles console-close cleanup."""
    def __init__(self,command,**kwargs):
        self.proc=None;self.job=None
        if os.name=='nt':
            import ctypes
            from ctypes import wintypes as w
            class Basic(ctypes.Structure):
                _fields_=[('ProcessTime',ctypes.c_int64),('JobTime',ctypes.c_int64),('LimitFlags',w.DWORD),('Min',ctypes.c_size_t),('Max',ctypes.c_size_t),('Active',w.DWORD),('Affinity',ctypes.c_size_t),('Priority',w.DWORD),('Scheduling',w.DWORD)]
            class IO(ctypes.Structure):
                _fields_=[(name,ctypes.c_uint64) for name in ('ReadOps','WriteOps','OtherOps','ReadBytes','WriteBytes','OtherBytes')]
            class Limits(ctypes.Structure):
                _fields_=[('Basic',Basic),('IO',IO),('ProcessMemory',ctypes.c_size_t),('JobMemory',ctypes.c_size_t),('PeakProcess',ctypes.c_size_t),('PeakJob',ctypes.c_size_t)]
            self.kernel=ctypes.WinDLL('kernel32',use_last_error=True)
            self.kernel.CreateJobObjectW.argtypes=[ctypes.c_void_p,w.LPCWSTR];self.kernel.CreateJobObjectW.restype=w.HANDLE
            self.kernel.SetInformationJobObject.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD];self.kernel.SetInformationJobObject.restype=w.BOOL
            self.kernel.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE];self.kernel.AssignProcessToJobObject.restype=w.BOOL
            self.kernel.CloseHandle.argtypes=[w.HANDLE];self.kernel.CloseHandle.restype=w.BOOL
            self.job=self.kernel.CreateJobObjectW(None,None)
            limits=Limits();limits.Basic.LimitFlags=0x2000 # KILL_ON_JOB_CLOSE
            if not self.job or not self.kernel.SetInformationJobObject(self.job,9,ctypes.byref(limits),ctypes.sizeof(limits)):
                self.close();raise OSError('Unable to establish owned tunnel cleanup; no tunnel started.')
        try:
            self.proc=subprocess.Popen(command,**kwargs)
            if self.job and not self.kernel.AssignProcessToJobObject(self.job,int(self.proc._handle)):
                raise OSError('Unable to attach owned tunnel to cleanup job.')
        except BaseException:
            self.close();raise

    def close(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:self.proc.kill();self.proc.wait(timeout=5)
        if self.job:
            self.kernel.CloseHandle(self.job);self.job=None


def tunnel_origin(child,timeout=40):
    messages=queue.Queue()
    def drain():
        for line in child.proc.stdout:
            match=re.search(r'https://[a-z0-9-]+\.trycloudflare\.com',line,re.I)
            if match:messages.put(match[0])
    threading.Thread(target=drain,daemon=True).start()
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        try:return messages.get(timeout=.2)
        except queue.Empty:
            if child.proc.poll() is not None:break
    raise RuntimeError('Cloudflared did not provide an HTTPS address. Check Internet access and official cloudflared setup.')


def main(tunnel=True,env=None,port=5051,bind='0.0.0.0',reuse=True):
    if existing_server(port,allow_reuse=reuse):return 0
    if env is not None:os.environ.update(env)
    os.environ.update(PORT=str(port),BIND_HOST=bind)
    child=None
    try:
        if tunnel:
            child=OwnedProcess([find_cloudflared(),'tunnel','--url',f'http://127.0.0.1:{port}'],
                stdout=subprocess.PIPE,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,
                text=True,encoding='utf-8',errors='replace',
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            origin=tunnel_origin(child)
            os.environ['PUBLIC_ORIGIN']=origin
            os.environ['MATH_TRUSTED_PROXIES']='127.0.0.1/32,::1/128'
            print('OWNER HTTPS: '+origin+'\nTemporary addresses change after restart. Keep this window open.',flush=True)
        # No backend child exists: Ctrl+C and window close release this process's port.
        import server
        old_args=sys.argv
        try:
            sys.argv=[str(ROOT/'server.py')]
            server.main()
        finally:sys.argv=old_args
        return 0
    except KeyboardInterrupt:return 0
    finally:
        if child:child.close()


if __name__=='__main__':raise SystemExit(main())
