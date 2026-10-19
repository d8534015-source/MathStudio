"""Synthetic pairing/device regression coverage. No installed OWNER or credentials."""
import concurrent.futures
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import subprocess
from types import SimpleNamespace
import unittest
from unittest import mock

import owner_auth
import desktop_credentials
from test_security_stability import BackendCase


class PairingTests(BackendCase):
    def setUp(self):
        super().setUp()
        with self.app.db() as c:
            c.execute('DELETE FROM users')
            c.execute("DELETE FROM settings WHERE key='owner_initialized'")
        self.previous=owner_auth.PAIRING
        owner_auth.PAIRING=owner_auth.Pairing()

    def tearDown(self):
        owner_auth.PAIRING=self.previous
        super().tearDown()

    def payload(self):
        return {'username':'new_teacher','name':'Synthetic Teacher','password':'synthetic-password-123','pairing':owner_auth.PAIRING.code}

    def test_pairing_requires_csrf_and_local_secret(self):
        state=self.client()
        self.assertFalse(self.request('/api/desktop/setup-status')[1]['initialized'])
        payload=self.payload()
        self.assertEqual(self.request('/api/desktop/setup',payload,state,headers={'X-CSRF-Token':'wrong'})[0],403)
        for wrong in ('','0'*32):
            self.assertEqual(self.request('/api/desktop/setup',dict(payload,pairing=wrong),state)[0],403)
        with self.app.db() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM users').fetchone()[0],0)
        self.assertNotIn('pairing',self.request('/api/desktop/setup-status')[1])

    def test_first_account_rotates_session_consumes_code_and_persists_completion(self):
        state=self.client();old=state['cookie'];payload=self.payload()
        status,out,_=self.request('/api/desktop/setup',payload,state)
        self.assertEqual(status,200,out);self.assertEqual(out['user']['role'],'admin')
        self.assertNotEqual(old,state['cookie']);self.assertFalse(owner_auth.PAIRING.valid(payload['pairing']))
        self.assertTrue(self.request('/api/desktop/setup-status')[1]['initialized'])
        owner_auth.PAIRING=owner_auth.Pairing()
        self.assertEqual(self.request('/api/desktop/setup',self.payload(),self.client())[0],409)
        with self.app.db() as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0],1)
            c.execute("UPDATE users SET role='student'")
        self.app.init()
        self.assertTrue(self.request('/api/desktop/setup-status')[1]['initialized'])

    def test_expired_pairing_and_interrupted_invalid_setup_do_not_initialize(self):
        state=self.client();payload=self.payload();owner_auth.PAIRING.expires=0
        self.assertEqual(self.request('/api/desktop/setup',payload,state)[0],403)
        owner_auth.PAIRING=owner_auth.Pairing();payload=self.payload()
        self.assertEqual(self.request('/api/desktop/setup',dict(payload,password='short'),state)[0],400)
        self.assertTrue(owner_auth.PAIRING.valid(payload['pairing']))
        self.assertEqual(self.request('/api/desktop/setup',payload,state)[0],200)

    def test_pairing_concurrency_creates_exactly_one_teacher(self):
        states=[self.client(),self.client()];payload=self.payload()
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            codes=list(pool.map(lambda state:self.request('/api/desktop/setup',payload,state)[0],states))
        self.assertEqual(codes.count(200),1,codes)
        with self.app.db() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM users').fetchone()[0],1)

    def test_pairing_throttle_is_server_side(self):
        state=self.client();payload=dict(self.payload(),pairing='wrong')
        for _ in range(5):self.assertEqual(self.request('/api/desktop/setup',payload,state)[0],403)
        self.assertEqual(self.request('/api/desktop/setup',self.payload(),state)[0],429)

    def test_owner_startup_never_prompts_for_account_and_cleans_pairing_window(self):
        http=mock.Mock();http.serve_forever.side_effect=KeyboardInterrupt
        window=mock.Mock()
        with mock.patch.object(self.app,'ThreadingHTTPServer',return_value=http),mock.patch.object(owner_auth,'pairing_window',return_value=window),mock.patch.object(sys,'argv',['server.py']),mock.patch('builtins.input',side_effect=AssertionError('console account creation')),mock.patch.object(self.app.getpass,'getpass',side_effect=AssertionError('password prompt')),mock.patch('sys.stdout',new_callable=io.StringIO) as output:
            self.app.main()
            self.assertNotIn('Password',output.getvalue())
        window.close.assert_called_once();http.server_close.assert_called_once()
        with self.app.db() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM users').fetchone()[0],0)


class RememberTests(BackendCase):
    def remember(self):
        state=self.client('teacher');device='a'*64
        status,out,_=self.request('/api/desktop/remember',{'password':'synthetic-password-123','device':device},state)
        self.assertEqual(status,200,out)
        return state,{'refresh':out['refresh'],'device':device}

    def test_issue_requires_teacher_csrf_and_recent_password(self):
        payload={'password':'synthetic-password-123','device':'a'*64}
        self.assertEqual(self.request('/api/desktop/remember',payload,self.client())[0],401)
        self.assertEqual(self.request('/api/desktop/remember',payload,self.client('student'))[0],403)
        state=self.client('teacher')
        self.assertEqual(self.request('/api/desktop/remember',dict(payload,password='wrong'),state)[0],401)
        self.assertEqual(self.request('/api/desktop/remember',payload,state,headers={'X-CSRF-Token':'wrong'})[0],403)

    def test_restore_rotates_secret_and_old_access_and_replay_revokes_family(self):
        old,payload=self.remember();fresh=self.client()
        status,out,_=self.request('/api/desktop/refresh',payload,fresh)
        self.assertEqual(status,200,out);self.assertNotEqual(out['refresh'],payload['refresh'])
        self.assertEqual(out['user']['role'],'admin')
        self.assertIsNone(self.request('/api/me',state=old)[1]['user'])
        self.assertEqual(self.request('/api/desktop/refresh',payload,self.client())[0],401)
        self.assertIsNone(self.request('/api/me',state=fresh)[1]['user'])
        self.assertEqual(self.request('/api/desktop/refresh',dict(payload,refresh=out['refresh']),self.client())[0],401)

    def test_restore_survives_ordinary_session_loss_and_has_no_plaintext_db_secret(self):
        state,payload=self.remember()
        with self.app.db() as c:
            record=dict(c.execute('SELECT * FROM desktop_credentials').fetchone())
            self.assertNotIn(payload['refresh'],json.dumps(record))
            self.assertNotEqual(record['device'],payload['device'])
        self.app.SESSIONS.clear()
        self.assertEqual(self.request('/api/desktop/refresh',payload,self.client())[0],200)

    def test_password_role_expiration_and_wrong_device_revoke(self):
        for change in ('password','role','expires','idle','device'):
            with self.subTest(change=change):
                with self.app.db() as c:
                    c.execute("UPDATE users SET role='admin',password=? WHERE username='teacher'",(self.password_hash,))
                state,payload=self.remember()
                with self.app.db() as c:
                    if change=='password':c.execute("UPDATE users SET password='changed' WHERE username='teacher'")
                    elif change=='role':c.execute("UPDATE users SET role='student' WHERE username='teacher'")
                    elif change in ('expires','idle'):c.execute('UPDATE desktop_credentials SET '+change+'=0')
                if change=='device':payload['device']='b'*64
                self.assertEqual(self.request('/api/desktop/refresh',payload,self.client())[0],401)
                self.assertIsNone(self.request('/api/me',state=state)[1]['user'])

    def test_logout_and_disable_revoke_but_disable_keeps_normal_login(self):
        for action in ('/api/desktop/forget','/api/logout'):
            state,payload=self.remember()
            self.assertEqual(self.request(action,{},state)[0],200)
            self.assertEqual(self.request('/api/desktop/refresh',payload,self.client())[0],401)
            user=self.request('/api/me',state=state)[1]['user']
            self.assertEqual(user is None,action=='/api/logout')

    def test_student_cannot_revoke_another_teacher_device(self):
        state,payload=self.remember();other=self.client('teacher2')
        self.assertEqual(self.request('/api/desktop/forget',payload,other)[0],200)
        self.assertEqual(self.request('/api/desktop/refresh',payload,self.client())[0],200)

    def test_revoked_remembered_native_token_is_rejected(self):
        teacher,payload=self.remember();meeting=self.instant(teacher)
        cid=meeting['class_id']
        status,out,_=self.request('/api/admin/teacher-app-launch',{'class_id':cid},teacher)
        self.assertEqual(status,200,out)
        with self.app.db() as c:c.execute('DELETE FROM desktop_credentials')
        self.assertEqual(self.request('/api/teacher-app/state?token='+out['token'])[0],403)

    def test_disabling_remember_preserves_current_native_classroom_session(self):
        teacher,payload=self.remember();meeting=self.instant(teacher)
        status,out,_=self.request('/api/admin/teacher-app-launch',{'class_id':meeting['class_id']},teacher)
        self.assertEqual(status,200,out);cookie=teacher['cookie']
        self.assertEqual(self.request('/api/desktop/forget',{},teacher)[0],200)
        self.assertEqual(teacher['cookie'],cookie)
        self.assertEqual(self.request('/api/teacher-app/state?token='+out['token'])[0],200)
        self.assertEqual(self.request('/api/desktop/refresh',payload,self.client())[0],401)

    @unittest.skipUnless(os.name=='nt','DPAPI process restart acceptance requires Windows')
    def test_real_windows_remember_restore_in_new_process_and_logout(self):
        origin=f'http://127.0.0.1:{self.http.server_port}'
        env=os.environ.copy();env.update(LOCALAPPDATA=str(Path(self.temp.name)/'desktop-profile'),PYTHONUTF8='1')
        for operation in (
            "c.login('teacher','synthetic-password-123',remember=True); assert c.user['role']=='admin'",
            "assert c.startup_auth()=='authenticated'; assert c.me()['role']=='admin'",
            "assert c.startup_auth()=='authenticated'; c.logout(); assert c.startup_auth()=='login'",
        ):
            script='from teacher_desktop_app import APIClient; c=APIClient('+repr(origin)+'); '+operation
            result=subprocess.run([sys.executable,'-c',script],env=env,cwd=Path(__file__).parent,capture_output=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr.decode('utf-8','replace'))
        with self.app.db() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM desktop_credentials').fetchone()[0],0)


class DesktopStorageTests(unittest.TestCase):
    def test_build_metadata_labels_only_review_builds_as_review(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('review_windows_build',Path(__file__).parent/'packaging/windows/build.py')
        build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)
        with tempfile.TemporaryDirectory() as folder,mock.patch.object(build,'HERE',Path(folder)):
            for review in (True,False):
                build.assets(review=review)
                metadata=(Path(folder)/'generated/version.txt').read_text(encoding='utf-8')
                self.assertEqual('MathStudio Teacher Review' in metadata,review)
                self.assertIn("StringStruct('CompanyName','MathStudio project')",metadata)

    def test_no_non_windows_plaintext_fallback(self):
        with mock.patch.object(desktop_credentials,'available',return_value=False):
            with self.assertRaises(RuntimeError):desktop_credentials.crypt(b'synthetic','https://owner.example')

    @unittest.skipUnless(os.name=='nt','Real DPAPI requires Windows; never emulate it as acceptance')
    def test_actual_dpapi_roundtrip_origin_and_review_isolation(self):
        with tempfile.TemporaryDirectory() as folder,mock.patch.object(desktop_credentials,'state_directory',return_value=Path(folder)/'review'):
            origin='https://synthetic.example';token='s'*32+'.'+'t'*43;device='a'*64
            desktop_credentials.save(origin,token,device)
            self.assertNotIn(token.encode(),desktop_credentials.path_for(origin).read_bytes())
            self.assertEqual(desktop_credentials.load(origin)['refresh'],token)
            blob=desktop_credentials.path_for(origin).read_bytes()
            with self.assertRaises(RuntimeError):desktop_credentials.crypt(blob,'https://another.example',decrypt=True)
            with mock.patch.object(desktop_credentials,'state_directory',return_value=Path(folder)/'production'):
                with self.assertRaises(RuntimeError):desktop_credentials.crypt(blob,origin,decrypt=True)
            desktop_credentials.forget(origin);self.assertIsNone(desktop_credentials.load(origin))

    def test_desktop_restore_saves_rotated_credential_and_logout_clears(self):
        from teacher_desktop_app import APIClient
        client=APIClient('https://synthetic.example');stored={'refresh':'old','device':'a'*64}
        with mock.patch.object(desktop_credentials,'load',return_value=stored),mock.patch.object(desktop_credentials,'save') as save,mock.patch.object(desktop_credentials,'forget') as forget,mock.patch.object(client,'json',return_value={'user':{'id':1,'role':'admin'},'refresh':'rotated'}):
            self.assertEqual(client.startup_auth(),'authenticated')
            save.assert_called_once_with(client.base,'rotated',stored['device'])
            client.logout();forget.assert_called_once_with(client.base)
        self.assertIsNone(client.user)


class ReviewTunnelTests(unittest.TestCase):
    @unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Local pairing GUI needs Windows or Xvfb')
    def test_actual_pairing_window_uses_private_stdin_and_owned_cleanup(self):
        child=owner_auth.pairing_window('a'*32)
        try:
            self.assertIsNone(child.proc.poll())
            self.assertNotIn('a'*32,str(child.proc.args))
        finally:child.close()
        self.assertIsNotNone(child.proc.poll())

    def test_review_tunnel_uses_5059_and_cleanup_on_server_exit(self):
        import owner_launcher as launch
        child=mock.Mock();fake=SimpleNamespace(main=mock.Mock(side_effect=KeyboardInterrupt))
        with mock.patch.object(launch,'existing_server',return_value=False) as existing,mock.patch.object(launch,'OwnedProcess',return_value=child) as spawn,mock.patch.object(launch,'find_cloudflared',return_value='official-cloudflared'),mock.patch.object(launch,'tunnel_origin',return_value='https://synthetic.trycloudflare.com'),mock.patch.dict(sys.modules,{'server':fake}),mock.patch.dict(os.environ,{}),mock.patch('sys.stdout',new_callable=io.StringIO):
            self.assertEqual(launch.main(port=5059,bind='127.0.0.1',reuse=False),0)
            self.assertEqual(os.environ['PUBLIC_ORIGIN'],'https://synthetic.trycloudflare.com')
            self.assertEqual(os.environ['MATH_TRUSTED_PROXIES'],'127.0.0.1/32,::1/128')
        existing.assert_called_once_with(5059,allow_reuse=False)
        self.assertIn('http://127.0.0.1:5059',spawn.call_args.args[0]);child.close.assert_called_once()

    def test_tunnel_failure_never_initializes_backend(self):
        import owner_launcher as launch
        child=mock.Mock();fake=SimpleNamespace(main=mock.Mock())
        with mock.patch.object(launch,'existing_server',return_value=False),mock.patch.object(launch,'OwnedProcess',return_value=child),mock.patch.object(launch,'find_cloudflared',return_value='cloudflared'),mock.patch.object(launch,'tunnel_origin',side_effect=RuntimeError('startup failed')),mock.patch.dict(sys.modules,{'server':fake}):
            with self.assertRaises(RuntimeError):launch.main(port=5059,reuse=False)
        fake.main.assert_not_called();child.close.assert_called_once()


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Tk display required')
class DesktopAuthUI(BackendCase):
    def setUp(self):
        super().setUp()
        from teacher_desktop_app import TeacherDesktopApp,APIClient
        with mock.patch.object(TeacherDesktopApp,'_bootstrap'),mock.patch('teacher_desktop_app.read_language',return_value='en'):
            self.ui=TeacherDesktopApp()
        self.ui.client=APIClient(f'http://127.0.0.1:{self.http.server_port}')
        self.ui.remote=True

    def tearDown(self):
        import gc
        for job in self.ui.root.tk.call('after','info'):self.ui.root.after_cancel(job)
        self.ui.root.destroy();self.ui=None;gc.collect()
        super().tearDown()

    def widgets(self,kind):
        def walk(parent):
            result=[]
            for widget in parent.winfo_children():
                if isinstance(widget,kind):result.append(widget)
                result.extend(walk(widget))
            return result
        return walk(self.ui.root)

    def test_setup_language_roundtrip_preserves_inputs_and_remember_default(self):
        from tkinter import ttk
        self.ui.show_setup()
        entries=self.widgets(ttk.Entry)
        values=['synthetic_teacher','王老师','synthetic-password-123','synthetic-password-123','a'*32]
        for entry,value in zip(entries,values):entry.insert(0,value)
        checkbox=self.widgets(ttk.Checkbutton)[0]
        self.assertFalse(checkbox.instate(['selected']))
        with mock.patch('teacher_desktop_app.save_language'):
            for language in ('zh','en'):
                next(button for button in self.widgets(ttk.Button) if button['text']=='中文 / EN').invoke()
                self.assertEqual(self.ui.lang,language)
                self.assertEqual([entry.get() for entry in self.widgets(ttk.Entry)],values)

    def test_login_without_remember_is_async_and_logout_returns_to_login(self):
        from tkinter import ttk
        self.ui.show_login()
        entries=self.widgets(ttk.Entry);entries[0].insert(0,'teacher');entries[1].insert(0,'synthetic-password-123')
        self.assertFalse(self.widgets(ttk.Checkbutton)[0].instate(['selected']))
        for label in ('Sign in to Teacher','logout'):
            if label=='logout':self.ui.sign_out()
            else:
                next(button for button in self.widgets(ttk.Button) if button['text']==label).invoke()
                self.assertTrue(self.ui._auth_busy)
            deadline=time.monotonic()+10
            while self.ui._auth_busy and time.monotonic()<deadline:
                self.ui.root.update();time.sleep(.01)
            self.assertFalse(self.ui._auth_busy)
        self.assertIsNone(self.ui.client.user)
        with self.app.db() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM desktop_credentials').fetchone()[0],0)

    def test_offline_old_tunnel_does_not_prevent_address_change(self):
        from teacher_desktop_app import APIClient
        old=self.ui.client
        with mock.patch.object(old,'logout',side_effect=RuntimeError('offline')),mock.patch('teacher_desktop_app.messagebox.askyesno',return_value=True),mock.patch('teacher_desktop_app.messagebox.showwarning') as warning,mock.patch('teacher_desktop_app.select_origin',return_value='https://new.trycloudflare.com'),mock.patch.object(self.ui,'_bootstrap') as connect,mock.patch.object(desktop_credentials,'forget') as forget:
            self.ui.change_owner_server()
            self.assertEqual(self.ui.client.base,'https://new.trycloudflare.com')
            forget.assert_called_once_with(old.base);warning.assert_called_once();connect.assert_called_once()


if __name__=='__main__':unittest.main()
