"""Optional real Chromium mux/decode test, synthetic media only; no devices/cloud."""
import functools
import http.server
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest
try:
    from playwright.sync_api import sync_playwright
except ImportError:sync_playwright=None


@unittest.skipUnless(sync_playwright and shutil.which('chromium') and shutil.which('ffprobe'),'Optional Chromium/Playwright/ffprobe harness unavailable')
class BrowserRecording(unittest.TestCase):
    def test_actual_mux_tracks_pause_stop_annotations_and_original_tracks_survive(self):
        root=Path(__file__).parent
        with tempfile.TemporaryDirectory() as temp:
            temp=Path(temp);(temp/'classroom_recorder.js').write_bytes((root/'classroom_recorder.js').read_bytes())
            (temp/'index.html').write_text('<!doctype html><html lang="en"><body><div id="controls"></div><canvas id="board" width="1600" height="900"></canvas><canvas id="camera" width="320" height="180"></canvas><canvas id="screen" width="800" height="600"></canvas><video id="v" autoplay muted></video><video id="s" autoplay muted></video></body></html>')
            class Quiet(http.server.SimpleHTTPRequestHandler):
                def log_message(self,*args):pass
            server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(temp)))
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                with sync_playwright() as p:
                    browser=p.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox','--autoplay-policy=no-user-gesture-required'])
                    page=browser.new_page(viewport={'width':1400,'height':900});page.goto(f'http://127.0.0.1:{server.server_port}')
                    page.evaluate('''async()=>{
                      const {MeetingRecorder}=await import('/classroom_recorder.js');window.uploads=[];window.actions=[];window.messages=[];
                      const board=document.querySelector('#board'),b=board.getContext('2d');b.strokeStyle='red';b.lineWidth=30;b.strokeRect(400,225,800,450);
                      const camera=document.querySelector('#camera'),c=camera.getContext('2d');c.fillStyle='blue';c.fillRect(0,0,320,180);
                      const screen=document.querySelector('#screen'),s=screen.getContext('2d');s.fillStyle='lime';s.fillRect(0,0,800,600);
                      window.cam=camera.captureStream(15);window.share=screen.captureStream(15);const v=document.querySelector('#v'),sv=document.querySelector('#s');v.srcObject=cam;sv.srcObject=share;await Promise.all([v.play(),sv.play()]);
                      window.input=new AudioContext();const osc=input.createOscillator();osc.frequency.value=440;const dst=input.createMediaStreamDestination();osc.connect(dst);osc.start();window.mic=dst.stream.getAudioTracks()[0];
                      const silent=input.createMediaStreamDestination();window.disabled=silent.stream.getAudioTracks()[0];disabled.enabled=false;
                      window.fetch=async(url,opts)=>{uploads.push(new Uint8Array(await opts.body.arrayBuffer()));return {ok:true,json:async()=>({sequence:uploads.length})};};
                      const post=async(action,data)=>{actions.push({action,data});if(action==='recording-start')return {id:'a'.repeat(32),lease_ms:1500,allowed:['teacher','student']};if(action==='recording-heartbeat')return {lease_ms:1500,allowed:['teacher','student']};if(action==='recording-pause'||action==='recording-resume')return {phase:action.endsWith('pause')?'paused':'active',owner:true};return {};};
                      const api=async(path,data)=>{actions.push({action:path,data});return {csrf:'synthetic'};};
                      window.r=new MeetingRecorder({host:document.querySelector('#controls'),admin:true,post,api,notice:x=>messages.push(x),snapshot:()=>({board,screen:{id:'teacher',element:sv},cameras:[{id:'student',element:v,enabled:true}],audio:[{id:'student',track:mic,enabled:true},{id:'teacher',track:disabled,enabled:false}]})});
                      r.update({phase:'pending',owner:true,consent_count:2,participants:2});const start=Array.from(document.querySelectorAll('#controls button')).find(x=>x.textContent==='Start recording');start.click();start.click();while(!r.running)await new Promise(resolve=>setTimeout(resolve,10));if(actions.filter(x=>x.action==='recording-start').length!==1)throw new Error('Duplicate start request');
                    }''')
                    page.wait_for_timeout(1250)
                    state=page.evaluate("({sources:r.sources.size,tracks:r.stream.getTracks().map(x=>x.kind),pixel:Array.from(r.ctx.getImageData(256,216,1,1).data)})")
                    self.assertEqual(state['sources'],1);self.assertEqual(sorted(state['tracks']),['audio','video'])
                    # Screen is letterboxed inside the exact same 16:9 stage as annotations.
                    self.assertGreater(state['pixel'][0],180);self.assertLess(state['pixel'][1],100)
                    page.evaluate('r.pause()');page.wait_for_timeout(200);self.assertEqual(page.evaluate('r.recorder.state'),'paused')
                    page.evaluate('r.pause()');page.wait_for_timeout(1100);page.evaluate('r.stop(true)')
                    state=page.evaluate("({states:[cam.getVideoTracks()[0].readyState,mic.readyState],last:actions.filter(x=>x.action.endsWith('/finish')).at(-1),messages,chunks:uploads.length})")
                    self.assertEqual(state['states'],['live','live']);self.assertTrue(state['last']['data']['complete']);self.assertGreaterEqual(state['chunks'],2)
                    data=page.evaluate('Array.from(uploads.reduce((a,b)=>{const c=new Uint8Array(a.length+b.length);c.set(a);c.set(b,a.length);return c;},new Uint8Array()))')
                    output=temp/'synthetic.webm';output.write_bytes(bytes(data))
                    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=codec_type,width,height','-of','json',str(output)]))
                    self.assertEqual({x['codec_type'] for x in probe['streams']},{'audio','video'})
                    subprocess.run(['ffmpeg','-v','error','-i',str(output),'-f','null','-'],check=True,timeout=20)
                    # Permission lease and membership loss stop without affecting originals.
                    page.evaluate("r.state={phase:'pending',owner:true};r.finishing=null;r.stopped=null;r.id=null;r.sequence=0;uploads=[];r.post=async action=>action==='recording-start'?{id:'b'.repeat(32),lease_ms:1500,allowed:['teacher','student']}:Promise.reject(new Error('authorization ended'));r.start()")
                    page.wait_for_timeout(1900);self.assertFalse(page.evaluate('r.running'))
                    browser.close()
            finally:server.shutdown();server.server_close();thread.join(2)
