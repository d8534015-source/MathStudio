"""Optional real Chromium mux/decode test, synthetic media only; no devices/cloud."""
import functools
import http.server
import json
import os
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
            temp=Path(temp)
            for name in ('classroom_recorder.js','recording_limits.js'):(temp/name).write_bytes((root/name).read_bytes())
            (temp/'index.html').write_text('<!doctype html><html lang="en"><body><div id="controls"></div><canvas id="board" width="1600" height="900"></canvas><canvas id="camera" width="320" height="180"></canvas><canvas id="screen" width="800" height="600"></canvas><video id="v" autoplay muted></video><video id="s" autoplay muted></video></body></html>')
            class Quiet(http.server.SimpleHTTPRequestHandler):
                def log_message(self,*args):pass
            server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(temp)))
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                with sync_playwright() as p:
                    browser=p.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox','--autoplay-policy=no-user-gesture-required','--disable-features=WebRtcHideLocalIpsWithMdns'])
                    page=browser.new_page(viewport={'width':1400,'height':900});page.goto(f'http://127.0.0.1:{server.server_port}')
                    cdp=browser.new_browser_cdp_session();cpu_before=sum(p['cpuTime'] for p in cdp.send('SystemInfo.getProcessInfo')['processInfo'])
                    import time
                    measured_began=time.monotonic()
                    page.evaluate('''async()=>{
                      const {MeetingRecorder}=await import('/classroom_recorder.js');window.uploads=[];window.actions=[];window.messages=[];
                      const board=document.querySelector('#board'),b=board.getContext('2d');b.strokeStyle='red';b.lineWidth=30;b.strokeRect(400,225,800,450);
                      const camera=document.querySelector('#camera'),c=camera.getContext('2d');c.fillStyle='blue';c.fillRect(0,0,320,180);
                      const screen=document.querySelector('#screen'),s=screen.getContext('2d');s.fillStyle='lime';s.fillRect(0,0,800,600);
                      window.cam=camera.captureStream(30);window.share=screen.captureStream(30);const v=document.querySelector('#v'),sv=document.querySelector('#s');v.srcObject=cam;sv.srcObject=share;await Promise.all([v.play(),sv.play()]);
                      window.input=new AudioContext();const osc=input.createOscillator();osc.frequency.value=440;const dst=input.createMediaStreamDestination();osc.connect(dst);osc.start();window.mic=dst.stream.getAudioTracks()[0];
                      const silent=input.createMediaStreamDestination();window.disabled=silent.stream.getAudioTracks()[0];disabled.enabled=false;
                      window.fetch=async(url,opts)=>{uploads.push(new Uint8Array(await opts.body.arrayBuffer()));return {ok:true,json:async()=>({sequence:uploads.length})};};
                      const post=async(action,data)=>{actions.push({action,data});if(action==='recording-start')return {id:'a'.repeat(32),lease_ms:1500,allowed:['teacher','student','student2']};if(action==='recording-heartbeat')return {lease_ms:1500,allowed:['teacher','student','student2']};if(action==='recording-pause'||action==='recording-resume')return {phase:action.endsWith('pause')?'paused':'active',owner:true};return {};};
                      const api=async(path,data)=>{actions.push({action:path,data});return {csrf:'synthetic'};};
                      // Real local WebRTC transport: two separately received cameras/mics.
                      window.remote=[];window.connections=[];window.animations=[];
                      for(const [id,freq,color] of [['student',660,'yellow'],['student2',880,'purple']]){
                        const image=document.createElement('canvas');image.width=320;image.height=180;const cc=image.getContext('2d');cc.fillStyle=color;cc.fillRect(0,0,320,180);animations.push(setInterval(()=>{cc.fillStyle=color;cc.fillRect(0,0,1,1);},30));
                        const media=image.captureStream(30),o=input.createOscillator(),gain=input.createGain(),audio=input.createMediaStreamDestination();o.frequency.value=freq;gain.gain.value=.1;o.connect(gain);gain.connect(audio);o.start();media.addTrack(audio.stream.getAudioTracks()[0]);
                        if(!globalThis.MATH_TEST_LOOPBACK_WEBRTC){const video=document.createElement('video');video.muted=true;video.srcObject=media;document.body.append(video);await video.play();remote.push({id,video,track:media.getAudioTracks()[0]});continue;}
                        const send=new RTCPeerConnection({iceServers:[]}),recv=new RTCPeerConnection({iceServers:[]});connections.push(send,recv);
                        const video=document.createElement('video');video.muted=true;video.autoplay=true;document.body.append(video);let received;
                        const got=new Promise(resolve=>received=resolve);recv.ontrack=e=>{video.srcObject=e.streams[0];if(e.track.kind==='audio')received();};
                        media.getTracks().forEach(t=>send.addTrack(t,media));const gathered=pc=>pc.iceGatheringState==='complete'?Promise.resolve():new Promise(resolve=>{pc.addEventListener('icegatheringstatechange',()=>{if(pc.iceGatheringState==='complete')resolve();});setTimeout(resolve,4000);});await send.setLocalDescription(await send.createOffer());await gathered(send);await recv.setRemoteDescription(send.localDescription);await recv.setLocalDescription(await recv.createAnswer());await gathered(recv);await send.setRemoteDescription(recv.localDescription);await got;await Promise.race([video.play(),new Promise((_,reject)=>setTimeout(()=>reject(new Error('Synthetic RTC video unavailable: '+send.iceConnectionState+'/'+recv.iceConnectionState+'/'+video.readyState)),10000))]);remote.push({id,video,track:video.srcObject.getAudioTracks()[0]});
                      }
                      window.screenOn=true;
                      window.r=new MeetingRecorder({host:document.querySelector('#controls'),admin:true,post,api,notice:x=>messages.push(x),snapshot:()=>({board,screen:screenOn?{id:'teacher',element:sv}:null,cameras:[{id:'teacher',element:v,enabled:true},...remote.map(x=>({id:x.id,element:x.video,enabled:true}))],audio:[{id:'teacher',track:mic,enabled:true},{id:'teacher',track:disabled,enabled:false},...remote.map(x=>({id:x.id,track:x.track,enabled:true}))]})});
                      r.update({phase:'pending',owner:true,consent_count:2,participants:2});const start=Array.from(document.querySelectorAll('#controls button')).find(x=>x.textContent==='Start recording');start.click();start.click();while(!r.running)await new Promise(resolve=>setTimeout(resolve,10));if(actions.filter(x=>x.action==='recording-start').length!==1)throw new Error('Duplicate start request');
                    }''')
                    page.wait_for_timeout(1250)
                    state=page.evaluate("({sources:r.sources.size,tracks:r.stream.getTracks().map(x=>x.kind),pixel:Array.from(r.ctx.getImageData(256,216,1,1).data)})")
                    self.assertEqual(state['sources'],3);self.assertEqual(sorted(state['tracks']),['audio','video'])
                    # Screen is letterboxed inside the exact same 16:9 stage as annotations.
                    self.assertGreater(state['pixel'][0],180);self.assertLess(state['pixel'][1],100)
                    page.evaluate("screenOn=false;document.querySelector('#board').getContext('2d').fillRect(600,300,20,20)");page.wait_for_timeout(150);page.evaluate('screenOn=true')
                    page.evaluate('r.pause()');page.wait_for_timeout(200);self.assertEqual(page.evaluate('r.recorder.state'),'paused')
                    page.evaluate('r.pause()');page.wait_for_timeout(1100);page.evaluate('r.stop(true)')
                    state=page.evaluate("({states:[cam.getVideoTracks()[0].readyState,mic.readyState],last:actions.filter(x=>x.action.endsWith('/finish')).at(-1),messages,chunks:uploads.length})")
                    self.assertEqual(state['states'],['live','live']);self.assertTrue(state['last']['data']['complete']);self.assertGreaterEqual(state['chunks'],2)
                    data=page.evaluate('Array.from(uploads.reduce((a,b)=>{const c=new Uint8Array(a.length+b.length);c.set(a);c.set(b,a.length);return c;},new Uint8Array()))')
                    output=temp/'synthetic.webm';output.write_bytes(bytes(data))
                    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=codec_type,width,height','-of','json',str(output)]))
                    self.assertEqual({x['codec_type'] for x in probe['streams']},{'audio','video'})
                    subprocess.run(['ffmpeg','-v','error','-i',str(output),'-f','null','-'],check=True,timeout=20)
                    metrics=page.evaluate('r.metrics');cpu_after=sum(p['cpuTime'] for p in cdp.send('SystemInfo.getProcessInfo')['processInfo']);metrics['browserCpuPercentOneCoreApprox']=round(100*(cpu_after-cpu_before)/(time.monotonic()-measured_began),1);metrics['outputBytes']=output.stat().st_size;print('Synthetic recording metrics:',json.dumps(metrics))
                    self.assertGreater(metrics['effectiveCaptureFps'],20);self.assertEqual(metrics['requested'],'1280×720/30FPS')
                    page.evaluate('connections.forEach(p=>p.close());animations.forEach(clearInterval)')
                    from recording_media import remux
                    indexed=temp/'indexed.webm';remux(Path(shutil.which('ffmpeg')),output,indexed,'video/webm')
                    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=nb_read_frames,avg_frame_rate:format=duration','-of','json',str(indexed)]))
                    self.assertGreater(float(info['format']['duration']),1)
                    subprocess.run(['ffmpeg','-v','error','-ss','1','-i',str(indexed),'-frames:v','1','-f','null','-'],check=True,timeout=20)
                    metrics['indexedBytes']=indexed.stat().st_size;metrics['encodedFrames']=int(info['streams'][0]['nb_read_frames']);metrics['indexedDuration']=float(info['format']['duration'])
                    print('Seekable playback verification:',json.dumps({'frames':metrics['encodedFrames'],'seconds':metrics['indexedDuration'],'bytes':metrics['indexedBytes']}))
                    if os.environ.get('MATH_RECORDING_TEST_OUTPUT'):
                        Path(os.environ['MATH_RECORDING_TEST_OUTPUT']).write_bytes(indexed.read_bytes())
                    # Local Save As API contract (mocked file picker/writer, real encoder).
                    page.evaluate('''async()=>{window.saved=[];window.localClosed=false;window.showSaveFilePicker=async()=>({createWritable:async()=>({write:async blob=>saved.push(new Uint8Array(await blob.arrayBuffer())),close:async()=>{localClosed=true;},abort:async()=>{}})});r.state={phase:'pending',owner:true,mode:'local'};r.finishing=null;await r.start();}''')
                    page.wait_for_timeout(1200);cloud_count=page.evaluate('uploads.length')
                    page.evaluate("r.started=performance.now()-10800000;r.encodedBytes=4000000000;r.checkLimits()")
                    page.wait_for_function('()=>r.finishing===null&&!r.running')
                    self.assertTrue(page.evaluate('localClosed'));self.assertEqual(page.evaluate('uploads.length'),cloud_count)
                    self.assertEqual(page.evaluate('r.reason'),'time');self.assertTrue(page.evaluate("r.warnings.has('timeWarning')&&r.warnings.has('sizeWarning')"))
                    self.assertGreater(page.evaluate('saved.reduce((n,x)=>n+x.length,0)'),0)
                    # Size-limit finalization reserves the final chunk; no 5GB allocation.
                    page.evaluate("r.state={phase:'pending',owner:true,mode:'cloud'};r.finishing=null;uploads=[];r.start()")
                    page.wait_for_function('()=>r.running');page.wait_for_timeout(200)
                    page.evaluate('r.encodedBytes=5000000000-8*1024*1024;r.checkLimits()')
                    page.wait_for_function('()=>r.finishing===null&&!r.running')
                    self.assertEqual(page.evaluate('r.reason'),'size');self.assertTrue(page.evaluate("actions.filter(x=>x.action.endsWith('/finish')).at(-1).data.complete"))
                    self.assertLessEqual(page.evaluate('r.encodedBytes'),5000000000)
                    # Permission lease and membership loss stop without affecting originals.
                    page.evaluate("r.state={phase:'pending',owner:true,mode:'cloud'};r.finishing=null;r.stopped=null;r.id=null;r.sequence=0;uploads=[];r.post=async action=>action==='recording-start'?{id:'b'.repeat(32),lease_ms:1500,allowed:['teacher','student','student2']}:Promise.reject(new Error('authorization ended'));r.start()")
                    page.wait_for_timeout(1900);self.assertFalse(page.evaluate('r.running'))
                    browser.close()
            finally:server.shutdown();server.server_close();thread.join(2)
