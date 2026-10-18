"""Windows distribution/startup regressions; synthetic data only, no production network."""
import io
import json
import os
from pathlib import Path
import ssl
import sys
import tempfile
from types import SimpleNamespace,MethodType
import unittest
from unittest import mock
from urllib.error import HTTPError,URLError


class WindowsStartupTests(unittest.TestCase):
    def test_teacher_install_never_probes_owner_port(self):
        import runtime_setup as setup
        with tempfile.TemporaryDirectory() as folder,mock.patch.object(setup,'teacher_only',return_value=True),mock.patch.object(setup,'VENV',Path(folder)/'venv'),mock.patch.object(setup.socket,'create_connection',side_effect=AssertionError('client probed 5051')),mock.patch.object(setup.venv,'EnvBuilder'),mock.patch.object(setup.subprocess,'run'),mock.patch('sys.stdout',new_callable=io.StringIO):
            setup.install()

    def test_utf8_files_are_read_under_gbk_default(self):
        import teacher_connection as connection
        import dependency_check
        original=Path.open
        def gbk_open(path,mode='r',buffering=-1,encoding=None,errors=None,newline=None):
            return original(path,mode,buffering,encoding or ('gbk' if 'b' not in mode else None),errors,newline)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'teacher_connection.json').write_text(json.dumps({'server_url':'https://owner.example'},ensure_ascii=False)+'\n',encoding='utf-8')
            (root/'requirements.txt').write_text('# UTF-8 — 中文\nPillow==12.3.0\n',encoding='utf-8')
            with mock.patch.object(Path,'open',gbk_open),mock.patch.object(connection,'connection_path',return_value=root/'teacher_connection.json'),mock.patch.dict(os.environ,{'MATHSTUDIO_SERVER_URL':''}),mock.patch.object(dependency_check,'__file__',str(root/'dependency_check.py')):
                self.assertEqual(connection.configured_origin(),'https://owner.example')
                self.assertEqual(dependency_check.pinned_versions(),{'Pillow':'12.3.0'})

    def test_owner_launch_uses_no_powershell_or_backend_child(self):
        import runtime_setup as setup
        with mock.patch.object(setup,'teacher_only',return_value=False),mock.patch.object(setup,'verify_runtime'),mock.patch.object(setup,'cloudflared_available',return_value=True),mock.patch.object(setup,'apply_config',side_effect=lambda env:env),mock.patch('owner_launcher.main',return_value=0) as launch,mock.patch.object(setup.subprocess,'call') as child:
            self.assertEqual(setup.launch('website'),0)
            launch.assert_called_once();child.assert_not_called()

    def test_owned_child_cleanup_waits_and_never_kills_unrelated_process(self):
        from owner_launcher import OwnedProcess
        obj=OwnedProcess.__new__(OwnedProcess);obj.job=None;obj.proc=mock.Mock()
        obj.proc.poll.return_value=None
        obj.close()
        obj.proc.terminate.assert_called_once();obj.proc.wait.assert_called_once_with(timeout=5)
        obj.proc.kill.assert_not_called()

    def test_ctrl_c_cleans_only_owned_tunnel_and_restores_cli(self):
        import owner_launcher as launch
        fake_server=SimpleNamespace(main=mock.Mock(side_effect=KeyboardInterrupt))
        child=mock.Mock()
        args=sys.argv
        with mock.patch.object(launch,'existing_server',return_value=False),mock.patch.object(launch,'OwnedProcess',return_value=child),mock.patch.object(launch,'find_cloudflared',return_value='cloudflared'),mock.patch.object(launch,'tunnel_origin',return_value='https://synthetic.trycloudflare.com'),mock.patch.dict(sys.modules,{'server':fake_server}),mock.patch.dict(os.environ,{}),mock.patch('sys.stdout',new_callable=io.StringIO):
            self.assertEqual(launch.main(),0)
        child.close.assert_called_once();self.assertIs(sys.argv,args)

    def test_duplicate_owner_launch_does_not_touch_server_or_tunnel(self):
        import owner_launcher as launch
        with mock.patch.object(launch,'existing_server',return_value=True),mock.patch.object(launch,'OwnedProcess') as child:
            self.assertEqual(launch.main(),0);child.assert_not_called()

    def test_connection_diagnostics_distinguish_network_gateway_build_and_health(self):
        from teacher_connection import check_connection,ConnectionProblem
        from build_info import BUILD_ID
        errors=[(URLError('DNS failed'),'network'),(URLError(TimeoutError()),'timeout'),
                (URLError(ssl.SSLCertVerificationError('invalid')),'tls'),
                (HTTPError('https://owner.example',403,'Forbidden',{},None),'auth'),
                (HTTPError('https://owner.example',502,'Bad Gateway',{},None),'owner')]
        for error,code in errors:
            with self.subTest(code=code),mock.patch('urllib.request.urlopen',side_effect=error):
                with self.assertRaises(ConnectionProblem) as ex:check_connection('https://owner.example')
                self.assertEqual(ex.exception.code,code)
        response=mock.MagicMock();response.__enter__.return_value=response
        response.geturl.return_value='https://owner.example/api/desktop-info'
        with mock.patch('urllib.request.urlopen',return_value=response):
            response.read.return_value=json.dumps({'build':BUILD_ID}).encode()
            self.assertEqual(check_connection('https://owner.example'),'https://owner.example')
            response.read.return_value=b'{"build":"wrong"}'
            with self.assertRaises(ConnectionProblem) as ex:check_connection('https://owner.example')
            self.assertEqual(ex.exception.code,'build')

    def test_invalid_saved_address_can_be_replaced_without_reinstall(self):
        import teacher_connection as connection
        root=SimpleNamespace(withdraw=lambda:None,destroy=lambda:None)
        fake=SimpleNamespace(Tk=lambda:root,simpledialog=SimpleNamespace(askstring=lambda *a,**k:'https://new.example'),messagebox=SimpleNamespace(showerror=mock.Mock()))
        with tempfile.TemporaryDirectory() as folder,mock.patch.dict(sys.modules,{'tkinter':fake}),mock.patch.object(connection,'configured_origin',side_effect=ValueError('invalid saved URL')),mock.patch.object(connection,'check_connection',side_effect=lambda x:x),mock.patch.object(connection,'connection_path',return_value=Path(folder)/'settings.json'):
            self.assertEqual(connection.select_origin(),'https://new.example')
            self.assertEqual(json.loads((Path(folder)/'settings.json').read_text(encoding='utf-8'))['server_url'],'https://new.example')

    def test_frozen_native_command_uses_executable_dispatch(self):
        from test_teaching_workflows import extracted_functions
        calls=[]
        client=SimpleNamespace(base='https://owner.example',json=lambda *a:{'token':'synthetic'})
        namespace=extracted_functions('teacher_desktop_app.py',{'_launch_teacher_meeting'},
            {'sys':SimpleNamespace(frozen=True,executable='C:/用户 Folder/MathStudioClient.exe'),'ROOT':Path('/synthetic'),
            'subprocess':SimpleNamespace(Popen=lambda cmd,**kw:calls.append(cmd))})
        obj=SimpleNamespace(remote=True,client=client,tr=lambda x:x)
        self.assertTrue(MethodType(namespace['_launch_teacher_meeting'],obj)(1)['launched'])
        self.assertEqual(calls[0][:2],['C:/用户 Folder/MathStudioClient.exe','--meeting-bootstrap'])
        self.assertNotIn('teacher_app_bootstrap.py',calls[0])
