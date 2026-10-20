"""Actual encoder -> authenticated OWNER -> multipart transport -> actual FFmpeg.

R2 is memory-backed, sources synthetic, file picker mocked. No live cloud/devices.
"""
import hashlib,io,json,shutil,subprocess,tempfile,threading,time,unittest
from pathlib import Path
from test_security_stability import BackendCase
import test_classroom_recording as fixtures
from recording_cloud import R2
try:
    from playwright.sync_api import sync_playwright
except ImportError:sync_playwright=None

class MemoryR2(R2):
    def __init__(self):
        super().__init__(lambda:{'backend':'r2'});self.parts={};self.objects={};self.entered=threading.Event();self.release=threading.Event();self.pause=True
    def request(self,method,key,body=b'',query=None,headers=None,stream=False):
        query=query or {}
        if method=='POST' and 'uploads' in query:
            self.parts[key]={};return b'<InitiateMultipartUploadResult><UploadId>synthetic</UploadId></InitiateMultipartUploadResult>',{}
        if method=='PUT':self.parts[key][int(query['partNumber'])]=body;return b'',{'ETag':'"synthetic-'+str(query['partNumber'])+'"'}
        if method=='POST':
            if self.pause and not key.endswith('_playback'):
                self.pause=False;self.entered.set()
                if not self.release.wait(10):raise RuntimeError('Synthetic acknowledgment held')
            self.objects[key]=b''.join(v for k,v in sorted(self.parts[key].items()))
            return b'<CompleteMultipartUploadResult/>',{}
        if method=='HEAD':
            if key not in self.objects:raise RuntimeError('Not committed')
            return b'',{'Content-Length':str(len(self.objects[key]))}
        if method=='GET':
            data=self.objects[key];response=io.BytesIO(data);response.status=200;response.headers={'Content-Length':str(len(data)),'Content-Type':'video/webm'};return response
        if method=='DELETE':self.objects.pop(key,None);return b'',{}
        raise AssertionError('Unexpected synthetic R2 operation')

@unittest.skipUnless(sync_playwright and shutil.which('chromium') and shutil.which('ffmpeg'),'Optional real Chromium/FFmpeg integration harness unavailable')
class StopBrowserTests(BackendCase):
    def test_short_silent_teacher_cloud_inflight_stop_multiple_participants_and_local_stop(self):
        teacher,student,cid,tp,sp=self.room();fixtures.RecordingTests.policy(self)
        store=self.app.RECORDING_STORE;cloud=MemoryR2();store.cloud=cloud
        exe=Path(shutil.which('ffmpeg'));(self.app.DATA/'recording-processor.json').write_text(json.dumps({'ffmpeg':str(exe),'sha256':hashlib.sha256(exe.read_bytes()).hexdigest()}))
        store.launch();base=f'http://127.0.0.1:{self.http.server_port}'
        try:
            with sync_playwright() as p,tempfile.TemporaryDirectory() as directory:
                browser=p.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox','--autoplay-policy=no-user-gesture-required'])
                ctx=browser.new_context();csrf=ctx.request.get(base+'/api/me').json()['csrf']
                self.assertTrue(ctx.request.post(base+'/api/login',data={'username':'teacher','password':'synthetic-password-123'},headers={'X-CSRF-Token':csrf}).ok)
                page=ctx.new_page();page.goto(base+'/recordings')
                for cycle in range(3):
                    with self.app.LOCK:self.app.ROOMS[cid]['peers'].clear()
                    page.evaluate('''async ({cid,local})=>{
                      window.saved=[];window.savedClosed=false;
                      window.showSaveFilePicker=async()=>({createWritable:async()=>({write:async b=>saved.push(Array.from(new Uint8Array(await b.arrayBuffer()))),close:async()=>{savedClosed=true;},abort:async()=>{}})});
                      const {MeetingRecorder}=await import('/classroom_recorder.js');window.messages=[];
                      const csrf=(await fetch('/api/me').then(r=>r.json())).csrf;
                      window.api=async(path,data)=>{const r=await fetch(path,{method:data?'POST':'GET',headers:data?{'Content-Type':'application/json','X-CSRF-Token':csrf}:{},body:data?JSON.stringify(data):undefined});const out=await r.json();if(!r.ok)throw Error('HTTP '+r.status);return out;};
                      window.peer=(await api('/api/room/join',{class_id:cid})).peer;
                      window.post=(action,data={})=>api('/api/room/'+action,{class_id:cid,peer,...data});
                      window.board=document.createElement('canvas');board.width=1280;board.height=720;board.getContext('2d').fillText('Synthetic x + 1 = 2',100,100);
                      window.r=new MeetingRecorder({host:document.createElement('div'),admin:true,post,api,snapshot:()=>({board,audio:[],cameras:[]}),notice:x=>messages.push(x)});r.choice.mode=local?'local':'cloud';
                    }''',{'cid':cid,'local':cycle==2})
                    if cycle==1:
                        sp=self.request('/api/room/join',{'class_id':cid},student)[1]['peer']
                    page.evaluate('r.request()');rid=page.evaluate('r.state.id')
                    if cycle==1:self.assertEqual(self.request('/api/room/recording-consent',{'class_id':cid,'peer':sp,'id':rid,'accepted':True},student)[0],200)
                    page.evaluate('r.start()');page.wait_for_timeout(450 if cycle==0 else 1300)
                    if cycle==1:
                        page.evaluate("r.snapshot=()=>({board,audio:[],cameras:[]});board.getContext('2d').fillRect(5,5,10,10)")
                    page.evaluate('r.stop(true)')
                    self.assertFalse(page.evaluate('r.fault'));self.assertGreater(page.evaluate('r.sequence'),0)
                    self.assertTrue(page.evaluate("r.metrics.failure===undefined"))
                    if cycle==2:
                        self.assertTrue(page.evaluate('savedClosed'));data=bytes(sum(page.evaluate('saved'),[]));self.assertNotIn(cloud.key(rid),cloud.objects)
                        self.assertEqual(store.row(rid,self.uid('teacher'))['state'],'local')
                    else:
                        if cycle==0:
                            self.assertTrue(cloud.entered.wait(2));self.assertNotEqual(store.row(rid,self.uid('teacher'))['state'],'ready');cloud.release.set()
                        deadline=time.monotonic()+12
                        while store.row(rid,self.uid('teacher'))['state']!='ready' and time.monotonic()<deadline:page.wait_for_timeout(100)
                        row=store.row(rid,self.uid('teacher'));self.assertEqual(row['state'],'ready',row.get('error'));self.assertEqual(row['interrupted'],0)
                        self.assertEqual(row['playback_state'],'ready');data=cloud.objects[cloud.key(rid)]
                        indexed=Path(directory)/'indexed.webm';indexed.write_bytes(cloud.objects[cloud.key(rid+'_playback')])
                        subprocess.run(['ffmpeg','-v','error','-ss','0.1','-i',str(indexed),'-frames:v','1','-f','null','-'],check=True,timeout=10)
                        self.assertFalse((store.folder/(rid+'.webm')).exists())
                    original=Path(directory)/'original.webm';original.write_bytes(data)
                    subprocess.run(['ffmpeg','-v','error','-i',str(original),'-f','null','-'],check=True,timeout=10)
                browser.close()
        finally:
            cloud.release.set();store.close();store.worker.join(3);store.processor.join(3)
