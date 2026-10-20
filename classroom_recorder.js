import {LIMITS,recordingLimits} from './recording_limits.js';
// Records only media already received by this browser. Never alters a peer connection.
export const TEXT={
  days:['days','天'],teacherOnly:['Teacher only','仅教师'],noDownload:['No recipient download','接收者不可下载'],diagnostics:['Effective settings / diagnostics','实际设置／诊断'],
  cloud:['Cloud Recording','云端录制'],local:['Local Recording (Save As)','本地录制（另存为）'],future:['Allow a later explicit upload to private R2','允许以后明确上传至私有 R2'],sharing:['Authorize sharing with verified enrolled absentees','授权与已核实缺席的本课学生分享'],download:['Allow those recipients to download','允许这些接收者下载'],timeWarning:['30 minutes remain before the 3-hour limit.','距离 3 小时限制还剩 30 分钟。'],sizeWarning:['1 GB remains before the 5 GB limit (decimal GB).','距离 5 GB 限制还剩 1 GB（十进制）。'],time:['Stopped at the 3-hour limit.','已达到 3 小时时限，录制已停止。'],size:['Stopped to finalize within the 5 GB limit.','为确保文件不超过 5 GB，已停止并完成录制。'],localSaved:['Local file finalized. No automatic cloud upload occurred.','本地文件已完成，未自动上传至云端。'],localUnsupported:['Local Save As requires a browser supporting the File System Access API (current desktop Chrome/Edge).','本地另存为需要支持文件系统访问 API 的浏览器（新版桌面 Chrome／Edge）。'],quality:['Target 1280×720 / 30 FPS. Actual settings and measured capture FPS appear below.','目标 1280×720／30 FPS，实际设置与测得的捕获帧率显示在下方。'],slow:['Measured capture is below 27 FPS; target quality is not being sustained.','测得捕获帧率低于 27 FPS，未能维持目标质量。'],
  record:['Record','录制'],request:['Request recording (I consent)','请求录制（我同意）'],start:['Start recording','开始录制'],
  pause:['Pause','暂停'],resume:['Resume','继续'],stop:['Stop recording','停止录制'],agree:['I consent','我同意'],decline:['Decline / withdraw','拒绝／撤回同意'],
  off:['Recording is off.','未在录制。'],pending:['Recording requested; waiting for every participant’s consent.','已请求录制，正在等待所有参与者同意。'],
  active:['● Recording — enabled microphones, received cameras, shared screen and annotations.','● 正在录制：已启用麦克风、收到的摄像头画面、共享屏幕与批注。'],
  paused:['Recording paused.','录制已暂停。'],stopping:['Recording stopping…','正在停止录制…'],stopped:['Recording stopped.','录制已停止。'],
  saved:['Recording queued for private cloud upload. Check Recordings for status.','录制已进入私有云上传队列，请在“录制”中查看状态。'],
  failed:['Recording interrupted. Received chunks are retained; check Recordings.','录制中断，已收到的片段将被保留，请查看“录制”。'],
  unavailable:['Recording needs a visible browser with MediaRecorder and AudioContext support.','录制需要可见且支持 MediaRecorder 和 AudioContext 的浏览器。'],
  backlog:['Recording upload cannot keep up. Recording has stopped safely.','录制上传速度不足，录制已安全停止。'],
  confirm:['Before starting, read the notice and obtain every participant’s consent.','开始前，请阅读通知并取得所有参与者同意。']
};
export function recordingText(key){return TEXT[key]?.[document.documentElement.lang.startsWith('zh')?1:0]||key;}
export class MeetingRecorder{
  constructor({host,admin,post,api,snapshot,notice}){
    Object.assign(this,{host,admin,post,api,snapshot,notice});this.state={phase:'off'};this.pending=[];this.sequence=0;this.deadline=0;this.running=false;this.finishing=null;this.choice={mode:'cloud',sharing:false,download:false,future_upload:false};this.warnings=new Set();
    this.visibility=()=>{if(document.hidden&&this.running)this.stop(false);};document.addEventListener('visibilitychange',this.visibility);
    this.language=()=>this.render();window.addEventListener('mathstudio-language',this.language);this.render();
  }
  button(label,action){const b=document.createElement('button');b.textContent=recordingText(label);b.className='small secondary';b.onclick=async()=>{b.disabled=true;try{await action();}catch(e){this.notice(e.message);}finally{b.disabled=false;}};this.host.append(b);return b;}
  render(){
    this.host.replaceChildren();const p=document.createElement('p');p.setAttribute('role','status');p.textContent=recordingText(this.state.phase);this.host.append(p);
    if(this.state.notice){const n=document.createElement('p');n.dataset.noTranslate='';n.textContent=this.state.notice;this.host.append(n);}
    if(['off','stopped'].includes(this.state.phase)&&this.admin){
      const select=document.createElement('select');for(const mode of ['cloud','local']){const o=document.createElement('option');o.value=mode;o.textContent=recordingText(mode);select.append(o);}select.value=this.choice.mode;select.onchange=()=>this.choice.mode=select.value;this.host.append(select);
      for(const key of ['future_upload','sharing','download']){const label=document.createElement('label'),input=document.createElement('input');input.type='checkbox';input.checked=this.choice[key];input.onchange=()=>this.choice[key]=input.checked;label.append(input,document.createTextNode(recordingText(key==='future_upload'?'future':key)));this.host.append(label);}
      this.button('request',()=>this.request());
    }
    if(this.state.scope){const p=document.createElement('p');p.textContent=(this.state.mode==='local'?recordingText('local'):recordingText('cloud'))+' · '+this.state.scope.retention_days+' '+recordingText('days')+' · '+(this.state.scope.sharing?recordingText('sharing'):recordingText('teacherOnly'))+' · '+(this.state.scope.download?recordingText('download'):recordingText('noDownload'));this.host.append(p);}
    for(const key of this.warnings){const p=document.createElement('p');p.setAttribute('role','status');p.textContent=recordingText(key);this.host.append(p);}
    if(this.metrics){const p=document.createElement('p');p.textContent=recordingText('quality')+' '+this.metrics.effectiveCaptureFps+' / 30 FPS · '+(this.recorder?.mimeType||'')+' · '+(this.metrics.videoBitrate/1e6).toFixed(1)+' Mbps';const details=document.createElement('details'),summary=document.createElement('summary'),pre=document.createElement('pre');summary.textContent=recordingText('diagnostics');pre.textContent=JSON.stringify(this.metrics,null,2);details.append(summary,pre);this.host.append(p,details);}
    if(this.state.phase==='pending'){
      if(!this.state.consented)this.button('agree',()=>this.consent(true));
      this.button('decline',()=>this.consent(false));
      if(this.state.owner&&this.state.consent_count===this.state.participants)this.button('start',()=>this.start());
    }
    if(['active','paused'].includes(this.state.phase)){
      if(this.state.owner){this.button(this.state.phase==='paused'?'resume':'pause',()=>this.pause());this.button('stop',()=>this.stop(true));}
      else this.button('decline',()=>this.post('recording-withdraw',{id:this.state.id}));
    }
  }
  update(state){
    const changed=JSON.stringify(state)!==JSON.stringify(this.state);this.state=state||{phase:'off'};
    if(this.running&&!['active','paused'].includes(this.state.phase))this.stop(false);
    if(changed)this.render();
  }
  focus(){this.host.scrollIntoView({block:'center'});this.notice(recordingText('confirm'));}
  async request(){this.update(await this.post('recording-request',{consent:true,...this.choice}));}
  async consent(accepted){this.update(await this.post('recording-consent',{id:this.state.id,accepted}));}
  async pause(){
    if(!this.running||!this.state.owner)return;
    const pause=this.recorder.state==='recording';
    if(pause){this.pausedAt=performance.now();this.recorder.pause();this.mute();}
    try{this.update(await this.post(pause?'recording-pause':'recording-resume'));if(!pause){await this.renew();this.pausedMs+=performance.now()-this.pausedAt;this.pausedAt=0;this.recorder.resume();}}
    catch(e){await this.stop(false);throw e;}
  }
  async start(){
    if(this.running||this.finishing||this.starting)return;
    if(document.hidden||!globalThis.MediaRecorder||!globalThis.AudioContext||!HTMLCanvasElement.prototype.captureStream)throw new Error(recordingText('unavailable'));
    const mime=['video/webm;codecs=vp8,opus','video/webm','video/mp4'].find(t=>MediaRecorder.isTypeSupported(t));
    if(!mime)throw new Error(recordingText('unavailable'));
    this.starting=true;
    try{
    this.mode=this.state.mode||'cloud';this.id=null;this.writer=null;
    if(this.mode==='local'){
      if(!globalThis.showSaveFilePicker)throw new Error(recordingText('localUnsupported'));
      const ext=mime.startsWith('video/mp4')?'mp4':'webm';
      this.handle=await showSaveFilePicker({suggestedName:'MathStudio-lesson.'+ext,types:[{description:'Meeting video',accept:{[mime.split(';')[0]]:['.'+ext]}}]});this.writer=await this.handle.createWritable();
    }
    this.canvas=document.createElement('canvas');this.canvas.width=1280;this.canvas.height=720;this.ctx=this.canvas.getContext('2d');
    this.audio=new AudioContext();await this.audio.resume();this.destination=this.audio.createMediaStreamDestination();this.sources=new Map();
    this.stream=this.canvas.captureStream(0);this.stream.addTrack(this.destination.stream.getAudioTracks()[0]);
    this.recorder=new MediaRecorder(this.stream,{mimeType:mime,videoBitsPerSecond:LIMITS.videoBitrate,audioBitsPerSecond:LIMITS.audioBitrate});
      const began=performance.now();const grant=await this.post('recording-start',{mime:mime.split(';')[0]});
      this.id=grant.id;this.allowed=new Set(grant.allowed);this.deadline=began+grant.lease_ms;
      this.finished=false;this.pending=[];this.sequence=0;this.duration=0;this.started=performance.now();this.pausedMs=0;this.pausedAt=0;this.last=0;this.fault=false;this.encodedBytes=0;this.frames=0;this.drawMs=0;this.warnings.clear();this.reason='';this.metrics={requested:'1280×720/30FPS',track:((s)=>({width:s.width,height:s.height,frameRate:s.frameRate,aspectRatio:s.aspectRatio}))(this.stream.getVideoTracks()[0].getSettings()),codec:mime,videoBitrate:this.recorder.videoBitsPerSecond,audioBitrate:this.recorder.audioBitsPerSecond};
      this.recorder.ondataavailable=e=>{
        if(!e.data.size)return;
        if(this.encodedBytes+e.data.size>LIMITS.maxBytes){this.fault=true;this.reason='size';this.stop(false);return;}
        this.encodedBytes+=e.data.size;this.checkLimits();
        const size=this.pending.reduce((n,x)=>n+x.size,0)+e.data.size;
        if(e.data.size>8*1024*1024||this.pending.length>=8||size>32*1024*1024){this.fault=true;this.notice(recordingText('backlog'));this.stop(false);return;}
        this.pending.push(e.data);this.pump();
      };
      this.recorder.onerror=()=>this.stop(false);
      this.stopped=new Promise(resolve=>{this.recorder.onstop=resolve;});
      this.recorder.start(1000);this.running=true;this.draw();this.limitTimer=setInterval(()=>this.checkLimits(),1000);this.renewTimer=setInterval(()=>this.renew().catch(()=>this.stop(false)),500);
      this.update({...this.state,phase:'active'});
    }catch(e){
      if(this.running)await this.stop(false);
      else{this.dispose();if(this.id){await this.post('recording-stop',{ack:true}).catch(()=>{});await this.api('/api/admin/recordings/finish',{id:this.id,complete:false,duration:0}).catch(()=>{});}}
      throw e;
    }finally{this.starting=false;}
  }
  mute(){if(!this.audio)return;for(const s of this.sources.values()){s.gain.gain.cancelScheduledValues(this.audio.currentTime);s.gain.gain.setValueAtTime(0,this.audio.currentTime);}}
  async renew(){
    if(!this.running||this.renewing)return;this.renewing=true;const began=performance.now();
    try{const grant=await this.post('recording-heartbeat',{id:this.id});if(!this.running)return;this.allowed=new Set(grant.allowed);this.deadline=began+grant.lease_ms;}
    finally{this.renewing=false;}
  }
  audioMix(items){
    const live=new Set();const remaining=Math.max(0,(this.deadline-performance.now())/1000);
    for(const item of items){
      const track=item.track;if(!item.enabled||!this.allowed.has(item.id)||!track||!track.enabled||track.readyState!=='live')continue;
      live.add(track.id);let s=this.sources.get(track.id);
      if(!s){s={input:this.audio.createMediaStreamSource(new MediaStream([track])),gain:this.audio.createGain()};s.input.connect(s.gain);s.gain.connect(this.destination);this.sources.set(track.id,s);}
      const now=this.audio.currentTime;s.gain.gain.cancelScheduledValues(now);s.gain.gain.setValueAtTime(1,now);s.gain.gain.setValueAtTime(0,now+remaining);
    }
    for(const [id,s] of this.sources){if(!live.has(id)){s.input.disconnect();s.gain.disconnect();this.sources.delete(id);}}
  }
  contain(element,x,y,w,h){
    const ew=element.videoWidth||element.naturalWidth||element.width,eh=element.videoHeight||element.naturalHeight||element.height;
    if(!ew||!eh)return;const scale=Math.min(w/ew,h/eh);this.ctx.drawImage(element,x+(w-ew*scale)/2,y+(h-eh*scale)/2,ew*scale,eh*scale);
  }
  draw(){
    if(!this.running)return;
    if(performance.now()>=this.deadline||document.hidden){this.stop(false);return;}
    this.frame=requestAnimationFrame(()=>this.draw());if(performance.now()-this.last<1000/LIMITS.fps-1)return;this.last=performance.now();const drawBegan=performance.now();
    if(this.recorder.state==='paused'){this.mute();return;}
    const data=this.snapshot();this.audioMix(data.audio);const c=this.ctx;c.fillStyle='#fff';c.fillRect(0,0,1280,720);
    if(data.screen&&this.allowed.has(data.screen.id))this.contain(data.screen.element,0,72,1024,576);
    this.contain(data.board,0,72,1024,576);
    const cameras=data.cameras.filter(x=>x.enabled&&this.allowed.has(x.id)&&x.element.readyState>=2&&x.element.srcObject?.getVideoTracks().some(t=>t.readyState==='live'&&!t.muted));
    cameras.forEach((x,i)=>this.contain(x.element,1024,i*720/6,256,720/6));
    this.stream.getVideoTracks()[0].requestFrame();this.frames++;this.drawMs+=performance.now()-drawBegan;
  }
  async pump(){
    if(this.uploading)return this.uploading;
    this.uploading=(async()=>{
      while(this.pending.length){
        const blob=this.pending[0];let error;
        if(this.mode==='local'){try{await this.writer.write(blob);const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',await blob.arrayBuffer()))).map(x=>x.toString(16).padStart(2,'0')).join('');await this.api('/api/admin/recordings/local-checkpoint',{id:this.id,sequence:this.sequence,size:blob.size,digest});this.pending.shift();this.sequence++;continue;}catch(e){this.fault=true;this.pending=[];this.notice(recordingText('failed')+' '+e.name);queueMicrotask(()=>this.stop(false));break;}}
        for(let attempt=0;attempt<3;attempt++){
          try{
            const me=await this.api('/api/me');
            const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),15000);
            try{
              const r=await fetch(`/api/admin/recordings/chunk?id=${this.id}&sequence=${this.sequence}`,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/octet-stream','X-CSRF-Token':me.csrf},body:blob,signal:controller.signal});
              if(!r.ok)throw new Error('Recording chunk was not acknowledged.');
              const ack=await r.json();if(ack.sequence!==this.sequence+1)throw new Error('Invalid chunk acknowledgment.');
            }finally{clearTimeout(timeout);}
            error=null;break;
          }catch(e){error=e;}
        }
        if(error){this.fault=true;this.pending=[];this.notice(recordingText('failed'));queueMicrotask(()=>this.stop(false));break;}
        this.pending.shift();this.sequence++;
      }
    })();
    try{await this.uploading;}finally{this.uploading=null;}
  }
  async stop(complete){
    if(this.finishing)return this.finishing;if(!this.running)return;
    this.running=false;clearInterval(this.renewTimer);cancelAnimationFrame(this.frame);this.mute();
    clearInterval(this.limitTimer);this.duration=Math.min(LIMITS.maxSeconds,(performance.now()-this.started-this.pausedMs-(this.pausedAt?performance.now()-this.pausedAt:0))/1000);
    if(this.recorder.state!=='inactive')this.recorder.stop();
    this.finishing=(async()=>{
      try{
        await this.stopped;
        // Stop acknowledgment precedes upload drain; no more participant media is captured.
        await this.post('recording-stop',{ack:true}).catch(()=>{});
        while(this.uploading||this.pending.length)await (this.uploading||this.pump());
        if(this.writer){await this.writer.close();this.writer=null;}
        await this.api('/api/admin/recordings/finish',{id:this.id,complete:complete===true&&!this.fault,duration:this.duration,metrics:this.metrics,stop_reason:this.reason});
        this.notice(recordingText(this.fault||!complete?'failed':this.mode==='local'?'localSaved':'saved')+(this.reason?' '+recordingText(this.reason):''));
      }catch{this.notice(recordingText('failed'));}
      finally{this.dispose();this.update({...this.state,phase:'stopped'});this.finishing=null;}
    })();return this.finishing;
  }
  checkLimits(){
    const wall=(performance.now()-this.started)/1000,limits=recordingLimits(wall,this.encodedBytes);
    let changed=false;for(const [key,on] of [['timeWarning',limits.timeWarning],['sizeWarning',limits.sizeWarning]]){if(on&&!this.warnings.has(key)){this.warnings.add(key);changed=true;}}
    const active=Math.max(1,wall-this.pausedMs/1000-(this.pausedAt?(performance.now()-this.pausedAt)/1000:0));
    if(this.metrics){this.metrics.effectiveCaptureFps=Number((this.frames/active).toFixed(1));this.metrics.canvasCpuMs=Number(this.drawMs.toFixed(1));this.metrics.missedCaptureFramesEstimate=Math.max(0,Math.floor(active*LIMITS.fps)-this.frames);this.metrics.receivedCameraPlaybackDrops=this.snapshot().cameras.reduce((n,x)=>n+(x.element.getVideoPlaybackQuality?.().droppedVideoFrames||0),0);this.metrics.encodedGB=Number((this.encodedBytes/1e9).toFixed(3));this.metrics.heapBytes=performance.memory?.usedJSHeapSize??'unavailable';if(active>10&&this.metrics.effectiveCaptureFps<27){this.warnings.add('slow');changed=true;}}
    if(changed||this.running)this.render();
    if(this.running&&limits.stop){this.reason=limits.stop;this.stop(true);}
  }
  dispose(){clearInterval(this.limitTimer);if(this.writer){this.writer.abort().catch(()=>{});this.writer=null;}clearInterval(this.renewTimer);cancelAnimationFrame(this.frame);this.mute();this.stream?.getTracks().forEach(t=>t.stop());this.audio?.close().catch(()=>{});this.sources?.clear();}
}
