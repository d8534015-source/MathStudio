"""Keep the full-screen pen input surface out of native control-window bounds.

A clipped HWND cannot intercept a control click regardless of topmost/owner order.
Only the input surface is clipped; the shared ink coordinates remain unchanged.
"""
import ctypes
from ctypes import wintypes


def exclude_windows(surface,controls):
    user=ctypes.windll.user32;gdi=ctypes.windll.gdi32
    user.GetWindowRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)];user.GetWindowRect.restype=wintypes.BOOL
    user.SetWindowRgn.argtypes=[wintypes.HWND,wintypes.HRGN,wintypes.BOOL];user.SetWindowRgn.restype=ctypes.c_int
    gdi.CreateRectRgn.argtypes=[ctypes.c_int]*4;gdi.CreateRectRgn.restype=wintypes.HRGN
    gdi.CombineRgn.argtypes=[wintypes.HRGN]*3+[ctypes.c_int];gdi.CombineRgn.restype=ctypes.c_int
    gdi.DeleteObject.argtypes=[wintypes.HANDLE];gdi.DeleteObject.restype=wintypes.BOOL
    bounds=wintypes.RECT()
    if not user.GetWindowRect(surface,ctypes.byref(bounds)):raise RuntimeError('Pen input bounds unavailable.')
    region=gdi.CreateRectRgn(0,0,bounds.right-bounds.left,bounds.bottom-bounds.top)
    if not region:raise RuntimeError('Pen input region unavailable.')
    try:
        for hwnd in controls:
            rect=wintypes.RECT()
            if not user.GetWindowRect(hwnd,ctypes.byref(rect)):raise RuntimeError('Control window bounds unavailable.')
            hole=gdi.CreateRectRgn(rect.left-bounds.left,rect.top-bounds.top,rect.right-bounds.left,rect.bottom-bounds.top)
            if not hole:raise RuntimeError('Control exclusion unavailable.')
            try:
                if not gdi.CombineRgn(region,region,hole,4):raise RuntimeError('Control exclusion failed.')  # RGN_DIFF
            finally:gdi.DeleteObject(hole)
        if not user.SetWindowRgn(surface,region,True):raise RuntimeError('Pen input region could not be applied.')
        region=None  # Windows owns the successfully installed region.
    finally:
        if region:gdi.DeleteObject(region)
