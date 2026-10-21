"""Real Tk geometry; Windows monitor/hit testing remains covered separately."""
import tkinter as tk
import unittest
from types import SimpleNamespace,MethodType
from unittest import mock
from native_toolbar import ToolbarLayout
from test_teaching_workflows import extracted_functions
from teacher_localization import translate

class ToolbarTests(unittest.TestCase):
    def test_real_controls_fit_first_launch_dpi_languages_narrow_monitor_and_resize(self):
        ns=extracted_functions('teacher_meeting_app.py',{'build_toolbar','make_button'},dict(tk=tk))
        for scale,width,lang in ((1,1920,'en'),(1.5,1280,'zh'),(2,1024,'en'),(2,768,'zh')):
            with self.subTest(scale=scale,width=width,lang=lang):
                root=tk.Tk();root.withdraw();root.tk.call('tk','scaling',scale)
                try:
                    obj=SimpleNamespace(toolbar=root,BG='#111111',PANEL='#222222',PANEL_2='#333333',TEXT='#ffffff',MUTED='#cccccc',BORDER='#444444',ACCENT_DARK='#555555',DANGER='#aa0000',lang=lang,
                        status_var=tk.StringVar(root,value='Connected'),people_var=tk.StringVar(root,value='Students: 12'),tool_buttons={},color_buttons={},width_buttons={},tr=lambda x:translate(x,lang))
                    for name in ('send_media_command','toggle_native_screen_share','open_media','recording_controls','end_class','on_close','toggle_language','toggle_mode','toggle_student_drawing','select_tool','select_color','select_width','undo','clear_all','toggle_ink','refresh_button_states'):setattr(obj,name,lambda *a:None)
                    for name,fn in ns.items():
                        if name in ('make_button','build_toolbar'):setattr(obj,name,MethodType(fn,obj))
                    obj.build_toolbar();changes=[]
                    with mock.patch('native_toolbar.work_area',return_value=(-width,0,0,1080)):
                        layout=ToolbarLayout(root,obj.toolbar_containers,lambda:changes.append(1));root.deiconify();root.update()
                        for newwidth in (root.winfo_width(),max(600,width-200)):
                            root.geometry(f'{newwidth}x{root.winfo_height()}-{width}+20');root.update();layout.fit();root.update()
                            for box,children in layout.children.items():
                                for child in children:
                                    if child.winfo_class()!='Button':continue
                                    self.assertTrue(child.winfo_ismapped())
                                    self.assertGreaterEqual(child.winfo_rootx(),root.winfo_rootx())
                                    self.assertLessEqual(child.winfo_rootx()+child.winfo_width(),root.winfo_rootx()+root.winfo_width())
                                    self.assertLessEqual(child.winfo_rooty()+child.winfo_height(),root.winfo_rooty()+root.winfo_height())
                            self.assertLessEqual(root.winfo_width(),width)
                            self.assertGreaterEqual(root.winfo_x(),-width)
                            self.assertLessEqual(root.winfo_x()+root.winfo_width(),0)
                        self.assertGreater(len(changes),1)
                finally:root.destroy()
