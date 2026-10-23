"""Measured horizontal toolbar layout with a narrow-monitor fallback.

Coordinates use Tk's current DPI units.
"""
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
        self.applied_size = None
        self.user_width = self.user_height = None
        self.children = {box: list(box.winfo_children()) for box in containers}
        for box, children in self.children.items():
            for child in children:
                child.pack_forget()
        root.bind('<Configure>', self.schedule, add='+')
        self.fit(initial=True)

    def schedule(self, event=None):
        if event is not None and event.widget != self.root: return
        if self.busy: return
        if event is not None and self.applied_size is not None:
            if event.width != self.applied_size[0]: self.user_width = event.width
            if event.height != self.applied_size[1]: self.user_height = event.height
        if self.pending: return
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
            gap = 6
            sizes = {}

            def padding(box):
                border = int(box.cget('highlightthickness')) + int(box.cget('borderwidth'))
                return int(box.cget('padx'))+border+4, int(box.cget('pady'))+border+3

            def measure(box):
                # Measure the entire nested row before choosing the window width.
                # A container emptied by pack_forget reports a stale/one-pixel request.
                px, py = padding(box)
                children = self.children[box]
                dims = [measure(child) if child in self.children else
                        (child.winfo_reqwidth(), child.winfo_reqheight()) for child in children]
                sizes[box] = (2*px + sum(w for w,h in dims) + gap*max(0,len(dims)-1),
                              2*py + max((h for w,h in dims),default=0))
                return sizes[box]

            outer = [box for box in self.containers if box.master not in self.children]
            margins = {box: 2*int(box.pack_info().get('padx',0)) for box in outer}
            natural = max(measure(box)[0]+margins[box] for box in outer)
            minimum = max(w.winfo_reqwidth()+64 for children in self.children.values()
                          for w in children if w not in self.children and w.winfo_class()!='Label')
            desired = natural if initial or self.user_width is None else self.user_width
            width = min(max_width,max(minimum,desired))

            def arrange(box,budget):
                px,py = padding(box)
                x,y,row_height,extent = px,py,0,0
                for child in self.children[box]:
                    cw,ch = sizes[child] if child in sizes else (child.winfo_reqwidth(),child.winfo_reqheight())
                    if x>px and x+cw+px>budget:
                        y+=row_height+gap; x=px;row_height=0
                    if child in self.children:
                        cw,ch=arrange(child,min(cw,budget-2*px))
                    elif child.winfo_class()=='Label' and cw>budget-2*px:
                        child.configure(wraplength=max(1,budget-2*px))
                        root.update_idletasks();cw,ch=child.winfo_reqwidth(),child.winfo_reqheight()
                    child.place(x=x,y=y,width=cw,height=ch)
                    x+=cw+gap;extent=max(extent,x-gap+px);row_height=max(row_height,ch)
                height=y+row_height+py
                box.configure(width=extent,height=height)
                return extent,height

            for box in outer: arrange(box,width-margins[box])
            root.update_idletasks()
            required_height=root.winfo_reqheight()
            height=max(required_height,self.user_height or 0)
            root.minsize(min(minimum,max_width),min(required_height,max_height))
            x = max(left,min(root.winfo_x() if not initial else left+24,right-width-12))
            y = max(top,min(root.winfo_y() if not initial else top+24,bottom-min(height,max_height)-40))
            target=f'{width}x{min(height,max_height)}+{x}+{y}'
            self.applied_size=(width,min(height,max_height))
            if (root.winfo_width(),root.winfo_height(),root.winfo_x(),root.winfo_y()) != (width,min(height,max_height),x,y): root.geometry(target)
            self.changed()
        finally:
            self.busy=False
