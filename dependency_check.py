"""Verify the runtime against the reviewed, hash-locked requirements."""
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path
import re
import sys
import struct


def pinned_versions():
    return dict(re.findall(r'^([A-Za-z0-9_-]+)==([0-9][^\s\\]*)',
        Path(__file__).with_name('requirements.txt').read_text(encoding='utf-8'),re.M))


def require_distribution(name):
    expected=pinned_versions()[name]
    try:installed=version(name)
    except PackageNotFoundError:installed='missing'
    if installed!=expected:
        raise RuntimeError(f'{name} {expected} is required (installed: {installed}). Run SETUP MATHSTUDIO.bat before teaching.')


def verify_runtime(gui=False):
    if struct.calcsize("P")!=8:raise RuntimeError("Install 64-bit CPython for this release.")
    if not (3,12)<=sys.version_info[:2]<(3,15):
        raise RuntimeError('Use 64-bit CPython 3.12, 3.13 or 3.14; the Windows installer must include Tcl/Tk and pip.')
    for name in pinned_versions():require_distribution(name)
    from PIL import Image, ImageGrab
    from pypdf import PdfReader
    from studio_time import studio_zone
    for name in ('America/Edmonton','America/Vancouver','America/Toronto','Asia/Shanghai'):studio_zone(name)
    if gui:
        import tkinter
        root=tkinter.Tk();root.withdraw();root.destroy()
