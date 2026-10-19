// Records only media already received by this browser. Never alters a peer connection.
export const TEXT={
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
    Object.assign(this,{host,admin,post,api,snapshot,notice});this.state={phase:'off'};this.pending=[];this.sequence=0;this.deadline=0;this.running=false;this.finishing=null;
    this.visibility=()=>{if(document.hidden&&this.running)this.stop(false);};document.addEventListener('visibilitychange',this.visibility);
    this.language=()=>this.render();window.addEventListener('mathstudio-language',this.language);this.render();
  }
  button(label,action){const b=document.createElement('button');b.textContent=recordingText(label);b.className='small secondary';b.onclick=()=>Promise.resolve(action()).catch(e=>this.notice(e.message));this.host.append(b);return b;}
  render(){
    this.host.replaceChildren();const p=document.createElement('p');p.setAttribute('role','status');p.textContent=recordingText(this.state.phase);this.host.append(p);
    if(this.state.notice){const n=document.createElement('p');n.dataset.noTranslate='';n.textContent=this.state.notice;this.host.append(n);}
    if(['off','stopped'].includes(this.state.phase)&&this.admin)this.button('request',()=>this.request());
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
  async request(){this.update(await this.post('recording-request',{consent:true}));}
  async consent(accepted){this.update(await this.post('recording-consent',{id:this.state.id,accepted}));}
  async pause(){
    if(!this.running||!this.state.owner)return;
    const pause=this.recorder.state==='recording';
    if(pause){this.pausedAt=performance.now();this.recorder.pause();this.mute();}
    try{this.update(await this.post(pause?'recording-pause':'recording-resume'));if(!pause){await this.renew();this.pausedMs+=performance.now()-this.pausedAt;this.pausedAt=0;this.recorder.resume();}}
    catch(e){await this.stop(false);throw e;}
  }
  async start(){
    if(this.running||this.finishing)return;
    if(document.hidden||!globalThis.MediaRecorder||!globalThis.AudioContext||!HTMLCanvasElement.prototype.captureStream)throw new Error(recordingText('unavailable'));
    const mime=['video/webm;codecs=vp8,opus','video/webm','video/mp4'].find(t=>MediaRecorder.isTypeSupported(t));
    if(!mime)throw new Error(recordingText('unavailable'));
    try{
    this.canvas=document.createElement('canvas');this.canvas.width=1280;this.canvas.height=720;this.ctx=this.canvas.getContext('2d');
    this.audio=new AudioContext();await this.audio.resume();this.destination=this.audio.createMediaStreamDestination();this.sources=new Map();
    this.stream=this.canvas.captureStream(0);this.stream.addTrack(this.destination.stream.getAudioTracks()[0]);
    this.recorder=new MediaRecorder(this.stream,{mimeType:mime,videoBitsPerSecond:1800000,audioBitsPerSecond:96000});
      const began=performance.now();const grant=await this.post('recording-start',{mime:mime.split(';')[0]});
      this.id=grant.id;this.allowed=new Set(grant.allowed);this.deadline=began+grant.lease_ms;
      this.finished=false;this.pending=[];this.sequence=0;this.duration=0;this.started=performance.now();this.pausedMs=0;this.pausedAt=0;this.last=0;this.fault=false;
      this.recorder.ondataavailable=e=>{
        if(!e.data.size)return;
        const size=this.pending.reduce((n,x)=>n+x.size,0)+e.data.size;
        if(e.data.size>8*1024*1024||this.pending.length>=8||size>32*1024*1024){this.fault=true;this.notice(recordingText('backlog'));this.stop(false);return;}
        this.pending.push(e.data);this.pump();
      };
      this.recorder.onerror=()=>this.stop(false);
      this.stopped=new Promise(resolve=>{this.recorder.onstop=resolve;});
      this.recorder.start(1000);this.running=true;this.draw();this.renewTimer=setInterval(()=>this.renew().catch(()=>this.stop(false)),500);
      this.update({...this.state,phase:'active'});
    }catch(e){
      if(this.running)await this.stop(false);
      else{this.dispose();if(this.id){await this.post('recording-stop',{ack:true}).catch(()=>{});await this.api('/api/admin/recordings/finish',{id:this.id,complete:false,duration:0}).catch(()=>{});}}
      throw e;
    }
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
    this.frame=requestAnimationFrame(()=>this.draw());if(performance.now()-this.last<66)return;this.last=performance.now();
    if(this.recorder.state==='paused'){this.mute();return;}
    const data=this.snapshot();this.audioMix(data.audio);const c=this.ctx;c.fillStyle='#fff';c.fillRect(0,0,1280,720);
    if(data.screen&&this.allowed.has(data.screen.id))this.contain(data.screen.element,0,72,1024,576);
    this.contain(data.board,0,72,1024,576);
    const cameras=data.cameras.filter(x=>x.enabled&&this.allowed.has(x.id)&&x.element.readyState>=2&&x.element.srcObject?.getVideoTracks().some(t=>t.readyState==='live'&&!t.muted));
    cameras.forEach((x,i)=>this.contain(x.element,1024,i*720/6,256,720/6));
    this.stream.getVideoTracks()[0].requestFrame();
  }
  async pump(){
    if(this.uploading)return this.uploading;
    this.uploading=(async()=>{
      while(this.pending.length){
        const blob=this.pending[0];let error;
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
    this.duration=Math.min(7200,(performance.now()-this.started-this.pausedMs-(this.pausedAt?performance.now()-this.pausedAt:0))/1000);
    if(this.recorder.state!=='inactive')this.recorder.stop();
    this.finishing=(async()=>{
      try{
        await this.stopped;
        // Stop acknowledgment precedes upload drain; no more participant media is captured.
        await this.post('recording-stop',{ack:true}).catch(()=>{});
        while(this.uploading||this.pending.length)await (this.uploading||this.pump());
        await this.api('/api/admin/recordings/finish',{id:this.id,complete:complete===true&&!this.fault,duration:this.duration});
        this.notice(recordingText(this.fault||!complete?'failed':'saved'));
      }catch{this.notice(recordingText('failed'));}
      finally{this.dispose();this.update({...this.state,phase:'stopped'});this.finishing=null;}
    })();return this.finishing;
  }
  dispose(){clearInterval(this.renewTimer);cancelAnimationFrame(this.frame);this.mute();this.stream?.getTracks().forEach(t=>t.stop());this.audio?.close().catch(()=>{});this.sources?.clear();}
}
