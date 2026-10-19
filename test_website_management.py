"""Desktop -> OWNER public-content regressions, synthetic sessions/data only."""
import concurrent.futures
import json
import os
from pathlib import Path
import time
import unittest
from unittest import mock
import public_translations as pt
from test_security_stability import BackendCase
from teacher_desktop_app import APIClient,APIError
from teacher_website import WebsiteService,preview_text
from teacher_localization import translate as translate_ui


class WebsiteManagementAPI(BackendCase):
    def setUp(self):
        super().setUp();self.teacher=self.client('teacher')

    def entry(self,key='settings:0:intro'):
        result=self.request('/api/admin/website-content',state=self.teacher)
        self.assertEqual(result[0],200)
        return next(e for e in result[1]['entries'] if e['key']==key)

    def act(self,action,key='settings:0:intro',**extra):
        item=self.entry(key)
        return self.request('/api/admin/website-content',dict(action=action,key=key,
            base_hash=item['base_hash'],revision=item['revision'],**extra),self.teacher)

    def translate(self,action='approve',key='settings:0:intro',target='zh',**extra):
        status,data,_=self.request('/api/admin/content-translations',state=self.teacher)
        self.assertEqual(status,200)
        source=next(s for s in data['sources'] if s['key']==key)
        row=next((r for r in data['translations'] if r['source_key']==key and r['target']==target),None)
        return self.request('/api/admin/content-translations',dict(action=action,key=key,target=target,
            source_hash=source['source_hash'],revision=row['revision'] if row else 0,**extra),self.teacher)

    def test_all_privileged_actions_require_teacher_csrf_and_valid_session(self):
        for state in (self.client(),self.client('student')):
            for path in ('/api/admin/website-content','/api/admin/content-translations'):
                self.assertIn(self.request(path,state=state)[0],(401,403))
                for action in ('save','publish','unpublish','create_post','generate','approve','config'):
                    self.assertIn(self.request(path,{'action':action},state)[0],(401,403))
        self.assertEqual(self.request('/api/admin/website-content',{'action':'publish'},self.teacher,headers={'X-CSRF-Token':'bad'})[0],403)
        self.request('/api/logout',{},self.teacher)
        self.assertEqual(self.request('/api/admin/website-content',state=self.teacher)[0],401)

    def test_original_draft_approval_publication_and_unpublication_are_separate(self):
        old=self.request('/api/public')[1]['settings']['intro']
        self.assertEqual(self.act('save',text='New public source with $x^2+1$.')[0],200)
        self.assertEqual(self.request('/api/public')[1]['settings']['intro'],old)
        self.assertEqual(self.translate(text='新介绍 $x^2+1$。')[0],200)
        self.assertNotIn('settings:0:intro',self.request('/api/content-translations?lang=zh')[1]['translations'])
        self.assertEqual(self.act('publish')[0],200)
        self.assertEqual(self.request('/api/public')[1]['settings']['intro'],'New public source with $x^2+1$.')
        self.assertEqual(self.request('/api/content-translations?lang=zh')[1]['translations']['settings:0:intro']['text'],'新介绍 $x^2+1$。')
        self.assertEqual(self.act('unpublish')[0],200)
        self.assertEqual(self.request('/api/public')[1]['settings']['intro'],'')
        self.assertEqual(self.request('/api/content-translations?lang=zh')[1]['translations'],{})
        self.assertEqual(self.entry()['draft'],'New public source with $x^2+1$.')

    def test_new_announcements_stay_private_then_publish_edit_and_unpublish(self):
        status,result,_=self.request('/api/admin/website-content',dict(action='create_post',title='Private synthetic draft',text='Unpublished body'),self.teacher)
        self.assertEqual(status,200);key=result['key']
        for state in (None,self.client('student'),self.teacher):self.assertEqual(self.request('/api/public',state=state)[1]['posts'],[])
        self.assertEqual(self.translate(key=key,text='获准的公开公告')[0],200)
        self.assertEqual(self.request('/api/content-translations?lang=zh')[1]['translations'],{})
        self.assertEqual(self.act('publish',key)[0],200)
        self.assertEqual(self.request('/api/public')[1]['posts'][0]['body'],'Unpublished body')
        self.assertEqual(self.act('save',key,text='New body',title='New title')[0],200)
        self.assertEqual(self.request('/api/public')[1]['posts'][0]['body'],'Unpublished body')
        self.assertEqual(self.act('publish',key)[0],200)
        self.assertEqual(self.request('/api/content-translations?lang=zh')[1]['translations'],{})
        self.assertEqual(self.act('unpublish',key)[0],200)
        self.assertEqual(self.request('/api/public')[1]['posts'],[])

    def test_public_lesson_descriptions_only_private_records_never_sources(self):
        private=self.lesson(user='student')
        with self.app.db() as c:lid=c.execute('SELECT id FROM lesson_types LIMIT 1').fetchone()[0]
        key=f'courses:{lid}:description'
        self.assertEqual(self.act('save',key,text='Synthetic lesson description')[0],200)
        self.assertNotIn('Synthetic lesson description',json.dumps(self.request('/api/schedule')[1]))
        self.assertEqual(self.act('publish',key)[0],200)
        self.assertIn('Synthetic lesson description',json.dumps(self.request('/api/schedule')[1]))
        self.assertEqual(self.act('unpublish',key)[0],200)
        self.assertNotIn('Synthetic lesson description',json.dumps(self.request('/api/schedule')[1]))
        for key in (f'groups:{private}:description','users:1:name','messages:1:text','files:1:name','settings:0:timezone'):
            self.assertEqual(self.request('/api/admin/website-content',dict(action='save',key=key),self.teacher)[0],404)

    def test_revision_and_legacy_source_races_refuse_to_overwrite(self):
        old=self.entry()
        self.assertEqual(self.act('save',text='First draft')[0],200)
        stale=dict(action='save',key=old['key'],base_hash=old['base_hash'],revision=old['revision'],text='Stale draft')
        self.assertEqual(self.request('/api/admin/website-content',stale,self.teacher)[0],409)
        with self.app.db() as c:c.execute("UPDATE settings SET value='Concurrent author edit' WHERE key='intro'")
        self.assertEqual(self.act('publish')[0],409)
        self.assertEqual(self.entry()['draft'],'First draft')

    def test_concurrent_publication_and_invalid_unicode_fail_safely(self):
        self.assertEqual(self.act('save',text='Single reviewed source.')[0],200)
        item=self.entry();payload=dict(action='publish',key=item['key'],base_hash=item['base_hash'],revision=item['revision'])
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:self.request('/api/admin/website-content',payload,dict(self.teacher))[0],range(2)))
        self.assertEqual(sorted(results),[200,409])
        self.assertEqual(self.act('save',text='\ud800')[0],400)
        self.assertEqual(self.entry()['draft'],'Single reviewed source.')

    def test_public_group_description_visibility_and_apex_navigation(self):
        group=self.lesson(kind='group');key=f'groups:{group}:description'
        self.assertEqual(self.act('save',key,text='Reviewed public group description.')[0],200)
        self.assertEqual(self.act('publish',key)[0],200)
        self.assertIn('Reviewed public group description.',json.dumps(self.request('/api/classes')[1]))
        self.assertEqual(self.act('unpublish',key)[0],200)
        data=self.request('/api/classes')[1]
        self.assertNotIn('Reviewed public group description.',json.dumps(data))
        self.assertTrue(any(c['id']==group for c in data['classes']))
        with mock.patch.object(self.app,'current_public_origin',return_value='https://hongmaths.com'):
            status,_,headers=self.request('/booking',headers={'Host':'www.hongmaths.com','Sec-Fetch-Mode':'navigate'})
        self.assertEqual(status,302);self.assertEqual(headers['Location'],'https://hongmaths.com/booking')

    def test_translation_regeneration_keeps_approved_edits_and_history(self):
        self.assertEqual(self.act('save',text='Public mathematical introduction.')[0],200)
        self.assertEqual(self.translate(text='人工审阅的介绍。')[0],200)
        self.assertEqual(self.act('publish')[0],200)
        self.request('/api/admin/content-translations',dict(action='config',enabled=True,terms=[]),self.teacher)
        with mock.patch.object(pt,'provider_name',return_value='argos'),mock.patch.object(pt.argos_runtime,'ready',return_value=True),mock.patch.object(pt.argos_runtime,'translate',return_value='新机器草稿。'):
            self.assertEqual(self.translate('generate',regenerate=True,offline_only=True)[0],200)
        self.assertEqual(self.request('/api/content-translations?lang=zh')[1]['translations']['settings:0:intro']['text'],'人工审阅的介绍。')
        self.assertEqual(self.act('save',text='Changed public source.')[0],200)
        state=self.request('/api/admin/content-translations',state=self.teacher)[1]
        self.assertTrue(any(r['approved']=='人工审阅的介绍。' for r in state['previous_translations']))
        self.assertEqual(self.act('publish')[0],200)
        self.assertNotIn('settings:0:intro',self.request('/api/content-translations?lang=zh')[1]['translations'])

    def test_native_client_uses_authenticated_owner_api_and_offline_only_generation(self):
        client=APIClient(f'http://127.0.0.1:{self.http.server_port}')
        client.login('teacher','synthetic-password-123');service=WebsiteService(client)
        entries,translations=service.load();entry=next(e for e in entries['entries'] if e['key']=='settings:0:intro')
        self.assertIsNot(service.client.jar,client.jar)
        service.content(entry,'save','Teacher desktop draft.','')
        entries,translations=service.load();source=next(s for s in translations['sources'] if s['key']==entry['key'])
        service.configure(True,[])
        with mock.patch.object(pt,'provider_name',return_value='legacy-google'),mock.patch.object(pt,'translate',side_effect=AssertionError('No external requests')):
            with self.assertRaises(APIError):service.translation(source,None,'zh','generate','')
        with mock.patch.object(pt,'provider_name',return_value='argos'),mock.patch.object(pt.argos_runtime,'ready',return_value=True),mock.patch.object(pt.argos_runtime,'translate',return_value='服务器上的草稿。'):
            service.translation(source,None,'zh','generate','')
        _,translations=service.load();row=next(r for r in translations['translations'] if r['source_key']==entry['key'])
        self.assertIsNone(row['approved']);self.assertEqual(preview_text(translations,entry['key'],'zh',source['original']),'服务器上的草稿。')
        service.translation(source,row,'zh','approve','教师编辑并审阅。')
        self.assertEqual(self.request('/api/content-translations?lang=zh')[1]['translations'],{})
        entry=next(e for e in service.load()[0]['entries'] if e['key']==entry['key']);service.content(entry,'publish')
        self.assertEqual(self.request('/api/content-translations?lang=zh')[1]['translations'][entry['key']]['text'],'教师编辑并审阅。')
        client.json('/api/logout',{})
        with self.assertRaises(APIError):service.load()

    def test_old_translation_route_is_retired_and_payload_is_not_public(self):
        status,_,headers=self.request('/teacher/translations')
        self.assertIn(status,(302,303));self.assertEqual(headers['Location'],'/teacher')
        self.assertEqual(self.request('/translation_manager.js')[0],404)
        page=self.request('/teacher')[1].decode()
        self.assertNotIn('href="/teacher/translations"',page)
        self.assertIn('teacher.website_management',page)


class ClientPayloadIsolation(unittest.TestCase):
    def test_review_client_state_is_separate_and_source_owner_state_is_unchanged(self):
        import runtime_paths
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            marker=Path(directory)/'teacher_package_role.json';marker.write_text('{"role":"teacher-remote","review":true}')
            with mock.patch.object(runtime_paths,'__file__',str(Path(directory)/'runtime_paths.py')),mock.patch.dict(os.environ,{'LOCALAPPDATA':directory}):
                with mock.patch.object(runtime_paths.sys,'frozen',True,create=True):
                    self.assertEqual(runtime_paths.state_directory(),Path(directory)/'MathStudioReview')
                with mock.patch.object(runtime_paths.sys,'frozen',False,create=True):
                    self.assertEqual(runtime_paths.state_directory(),Path(directory)/'MathStudio')

    def test_rejects_actual_owner_modules_and_model_or_native_runtime_payloads(self):
        import importlib.util
        path=Path(__file__).parent/'packaging/windows/check_client_payload.py'
        spec=importlib.util.spec_from_file_location('client_payload_check',path)
        checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
        self.assertEqual(checker.check_names(['teacher_website','http.server'],['MathStudioClient.exe'])['status'],'passed')
        for module in ['argos_runtime','website_content','argostranslate.translate','torch.nn','sentencepiece']:
            with self.assertRaises(ValueError):checker.check_names([module],[])
        for name in ['_internal/onnxruntime/capi/state.pyd','_internal/libtorch_cpu.dll','en.onnx','zh.argosmodel','sentencepiece.model','model.bin','posts.db']:
            with self.assertRaises(ValueError):checker.check_names([], [name])


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Tk display required (Windows runner or Xvfb)')
class NativeWebsiteUI(BackendCase):
    def setUp(self):
        super().setUp()
        from teacher_desktop_app import TeacherDesktopApp
        with mock.patch.object(TeacherDesktopApp,'_bootstrap'),mock.patch('teacher_desktop_app.read_language',return_value='en'):
            self.uiapp=TeacherDesktopApp()
        self.root=self.uiapp.root
        self.client_api=APIClient(f'http://127.0.0.1:{self.http.server_port}')
        self.client_api.login('teacher','synthetic-password-123')
        self.uiapp.client=self.client_api;self.uiapp.remote=True
        self.uiapp.public=self.client_api.json('/api/public')
        self.uiapp.build_main();self.uiapp.show_page('website')
        self.editor=self.uiapp.website_editor;self.drain()

    def drain(self):
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            self.root.update()
            if self.editor.pending is None:return
            time.sleep(.01)
        self.fail('Background desktop request did not finish')

    def tearDown(self):
        for job in self.root.tk.call('after','info'):self.root.after_cancel(job)
        self.root.destroy();super().tearDown()

    def select_intro(self):
        self.editor.content_choice.current(next(i for i,e in enumerate(self.editor.entries) if e['key']=='settings:0:intro'))
        self.editor.select_content(force=True)

    def test_language_switch_preserves_unsaved_content_and_selection(self):
        self.select_intro();text='Home — Teacher name / 学生原文 $x^2$'
        self.editor.put(self.editor.content_text,text);self.editor.dirty=True
        with mock.patch('teacher_website.messagebox.askyesno') as confirm,mock.patch('teacher_desktop_app.save_language'):
            for lang in ('zh','en','zh','en'):
                self.uiapp.toggle_language();self.root.update()
                self.assertIs(self.uiapp.website_editor,self.editor)
                self.assertEqual(self.editor.entry()['key'],'settings:0:intro')
                self.assertEqual(self.editor.content_text.get('1.0','end-1c'),text)
                self.assertEqual(self.editor.book.tab(0,'text'),'公开内容' if lang=='zh' else 'Public content')
                if os.environ.get('MATH_WEBSITE_SCREENSHOTS'):
                    from PIL import ImageGrab
                    destination=Path(os.environ['MATH_WEBSITE_SCREENSHOTS']);destination.mkdir(parents=True,exist_ok=True)
                    ImageGrab.grab(xdisplay=os.environ.get('DISPLAY')).save(destination/('desktop-content-'+lang+'.png'))
        confirm.assert_not_called();self.assertTrue(self.editor.dirty)
        self.root.geometry('900x650');self.root.update()
        canvas=self.editor.content_fields.master;canvas.yview_moveto(1);self.root.update()
        preview=next(w for w,key in self.editor.labels if key=='Preview English')
        self.assertLess(preview.winfo_rooty()+preview.winfo_height(),self.root.winfo_rooty()+self.root.winfo_height())

    def test_failure_keeps_editor_text_and_background_generation_keeps_tk_responsive(self):
        import threading
        self.select_intro();self.editor.put(self.editor.content_text,'Unsaved original $x^2$.');self.editor.dirty=True
        with mock.patch.object(self.editor.service,'content',side_effect=APIError('OWNER offline')),mock.patch('teacher_website.messagebox.showerror') as error:
            self.editor.content_action('save');self.drain();error.assert_called_once()
        self.assertEqual(self.editor.content_text.get('1.0','end-1c'),'Unsaved original $x^2$.')
        self.assertTrue(self.editor.dirty)
        self.editor.dirty=False
        with self.app.db() as c:c.execute("UPDATE settings SET value='Simple public text.' WHERE key='intro'")
        self.editor.service.configure(True,[])
        entered=threading.Event();release=threading.Event();heartbeat=[]
        def slow(text,target):entered.set();release.wait(4);return '服务器草稿。'
        with mock.patch.object(pt,'provider_name',return_value='argos'),mock.patch.object(pt.argos_runtime,'ready',return_value=True),mock.patch.object(pt.argos_runtime,'translate',side_effect=slow):
            self.editor.reload();self.drain()
            self.editor.translation_choice.current(next(i for i,s in enumerate(self.editor.translations['sources']) if s['key']=='settings:0:intro'))
            self.editor.select_translation(force=True);self.editor.book.select(self.editor.trans_tab);self.root.update()
            self.editor.translation_action('generate')
            self.assertTrue(entered.wait(2))
            self.root.after(0,lambda:heartbeat.append(True));self.root.update()
            self.assertTrue(heartbeat);self.assertIsNotNone(self.editor.pending)
            release.set();self.drain()
        self.assertEqual(self.editor.trans_text.get('1.0','end-1c'),'服务器草稿。')
        self.assertEqual(self.request('/api/content-translations?lang=zh')[1]['translations'],{})
        if os.environ.get('MATH_WEBSITE_SCREENSHOTS'):
            from PIL import ImageGrab
            with mock.patch('teacher_desktop_app.save_language'):
                for lang in ('zh','en'):
                    self.uiapp.toggle_language();self.root.update()
                    ImageGrab.grab(xdisplay=os.environ.get('DISPLAY')).save(Path(os.environ['MATH_WEBSITE_SCREENSHOTS'])/('desktop-translations-'+lang+'.png'))
