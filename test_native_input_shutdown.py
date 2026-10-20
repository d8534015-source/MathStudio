"""Input exclusion and nonblocking native teardown. No physical-device claims."""
import ctypes,gc,queue,sys,threading,time,unittest
from types import SimpleNamespace,MethodType
from unittest import mock
from test_teaching_workflows import extracted_functions

class ShutdownTests(unittest.TestCase):
    def controller(self,http,answer=True):
        seen=[];callbacks=queue.Queue()
        ns=extracted_functions('teacher_meeting_app.py',{'request_end','close'},dict(threading=threading,time=time,http_json=http,messagebox=SimpleNamespace(askyesno=lambda *a,**k:answer),APP_NAME='Synthetic',tk=SimpleNamespace(TclError=RuntimeError)))
        obj=SimpleNamespace(ending=False,closed=False,connected=True,server='http://synthetic.invalid',token='synthetic',
            end_btn=SimpleNamespace(configure=lambda **k:None),status_var=SimpleNamespace(set=seen.append),tr=lambda x:x,
            ui_stopped=threading.Event(),post_ui=lambda fn,result:callbacks.put((fn,result)),screen_sharing=True,screen_stop=threading.Event(),
            release_pointer=lambda:seen.append('capture-released'),close_share_indicator=lambda:None,
            input_overlay=None,overlay=None,root=SimpleNamespace(destroy=lambda:seen.append('destroyed')),toolbar=None)
        for name in ('request_end','close'):setattr(obj,name,MethodType(ns[name],obj))
        return obj,seen,callbacks

    def test_unreachable_owner_cannot_block_local_cleanup_or_touch_tk_from_worker(self):
        entered,release=threading.Event(),threading.Event();main=threading.get_ident();threads=[]
        def http(*a,**k):threads.append(threading.get_ident());entered.set();release.wait(3);raise OSError('synthetic unavailable')
        obj,seen,q=self.controller(http)
        try:
            before=time.monotonic();obj.request_end();self.assertLess(time.monotonic()-before,.2);self.assertTrue(entered.wait(1))
            before=time.monotonic();obj.close(force=True);self.assertLess(time.monotonic()-before,.2)
            self.assertTrue(obj.ui_stopped.is_set());self.assertIn('capture-released',seen);self.assertIn('destroyed',seen)
            self.assertNotIn('Class ended.',seen);self.assertTrue(all(t!=main for t in threads))
        finally:release.set()

    def test_pending_response_is_not_reported_as_end_success_and_error_can_close_locally(self):
        obj,seen,q=self.controller(lambda *a,**k:(_ for _ in ()).throw(OSError('synthetic')))
        obj.screen_sharing=False;obj.request_end();fn,result=q.get(timeout=1);fn(result)
        self.assertIn('Could not confirm that the remote classroom ended.',seen);self.assertIn('destroyed',seen)
        self.assertNotIn('Class ended.',seen)

    def test_pending_recording_finalization_keeps_ui_open_until_explicit_server_ack(self):
        calls=[]
        def http(*a,**k):calls.append(1);return {'pending':True,'ok':False} if len(calls)==1 else {'ok':True}
        obj,seen,q=self.controller(http);obj.screen_sharing=False;obj.request_end()
        self.assertNotIn('Class ended.',seen);fn,result=q.get(timeout=2);fn(result)
        self.assertEqual(len(calls),2);self.assertIn('Class ended.',seen);self.assertTrue(obj.closed)

@unittest.skipUnless(sys.platform=='win32','Real Win32 hit-testing requires Windows')
class Win32InputTests(unittest.TestCase):
    def test_controls_remain_hittable_even_when_input_window_is_raised_and_moved(self):
        import tkinter as tk
        from ctypes import wintypes
        import teacher_meeting_app as native
        from native_input import exclude_windows
        root=tk.Tk();app=None
        try:
            root.geometry('360x160+30+30');root.attributes('-topmost',True)
            button=tk.Button(root,text='Interact');button.pack()
            ink=tk.Toplevel(root);ink.withdraw()
            surface=tk.Toplevel(root);surface.overrideredirect(True);surface.geometry('700x500+0+0');surface.attributes('-topmost',True);surface.attributes('-alpha',.01)
            canvas=tk.Canvas(surface);canvas.pack(fill='both',expand=True);root.update()
            u=native.user32;u.WindowFromPoint.argtypes=[wintypes.POINT];u.WindowFromPoint.restype=wintypes.HWND
            u.GetWindowRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)];u.GetWindowRect.restype=wintypes.BOOL
            def control_point(widget):
                rect=wintypes.RECT();self.assertTrue(u.GetWindowRect(widget.winfo_id(),ctypes.byref(rect)))
                self.assertGreater(rect.right,rect.left);self.assertGreater(rect.bottom,rect.top)
                return wintypes.POINT((rect.left+rect.right)//2,(rect.top+rect.bottom)//2)
            root_hwnd=u.GetAncestor(root.winfo_id(),native.GA_ROOT);input_hwnd=u.GetAncestor(surface.winfo_id(),native.GA_ROOT)
            def hit():
                p=control_point(button)
                hwnd=u.WindowFromPoint(p);return u.GetAncestor(hwnd,native.GA_ROOT)
            surface.lift();root.update()
            self.assertEqual(hit(),input_hwnd,'Baseline fullscreen input captures control coordinates when raised')
            app=native.TeacherMeetingApp.__new__(native.TeacherMeetingApp)
            app.root=app.toolbar=root;app.overlay=ink;app.input_overlay=surface;app.input_canvas=canvas;app.canvas=None;app.share_overlay=None
            app.closed=False;app.draw_mode=True;app.draft=None;app.region_pending=False;app.status_var=tk.StringVar(root);app.refresh_button_states=lambda:None
            surface.bind('<Escape>',lambda e:app.set_mode(False))
            for x in (30,130,70):
                root.geometry(f'360x160+{x}+30');root.update();self.assertTrue(app.protect_controls());surface.lift();root.update();self.assertEqual(hit(),root_hwnd)
            # An additional native control panel is excluded too.
            panel=tk.Toplevel(root);panel.transient(root);panel.geometry('150x100+450+40')
            panel_button=tk.Button(panel,text='Stop recording');panel_button.pack(fill='both',expand=True)
            panel.update();self.assertTrue(app.protect_controls());surface.lift();root.update()
            point=control_point(panel_button)
            # Check the native region separately from Z-order/hit-test delivery.
            gdi=ctypes.windll.gdi32
            u.GetWindowRgn.argtypes=[wintypes.HWND,wintypes.HRGN];u.GetWindowRgn.restype=ctypes.c_int
            gdi.PtInRegion.argtypes=[wintypes.HRGN,ctypes.c_int,ctypes.c_int];gdi.PtInRegion.restype=wintypes.BOOL
            region=gdi.CreateRectRgn(0,0,0,0);bounds=wintypes.RECT()
            try:
                self.assertTrue(u.GetWindowRgn(input_hwnd,region));u.GetWindowRect(input_hwnd,ctypes.byref(bounds))
                self.assertFalse(gdi.PtInRegion(region,point.x-bounds.left,point.y-bounds.top),'Mapped control must be outside installed input region')
            finally:gdi.DeleteObject(region)
            hit_root=u.GetAncestor(u.WindowFromPoint(point),native.GA_ROOT);panel_root=u.GetAncestor(panel.winfo_id(),native.GA_ROOT)
            category='input' if hit_root==input_hwnd else 'toolbar' if hit_root==root_hwnd else 'panel' if hit_root==panel_root else 'other'
            self.assertEqual(hit_root,panel_root,'Control target classification='+category)
            for _ in range(20):app.set_mode(False);app.set_mode(True);root.update()
            u.SetCapture.argtypes=[wintypes.HWND];u.SetCapture.restype=wintypes.HWND
            u.SetCapture(canvas.winfo_id());self.assertTrue(u.GetCapture())
            surface.focus_force();root.update();surface.event_generate('<Escape>');root.update()
            self.assertFalse(u.GetCapture());self.assertFalse(surface.winfo_ismapped());self.assertFalse(app.draw_mode)
        finally:
            root.destroy();app=None;root=None;gc.collect()
