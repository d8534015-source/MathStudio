"""Delivery-only regressions: remote teacher cannot bootstrap an OWNER server."""
import os
from pathlib import Path
from types import SimpleNamespace,MethodType
import unittest
from unittest import mock
from test_security_stability import BackendCase
from test_teaching_workflows import extracted_functions

class RemoteClientTests(unittest.TestCase):
    def test_teacher_origin_requires_https_and_contains_no_credentials(self):
        from teacher_connection import validate_origin
        self.assertEqual(validate_origin(' https://owner.example/ '),'https://owner.example')
        for value in ('http://owner.example','https://name:pass@owner.example','https://owner.example/classroom',
                      'https://owner.example?token=secret','https://owner.example#fragment'):
            with self.assertRaises(ValueError):validate_origin(value)

    def test_remote_bootstrap_never_creates_account_or_server(self):
        events=[]
        ns=extracted_functions('teacher_desktop_app.py',{'_bootstrap'},
            {'BUILD_ID':'same','ensure_admin_account':lambda *a:events.append('account'),
             'start_server_process':lambda:events.append('server'),'can_connect':lambda:False})
        for build in ('same','wrong'):
            events.clear()
            obj=SimpleNamespace(remote=True,root=SimpleNamespace(deiconify=lambda:None),tr=lambda s:s,
                client=SimpleNamespace(json=lambda path:{'build':build}),show_login=lambda:events.append('login'),
                show_server_offline=lambda message:events.append('offline'))
            MethodType(ns['_bootstrap'],obj)()
            self.assertEqual(events,['login'] if build=='same' else ['offline'])

    def test_remote_launch_loads_no_owner_secrets_and_runs_only_client(self):
        import runtime_setup
        with mock.patch.object(runtime_setup,'teacher_only',return_value=True),mock.patch.object(runtime_setup,'select_origin',return_value='https://owner.example'),mock.patch.object(runtime_setup,'verify_runtime'),mock.patch.object(runtime_setup,'apply_config') as config,mock.patch.object(runtime_setup.subprocess,'call',return_value=0) as child:
            self.assertEqual(runtime_setup.launch('teacher'),0)
            config.assert_not_called()
            self.assertTrue(child.call_args.args[0][1].endswith('teacher_desktop_app.py'))
            self.assertEqual(child.call_args.kwargs['env']['MATHSTUDIO_SERVER_URL'],'https://owner.example')
            self.assertEqual(child.call_args.kwargs['env']['MATHSTUDIO_REMOTE'],'1')
            with self.assertRaisesRegex(RuntimeError,'cannot host'):runtime_setup.launch('server')

    def test_remote_native_toolbar_starts_on_client_with_owner_token(self):
        calls=[]
        client=SimpleNamespace(base='https://owner.example',json=lambda path,data:calls.append((path,data)) or {'token':'synthetic-token','browser_url':'synthetic'})
        ns=extracted_functions('teacher_desktop_app.py',{'_launch_teacher_meeting'},
            {'sys':SimpleNamespace(executable='python.exe'),'ROOT':Path('/synthetic'),
             'subprocess':SimpleNamespace(Popen=lambda *a,**kw:calls.append(a[0]))})
        obj=SimpleNamespace(remote=True,client=client,tr=lambda s:s)
        result=MethodType(ns['_launch_teacher_meeting'],obj)(123)
        self.assertEqual(calls[0][1],{'class_id':123,'client_launch':True})
        self.assertIn('https://owner.example',calls[1]);self.assertIn('synthetic-token',calls[1])
        self.assertTrue(result['launched'])

class RemoteBackendTests(BackendCase):
    def test_remote_teacher_handoff_never_spawns_owner_windows_app(self):
        teacher=self.client('teacher');meeting=self.instant(teacher)
        with mock.patch.object(self.app.sys,'platform','win32'),mock.patch.object(self.app.subprocess,'Popen') as child:
            response=self.request('/api/admin/teacher-app-launch',{'class_id':meeting['class_id'],'client_launch':True},teacher)
            self.assertEqual(response[0],200,response[1]);child.assert_not_called()
        token=response[1]['token']
        self.assertEqual(self.request('/api/teacher-app/state?token='+token)[0],200)
        self.assertIn('/teacher-media-login?token=',response[1]['browser_url'])
        # The existing session/role authorization still protects the new option.
        student=self.client('student')
        self.assertEqual(self.request('/api/admin/teacher-app-launch',{'class_id':meeting['class_id'],'client_launch':True},student)[0],403)

class DeliveryManifestTests(unittest.TestCase):
    def test_teacher_archive_selection_contains_no_backend_or_owner_launchers(self):
        import json
        from release_package import candidate_files
        root=Path(__file__).resolve().parent
        manifest=json.loads((root/'release_manifest.json').read_text())
        files=candidate_files(root,manifest,'teacher')
        self.assertEqual(json.loads(files['package_role.json'])['role'],'teacher-remote')
        self.assertIn('teacher_desktop_app.py',files);self.assertIn('teacher_connection.py',files)
        self.assertIn('OPEN MATHSTUDIO TEACHER.bat',files)
        for name in ('server.py','document_worker.py','START STUDENT WEBSITE.bat','SETUP FREE CAMERA + AUDIO.bat','media_config.bat','cloud_storage.bat','index.html'):
            self.assertNotIn(name,files)
        for name,data in files.items():
            if name.endswith('.py'):compile(data.decode('utf-8'),name,'exec')

class ConnectionValidationTests(unittest.TestCase):
    def test_tls_connection_and_build_are_validated_without_credentials(self):
        import json
        from build_info import BUILD_ID
        from teacher_connection import check_connection
        response=mock.MagicMock();response.__enter__.return_value=response
        response.geturl.return_value='https://owner.example/api/desktop-info'
        response.read.return_value=json.dumps({'build':BUILD_ID}).encode()
        with mock.patch('urllib.request.urlopen',return_value=response) as opening:
            self.assertEqual(check_connection('https://owner.example'),'https://owner.example')
            request=opening.call_args.args[0]
            self.assertNotIn('Authorization',request.headers);self.assertNotIn('Cookie',request.headers)
            response.read.return_value=b'{"build":"wrong"}'
            with self.assertRaises(ValueError):check_connection('https://owner.example')
            response.read.return_value=json.dumps({'build':BUILD_ID}).encode()
            response.geturl.return_value='http://owner.example/api/desktop-info'
            with self.assertRaises(ValueError):check_connection('https://owner.example')

    def test_failed_connection_is_not_saved_and_validated_address_is_saved(self):
        import json,tempfile
        import teacher_connection
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'connection.json'
            dialog=SimpleNamespace(askstring=mock.Mock(side_effect=['https://unavailable.example','https://owner.example']))
            messages=SimpleNamespace(showerror=mock.Mock())
            root=SimpleNamespace(withdraw=lambda:None,destroy=lambda:None)
            fake_tk=SimpleNamespace(Tk=lambda:root,simpledialog=dialog,messagebox=messages)
            with mock.patch.dict('sys.modules',{'tkinter':fake_tk}),mock.patch.object(teacher_connection,'configured_origin',return_value=''),mock.patch.object(teacher_connection,'connection_path',return_value=path),mock.patch.object(teacher_connection,'check_connection',side_effect=[ValueError('unavailable'),'https://owner.example']):
                self.assertEqual(teacher_connection.select_origin(),'https://owner.example')
                self.assertEqual(json.loads(path.read_text()),{'server_url':'https://owner.example'})
                messages.showerror.assert_called_once()

    def test_settings_change_signs_out_and_replaces_client_without_starting_server(self):
        events=[]
        root=SimpleNamespace(after_cancel=lambda job:events.append(('cancel',job)))
        ns=extracted_functions('teacher_desktop_app.py',{'change_owner_server'},
            {'messagebox':SimpleNamespace(askyesno=lambda *a,**kw:True),'APP_TITLE':'Test',
             'select_origin':lambda **kw:'https://new.example','os':os,
             'APIClient':lambda origin:SimpleNamespace(base=origin)})
        obj=SimpleNamespace(root=root,tr=lambda s:s,client=SimpleNamespace(base='https://old.example',json=lambda *a,**kw:events.append('logout')),
            message_poll_job='chat',_active_poll_job='classes',_bootstrap=lambda:events.append('connect'))
        with mock.patch.dict(os.environ,{}):MethodType(ns['change_owner_server'],obj)()
        self.assertEqual(obj.client.base,'https://new.example');self.assertEqual(obj.student_origin,'https://new.example')
        self.assertEqual(events,['logout',('cancel','chat'),('cancel','classes'),'connect'])
        self.assertIsNone(obj.active_chat_id)
        self.assertEqual(obj.admin,{})
        self.assertEqual(obj.classes,[])
