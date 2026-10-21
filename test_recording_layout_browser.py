"""Actual encoded dynamic framing, synthetic received media; no physical devices/R2."""
import functools,http.server,json,shutil,subprocess,tempfile,threading,unittest
from pathlib import Path
try:
    from playwright.sync_api import sync_playwright
except ImportError:sync_playwright=None

@unittest.skipUnless(sync_playwright and shutil.which('chromium') and shutil.which('ffmpeg'),'Optional Chromium/FFmpeg harness unavailable')
class LayoutBrowserTests(unittest.TestCase):
    def test_dynamic_layout_is_in_encoded_video_without_encoder_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            for name in ('classroom_recorder.js','recording_limits.js'):(folder/name).write_bytes(Path(name).read_bytes())
            (folder/'index.html').write_text('<html lang="en"><body></body></html>')
            class Quiet(http.server.SimpleHTTPRequestHandler):
                def log_message(self,*a):pass
            server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(folder)))
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                with sync_playwright() as playwright:
                    browser=playwright.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox','--autoplay-policy=no-user-gesture-required'])
                    page=browser.new_page();page.goto(f'http://127.0.0.1:{server.server_port}')
                    page.evaluate('''async()=>{
                      const {MeetingRecorder}=await import('/classroom_recorder.js');window.uploads=[];
                      const make=async color=>{const c=document.createElement('canvas');c.width=640;c.height=360;const cx=c.getContext('2d');cx.fillStyle=color;cx.fillRect(0,0,640,360);const v=document.createElement('video');v.muted=true;v.srcObject=c.captureStream(30);document.body.append(v);await v.play();return v;};
                      window.red=await make('red');window.blue=await make('blue');window.share=await make('yellow');
                      window.board=document.createElement('canvas');board.width=1280;board.height=720;board.getContext('2d').fillStyle='lime';board.getContext('2d').fillRect(0,0,1280,720);
                      window.people=[{id:'a',name:'Daniel Zhang',enabled:true,element:red}];window.screen=null;window.boardActive=false;
                      window.fetch=async(url,opts)=>{uploads.push(Array.from(new Uint8Array(await opts.body.arrayBuffer())));return {ok:true,json:async()=>({sequence:uploads.length})};};
                      const post=async action=>action==='recording-start'||action==='recording-heartbeat'?{id:'a'.repeat(32),lease_ms:1500,allowed:['a','b','c']}:{};
                      window.r=new MeetingRecorder({host:document.createElement('div'),admin:true,post,api:async()=>({}),notice:()=>{},snapshot:()=>({cameras:people,audio:[],screen,board:boardActive?board:null,boardActive})});await r.start();window.encoder=r.recorder;
                    }''')
                    samples=[]
                    for command,x,y,expected in [('',640,360,(255,0,0)),("people.push({id:'b',name:'李明',enabled:true,element:blue})",960,360,(0,0,255)),("people[0].enabled=false;people.splice(1)",100,100,(36,54,75)),("people[0].enabled=true;screen={id:'a',element:share}",200,200,(255,255,0)),("screen=null;boardActive=true",200,200,(0,255,0)),("boardActive=false;red.srcObject.getVideoTracks()[0].stop()",100,100,(36,54,75)),("people=[]",640,360,(16,29,43))]:
                        if command:page.evaluate(command)
                        page.wait_for_timeout(550)
                        samples.append((page.evaluate('(performance.now()-r.started)/1000'),x,y,expected))
                        page.wait_for_timeout(200)
                        self.assertTrue(page.evaluate('r.running&&r.recorder===encoder'),page.evaluate('({fault:r.fault,failure:r.failure,reason:r.reason})'))
                    page.evaluate('r.stop(true)');self.assertFalse(page.evaluate('r.fault'))
                    output=folder/'layout.webm';output.write_bytes(bytes(sum(page.evaluate('uploads'),[])))
                    for seconds,x,y,expected in samples:
                        data=subprocess.check_output(['ffmpeg','-v','error','-ss',str(seconds),'-i',str(output),'-frames:v','1','-vf',f'crop=2:2:{x}:{y}','-pix_fmt','rgb24','-f','rawvideo','-'],timeout=10)
                        self.assertGreaterEqual(len(data),3)
                        for actual,wanted in zip(data[:3],expected):self.assertLess(abs(actual-wanted),45,(seconds,list(data[:3]),expected))
                    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height','-of','json',str(output)]))
                    self.assertIn({'width':1280,'height':720},info['streams']);self.assertEqual(page.evaluate('r.metrics.requested'),'1280×720/30FPS');self.assertGreater(page.evaluate('r.metrics.effectiveCaptureFps'),24)
                    print('Dynamic encoded layout metrics:',json.dumps(page.evaluate('r.metrics')))
                    browser.close()
            finally:server.shutdown();server.server_close();thread.join(2)
