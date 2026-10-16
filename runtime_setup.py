"""Explicit setup and launch entry point; no dependency changes during lessons."""
import argparse
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import sys
import venv
from dependency_check import verify_runtime
from private_config import apply_config
from teacher_connection import teacher_only, select_origin

ROOT=Path(__file__).resolve().parent
VENV=ROOT/'.venv'


def runtime_python():
    return VENV/('Scripts/python.exe' if os.name=='nt' else 'bin/python')


def install(wheelhouse=None):
    if not (3,12)<=sys.version_info[:2]<(3,15):
        raise RuntimeError('Install current supported 64-bit CPython 3.12, 3.13 or 3.14 from python.org, with Tcl/Tk and pip.')
    if struct.calcsize('P')!=8:raise RuntimeError('Install 64-bit CPython.')
    try:
        with socket.create_connection(('127.0.0.1',5051),timeout=.5):
            raise RuntimeError('Port 5051 is in use. Finish all classes and stop MathStudio before installing dependencies.')
    except OSError:pass
    if VENV.exists() and not (VENV/'pyvenv.cfg').is_file():raise RuntimeError('Refusing to replace a folder that is not a Python environment.')
    if VENV.is_symlink():raise RuntimeError('The runtime folder must not be a symbolic link.')
    venv.EnvBuilder(with_pip=True,clear=VENV.exists()).create(VENV)
    command=[str(runtime_python()),'-m','pip','install','--disable-pip-version-check',
             '--require-hashes','--only-binary=:all:']
    if wheelhouse:command+=['--no-index','--find-links',str(Path(wheelhouse).resolve())]
    else:command+=['--index-url','https://pypi.org/simple']
    subprocess.run([*command,'-r',str(ROOT/'requirements.txt')],cwd=ROOT,check=True)
    subprocess.run([str(runtime_python()),'-m','pip','check'],cwd=ROOT,check=True)
    subprocess.run([str(runtime_python()),str(__file__),'--verify'],cwd=ROOT,check=True)
    print('Setup verified. Double-click OPEN MATHSTUDIO TEACHER.bat. No VS Code is required.')


def cloudflared_available():
    return bool(shutil.which('cloudflared.exe') or shutil.which('cloudflared') or any(
        (Path(os.environ.get(key,''))/'cloudflared'/'cloudflared.exe').is_file()
        for key in ('ProgramFiles','ProgramFiles(x86)','LOCALAPPDATA')))


def launch(kind):
    verify_runtime(gui=kind=='teacher')
    if teacher_only():
        if kind!='teacher':raise RuntimeError('Teacher Ready connects to OWNER; it cannot host the backend.')
        origin=select_origin()
        if not origin:return 0
        env=os.environ.copy();env['MATHSTUDIO_SERVER_URL']=origin;env['MATHSTUDIO_REMOTE']='1'
    else:
        env=apply_config(os.environ.copy())
    env['PORT']='5051'
    if kind=='website' and cloudflared_available():
        env['MATH_PYTHON']=str(runtime_python())
        return subprocess.call(['powershell.exe','-NoProfile','-File',str(ROOT/'start_https.ps1')],cwd=ROOT,env=env)
    script='teacher_desktop_app.py' if kind=='teacher' else 'server.py'
    if kind!='teacher':env['BIND_HOST']='0.0.0.0'
    return subprocess.call([sys.executable,str(ROOT/script)],cwd=ROOT,env=env)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    action=parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--configure-owner',action='store_true');action.add_argument('--install',action='store_true');action.add_argument('--verify',action='store_true')
    action.add_argument('--launch',choices=('teacher','website','server'))
    parser.add_argument('--wheelhouse',type=Path)
    args=parser.parse_args()
    try:
        if args.configure_owner:select_origin(force=True);return 0
        if args.install:install(args.wheelhouse);return 0
        if args.verify:verify_runtime(gui=os.name=='nt');print('Runtime versions, timezone data and required imports verified.');return 0
        return launch(args.launch)
    except Exception as ex:
        print('MathStudio could not complete setup/launch: '+str(ex))
        print('Run SETUP MATHSTUDIO.bat before teaching. Do not reinstall during a live class.')
        return 1


if __name__=='__main__':raise SystemExit(main())
