"""Phase 2B Part 2 regressions using synthetic state and GUI doubles."""
from types import SimpleNamespace, MethodType
import unittest
from test_teaching_workflows import extracted_functions

class NativeAnnotationTests(unittest.TestCase):
    def controller(self, operation, fail=False, conflicts=1):
        calls=[]
        current={"background":"grid","shapes":[{"id":"own"},{"id":"other"},{"id":"concurrent"}]}
        def http(url, method="GET", data=None):
            if method=="GET": return {"version":2,"board":current}
            calls.append(data)
            if fail: raise RuntimeError("offline")
            if len(calls)<=conflicts: raise RuntimeError("Board changed; retry")
            return {"version":3}
        ns=extracted_functions('teacher_meeting_app.py',{'save_board','undo','clear_all','erase_at'},
            {'http_json':http,'threading':SimpleNamespace(Thread=lambda target,**kw:SimpleNamespace(start=target)),
             'messagebox':SimpleNamespace(askyesno=lambda *a,**kw:True),'APP_NAME':'Test'})
        obj=SimpleNamespace(board={"background":"blank","shapes":[{"id":"own"},{"id":"other"}]},
            version=1,my_shapes=['own'],saving=False,connected=True,closed=False,token='synthetic',server='local',
            root=SimpleNamespace(after=lambda delay,fn,*args:fn(*args)),status_var=SimpleNamespace(set=lambda text:None),
            redraw=lambda:None,state_url=lambda:'state',toolbar=None,tr=lambda x:x,
            shape_distance=lambda shape,x,y:0 if shape['id']=='own' else 1)
        for name in ('save_board','undo','clear_all','erase_at'): setattr(obj,name,MethodType(ns[name],obj))
        return obj,calls

    def test_rel03_undo_and_erase_retry_remove_only_target(self):
        for operation in ('undo','erase_at'):
            with self.subTest(operation=operation):
                obj,calls=self.controller(operation)
                getattr(obj,operation)(*([0,0] if operation=='erase_at' else []))
                self.assertEqual([s['id'] for s in obj.board['shapes']],['other','concurrent'])
                self.assertEqual(obj.board['background'],'grid')
                self.assertEqual(obj.my_shapes,[])
                self.assertEqual(calls[-1]['version'],2)

    def test_rel03_clear_retries_explicit_clear_intent(self):
        obj,calls=self.controller('clear_all'); obj.clear_all()
        self.assertEqual(obj.board['shapes'],[])
        self.assertEqual(obj.board['background'],'grid')
        self.assertEqual(obj.my_shapes,[])

    def test_rel03_failed_undo_and_clear_keep_history(self):
        for operation in ('undo','clear_all'):
            obj,calls=self.controller(operation,fail=True); getattr(obj,operation)()
            self.assertEqual(obj.my_shapes,['own'])
            self.assertEqual([s['id'] for s in obj.board['shapes']],['own','other'])
            self.assertFalse(obj.saving)

    def test_rel03_repeated_conflicts_keep_intent_and_exhaustion_keeps_history(self):
        obj,calls=self.controller('undo',conflicts=2);obj.undo()
        self.assertEqual([s['id'] for s in obj.board['shapes']],['other','concurrent'])
        self.assertEqual(len(calls),3)
        obj,calls=self.controller('clear_all',conflicts=3);obj.clear_all()
        self.assertEqual(obj.my_shapes,['own'])
        self.assertEqual([s['id'] for s in obj.board['shapes']],['own','other'])
        self.assertFalse(obj.saving)

    def test_rel03_add_retry_keeps_remote_shapes(self):
        obj,calls=self.controller('add')
        obj.save_board({**obj.board,'shapes':[*obj.board['shapes'],{'id':'new'}]},'new')
        self.assertEqual([s['id'] for s in obj.board['shapes']],['own','other','concurrent','new'])
        self.assertEqual(obj.my_shapes,['own','new'])

class LabelDouble:
    def __init__(self, text='', children=()): self.text=text; self.children=children
    def cget(self, key): return self.text if key=='text' else ''
    def configure(self, **kw): self.text=kw.get('text',self.text)
    config=configure
    def winfo_children(self): return self.children

class TreeDouble(LabelDouble):
    def __init__(self):
        super().__init__(); self.headings={'name':'Name','role':'Role'}; self.values={'one':['Teacher','student']}
    def __getitem__(self,key): return ('name','role') if key=='columns' else 'headings'
    def heading(self,col,option=None,**kw):
        if 'text' in kw:self.headings[col]=kw['text']
        return self.headings[col]
    def get_children(self,parent=''):return list(self.values)
    def item(self,iid,option=None,**kw):
        if 'values' in kw:self.values[iid]=kw['values']
        return self.values[iid]

class LocalizationTests(unittest.TestCase):
    def desktop(self):
        from teacher_localization import translate, localize_value
        ns=extracted_functions('teacher_desktop_app.py',{'apply_language'},
            {'localize_value':localize_value,'tk':SimpleNamespace(TclError=RuntimeError),'ttk':SimpleNamespace(Treeview=TreeDouble)})
        obj=SimpleNamespace(lang='zh')
        obj.tr=lambda value:translate(value,obj.lang)
        obj.apply_language=MethodType(ns['apply_language'],obj)
        return obj

    def test_l10n01_protected_widget_content_is_never_translated(self):
        obj=self.desktop(); label=LabelDouble('Teacher'); label._mathstudio_no_translate=True
        for lang in ('zh','en','zh'):
            obj.lang=lang; obj.apply_language(label); self.assertEqual(label.text,'Teacher')

    def test_l10n02_tree_headings_and_controlled_values_round_trip(self):
        obj=self.desktop(); tree=TreeDouble();obj.users_tree=tree
        # Match the real users tree's role column index.
        tree.values={'one':['Teacher','teacher_username','student']}
        for lang in ('zh','en','zh','en'):
            obj.lang=lang;obj.apply_language(tree)
            self.assertEqual(tree.headings['name'],'姓名' if lang=='zh' else 'Name')
            self.assertEqual(tree.values['one'][0],'Teacher')
            self.assertEqual(tree.values['one'][2],'学生' if lang=='zh' else 'student')

    def test_l10n02_dynamic_status_source_updates_and_round_trips(self):
        obj=self.desktop();label=LabelDouble('Connected')
        obj.apply_language(label);self.assertEqual(label.text,'已连接')
        label.text='Connection problem';obj.apply_language(label);self.assertEqual(label.text,'连接异常')
        obj.lang='en';obj.apply_language(label);self.assertEqual(label.text,'Connection problem')

    def test_l10n03_native_annotations_and_dialog_strings_have_translations(self):
        from teacher_localization import translate
        for value in ('Saving annotation…','Nothing from this teacher session to undo.',
                      'Clear every shared annotation for everyone?','MathStudio annotation',
                      'Text or math symbols:','The classroom is now closed.',
                      'End this class for the teacher and all students?'):
            with self.subTest(value=value):self.assertNotEqual(translate(value,'zh'),value)

    def test_l10n01_content_label_and_native_title_protection(self):
        from teacher_localization import content_label, translate
        label=content_label(LabelDouble,text='Teacher')
        self.desktop().apply_language(label);self.assertEqual(label.text,'Teacher')
        ns=extracted_functions('teacher_meeting_app.py',{'apply_toolbar_language'},
            {'tk':SimpleNamespace(Label=LabelDouble,TclError=RuntimeError)})
        obj=SimpleNamespace(toolbar=label,tr=lambda value:translate(value,'zh'))
        obj.apply_toolbar_language=MethodType(ns['apply_toolbar_language'],obj)
        obj.apply_toolbar_language();self.assertEqual(label.text,'Teacher')

    def test_l10n02_page_header_keeps_english_source_when_created_in_chinese(self):
        obj=self.desktop()
        ns=extracted_functions('teacher_desktop_app.py',{'show_page'},{})
        obj.clear_content=lambda:None;obj.page_title=LabelDouble();obj.page_subtitle=LabelDouble()
        obj.content=LabelDouble();obj.sidebar_buttons={};obj.page_schedule=lambda:None
        MethodType(ns['show_page'],obj)('schedule')
        obj.apply_language(obj.page_title);self.assertEqual(obj.page_title.text,'课表')
        obj.lang='en';obj.apply_language(obj.page_title);self.assertEqual(obj.page_title.text,'Schedule')
        obj.apply_language(obj.page_subtitle)
        self.assertEqual(obj.page_subtitle.text,'Set availability, post group lessons, and review the week')

    def test_l10n03_dialogs_use_translated_templates_not_literal_prompts(self):
        import ast
        from pathlib import Path
        from teacher_localization import translate
        for filename in ('teacher_desktop_app.py','teacher_meeting_app.py'):
            tree=ast.parse(Path(__file__).with_name(filename).read_text())
            for cls in (n for n in tree.body if isinstance(n,ast.ClassDef)):
                for node in ast.walk(cls):
                    if not isinstance(node,ast.Call) or not ast.unparse(node.func).startswith(('messagebox.','simpledialog.')):continue
                    for arg in node.args[:2]:
                        self.assertFalse(isinstance(arg,(ast.JoinedStr,ast.Constant)),(filename,node.lineno,ast.unparse(arg)))
                        for call in ast.walk(arg):
                            if isinstance(call,ast.Call) and ast.unparse(call.func)=='self.tr' and call.args and isinstance(call.args[0],ast.Constant):
                                value=call.args[0].value
                                self.assertNotEqual(translate(value,'zh'),value,(filename,node.lineno,value))

    def test_l10n02_native_status_preserves_diagnostic_content_across_languages(self):
        from teacher_localization import translate
        status='Could not sync annotation: Teacher'
        self.assertEqual(translate(status,'zh'),'无法同步标注：Teacher')
        self.assertEqual(translate(status,'en'),status)

class NativeStatusTests(unittest.TestCase):
    def test_l10n02_localized_variables_keep_canonical_source(self):
        import ast
        from pathlib import Path
        from teacher_localization import translate
        class Var:
            def __init__(self, master=None, value=''): self.value=value
            def set(self,value):self.value=value
        tree=ast.parse(Path(__file__).with_name('teacher_meeting_app.py').read_text())
        cls=next(n for n in ast.walk(tree) if isinstance(n,ast.ClassDef) and n.name=='_LocalizedVar')
        ns={'tk':SimpleNamespace(StringVar=Var)}
        exec(compile(ast.Module(body=[cls],type_ignores=[]),'native-status','exec'),ns)
        owner=SimpleNamespace(lang='zh');owner.tr=lambda text:translate(text,owner.lang)
        status=ns['_LocalizedVar'](None,owner,'Saving annotation…')
        self.assertEqual(status.value,'正在保存标注…')
        status.set('Could not sync annotation: Teacher')
        self.assertEqual(status.value,'无法同步标注：Teacher')
        owner.lang='en';status.refresh();self.assertEqual(status.value,'Could not sync annotation: Teacher')
        owner.lang='zh';status.refresh();self.assertEqual(status.value,'无法同步标注：Teacher')

    def test_l10n03_python_translation_placeholders_match(self):
        import re
        from teacher_localization import ZH
        for source,translated in ZH.items():
            self.assertEqual(set(re.findall(r'\{\d+\}',source)),set(re.findall(r'\{\d+\}',translated)),source)


from test_security_stability import BackendCase

class AnnotationAuthorizationTests(BackendCase):
    def test_media02_native_share_preserves_browser_and_overlay_permissions(self):
        teacher, student, cid, tp, sp = self.room()
        launch=self.request('/api/admin/teacher-app-launch',{'class_id':cid,'client_launch':True},teacher)
        self.assertEqual(launch[0],200,launch[1]); token=launch[1]['token']
        self.assertEqual(self.request('/api/teacher-app/screen',{'token':token,'active':True})[0],200)
        overlay=self.request('/api/room/overlay-token',{'class_id':cid,'peer':sp},student)[1]['token']
        version=0
        for allowed in (False,True,False):
            self.assertEqual(self.request('/api/teacher-app/permissions',{'token':token,'drawing':allowed})[0],200)
            for endpoint,state,data in (
                ('/api/room/board',student,{'class_id':cid,'peer':sp}),
                ('/api/overlay/board',None,{'token':overlay})):
                response=self.request(endpoint,{**data,'version':version,'board':{'background':'grid','shapes':[]}},state)
                self.assertEqual(response[0],200 if allowed else 403,response[1])
                if allowed:version=response[1]['version']
        # Teacher annotation remains authorized when students are view-only.
        response=self.request('/api/teacher-app/board',{'token':token,'version':version,
            'board':{'background':'grid','shapes':[]}})
        self.assertEqual(response[0],200,response[1])
