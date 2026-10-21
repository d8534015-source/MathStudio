"""Measured wrapping toolbar layout. Coordinates use Tk's current DPI units."""
import ctypes
import sys
from ctypes import wintypes


def work_area(widget):
    if sys.platform == 'win32':
        class MonitorInfo(ctypes.Structure):
            _fields_ = [('size', wintypes.DWORD), ('monitor', wintypes.RECT),
                        ('work', wintypes.RECT), ('flags', wintypes.DWORD)]
        user = ctypes.windll.user32
        user.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
        user.MonitorFromWindow.restype = wintypes.HANDLE
        user.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]
        user.GetMonitorInfoW.restype = wintypes.BOOL
        info = MonitorInfo(); info.size = ctypes.sizeof(info)
        monitor = user.MonitorFromWindow(widget.winfo_id(), 2)
        if user.GetMonitorInfoW(monitor, ctypes.byref(info)):
            r = info.work
            return r.left, r.top, r.right, r.bottom
    return 0, 0, widget.winfo_screenwidth(), widget.winfo_screenheight()


class ToolbarLayout:
    def __init__(self, root, containers, changed):
        self.root, self.containers, self.changed = root, containers, changed
        self.pending = None
        self.busy = False
        self.children = {box: list(box.winfo_children()) for box in containers}
        for box, children in self.children.items():
            for child in children:
                child.pack_forget()
                # Labels may wrap, controls never truncate their text.
                if child.winfo_class() == 'Label': child.configure(wraplength=350)
        root.bind('<Configure>', self.schedule, add='+')
        self.fit(initial=True)

    def schedule(self, event=None):
        if event is not None and event.widget != self.root: return
        if self.busy or self.pending: return
        self.pending = self.root.after_idle(self.fit)

    def fit(self, initial=False):
        self.pending = None
        if self.busy: return
        self.busy = True
        try:
            root = self.root
            root.update_idletasks()
            left, top, right, bottom = work_area(root)
            # Leave space for Windows non-client borders and the caption.
            max_width, max_height = right-left-24, bottom-top-64
            natural = max(sum(w.winfo_reqwidth()+8 for w in children)+56 for children in self.children.values())
            minimum = max(w.winfo_reqwidth()+56 for children in self.children.values() for w in children if w not in self.containers)
            width = min(max_width, max(minimum, natural if initial else root.winfo_width()))
            # Place measured controls into independent flow rows. A shared Tk grid
            # would align columns across rows and can itself reintroduce clipping.
            for box in self.containers:  # nested meeting buttons precede their parent
                padding=int(box.cget('padx'))+4
                available=width-56
                x=padding; y=int(box.cget('pady'))+3; row_height=0; extent=0
                for child in self.children[box]:
                    cw,ch=child.winfo_reqwidth(),child.winfo_reqheight()
                    if x>padding and x+cw+padding>available:
                        y+=row_height+6; x=padding; row_height=0
                    child.place(x=x,y=y,width=cw,height=ch)
                    x+=cw+8; extent=max(extent,x+padding);row_height=max(row_height,ch)
                box.configure(width=extent,height=y+row_height+int(box.cget('pady'))+3)
                root.update_idletasks()
            root.update_idletasks()
            height = max(root.winfo_reqheight(), root.winfo_height() if not initial else 0)
            # Essential controls set the minimum; user width/height above this survives.
            root.minsize(min(minimum,max_width), min(root.winfo_reqheight(),max_height))
            x = max(left,min(root.winfo_x() if not initial else left+24,right-width-12))
            y = max(top,min(root.winfo_y() if not initial else top+24,bottom-min(height,max_height)-40))
            target=f'{width}x{min(height,max_height)}+{x}+{y}'
            if (root.winfo_width(),root.winfo_height(),root.winfo_x(),root.winfo_y()) != (width,min(height,max_height),x,y): root.geometry(target)
            self.changed()
        finally:
            self.busy=False
