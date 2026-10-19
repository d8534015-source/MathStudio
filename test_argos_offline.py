"""OWNER offline regressions: synthetic data only; model downloads are never used here."""
import copy
import concurrent.futures
import contextlib
import io
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import unittest
from unittest import mock
import zipfile
import argos_runtime as ar
import argos_setup as setup
import argos_worker as worker
import public_translations as pt
from test_security_stability import BackendCase


def completed(*args):
    # Fixtures follow the binary-pipe contract used by every worker caller.
    result=subprocess.CompletedProcess(*args)
    for name in ('stdout','stderr'):
        value=getattr(result,name)
        if isinstance(value,str):setattr(result,name,value.encode('utf-8'))
    return result


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.env=mock.patch.dict(os.environ,{'MATH_ARGOS_HOME':self.temp.name})
        self.env.start()
        self.addCleanup(self.temp.cleanup);self.addCleanup(self.env.stop)

    def sentence_files(self):
        profile=copy.deepcopy(ar.PROFILE)
        folder=Path(self.temp.name)/'sentence-files';folder.mkdir(exist_ok=True)
        import hashlib
        for spec in profile['sentence_models'].values():
            data=b'synthetic sentence model, not real ONNX'
            (folder/spec['filename']).write_bytes(data)
            spec['sha256']=hashlib.sha256(data).hexdigest()
        patch=mock.patch.object(ar,'PROFILE',profile);patch.start();self.addCleanup(patch.stop)
        return folder

    def ready_files(self):
        sentence_files=self.sentence_files()
        python=ar.python_path();python.parent.mkdir(parents=True);python.touch()
        models={}
        for pair in ('en_zh','zh_en'):
            folder='translate-'+pair+'-1_9';path=Path(self.temp.name)/'packages'/folder
            (path/'model').mkdir(parents=True)
            (path/'model'/'model.bin').write_bytes(b'synthetic, not a real model')
            (path/'metadata.json').write_text('{}')
            sbd=path/'minisbd';sbd.mkdir()
            spec=ar.PROFILE['sentence_models'][pair];(sbd/spec['filename']).write_bytes((sentence_files/spec['filename']).read_bytes())
            models[pair]={'folder':folder}
        (Path(self.temp.name)/'installation.json').write_text(json.dumps({'schema':2,'profile':ar.PROFILE['id'],'argos':'1.11.0','python':'synthetic-test-runtime','verified':True,'models':models}))

    def test_missing_models_and_maintenance_are_lightweight_and_fail_closed(self):
        with mock.patch('subprocess.run') as child:
            self.assertFalse(ar.ready())
            with self.assertRaisesRegex(ar.ArgosError,'models are unavailable'):ar.translate('Hello','zh')
            child.assert_not_called()
        self.ready_files();self.assertTrue(ar.ready())
        with setup.maintenance():self.assertFalse(ar.ready())
        self.assertTrue(ar.ready())
        (Path(self.temp.name)/'packages'/'translate-zh_en-1_9'/'model'/'model.bin').unlink()
        self.assertFalse(ar.ready())

    def test_external_storage_survives_source_location_and_rejects_in_tree(self):
        self.assertEqual(ar.home(),Path(self.temp.name).resolve())
        with mock.patch.dict(os.environ,{'MATH_ARGOS_HOME':'relative-models'}):
            with self.assertRaises(ar.ArgosError):ar.home()
        with mock.patch.dict(os.environ,{'MATH_ARGOS_HOME':str(ar.ROOT/'models')}):
            with self.assertRaises(ar.ArgosError):ar.home()

    def test_readiness_requires_current_profile_and_pinned_sentence_models(self):
        self.ready_files();base=Path(self.temp.name)
        receipt=base/'installation.json';info=json.loads(receipt.read_text())
        info['schema']=1;receipt.write_text(json.dumps(info));self.assertFalse(ar.ready())
        info['schema']=2;receipt.write_text(json.dumps(info));self.assertTrue(ar.ready())
        (base/'packages'/'translate-en_zh-1_9'/'minisbd'/'en.onnx').write_bytes(b'corrupt')
        with mock.patch.object(setup,'download_model') as network:
            self.assertFalse(ar.ready());network.assert_not_called()
            with self.assertRaisesRegex(RuntimeError,'checksum'):
                setup.sentence_model(base,'en_zh',base/'packages'/'translate-en_zh-1_9'/'minisbd',allow_download=False)

    @unittest.skipUnless(importlib.util.find_spec('stanza'),'Optional installed dependency runtime required')
    def test_legacy_all_caps_is_unsupported_by_stanza110_data_api(self):
        from stanza.models.tokenization.data import TokenizationDataset
        dataset=object.__new__(TokenizationDataset)
        dataset.args={'feat_funcs':['all_caps']}
        with self.assertRaisesRegex(ValueError,'all_caps'):dataset.para_to_sentences([])

    @unittest.skipUnless(importlib.util.find_spec('minisbd') and os.environ.get('MATH_ARGOS_TEST_SBD_DIR'),'Official local MiniSBD models required')
    def test_real_minisbd_models_use_argos_supported_api_offline_repeatedly(self):
        import hashlib
        import onnxruntime
        onnxruntime.disable_telemetry_events()
        from types import SimpleNamespace
        with mock.patch.dict(os.environ,ar.environment(Path(self.temp.name))):
            from argostranslate import sbd,settings,translate
        self.assertEqual(settings.chunk_type,settings.ChunkType.MINISBD)
        root=Path(os.environ['MATH_ARGOS_TEST_SBD_DIR']);profile=worker.profile()
        for pair,spec in profile['sentence_models'].items():
            data=(root/spec['filename']).read_bytes();self.assertEqual(hashlib.sha256(data).hexdigest(),spec['sha256'])
            folder=Path(self.temp.name)/pair;(folder/'minisbd').mkdir(parents=True)
            (folder/'minisbd'/spec['filename']).write_bytes(data)
            pkg=SimpleNamespace(package_path=folder,from_code=pair.split('_')[0])
            engine=translate.PackageTranslation(None,None,pkg)
            detector=engine.sentencizer;self.assertIsInstance(detector,sbd.MiniSBDSentencizer)
            text='We learn mathematics. We solve an equation.' if pair=='en_zh' else '我们学习数学。我们解一个方程。'
            with mock.patch('stanza.Pipeline',side_effect=AssertionError('No legacy Stanza path')),mock.patch('torch.load',side_effect=AssertionError('No checkpoint conversion')),mock.patch('socket.create_connection',side_effect=AssertionError('No network')):
                first=detector.split_sentences(text);second=detector.split_sentences(text)
            self.assertEqual(first,second);self.assertEqual(len(first),2)
            self.assertEqual(detector.detector.session.get_providers(),['CPUExecutionProvider'])

    def test_process_scrubs_credentials_caps_threads_and_preserves_tokens(self):
        self.ready_files()
        token='MSKEEP'+'A'*24+'X0END'
        with mock.patch.dict(os.environ,{'CLOUDFLARE_TURN_API_TOKEN':'synthetic-only','OPENAI_API_KEY':'synthetic-only','MATH_PUBLIC_TRANSLATION_API_KEY':'synthetic-only'}):
            def run(command,**kwargs):
                self.assertEqual(command[1:3],['-I','-u'])
                self.assertFalse(any('KEY' in key or 'TOKEN' in key for key in kwargs['env']))
                self.assertEqual(kwargs['env']['ARGOS_INTRA_THREADS'],'1')
                self.assertEqual(kwargs['env']['ARGOS_DEVICE_TYPE'],'cpu')
                self.assertEqual(kwargs['env']['ARGOS_CHUNK_TYPE'],'MINISBD')
                self.assertIs(kwargs['stderr'],subprocess.DEVNULL)
                self.assertEqual(Path(kwargs['env']['USERPROFILE']).resolve(),Path(self.temp.name).resolve())
                self.assertEqual(kwargs['timeout'],30)
                self.assertEqual(Path(kwargs['cwd']).resolve(),Path(self.temp.name).resolve())
                request=json.loads(kwargs['input']);self.assertEqual(request['pieces'],['Learn ',' today.'])
                return completed(command,0,json.dumps({'pieces':['学习 ',' 今天。']}))
            with mock.patch.object(ar.subprocess,'run',side_effect=run):
                self.assertEqual(ar.translate('Learn '+token+' today.','zh'),'学习 '+token+' 今天。')

    def test_timeout_busy_and_bad_output_release_single_worker_slot(self):
        self.ready_files()
        with mock.patch.object(ar.subprocess,'run',side_effect=subprocess.TimeoutExpired('synthetic',30)):
            with self.assertRaisesRegex(ar.ArgosError,'timed out'):ar.translate('Hello','zh')
        self.assertTrue(ar._SLOT.acquire(False))
        try:
            with self.assertRaisesRegex(ar.ArgosError,'busy'):ar.translate('Hello','zh')
        finally:ar._SLOT.release()
        for result in [completed([],2,''),completed([],0,'{}'),completed([],0,json.dumps({'pieces':[]})),completed([],0,json.dumps({'pieces':'x'}))]:
            with mock.patch.object(ar.subprocess,'run',return_value=result):
                with self.assertRaises(ar.ArgosError):ar.translate('Hello','zh')
        self.assertTrue(ar._SLOT.acquire(False));ar._SLOT.release()

    def archive(self,names):
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w') as z:
            for name,value in names.items():
                info=zipfile.ZipInfo(name);info.filename=name  # Keep malicious backslashes on Windows too.
                z.writestr(info,value)
        buffer.seek(0);return buffer

    def test_setup_refuses_unsafe_models_wrong_pair_and_running_owner(self):
        with tempfile.TemporaryDirectory() as target:
            for name in ['../escape','/absolute','folder\\escape','C:/escape','folder/.. /escape','folder/CON','folder/file.','folder/file:stream']:
                with self.assertRaises(RuntimeError):setup.unpack_model(self.archive({name:'bad'}),target,'en_zh')
            wrong={'model/metadata.json':json.dumps({'from_code':'zh','to_code':'en','package_version':'1.9'}),'model/model/model.bin':'synthetic'}
            with self.assertRaises(RuntimeError):setup.unpack_model(self.archive(wrong),target,'en_zh')
        with mock.patch.object(setup.socket,'create_connection',return_value=mock.MagicMock()):
            with self.assertRaisesRegex(RuntimeError,'Stop OWNER'):setup.stopped_owner()
        with setup.maintenance():
            with self.assertRaisesRegex(RuntimeError,'already running'):
                with setup.maintenance():pass

    def test_technical_math_latex_names_and_urls_remain_verbatim(self):
        original=r'Use 2x + 3 = 7, x² + y² = z², \frac{x}{y}, $a^2+b^2$ and https://example.org with Alice Chen.'
        protected,spans=pt.protect(original,['Alice Chen'])
        for value in ['2x + 3 = 7','x² + y² = z²',r'\frac{x}{y}','$a^2+b^2$','https://example.org','Alice Chen']:
            self.assertNotIn(value,protected)
        restored=pt.restore('翻译：'+protected,spans)
        self.assertEqual(restored,'翻译：'+original)

    def test_worker_failure_reports_type_and_location_without_private_details(self):
        script="""import json,runpy,sys
def synthetic_failure(*args):
    raise FileNotFoundError(2,'synthetic-secret student text',r'C:\\Users\\Private Name\\private-model')
json.loads=synthetic_failure
runpy.run_path(sys.argv[1],run_name='__main__')
"""
        result=subprocess.run([__import__('sys').executable,'-c',script,str(Path(__file__).with_name('argos_worker.py'))],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,2);self.assertEqual(result.stdout,'')
        self.assertIn('ARGOS_DIAGNOSTIC exception=FileNotFoundError',result.stderr)
        self.assertIn('errno=2',result.stderr);self.assertIn('synthetic_failure:',result.stderr)
        for private in ['synthetic-secret','student text','Private Name','private-model','Traceback']:
            self.assertNotIn(private,result.stderr)

    def test_windows_binary_worker_pipes_isolate_native_codepage_output(self):
        import sys
        base=Path(self.temp.name);root=base/'launcher';root.mkdir()
        script='import sys\nsys.path.insert(0,'+repr(str(Path(worker.__file__).resolve().parent))+')\n'+r'''
import os,argos_worker
def native(payload):
    os.write(1,b'native stdout \xce\xd2\n')
    os.write(2,b'native stderr \xce\xd2\n')
    print('Python diagnostic',flush=True)
    if os.name=='nt':
        import ctypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.GetStdHandle.argtypes=(ctypes.c_uint32,);kernel.GetStdHandle.restype=ctypes.c_void_p
        kernel.WriteFile.argtypes=(ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint32,ctypes.POINTER(ctypes.c_uint32),ctypes.c_void_p)
        kernel.WriteFile.restype=ctypes.c_int
        data=b'native Win32 \xce\xd2\n';written=ctypes.c_uint32()
        if not kernel.WriteFile(kernel.GetStdHandle(0xfffffff5),data,len(data),ctypes.byref(written),None):raise OSError('native test write failed')
    return {'pieces':['学习数学','我们解方程'] if payload['target']=='zh' else ['Learn mathematics','Solve equations']}
argos_worker.run=native
raise SystemExit(argos_worker.main())
'''
        (root/'argos_worker.py').write_text(script,encoding='utf-8')
        real_run=subprocess.run;captures=[]
        def launch(command,**kwargs):
            self.assertIsInstance(kwargs['input'],bytes)
            self.assertFalse(any(key in kwargs for key in ('encoding','errors','text','universal_newlines')))
            result=real_run(command,**kwargs);captures.append(result)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn(b'\xce',result.stderr);self.assertNotIn(b'native',result.stdout)
            self.assertNotIn(b'UnicodeDecodeError',result.stderr)
            if os.name=='nt':self.assertIn(b'native Win32 \xce\xd2',result.stderr)
            return result
        with mock.patch.object(setup,'ROOT',root),mock.patch.object(ar,'python_path',return_value=Path(sys.executable)),mock.patch.object(setup.subprocess,'run',side_effect=launch),mock.patch('threading.excepthook') as thread_failure,contextlib.redirect_stdout(io.StringIO()):
            examples=setup.self_test(base,base/'packages')
        thread_failure.assert_not_called();self.assertEqual(len(captures),2)
        self.assertEqual(examples[0]['translation'],'学习数学')
        self.assertEqual(examples[0]['repeated_translation'],'我们解方程')
        self.assertEqual(examples[1]['translation'],'Learn mathematics')

    def test_binary_json_is_strict_and_native_diagnostics_remain_sanitized(self):
        self.assertEqual(ar.worker_json('{"pieces":["中文"]}'.encode('utf-8')),{'pieces':['中文']})
        for data in (b'\xce',b'{"pieces":["\xce"]}',b'log\n{"pieces":[]}',b'{'):
            with self.assertRaises(ValueError):ar.worker_json(data)
        data=b'private native \xce\nARGOS_DIAGNOSTIC exception=ValueError; at=argos_worker.run:1\nprivate native \xce'
        self.assertEqual(ar.worker_diagnostic(data),'exception=ValueError; at=argos_worker.run:1')
        self.assertNotIn('private',ar.worker_diagnostic(data))

    def test_self_test_diagnostics_and_response_validation_fail_closed(self):
        good=completed([],0,json.dumps({'pieces':['翻译','翻译']}),'')
        failure=completed([],2,'','private path and synthetic-secret\nARGOS_DIAGNOSTIC exception=RuntimeError; at=stanza.example.load:42\n')
        cases=[(failure,'exception=RuntimeError'),
               (completed([],2,'','private path and synthetic-secret'),'No safe exception record'),
               (completed([],0,'not JSON',''),'Invalid worker response'),
               (completed([],0,json.dumps({'pieces':[]}),''),'Invalid worker response'),
               (completed([],0,b'{"pieces":["\xce"]}',b'native \xce'),'Invalid worker response'),
               (completed([],0,json.dumps({'pieces':['我们一起学习数学。','我们一起学习数学。']}),''),'unchanged translation'),
               (subprocess.TimeoutExpired('private path and synthetic-secret',30),'deadline'),
               (FileNotFoundError(2,'synthetic-secret','private path'),'errno=2')]
        for failed,expected in cases:
            with self.subTest(expected=expected):
                with mock.patch.object(setup.subprocess,'run',side_effect=[good,failed]),contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaises(RuntimeError) as caught:setup.self_test(Path(self.temp.name),Path(self.temp.name)/'staged')
                message=str(caught.exception)
                self.assertIn('zh_en',message);self.assertIn(expected,message)
                self.assertIn('No new models were activated',message)
                self.assertNotIn('private path',message);self.assertNotIn('synthetic-secret',message)

    def test_retry_skips_pip_and_never_activates_models_on_second_direction_failure(self):
        base=Path(self.temp.name);python=ar.python_path();python.parent.mkdir(parents=True);python.touch()
        original=b'{"verified":false}'
        (base/'installation.json').write_bytes(original)
        sentence_files=self.sentence_files()
        archives=base/'official-files';archives.mkdir()
        for pair in ('en_zh','zh_en'):
            source,target=pair.split('_');folder='translate-'+pair+'-1_9'
            data={folder+'/metadata.json':json.dumps({'from_code':source,'to_code':target,'package_version':'1.9'}),folder+'/model/model.bin':'synthetic'}
            (archives/(folder+'.argosmodel')).write_bytes(self.archive(data).getvalue())
        results=[completed([],0,json.dumps({'pieces':['学习数学','学习数学']}),''),completed([],2,'','ARGOS_DIAGNOSTIC exception=ValueError; at=argos_worker.run:65\n')]
        for failure in (results[1],completed([],0,b'{"pieces":["\xce"]}',b'native diagnostic \xce')):
            with mock.patch.object(setup,'check_host'),mock.patch.object(setup.subprocess,'run',side_effect=[results[0],failure]) as child,contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(RuntimeError,'zh_en'):setup.install(model_files=archives,skip_dependencies=True,sbd_files=sentence_files)
            self.assertEqual(child.call_count,2)
            for call in child.call_args_list:
                self.assertIn('argos_worker.py',call.args[0][-1]);self.assertNotIn('pip',call.args[0])
            self.assertEqual((base/'installation.json').read_bytes(),original)
            self.assertEqual(list((base/'packages').iterdir()),[])
            self.assertFalse((base/'.setup.lock').exists());self.assertFalse(ar.ready())
        results[1]=completed([],0,json.dumps({'pieces':['We learn mathematics together.','We learn mathematics together.']}),'')
        with mock.patch.object(setup,'check_host'),mock.patch.object(setup.subprocess,'run',side_effect=results) as child,contextlib.redirect_stdout(io.StringIO()):
            setup.install(model_files=archives,skip_dependencies=True,sbd_files=sentence_files)
        self.assertEqual(child.call_count,2);self.assertTrue(ar.ready())
        receipt=json.loads((base/'installation.json').read_text(encoding='utf-8'))
        self.assertTrue(receipt['verified']);self.assertEqual(len(receipt['offline_examples']),2)

    def test_windows_diagnostic_uses_existing_models_and_never_activates(self):
        import diagnose_argos
        base=Path(self.temp.name);sentences=self.sentence_files()
        archives=base/'archives';archives.mkdir()
        for pair in ('en_zh','zh_en'):
            source,target=pair.split('_');folder='translate-'+pair+'-1_9'
            entries={folder+'/metadata.json':json.dumps({'from_code':source,'to_code':target,'package_version':'1.9'}),folder+'/model/model.bin':'synthetic'}
            (archives/(folder+'.argosmodel')).write_bytes(self.archive(entries).getvalue())
        receipt=base/'installation.json';receipt.write_bytes(b'original receipt')
        output=base/'report.json'
        inspect=completed([],0,json.dumps({'versions':{},'models':[]}),'')
        good=completed([],0,json.dumps({'pieces':['translated','translated']}),'')
        bad=completed([],2,'','ARGOS_DIAGNOSTIC exception=ValueError; at=argos_worker.run:1\nprivate path')
        for failure in (False,True):
            with self.subTest(failure=failure),mock.patch.object(setup,'check_host'),mock.patch.object(setup,'download_model',side_effect=AssertionError('No downloads')),mock.patch.object(setup.subprocess,'run',side_effect=[inspect,good,bad if failure else good]) as child,mock.patch('sys.argv',['diagnose_argos.py','--model-files',str(archives),'--sbd-files',str(sentences),'--output',str(output)]),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(diagnose_argos.main(),1 if failure else 0)
            report=json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(report['status'],'failed' if failure else 'passed_staged_real_models')
            self.assertNotIn('private path',output.read_text(encoding='utf-8'))
            self.assertEqual(receipt.read_bytes(),b'original receipt')
            self.assertFalse((base/'packages').exists());self.assertFalse((base/'.setup.lock').exists())
            self.assertEqual(child.call_count,3)
            for call in child.call_args_list:self.assertNotIn('pip',call.args[0])

    def test_acceptance_harness_checks_edits_and_reports_safe_failure(self):
        import verify_argos_models
        self.ready_files();output=Path(self.temp.name)/'acceptance.json'
        for fail in (False,True):
            model=ar.ArgosError('private-secret') if fail else lambda text,target:('学习 ' if target=='zh' else 'Learn ')+text
            with mock.patch.object(ar,'translate',side_effect=model),mock.patch('sys.argv',['verify_argos_models.py','--output',str(output)]),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(verify_argos_models.main(),1 if fail else 0)
            report=json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(report['status'],'failed' if fail else 'passed')
            self.assertNotIn('private-secret',output.read_text(encoding='utf-8'))
            if not fail:self.assertEqual(len(report['examples']),2)

    def test_worker_guard_denies_network_before_optional_imports(self):
        # A separate process prevents the guard from modifying this test runner's sockets.
        script="""import runpy,socket,sys
module=runpy.run_path(sys.argv[1])
try:module['run']({'target':'zh','pieces':[]})
except (ImportError,ValueError):pass
try:socket.create_connection(('example.org',443))
except OSError:print('offline guard active')
else:raise AssertionError('Network was allowed')
"""
        result=subprocess.run([__import__('sys').executable,'-c',script,str(Path(__file__).with_name('argos_worker.py'))],capture_output=True,text=True,timeout=30,env=ar.environment(Path(self.temp.name)))
        self.assertEqual(result.returncode,0,result.stderr);self.assertIn('offline guard active',result.stdout)


class ArgosBackendTests(BackendCase):
    def setUp(self):
        super().setUp()
        self.argos_env=mock.patch.dict(os.environ,{'MATH_PUBLIC_TRANSLATION_PROVIDER':'argos','MATH_ARGOS_HOME':str(Path(self.temp.name)/'argos')})
        self.argos_env.start();self.addCleanup(self.argos_env.stop)
        self.teacher=self.client('teacher')
        with self.app.db() as c:c.execute("UPDATE settings SET value='Study $x^2+1$ with Alice Chen at https://example.org.' WHERE key='intro'")
        self.request('/api/admin/content-translations',{'action':'config','enabled':True,'terms':['Alice Chen']},self.teacher)

    def payload(self,target='zh',op='generate'):
        info=self.request('/api/admin/content-translations',state=self.teacher)[1]
        source=next(x for x in info['sources'] if x['key']=='settings:0:intro')
        row=next((x for x in info['translations'] if x['source_key']==source['key'] and x['target']==target),{})
        return {'action':op,'key':source['key'],'target':target,'source_hash':source['source_hash'],'revision':row.get('revision',0)}

    def test_selected_missing_models_honest_and_no_external_fallback(self):
        info=self.request('/api/admin/content-translations',state=self.teacher)[1]
        self.assertEqual(info['config']['provider'],'argos');self.assertTrue(info['config']['offline']);self.assertFalse(info['config']['configured'])
        with mock.patch.object(ar,'translate') as worker,mock.patch.object(pt.urllib.request,'urlopen') as external:
            self.assertEqual(self.request('/api/admin/content-translations',self.payload(),self.teacher)[0],503)
            worker.assert_not_called();external.assert_not_called()
        self.assertEqual(self.request('/api/content-translations?lang=zh')[1]['translations'],{})

    def test_offline_both_directions_protection_cache_approval_edit_and_invalidation(self):
        def child(text,target):
            # This unit fake is not a real-model success claim.
            self.assertNotIn('Alice Chen',text);self.assertNotIn('$x^2+1$',text);self.assertNotIn('example.org',text)
            return ('离线草稿 ' if target=='zh' else 'Offline draft ')+text
        with mock.patch.object(ar,'ready',return_value=True),mock.patch.object(ar,'translate',side_effect=child) as model:
            for target in ('zh','en'):
                request=self.payload(target)
                self.assertEqual(self.request('/api/admin/content-translations',request,self.teacher)[0],200)
                self.assertTrue(self.request('/api/admin/content-translations',request,self.teacher)[1]['cached'])
                row=next(x for x in self.request('/api/admin/content-translations',state=self.teacher)[1]['translations'] if x['target']==target)
                approve=self.payload(target,'approve');approve['text']=row['draft']+' edited'
                self.assertEqual(self.request('/api/admin/content-translations',approve,self.teacher)[0],200)
                visible=self.request('/api/content-translations?lang='+target)[1]['translations']['settings:0:intro']
                self.assertEqual(visible['text'],approve['text'])
                for text in ['$x^2+1$','Alice Chen','https://example.org.']:self.assertIn(text,visible['text'])
            self.assertEqual(model.call_count,2)
            with self.app.db() as c:c.execute("UPDATE settings SET value='New public source' WHERE key='intro'")
            self.assertEqual(self.request('/api/content-translations?lang=zh')[1]['translations'],{})

    def test_classroom_poll_and_login_do_not_wait_for_offline_generation(self):
        teacher,student,cid,tp,sp=self.room()
        started=threading.Event();finish=threading.Event()
        def slow(text,target):
            started.set();finish.wait(3);return text
        payload=self.payload()
        with mock.patch.object(ar,'ready',return_value=True),mock.patch.object(ar,'translate',side_effect=slow):
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                job=pool.submit(self.request,'/api/admin/content-translations',payload,self.teacher)
                try:
                    self.assertTrue(started.wait(2))
                    now=time.monotonic()
                    self.assertEqual(self.request(f'/api/room/poll?class={cid}&peer={sp}',state=student)[0],200)
                    self.assertEqual(self.request('/api/me',state=student)[0],200)
                    self.assertLess(time.monotonic()-now,1)
                finally:finish.set()
                self.assertEqual(job.result()[0],200)

    def test_private_sources_never_reach_offline_engine(self):
        cid=self.lesson('individual','student')
        with mock.patch.object(ar,'ready',return_value=True),mock.patch.object(ar,'translate') as model:
            request=self.payload();request['key']=f'groups:{cid}:description'
            self.assertEqual(self.request('/api/admin/content-translations',request,self.teacher)[0],404)
            model.assert_not_called()
