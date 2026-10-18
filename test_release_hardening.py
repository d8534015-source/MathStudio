"""Release hardening regressions; all backend data and file contents are synthetic."""
import io
import unittest
from urllib.parse import quote
from test_security_stability import BackendCase

class FileContentTests(BackendCase):
    def resource(self,name,mime,data):
        teacher=self.client('teacher')
        upload=self.request('/api/admin/files/upload',state=teacher,raw=data,headers={
            'Content-Type':'application/octet-stream','X-CSRF-Token':teacher['csrf'],
            'X-File-Name':quote(name),'X-File-Type':mime})
        self.assertEqual(upload[0],200,upload[1]);fid=upload[1]['file']['id']
        code=self.request('/api/admin/files/code',{'file_ids':[fid],'label':'Synthetic'},teacher)
        self.assertEqual(code[0],200,code[1])
        student=self.client('student')
        grant=self.request('/api/resources/redeem',{'code':code[1]['code']},student)
        self.assertEqual(grant[0],200,grant[1])
        return student,'?grant='+grant[1]['grant']+'&file='+str(fid)

    def test_sec05_active_and_mismatched_content_is_downloaded(self):
        for name,mime,data in [('notes.custom','text/html',b'<script>alert(1)</script>'),
                               ('notes.xml','application/xml',b'<svg onload="alert(1)"/>'),
                               ('vector.custom','image/svg+xml',b'<svg onload="alert(1)"/>'),
                               ('notes.png','image/png',b'<html>active</html>'),
                               ('notes.pdf','application/pdf',b'<script>active</script>')]:
            with self.subTest(name=name):
                student,query=self.resource(name,mime,data)
                status,body,headers=self.request('/resource/open'+query,state=student)
                self.assertEqual(status,200);self.assertEqual(body,data)
                self.assertTrue(headers['Content-Disposition'].startswith('attachment;'))
                self.assertEqual(headers['Content-Type'],'application/octet-stream')
                self.assertIn('sandbox',headers.get('Content-Security-Policy',''))

    def test_sec05_supported_pdf_and_raster_preview_and_session_isolation(self):
        from PIL import Image
        image=io.BytesIO();Image.new('RGB',(2,2)).save(image,format='PNG')
        for name,mime,data in [('公式.png','image/png',image.getvalue()),
                               ('notes.pdf','application/pdf',b'%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF\n')]:
            with self.subTest(name=name):
                student,query=self.resource(name,mime,data)
                status,body,headers=self.request('/resource/open'+query,state=student)
                self.assertEqual(status,200);self.assertEqual(body,data)
                self.assertEqual(headers['Content-Type'],mime)
                self.assertTrue(headers['Content-Disposition'].startswith('inline;'))
                self.assertIn('sandbox',headers.get('Content-Security-Policy',''))
                self.assertEqual(headers['X-Content-Type-Options'],'nosniff')
                self.assertEqual(self.request('/resource/open'+query,state=self.client('other'))[0],403)
                download=self.request('/resource/download'+query,state=student)
                self.assertTrue(download[2]['Content-Disposition'].startswith('attachment;'))
                self.assertEqual(download[2]['Content-Type'],'application/octet-stream')

    def test_sec05_header_injection_names_are_rejected(self):
        teacher=self.client('teacher')
        result=self.request('/api/admin/files/upload',state=teacher,raw=b'synthetic',headers={
            'Content-Type':'application/octet-stream','X-CSRF-Token':teacher['csrf'],
            'X-File-Name':quote('safe\r\nInjected: header.txt'),'X-File-Type':'text/plain'})
        self.assertEqual(result[0],400)

import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace,MethodType
from unittest import mock
from test_teaching_workflows import extracted_functions

class ConfigTests(unittest.TestCase):
    def test_pkg03_explicit_legacy_import_is_data_only_and_rejects_commands(self):
        from private_config import parse_legacy
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'旧配置.bat'
            path.write_text('@echo off\nset "CLOUDFLARE_TURN_KEY_ID=synthetic-id"\nset "CLOUDFLARE_TURN_API_TOKEN=synthetic-token"\n')
            self.assertEqual(parse_legacy(path)['CLOUDFLARE_TURN_KEY_ID'],'synthetic-id')
            for extra in ('\nstart malware.exe','\nset "PATH=attacker"','\ncall other.bat','\nset "CLOUDFLARE_TURN_KEY_ID=duplicate"'):
                original=path.read_text();path.write_text(original+extra)
                with self.assertRaises(ValueError):parse_legacy(path)
                path.write_text(original)
            path.write_text('set "CLOUDFLARE_TURN_KEY_ID=YOUR_KEY"\nset "CLOUDFLARE_TURN_API_TOKEN=YOUR_TOKEN"')
            with self.assertRaises(ValueError):parse_legacy(path)

    def test_pkg03_private_storage_environment_precedence_and_no_secret_logs(self):
        from private_config import write_config,read_config,apply_config,main
        values={'CLOUDFLARE_TURN_KEY_ID':'synthetic-id','CLOUDFLARE_TURN_API_TOKEN':'synthetic-never-valid-token'}
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'用户 设置'/'private_config.json'
            write_config(values,path);self.assertEqual(read_config(path),values)
            env={'CLOUDFLARE_TURN_API_TOKEN':'explicit-value'};apply_config(env,path)
            self.assertEqual(env['CLOUDFLARE_TURN_API_TOKEN'],'explicit-value')
            with mock.patch.dict(os.environ,{'MATH_CONFIG':str(path)}),mock.patch.object(sys,'argv',['config','check']),mock.patch('sys.stdout',new_callable=io.StringIO) as output:
                self.assertEqual(main(),0)
                self.assertNotIn(values['CLOUDFLARE_TURN_API_TOKEN'],output.getvalue())
            if os.name!='nt':self.assertEqual(path.stat().st_mode&0o077,0)

    def test_pkg03_incomplete_or_ambiguous_configuration_fails_closed(self):
        from private_config import validate,read_config
        for values in ({'CLOUDFLARE_TURN_KEY_ID':'synthetic'}, {'TURN_URL':'turn:synthetic.invalid'},
                       {'MATH_R2_BUCKET':'synthetic'},{'MATH_MAX_UPLOAD_MB':'bad'}):
            with self.assertRaises(ValueError):validate(values)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'private_config.json';path.write_text('{"STUN_URL":"stun:one.invalid","STUN_URL":"stun:two.invalid"}')
            with self.assertRaises(ValueError):read_config(path)

    def test_pkg03_launchers_never_execute_or_discover_private_batch_files(self):
        root=Path(__file__).parent
        for path in root.glob('*.bat'):
            text=path.read_text().lower()
            self.assertNotIn('call "%~dp0media_config.bat"',text,path.name)
            self.assertNotIn('call "%~dp0cloud_storage.bat"',text,path.name)
            self.assertNotIn('restore_media_config.ps1',text,path.name)
        recovery=(root/'restore_media_config.ps1').read_text().lower()
        self.assertNotIn('get-childitem',recovery);self.assertNotIn('invoke-expression',recovery)
        self.assertIn('mandatory=$true',recovery)

class RuntimeTests(unittest.TestCase):
    def test_dep01_old_installed_pillow_is_rejected(self):
        import dependency_check
        with mock.patch.object(dependency_check,'version',return_value='10.0.0'):
            with self.assertRaisesRegex(RuntimeError,'SETUP MATHSTUDIO'):dependency_check.require_distribution('Pillow')
        self.assertEqual(set(dependency_check.pinned_versions()),{'Pillow','pypdf','tzdata'})
        self.assertNotIn('PyPDF2',Path('server.py').read_text())

    def test_dep01_native_bootstrap_never_installs_during_launch(self):
        import teacher_app_bootstrap,dependency_check
        with mock.patch.object(sys,'platform','win32'),mock.patch.object(teacher_app_bootstrap,'parse_args',return_value=SimpleNamespace()),mock.patch.object(dependency_check,'verify_runtime',side_effect=RuntimeError('outdated dependency')),mock.patch.object(teacher_app_bootstrap,'message') as message,mock.patch.object(subprocess,'run') as run,mock.patch.object(subprocess,'Popen') as popen:
            self.assertEqual(teacher_app_bootstrap.main(),2)
            run.assert_not_called();popen.assert_not_called();message.assert_called_once()

    def test_dep01_pinned_timezone_data_works_without_system_database(self):
        import zoneinfo
        from datetime import datetime
        from studio_time import studio_zone
        original=zoneinfo.TZPATH
        try:
            zoneinfo.reset_tzpath([]);zoneinfo.ZoneInfo.clear_cache()
            zone=studio_zone('America/Edmonton')
            self.assertEqual(datetime(2026,11,1,16,tzinfo=zone).utcoffset().total_seconds(),-6*3600)
            zoneinfo.ZoneInfo('Asia/Shanghai')
        finally:zoneinfo.reset_tzpath(original);zoneinfo.ZoneInfo.clear_cache()

    def test_pkg01_clean_teacher_start_creates_account_then_server(self):
        events=[]
        ns=extracted_functions('teacher_desktop_app.py',{'_bootstrap'},
            {'can_connect':lambda:False,'server_build':lambda:'synthetic-build','BUILD_ID':'synthetic-build',
             'ensure_admin_account':lambda root:events.append('account') or True,
             'start_server_process':lambda:events.append('server') or 'process'})
        obj=SimpleNamespace(root=SimpleNamespace(deiconify=lambda:None),show_login=lambda:events.append('login'),
            show_server_offline=lambda message:events.append('offline'))
        MethodType(ns['_bootstrap'],obj)()
        self.assertEqual(events,['account','server','login'])

    def test_pkg01_matching_server_is_reused_and_mismatch_never_started(self):
        for build,expected in [('synthetic-build',['login']),('different',['offline'])]:
            events=[]
            ns=extracted_functions('teacher_desktop_app.py',{'_bootstrap'},
                {'can_connect':lambda:True,'server_build':lambda:build,'BUILD_ID':'synthetic-build',
                 'ensure_admin_account':lambda root:events.append('account'),
                 'start_server_process':lambda:events.append('server')})
            obj=SimpleNamespace(root=SimpleNamespace(deiconify=lambda:None),show_login=lambda:events.append('login'),
                show_server_offline=lambda message:events.append('offline'))
            MethodType(ns['_bootstrap'],obj)();self.assertEqual(events,expected)

    def test_pkg01_data_paths_preserve_legacy_and_upgrade_state(self):
        from runtime_paths import data_directory
        with tempfile.TemporaryDirectory() as folder,mock.patch.dict(os.environ,{'MATH_DATA':'','LOCALAPPDATA':folder}):
            root=Path(folder)/'app';root.mkdir()
            self.assertEqual(data_directory(root),Path(folder)/'MathStudio'/'data')
            legacy=root/'bulletin_data';legacy.mkdir();(legacy/'posts.db').write_bytes(b'synthetic')
            self.assertEqual(data_directory(root),legacy)
            with mock.patch.dict(os.environ,{'MATH_DATA':str(Path(folder)/'chosen')}):self.assertEqual(data_directory(root),(Path(folder)/'chosen').resolve())
            self.assertEqual((legacy/'posts.db').read_bytes(),b'synthetic')

    def test_pkg01_setup_enforces_hashed_wheels_and_explicit_offline_source(self):
        import runtime_setup
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'用户 Folder';root.mkdir()
            with mock.patch.object(runtime_setup,'ROOT',root),mock.patch.object(runtime_setup,'VENV',root/'.venv'),mock.patch.object(runtime_setup.socket,'create_connection',side_effect=OSError),mock.patch.object(runtime_setup.venv,'EnvBuilder') as builder,mock.patch.object(runtime_setup.subprocess,'run') as run,mock.patch('sys.stdout',new_callable=io.StringIO):
                runtime_setup.install(root/'verified wheels')
                command=run.call_args_list[0].args[0]
                for option in ('--require-hashes','--only-binary=:all:','--no-index','--find-links'):self.assertIn(option,command)
                self.assertNotIn('--extra-index-url',command)
                self.assertEqual(command[command.index('--find-links')+1],str((root/'verified wheels').resolve()))
                builder.assert_called_once_with(with_pip=True,clear=False)

    def test_pkg01_setup_refuses_running_server_before_changing_runtime(self):
        import runtime_setup
        with mock.patch.object(runtime_setup.socket,'create_connection') as connection,mock.patch.object(runtime_setup.venv,'EnvBuilder') as builder:
            with self.assertRaisesRegex(RuntimeError,'5051'):runtime_setup.install()
            builder.assert_not_called()

    def test_dep01_pdf_worker_uses_pinned_parser_and_fails_closed(self):
        from pypdf import PdfWriter
        output=io.BytesIO();writer=PdfWriter();writer.add_blank_page(width=72,height=72);writer.write(output)
        worker=Path(__file__).with_name('document_worker.py')
        valid=subprocess.run([sys.executable,str(worker)],input=output.getvalue(),capture_output=True,timeout=20)
        self.assertEqual(valid.returncode,0,valid.stderr)
        invalid=subprocess.run([sys.executable,str(worker)],input=b'not a PDF',capture_output=True,timeout=20)
        self.assertNotEqual(invalid.returncode,0)

class PackagingTests(unittest.TestCase):
    def manifest(self,root):
        (root/'app.py').write_text('# synthetic release source\n')
        return {'folders':{'teacher':'MathStudio_v41_6_6_TEACHER_READY_Release_Candidate'},'files':{
            'app.py':{'packages':['teacher'],'sha256':hashlib.sha256((root/'app.py').read_bytes()).hexdigest()}}}

    def test_pkg02_allowlist_excludes_private_files_and_is_reproducible(self):
        import zipfile
        from release_package import create_archive
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);manifest=self.manifest(root)
            (root/'media_config.bat').write_text('synthetic private credentials')
            (root/'posts.db').write_bytes(b'synthetic private database')
            (root/'student.txt').write_text('synthetic private student file')
            one=root/'one.zip';two=root/'two.zip'
            self.assertEqual(create_archive(root,manifest,'teacher',one),create_archive(root,manifest,'teacher',two))
            with zipfile.ZipFile(one) as archive:self.assertEqual(len(archive.namelist()),2)
            with self.assertRaises(FileExistsError):create_archive(root,manifest,'teacher',one)

    def test_pkg02_rejects_changed_sources_symlinks_and_private_paths(self):
        from release_package import candidate_files
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);manifest=self.manifest(root)
            (root/'app.py').write_text('changed')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):candidate_files(root,manifest,'teacher')
            for name in ('../secret','media_config.bat','private_config.json','data.db','MathStudioTeacher.exe','.venv/file.py'):
                manifest['files']={name:{'packages':['teacher'],'sha256':'0'*64}}
                with self.assertRaises(ValueError):candidate_files(root,manifest,'teacher')
            target=root/'real.py';target.write_text('synthetic')
            try:(root/'link.py').symlink_to(target)
            except OSError:
                if os.name=='nt':self.skipTest('Symlink creation unavailable to this Windows test user; do not change Windows protections.')
                raise
            manifest['files']={'link.py':{'packages':['teacher'],'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}}
            with self.assertRaises(ValueError):candidate_files(root,manifest,'teacher')

class VersionRouteTests(BackendCase):
    def test_pkg04_canonical_build_labels_assets_and_navigation(self):
        from build_info import BUILD_ID,ASSET_VERSION
        info=self.request('/api/desktop-info')[1]
        self.assertEqual(info['build'],BUILD_ID)
        for path in ('/','/diagnostics.js','/build_info.js'):
            result=self.request(path);self.assertEqual(result[0],200)
            text=result[1].decode()
            self.assertIn(BUILD_ID,text);self.assertNotIn('__BUILD_ID__',text)
            if path=='/':self.assertIn(ASSET_VERSION,text);self.assertNotIn('__ASSET_VERSION__',text)
        response=self.request('/admin');self.assertEqual(response[0],302)
        self.assertEqual(response[2]['Location'],'/teacher')
        for path in ('/teacher','/account','/join','/booking','/resources','/messages'):
            self.assertEqual(self.request(path)[0],200,path)
        self.assertNotIn("location.href='/admin'",Path('classroom.js').read_text())

    def test_dep01_pdf_timeout_is_bounded_and_reported(self):
        row={'original_name':'synthetic.pdf','mime':'application/pdf','storage_key':'synthetic','storage_backend':'local'}
        # Invoke the same production extractor without touching storage or translation services.
        with mock.patch.object(self.app,'storage_get',return_value=b'%PDF-1.7\n%%EOF'),mock.patch.object(self.app.subprocess,'run',side_effect=subprocess.TimeoutExpired('worker',15)):
            with self.assertRaises(self.app.APIError) as ex:self.app._extract_translatable_text(row)
            self.assertIn('timed out',str(ex.exception))

class ManifestConsistencyTests(unittest.TestCase):
    def test_pkg02_actual_manifest_matches_all_reviewed_source_inputs(self):
        from release_package import candidate_files
        from build_info import INFO
        root=Path(__file__).resolve().parent
        manifest=json.loads((root/'release_manifest.json').read_text())
        self.assertEqual(manifest['version'],INFO)
        for kind in ('teacher','owner'):
            files=candidate_files(root,manifest,kind)
            self.assertIn('requirements.txt',files);self.assertIn('version.json',files)
            self.assertIn('INSTALL_WINDOWS.md',files);self.assertNotIn('MathStudioTeacher.exe',files)
            self.assertNotIn('media_config.bat',files)
