"""Real Tk geometry with measured font/DPI requests; physical Windows is separate."""
from contextlib import contextmanager
import tkinter as tk
import unittest
from types import SimpleNamespace,MethodType
from unittest import mock
from native_toolbar import ToolbarLayout
from test_teaching_workflows import extracted_functions
from teacher_localization import translate

class ToolbarTests(unittest.TestCase):
    @contextmanager
    def toolbar(self,scaling,lang):
        methods={'build_toolbar','make_button','set_button_label','refresh_button_states','apply_toolbar_language'}
        ns=extracted_functions('teacher_meeting_app.py',methods,dict(tk=tk))
        root=tk.Tk();root.withdraw();root.tk.call('tk','scaling',scaling)
        obj=SimpleNamespace(toolbar=root,BG='#111111',PANEL='#222222',PANEL_2='#333333',TEXT='#ffffff',MUTED='#cccccc',BORDER='#444444',ACCENT='#008888',ACCENT_DARK='#555555',DANGER='#aa0000',lang=lang,
            status_var=tk.StringVar(root,value='Connected'),people_var=tk.StringVar(root,value='Students: 12'),tool_buttons={},color_buttons={},width_buttons={},
            draw_mode=False,students_can_draw=False,tool='pen',color='#e53935',width=2,ink_visible=True)
        obj.tr=lambda x:translate(x,obj.lang)
        for name in ('send_media_command','toggle_native_screen_share','open_media','recording_controls','end_class','on_close','toggle_language','toggle_mode','toggle_student_drawing','select_tool','select_color','select_width','undo','clear_all','toggle_ink'):setattr(obj,name,lambda *a:None)
        for name in methods:setattr(obj,name,MethodType(ns[name],obj))
        try:
            obj.build_toolbar();obj.apply_toolbar_language();yield root,obj
        finally:root.destroy();obj.tr=None

    def assert_visible(self,root,layout):
        for box,children in layout.children.items():
            for child in children:
                if child.winfo_class()!='Button':continue
                self.assertTrue(child.winfo_ismapped())
                self.assertGreaterEqual(child.winfo_rootx(),root.winfo_rootx())
                self.assertLessEqual(child.winfo_rootx()+child.winfo_width(),root.winfo_rootx()+root.winfo_width())
                self.assertLessEqual(child.winfo_rooty()+child.winfo_height(),root.winfo_rooty()+root.winfo_height())

    def test_two_primary_rows_at_1920_1080_100_percent_in_both_languages(self):
        # Tk scaling is pixels/point: Windows 100% =96 DPI =96/72, not1.
        for language in ('en','zh'):
            with self.subTest(language=language),self.toolbar(96/72,language) as (root,obj),mock.patch('native_toolbar.work_area',return_value=(0,0,1920,1040)):
                root.maxsize(1100,700)  # Deliberately stale/smaller primary-monitor limit.
                changes=[];layout=ToolbarLayout(root,obj.toolbar_containers,lambda:changes.append(1));obj.toolbar_layout=layout
                self.assertFalse(root.winfo_ismapped());root.deiconify();root.update()
                self.assert_visible(root,layout)
                for lang in (language,'zh','en'):
                    obj.lang=lang;obj.apply_toolbar_language();layout.schedule();root.update()
                    right,mode,top,row,footer=obj.toolbar_containers
                    print('Toolbar geometry diagnostic:',lang,{'actual':(root.winfo_width(),root.winfo_height()),'applied':layout.applied_size,'user_width':layout.user_width,'maxsize':root.maxsize(),'scaling':float(root.tk.call('tk','scaling')),'boxes':[(b.winfo_width(),b.winfo_height(),b.winfo_reqwidth()) for b in obj.toolbar_containers]})
                    # Title/status and ALL meeting controls occupy the first row.
                    self.assertEqual(len({b.winfo_rooty() for b in layout.children[right]}),1)
                    self.assertEqual(layout.children[top][0].winfo_y(),right.winfo_y())
                    # Every control in the second row overlaps one common horizontal band.
                    buttons=layout.children[mode]+[w for w in layout.children[row] if w.winfo_class()=='Button']
                    self.assertLess(max(w.winfo_rooty() for w in buttons),min(w.winfo_rooty()+w.winfo_height() for w in buttons))
                    self.assertLessEqual(root.winfo_height(),200)
                    self.assert_visible(root,layout)
                    print('Compact toolbar:',lang,root.winfo_width(),root.winfo_height())
                # Mode labels change too; geometry/exclusion callback must follow.
                for i in range(10):obj.draw_mode=bool(i%2);obj.refresh_button_states();root.update();self.assert_visible(root,layout)
                self.assertGreater(len(changes),10)

    def test_real_controls_fit_first_launch_dpi_languages_narrow_monitor_and_resize(self):
        cases=[(factor,width,lang) for factor,width in ((1.25,1920),(1.5,1920),(2,1920),(1.5,1024),(1.5,768)) for lang in ('en','zh')]
        for factor,width,lang in cases:
            with self.subTest(percent=factor*100,width=width,lang=lang),self.toolbar(factor*96/72,lang) as (root,obj),mock.patch('native_toolbar.work_area',return_value=(-width,0,0,1080)):
                changes=[];layout=ToolbarLayout(root,obj.toolbar_containers,lambda:changes.append(1));obj.toolbar_layout=layout;root.deiconify();root.update()
                for newwidth in (root.winfo_width(),max(600,width-200),700):
                    root.geometry(f'{newwidth}x{root.winfo_height()}+-{width}+20');root.update();layout.fit();root.update()
                    self.assert_visible(root,layout)
                    self.assertLessEqual(root.winfo_width(),width)
                    if newwidth==700:self.assertLessEqual(root.winfo_width(),760)
                    self.assertGreaterEqual(root.winfo_x(),-width)
                    self.assertLessEqual(root.winfo_x()+root.winfo_width(),0)
                self.assertGreater(len(changes),1)
