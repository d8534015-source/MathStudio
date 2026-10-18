"""OWNER offline regressions: synthetic data only; model downloads are never used here."""
import concurrent.futures
import io
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
import public_translations as pt
from test_security_stability import BackendCase


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.env=mock.patch.dict(os.environ,{'MATH_ARGOS_HOME':self.temp.name})
        self.env.start()
        self.addCleanup(self.temp.cleanup);self.addCleanup(self.env.stop)

    def ready_files(self):
        python=ar.python_path();python.parent.mkdir(parents=True);python.touch()
        models={}
        for pair in ('en_zh','zh_en'):
            folder='translate-'+pair+'-1_9';path=Path(self.temp.name)/'packages'/folder
            (path/'model').mkdir(parents=True)
            (path/'model'/'model.bin').write_bytes(b'synthetic, not a real model')
            (path/'metadata.json').write_text('{}')
            models[pair]={'folder':folder}
        (Path(self.temp.name)/'installation.json').write_text(json.dumps({'schema':1,'argos':'1.11.0','verified':True,'models':models}))

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

    def test_process_scrubs_credentials_caps_threads_and_preserves_tokens(self):
        self.ready_files()
        token='MSKEEP'+'A'*24+'X0END'
        with mock.patch.dict(os.environ,{'CLOUDFLARE_TURN_API_TOKEN':'synthetic-only','OPENAI_API_KEY':'synthetic-only','MATH_PUBLIC_TRANSLATION_API_KEY':'synthetic-only'}):
            def run(command,**kwargs):
                self.assertEqual(command[1:3],['-I','-u'])
                self.assertFalse(any('KEY' in key or 'TOKEN' in key for key in kwargs['env']))
                self.assertEqual(kwargs['env']['ARGOS_INTRA_THREADS'],'1')
                self.assertEqual(kwargs['env']['ARGOS_DEVICE_TYPE'],'cpu')
                self.assertEqual(Path(kwargs['env']['USERPROFILE']).resolve(),Path(self.temp.name).resolve())
                self.assertEqual(kwargs['timeout'],30)
                self.assertEqual(Path(kwargs['cwd']).resolve(),Path(self.temp.name).resolve())
                request=json.loads(kwargs['input']);self.assertEqual(request['pieces'],['Learn ',' today.'])
                return subprocess.CompletedProcess(command,0,json.dumps({'pieces':['学习 ',' 今天。']}))
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
        for result in [subprocess.CompletedProcess([],2,''),subprocess.CompletedProcess([],0,'{}'),subprocess.CompletedProcess([],0,json.dumps({'pieces':[]})),subprocess.CompletedProcess([],0,json.dumps({'pieces':'x'}))]:
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
