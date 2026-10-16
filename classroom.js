// Math Studio classroom v22: peer-to-peer WebRTC camera/microphone/screen sharing
// plus an optional shared annotation/whiteboard layer.
export async function mountClassroom({api,toast,me,settings,classes,esc,tr=s=>s,localize=()=>{}}) {
  const $=s=>document.querySelector(s);
  const cid=Number(new URLSearchParams(location.search).get('id'));
  const cl=classes.find(c=>c.id===cid);
  const admin=me.role==='admin';
  const instant=cl?.class_kind==='instant';
  const groupChatId=cl?.class_kind==='group'?cl.group_chat_id:null;
  if(!cl) throw new Error('Class not found.');

  $('#app').classList.add('roommain');
  $('#footer').classList.add('hidden');
  $('#app').innerHTML=`
    <div class="roomhead">
      <div><p class="eyebrow">Live classroom</p><h1><span data-no-translate>${esc(cl.title)}</span></h1></div>
      <a href="${instant?'/join':admin?'/teacher':'/account'}">Back to ${instant?'join meeting':admin?'teaching calendar':'my lessons'}</a>
    </div>
    <section id="prejoin" class="panel prejoin-card">
      <div>
        <h2>Ready to join?</h2>
        <p>Your camera and microphone start off. You can turn them on after joining.</p>
        <div id="mediaPreflight" class="media-preflight" role="status"></div>
        <div class="actions"><button id="checkMedia" type="button" class="secondary small">Check camera & microphone</button></div>
        <p class="meta">For another device, use the <strong>HTTPS</strong> address printed by <code>START STUDENT WEBSITE.bat</code>. A local address such as <code>http://10.x.x.x:5051</code> is not a secure browser origin.</p>
      </div>
      <button id="join">Join classroom</button>
      <p class="meta" id="joinerror" role="status"></p>
    </section>
    <section id="room" class="hidden live-room">
      <div id="roomnotice" class="notice" role="status"></div><div id="mediaLinkStatus" class="media-link-status" role="status">Media link: waiting for another participant.</div>
      <div class="roomcontrols" aria-label="Call controls">
        <button id="mic" class="secondary" aria-pressed="false">Unmute</button>
        <button id="camera" class="secondary" aria-pressed="false">Start camera</button>
        <button id="share" class="secondary" aria-pressed="false">Share screen</button>
        <button id="whiteboard" class="secondary" aria-pressed="false">Whiteboard</button>
        <button id="sound" class="secondary">Enable sound</button>
        <button id="leave" class="danger">Leave</button>
        ${admin?'<button id="end" class="secondary">End class for everyone</button>':''}
      </div>
      <div class="meeting-layout">
        <div class="meeting-main">
          <section id="shareStage" class="share-stage hidden" aria-label="Shared screen or whiteboard">
            <div class="shared-media" id="sharedMedia">
              <video id="presentation" class="hidden" autoplay playsinline muted></video>
              <img id="nativePresentation" class="hidden native-presentation" alt="Teacher shared screen">
              <canvas id="board" width="1600" height="900" aria-label="Live annotation overlay"></canvas>
              <div class="share-stage-label"><span id="stageTitle" class="stage-title">Whiteboard</span><span>Annotations are a separate live overlay</span></div>
              <div class="annotation-toolbar meeting-taskbar" aria-label="Annotation tools">
                ${[['pen','Pen'],['line','Line'],['circle','Circle'],['rect','Rectangle'],['text','Text'],['erase','Eraser']].map(([t,n])=>`<button data-tool="${t}" class="small secondary ${t==='pen'?'active':''}" aria-pressed="${t==='pen'}">${n}</button>`).join('')}
                <input type="color" id="color" value="#09695f" aria-label="Ink colour">
                <select id="width" aria-label="Line thickness"><option value="2">Thin</option><option value="4" selected>Medium</option><option value="7">Thick</option></select>
                <button id="grid" class="small secondary">Grid on</button>
                <button id="undo" class="small secondary">Undo</button>
                <button id="clear" class="small secondary">Clear</button>
                <button id="save" class="small secondary">Snapshot</button>
              </div>
            </div>
            <div class="equationbar" id="equationbar">
              <div><label for="function">Graph</label><select id="function"><option value="quadratic">y = a(x − h)² + k</option><option value="linear">y = a(x − h) + k</option><option value="sine">y = a sin(x − h) + k</option><option value="absolute">y = a|x − h| + k</option></select></div>
              ${['a','h','k'].map(k=>`<div><label for="coef-${k}">${k}</label><input type="number" id="coef-${k}" min="-10" max="10" step="0.1" value="${k==='a'?1:0}"></div>`).join('')}
              <button id="plot" class="small">Add graph</button>
            </div>
            <div class="boardstatus"><span id="boardstatus">Connecting…</span><span id="presenterlabel">Whiteboard</span></div>
          </section>

          <section>
            <div class="meeting-section-title"><div><h2>Classroom</h2><p class="meta" id="galleryHint">Camera tiles appear here.</p></div></div>
            <div class="video-gallery" id="gallery">
              <article class="video-card local-video-card" id="localTile">
                <div class="video-frame"><video id="local" autoplay playsinline muted></video><div class="camera-placeholder" id="localPlaceholder"><span data-no-translate>${esc(me.name.slice(0,1).toUpperCase())}</span></div></div>
                <div class="video-label"><span>You</span><small id="localStatus">Mic off · Camera off</small></div>
              </article>
            </div>
          </section>
        </div>

        <aside class="room-aside">
          <div class="participant-head"><h3>Participants</h3><span class="tag gray" id="participantCount">1</span></div>
          <div id="peoplelist" class="people-list"></div>
          ${admin?'<label class="switchrow"><input type="checkbox" id="allow"> Allow students to draw</label>':''}
          <p class="inline-note">Teachers can mute a participant. For privacy, allowing their microphone again does not turn it on automatically; the participant must unmute themselves.</p>
          <section class="room-chat" aria-label="Classroom chat">
            <div class="chat-head"><div><h3>${instant?'Meeting chat':groupChatId?'Group chat':'Class messages'}</h3><span id="chatStatus">${instant?'Live only':'Saved'}</span></div>${instant?'':`<a href="${groupChatId?`/messages?group=${groupChatId}`:`/messages?id=${cid}`}">Open full chat</a>`}</div>
            <div id="chatMessages" class="chat-messages" role="log" aria-live="polite" aria-relevant="additions"><div class="chat-empty">${instant?'Messages in an instant meeting are live for this session.':'Messages are saved with this lesson and remain available outside the meeting.'}</div></div>
            <form id="chatForm" class="chat-form"><label class="sr-only" for="chatInput">Message</label><div><textarea id="chatInput" maxlength="1000" rows="1" autocomplete="off" placeholder="Message the class…"></textarea><button type="submit" class="small">Send</button></div><p class="inline-note">Valid resource codes become clickable file links automatically.</p></form>
          </section>
        </aside>
      </div>
    </section>`;

  let peer=null,iceServers=[],seq=0,chatSeq=0,teacherCommandSeq=0,joined=false,stopping=false,timer=null,mediaHealthTimer=null,version=-1,lastChatPoll=0,relayConfigured=false,relayProvider='';
  let board={background:'grid',shapes:[]},draft=null,tool='pen',drawingAllowed=admin,saving=false,presenter=null,people=[];
  let nativeShare={active:false,seq:0,at:0},nativeFrameSeq=-1,nativePumpTimer=null;
  let audioTrack=null,cameraTrack=null,cameraStream=null,screenTrack=null,screenStream=null,forcedMute=false;
  let delayedSignals=[],signalFailures=0;
  let peers=new Map(),myShapes=[],roomPollFailures=0,viewMode='call',chatMessages=[];
  let annotatorWindow=null,annotatorCanvas=null,annotatorCtx=null,annotatorDraft=null,annotatorTool='pen',annotatorColor='#09695f',annotatorWidth=4;
  const canvas=$('#board'),ctx=canvas.getContext('2d'),W=1600,H=900;
  const post=(action,data={})=>api('/api/room/'+action,{class_id:cid,peer,...data});
  const note=text=>{$('#roomnotice').textContent=text;};
  const initials=name=>(String(name||'?').trim().split(/\s+/).map(x=>x[0]).join('').slice(0,2)||'?').toUpperCase();
  const chatTime=seconds=>new Intl.DateTimeFormat(undefined,{hour:'numeric',minute:'2-digit'}).format(new Date(seconds*1000));
  function chatBody(message){
    let html=esc(message.text);
    for(const item of message.codes||[]){
      const safe=item.code.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
      html=html.replace(new RegExp(`\\b${safe}\\b`,'gi'),`<a class="chat-resource-code" href="/resources?code=${encodeURIComponent(item.code)}" title="Open ${esc(item.label||'class resources')}"><strong>${esc(item.code)}</strong><span>Open files →</span></a>`);
    }
    return html.replace(/\n/g,'<br>');
  }
  function renderChat(){
    const box=$('#chatMessages');if(!box)return;
    if(!chatMessages.length){box.innerHTML=`<div class="chat-empty">${instant?'No messages yet. Instant meeting chat lasts for this live session.':'No messages yet. This chat stays with the lesson before and after the live meeting.'}</div>`;return;}
    const nearBottom=box.scrollHeight-box.scrollTop-box.clientHeight<90;
    box.innerHTML=chatMessages.map(m=>`<article class="chat-message ${m.role==='admin'?'teacher':''}"><div class="chat-meta"><strong>${esc(m.name)}</strong>${m.role==='admin'?'<span class="tag">Teacher</span>':''}<time>${chatTime(m.at)}</time></div><div class="chat-text">${chatBody(m)}</div></article>`).join('');
    if(nearBottom)box.scrollTop=box.scrollHeight;
  }
  async function fetchChat(force=false){
    if(instant)return;
    const now=Date.now();if(!force&&now-lastChatPoll<1800)return;lastChatPoll=now;
    const r=await api(groupChatId?`/api/group-messages?group=${groupChatId}&since=${chatSeq}`:`/api/messages?class=${cid}&since=${chatSeq}`);
    if(r.messages?.length){chatMessages.push(...r.messages);if(chatMessages.length>500)chatMessages=chatMessages.slice(-500);renderChat();}
    chatSeq=Math.max(chatSeq,r.seq||0);
  }
  async function sendChat(text){
    const clean=String(text||'').trim();if(!clean)return;
    const input=$('#chatInput'),button=$('#chatForm button');input.disabled=button.disabled=true;
    try{if(instant){await post('chat',{text:clean});input.value='';input.focus();}else{await api(groupChatId?'/api/group-messages/send':'/api/messages/send',groupChatId?{group_id:groupChatId,text:clean}:{class_id:cid,text:clean});input.value='';await fetchChat(true);input.focus();}}
    catch(ex){toast(ex.message);}finally{input.disabled=button.disabled=false;}
  }

  function updateMediaLinkStatus(){
    const el=$('#mediaLinkStatus');if(!el)return;
    const list=[...peers.values()];
    if(!list.length){el.textContent='Media link: waiting for another participant.';el.dataset.state='waiting';return;}
    const states=list.map(p=>p.pc.connectionState||p.pc.iceConnectionState);
    if(states.every(x=>x==='connected')){el.textContent=`Media link: connected to ${list.length} participant${list.length===1?'':'s'}.`;el.dataset.state='connected';}
    else if(states.some(x=>x==='failed')){el.textContent=relayConfigured?'Media link failed and is retrying through ICE/TURN.':'Direct media link failed and is retrying. If the devices are on different networks, configure a TURN relay.';el.dataset.state='failed';}
    else if(states.some(x=>x==='disconnected')){el.textContent='Media link interrupted — reconnecting…';el.dataset.state='connecting';}
    else{el.textContent='Media link: connecting…';el.dataset.state='connecting';}
  }
  function secureMediaAvailable(){return !!(window.isSecureContext&&navigator.mediaDevices?.getUserMedia&&window.RTCPeerConnection);}
  function mediaError(kind,ex){
    if(!window.isSecureContext) return `${kind} needs HTTPS on a LAN address. Stop this server and run START STUDENT WEBSITE.bat, then open the HTTPS link it prints.`;
    if(ex?.name==='NotAllowedError') return `${kind} permission was blocked. Allow it in the browser site permissions and try again.`;
    if(ex?.name==='NotFoundError') return `No ${kind.toLowerCase()} was found on this device.`;
    if(ex?.name==='NotReadableError') return `${kind} is already in use or the browser could not start it. Close other apps using the camera/microphone, then try again.`;
    if(ex?.name==='OverconstrainedError') return `${kind} could not use the requested quality. Math Studio will retry with the device default.`;
    return `${kind} unavailable: ${ex?.message||'unknown error'}`;
  }
  async function permissionState(name){
    try{if(!navigator.permissions?.query)return 'unknown';const r=await navigator.permissions.query({name});return r.state||'unknown';}catch{return 'unknown';}
  }
  async function renderMediaPreflight(extra=''){
    const box=$('#mediaPreflight');if(!box)return;
    const secure=window.isSecureContext, gum=!!navigator.mediaDevices?.getUserMedia, display=!!navigator.mediaDevices?.getDisplayMedia, rtc=!!window.RTCPeerConnection;
    const [camPerm,micPerm]=await Promise.all([permissionState('camera'),permissionState('microphone')]);
    const row=(ok,label,detail='')=>`<div class="media-check-row ${ok?'ok':'bad'}"><span>${ok?'✓':'!'}</span><div><strong>${label}</strong>${detail?`<small>${esc(detail)}</small>`:''}</div></div>`;
    let html=row(secure,'Secure connection',secure?location.origin:'This page is HTTP. Use the HTTPS classroom link.');
    html+=row(gum&&rtc,'Camera & microphone APIs',gum&&rtc?'Available in this browser':'Unavailable on this origin/browser');
    html+=row(display,'Screen-share API',display?'Available when the browser/device permits it':'This browser/device does not expose web screen sharing');
    html+=row(camPerm!=='denied','Camera permission',camPerm==='granted'?'Allowed':camPerm==='denied'?'Blocked in browser settings':'Will ask when used');
    html+=row(micPerm!=='denied','Microphone permission',micPerm==='granted'?'Allowed':micPerm==='denied'?'Blocked in browser settings':'Will ask when used');
    if(extra)html+=`<div class="media-check-result">${esc(extra)}</div>`;
    box.innerHTML=html;
  }
  async function testLocalMedia(){
    const b=$('#checkMedia');b.disabled=true;
    try{
      if(!window.isSecureContext)throw new Error('Open the HTTPS classroom address first.');
      if(!navigator.mediaDevices?.getUserMedia)throw new Error('This browser does not provide camera/microphone access here.');
      const stream=await navigator.mediaDevices.getUserMedia({video:true,audio:true});
      const cam=stream.getVideoTracks()[0],mic=stream.getAudioTracks()[0];
      const camName=cam?.label||'camera';const micName=mic?.label||'microphone';
      stream.getTracks().forEach(t=>t.stop());
      await renderMediaPreflight(`Device test passed: ${camName} and ${micName} opened successfully.`);
      toast('Camera and microphone opened successfully on this device.');
    }catch(ex){await renderMediaPreflight(mediaError('Media devices',ex));toast(mediaError('Media devices',ex));}
    finally{b.disabled=false;}
  }
  $('#checkMedia').onclick=testLocalMedia;
  renderMediaPreflight().catch(()=>{});

  function flagButton(id,on,onText,offText){const b=$(id);b.textContent=on?onText:offText;b.classList.toggle('active',on);b.setAttribute('aria-pressed',String(on));}
  function localStatus(){
    const mic=forcedMute?'Muted by teacher':audioTrack?.enabled?'Mic on':'Mic off';
    const cam=cameraTrack?.enabled?'Camera on':'Camera off';
    $('#localStatus').textContent=`${mic} · ${cam}`;
    $('#localPlaceholder').classList.toggle('hidden',!!cameraTrack?.enabled);
    const micBtn=$('#mic');
    micBtn.disabled=forcedMute;
    if(forcedMute){micBtn.textContent='Muted by teacher';micBtn.classList.remove('active');micBtn.setAttribute('aria-pressed','false');}
    else flagButton('#mic',!!audioTrack?.enabled,'Mute','Unmute');
    flagButton('#camera',!!cameraTrack?.enabled,'Stop camera','Start camera');
  }
  async function syncMediaState(){
    if(!joined)return;
    try{
      const r=await post('media-state',{mic_on:!!audioTrack?.enabled&&!forcedMute,camera_on:!!cameraTrack?.enabled});
      if(r.forcedMute&&!forcedMute){forcedMute=true;if(audioTrack)audioTrack.enabled=false;localStatus();}
    }catch(ex){if(ex.status!==409)note('Could not update media status: '+ex.message);}
  }

  function coordinatesFor(ev,targetCanvas){const r=targetCanvas.getBoundingClientRect();return [Math.max(0,Math.min(1,(ev.clientX-r.left)/r.width)),Math.max(0,Math.min(1,(ev.clientY-r.top)/r.height))];}
  function coordinates(ev){return coordinatesFor(ev,canvas);}
  function drawShape(s,target=ctx){
    target.strokeStyle=s.color;target.fillStyle=s.color;target.lineWidth=s.width*2;target.lineCap='round';target.lineJoin='round';target.beginPath();
    if(s.type==='pen'){s.points.forEach((p,i)=>i?target.lineTo(p[0]*W,p[1]*H):target.moveTo(p[0]*W,p[1]*H));if(s.points.length===1){target.arc(s.points[0][0]*W,s.points[0][1]*H,s.width,0,Math.PI*2);target.fill();}else target.stroke();}
    else if(s.type==='line'){target.moveTo(s.x*W,s.y*H);target.lineTo(s.x2*W,s.y2*H);target.stroke();}
    else if(s.type==='rect'){target.strokeRect(s.x*W,s.y*H,(s.x2-s.x)*W,(s.y2-s.y)*H);}
    else if(s.type==='circle'){const radius=Math.hypot((s.x2-s.x)*W,(s.y2-s.y)*H);target.arc(s.x*W,s.y*H,radius,0,2*Math.PI);target.stroke();}
    else if(s.type==='text'){target.font=`${22+s.width*3}px system-ui`;target.fillText(s.text,s.x*W,s.y*H);}
    else if(s.type==='graph'){
      let prev=false;for(let px=0;px<=W;px+=2){const x=(px-W/2)/80,v=x-s.h;const y=s.a*(s.fn==='quadratic'?v*v:s.fn==='sine'?Math.sin(v):s.fn==='absolute'?Math.abs(v):v)+s.k,py=H/2-y*80;if(!Number.isFinite(py)||py<-H*2||py>H*3){prev=false;continue;}if(prev)target.lineTo(px,py);else target.moveTo(px,py);prev=true;}target.stroke();
    }
  }
  function renderInto(target,showWhiteboard,draftShape=null){
    target.clearRect(0,0,W,H);
    if(showWhiteboard){
      target.fillStyle='#fff';target.fillRect(0,0,W,H);
      if(board.background==='grid'){
        target.lineWidth=1;target.strokeStyle='#e2e9ec';target.beginPath();for(let x=0;x<=W;x+=80){target.moveTo(x,0);target.lineTo(x,H);}for(let y=0;y<=H;y+=80){target.moveTo(0,y);target.lineTo(W,y);}target.stroke();
        target.strokeStyle='#8aa0a9';target.lineWidth=2;target.beginPath();target.moveTo(W/2,0);target.lineTo(W/2,H);target.moveTo(0,H/2);target.lineTo(W,H/2);target.stroke();
      }
    }
    for(const s of board.shapes)drawShape(s,target);if(draftShape)drawShape(draftShape,target);
  }
  function renderAnnotator(){
    if(!annotatorCtx||!annotatorWindow||annotatorWindow.closed)return;
    renderInto(annotatorCtx,!presenter&&!nativeShare.active&&viewMode==='whiteboard',annotatorDraft);
    const status=annotatorWindow.document.getElementById('annotatorStatus');
    if(status)status.textContent=tr(nativeShare.active?'Drawing over the teacher desktop share':presenter?'Drawing over the live shared screen':viewMode==='whiteboard'?'Shared whiteboard':'Start screen sharing or open the whiteboard first');
  }
  function render(){
    renderInto(ctx,!presenter&&!nativeShare.active&&viewMode==='whiteboard',draft);
    $('#grid').textContent=board.background==='grid'?'Grid on':'Grid off';
    renderAnnotator();
  }
  function scheduleNativePump(){
    clearTimeout(nativePumpTimer);nativePumpTimer=null;
    if(!nativeShare.active||!joined)return;
    const img=$('#nativePresentation');
    if(img&&!img.classList.contains('hidden'))img.src=`/api/native-screen?class=${cid}&t=${Date.now()}`;
    nativePumpTimer=setTimeout(scheduleNativePump,220);
  }
  function updateStage(){
    const share=$('#shareStage'),video=$('#presentation'),nativeImg=$('#nativePresentation');
    const nativeActive=!!nativeShare.active;
    const whiteboardOnly=!presenter&&!nativeActive&&viewMode==='whiteboard';
    share.classList.toggle('hidden',!presenter&&!nativeActive&&!whiteboardOnly);
    document.querySelector('.meeting-main')?.classList.toggle('presenting',!!presenter||nativeActive||whiteboardOnly);
    $('#equationbar').classList.toggle('hidden',!!presenter||nativeActive);
    $('#grid').classList.toggle('hidden',!!presenter||nativeActive);
    $('#stageTitle').textContent=nativeActive?'Teacher is sharing the desktop':presenter?(presenter===peer?'You are sharing your screen':(people.find(p=>p.id===presenter)?.name||'Participant')+' is sharing'):'Shared whiteboard';
    $('#presenterlabel').textContent=nativeActive?'Teacher desktop share':presenter?'Live screen share':'Shared whiteboard';
    $('#whiteboard').classList.toggle('active',whiteboardOnly);
    $('#whiteboard').setAttribute('aria-pressed',String(whiteboardOnly));
    let stream=presenter===peer?screenStream:peers.get(presenter)?.screen;
    video.classList.toggle('hidden',!presenter||nativeActive);
    if(video.srcObject!==stream){video.srcObject=stream||null;if(stream&&!nativeActive)video.play().catch(()=>{});}
    nativeImg.classList.toggle('hidden',!nativeActive);
    if(nativeActive&&!nativePumpTimer)scheduleNativePump();
    if(!nativeActive&&nativePumpTimer){clearTimeout(nativePumpTimer);nativePumpTimer=null;}
    if(nativeActive&&nativeShare.seq!==nativeFrameSeq){
      nativeFrameSeq=nativeShare.seq;
      nativeImg.src=`/api/native-screen?class=${cid}&seq=${nativeShare.seq}&t=${Date.now()}`;
    }
    syncFloatingPreview();
    render();
  }
  function syncFloatingPreview(){
    if(!annotatorWindow||annotatorWindow.closed)return;
    const video=annotatorWindow.document.getElementById('annotatorVideo');if(!video)return;
    const stream=presenter===peer?screenStream:peers.get(presenter)?.screen;
    video.classList.toggle('hidden',!presenter||nativeShare.active);
    if(video.srcObject!==stream){video.srcObject=stream||null;if(stream)video.play().catch(()=>{});}
    renderAnnotator();
  }
  function closeFloatingAnnotator(){
    const w=annotatorWindow;annotatorWindow=null;annotatorCanvas=null;annotatorCtx=null;annotatorDraft=null;
    try{if(w&&!w.closed)w.close();}catch{}
  }
  async function openFloatingAnnotator(){
    if(!joined){toast('Join the classroom first.');return;}
    if(!presenter&&!nativeShare.active&&viewMode!=='whiteboard'){toast('Start screen sharing or open the whiteboard first.');return;}
    if(annotatorWindow&&!annotatorWindow.closed){try{annotatorWindow.focus();}catch{}return;}
    let w=null;
    try{
      if(window.documentPictureInPicture?.requestWindow){
        w=await window.documentPictureInPicture.requestWindow({width:620,height:470});
      }else{
        w=window.open('','MathStudioAnnotator','popup=yes,width=620,height=470,resizable=yes');
        if(!w)throw new Error('The browser blocked the annotation window. Allow pop-ups for MathStudio and try again.');
      }
    }catch(ex){toast('Could not open the floating annotator: '+ex.message);return;}
    annotatorWindow=w;const d=w.document;d.title=tr('MathStudio annotations');
    d.head.innerHTML=`<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
      *{box-sizing:border-box}html,body{margin:0;background:#102a33;color:#fff;font:14px/1.35 system-ui,-apple-system,"Segoe UI",sans-serif;overflow:hidden}button,select,input{font:inherit}button{border:1px solid #55717a;border-radius:8px;background:#173b45;color:#fff;padding:7px 10px;cursor:pointer}button.active{background:#bce7d9;color:#102a33;border-color:#bce7d9}.bar{height:48px;display:flex;align-items:center;gap:6px;padding:6px 8px;background:#102a33;overflow-x:auto;white-space:nowrap}.bar input[type=color]{width:34px;height:34px;padding:1px;border:1px solid #6c858c;border-radius:7px;background:transparent}.bar select{height:34px;background:#173b45;color:#fff;border:1px solid #55717a;border-radius:7px}.stage{position:relative;width:100%;aspect-ratio:16/9;background:#07171c;overflow:hidden}.stage video,.stage canvas{position:absolute;inset:0;width:100%;height:100%}.stage video{object-fit:contain;background:#07171c}.stage canvas{touch-action:none}.hidden{display:none!important}.foot{height:32px;padding:7px 10px;background:#102a33;color:#c7dadd;font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    </style>`;
    d.body.innerHTML=`<div class="bar"><button data-atool="pen" class="active">Pen</button><button data-atool="line">Line</button><button data-atool="circle">Circle</button><button data-atool="rect">Rectangle</button><button data-atool="erase">Eraser</button><input id="aColor" type="color" value="${annotatorColor}" title="Ink colour"><select id="aWidth"><option value="2">Thin</option><option value="4" selected>Medium</option><option value="7">Thick</option></select><button id="aUndo">Undo</button><button id="aClear">Clear</button><button id="aBack">MathStudio</button></div><div class="stage"><video id="annotatorVideo" autoplay playsinline muted></video><canvas id="annotatorCanvas" width="1600" height="900"></canvas></div><div class="foot" id="annotatorStatus">Floating annotations</div>`;
    localize(d.body);
    annotatorCanvas=d.getElementById('annotatorCanvas');annotatorCtx=annotatorCanvas.getContext('2d');
    d.querySelectorAll('[data-atool]').forEach(b=>b.addEventListener('click',()=>{annotatorTool=b.dataset.atool;d.querySelectorAll('[data-atool]').forEach(x=>x.classList.toggle('active',x===b));}));
    d.getElementById('aColor').addEventListener('input',ev=>{annotatorColor=ev.target.value;});
    d.getElementById('aWidth').addEventListener('change',ev=>{annotatorWidth=Number(ev.target.value)||4;});
    d.getElementById('aUndo').addEventListener('click',async()=>{if(!canDraw())return;const id=[...myShapes].reverse().find(id=>board.shapes.some(s=>s.id===id));if(id&&await saveBoard({...board,shapes:board.shapes.filter(s=>s.id!==id)}))myShapes=myShapes.filter(x=>x!==id);});
    d.getElementById('aClear').addEventListener('click',()=>{if(canDraw()&&confirm(tr('Clear the shared annotations for everyone?')))saveBoard({...board,shapes:[]});});
    d.getElementById('aBack').addEventListener('click',()=>{try{window.focus();}catch{}});
    const freshFloating=type=>({id:crypto.randomUUID(),type,color:annotatorColor,width:annotatorWidth});
    annotatorCanvas.addEventListener('pointerdown',async ev=>{
      if(ev.button!==0&&ev.pointerType==='mouse')return;if(!canDraw())return;ev.preventDefault();const [x,y]=coordinatesFor(ev,annotatorCanvas);
      if(annotatorTool==='erase'){const found=[...board.shapes].reverse().find(s=>hit(s,x,y));if(found)await saveBoard({...board,shapes:board.shapes.filter(s=>s.id!==found.id)});return;}
      annotatorCanvas.setPointerCapture(ev.pointerId);annotatorDraft=annotatorTool==='pen'?{...freshFloating('pen'),points:[[x,y]]}:{...freshFloating(annotatorTool),x,y,x2:x,y2:y};renderAnnotator();
    });
    annotatorCanvas.addEventListener('pointermove',ev=>{if(!annotatorDraft)return;ev.preventDefault();const [x,y]=coordinatesFor(ev,annotatorCanvas);if(annotatorDraft.type==='pen'){if(annotatorDraft.points.length<1500)annotatorDraft.points.push([x,y]);}else{annotatorDraft.x2=x;annotatorDraft.y2=y;}renderAnnotator();});
    const finishFloating=async()=>{if(!annotatorDraft)return;const shape=annotatorDraft;annotatorDraft=null;await addShape(shape);renderAnnotator();};
    annotatorCanvas.addEventListener('pointerup',finishFloating);annotatorCanvas.addEventListener('pointercancel',()=>{annotatorDraft=null;renderAnnotator();});
    w.addEventListener('pagehide',()=>{if(annotatorWindow===w){annotatorWindow=null;annotatorCanvas=null;annotatorCtx=null;annotatorDraft=null;}});
    syncFloatingPreview();
    toast(window.documentPictureInPicture?.window===w?'Floating annotator is always on top while you change tabs.':'Floating annotator opened. Keep this small window visible while changing tabs.');
  }
  async function saveBoard(next){if(saving)return false;saving=true;$('#boardstatus').textContent='Saving…';try{const r=await post('board',{version,board:next});board=next;version=r.version;render();return true;}catch(ex){toast(ex.message);return false;}finally{saving=false;updateBoardStatus();}}
  function updateBoardStatus(){$('#boardstatus').textContent=!joined?'Disconnected':saving?'Saving…':drawingAllowed?'Draw with mouse, touch, or pen':'Viewing only · Teacher controls drawing';}
  function fresh(type){return {id:crypto.randomUUID(),type,color:$('#color').value,width:Number($('#width').value)};}
  function canDraw(){if(!joined||saving||(!presenter&&!nativeShare.active&&viewMode!=='whiteboard'))return false;if(!drawingAllowed){toast('The teacher has not enabled student drawing.');return false;}return true;}
  async function addShape(s){if(await saveBoard({...board,shapes:[...board.shapes,s]}))myShapes.push(s.id);}
  canvas.addEventListener('pointerdown',async ev=>{if(ev.button!==0&&ev.pointerType==='mouse')return;if(!canDraw())return;ev.preventDefault();const [x,y]=coordinates(ev);if(tool==='text'){const text=prompt(tr('Text or math symbols:'));if(text?.trim())await addShape({...fresh('text'),x,y,text:text.trim().slice(0,300)});return;}if(tool==='erase'){const found=[...board.shapes].reverse().find(s=>hit(s,x,y));if(found)await saveBoard({...board,shapes:board.shapes.filter(s=>s.id!==found.id)});return;}canvas.setPointerCapture(ev.pointerId);draft=tool==='pen'?{...fresh(tool),points:[[x,y]]}:{...fresh(tool),x,y,x2:x,y2:y};render();});
  canvas.addEventListener('pointermove',ev=>{if(!draft)return;ev.preventDefault();const [x,y]=coordinates(ev);if(draft.type==='pen'){if(draft.points.length<1500)draft.points.push([x,y]);}else{draft.x2=x;draft.y2=y;}render();});
  const finish=async()=>{if(!draft)return;const s=draft;draft=null;await addShape(s);render();};canvas.addEventListener('pointerup',finish);canvas.addEventListener('pointercancel',()=>{draft=null;render();});
  function distance(x,y,x1,y1,x2,y2){const a=(x-x1)*W,b=(y-y1)*H,c=(x2-x1)*W,d=(y2-y1)*H,t=Math.max(0,Math.min(1,(a*c+b*d)/(c*c+d*d||1)));return Math.hypot(a-t*c,b-t*d);}
  function hit(s,x,y){if(s.type==='pen')return s.points.some((p,i)=>distance(x,y,p[0],p[1],...(s.points[i+1]||p))<20);if(s.type==='line')return distance(x,y,s.x,s.y,s.x2,s.y2)<20;if(s.type==='circle')return Math.abs(Math.hypot((x-s.x)*W,(y-s.y)*H)-Math.hypot((s.x2-s.x)*W,(s.y2-s.y)*H))<20;if(s.type==='rect')return [[s.x,s.y,s.x2,s.y],[s.x2,s.y,s.x2,s.y2],[s.x2,s.y2,s.x,s.y2],[s.x,s.y2,s.x,s.y]].some(p=>distance(x,y,...p)<20);if(s.type==='text')return x>=s.x&&x<=s.x+.4&&Math.abs(y-s.y)<.05;return false;}
  document.querySelectorAll('[data-tool]').forEach(b=>b.onclick=()=>{tool=b.dataset.tool;document.querySelectorAll('[data-tool]').forEach(x=>{x.classList.toggle('active',x===b);x.setAttribute('aria-pressed',String(x===b));});});
  $('#grid').onclick=()=>{if(canDraw())saveBoard({...board,background:board.background==='grid'?'blank':'grid'});};
  $('#plot').onclick=()=>{if(!canDraw())return;const coeffs={};for(const key of ['a','h','k']){coeffs[key]=Number($('#coef-'+key).value);if(!Number.isFinite(coeffs[key])||Math.abs(coeffs[key])>10){toast('Graph values must be between −10 and 10.');return;}}addShape({...fresh('graph'),fn:$('#function').value,...coeffs});};
  $('#undo').onclick=async()=>{if(!canDraw())return;const id=[...myShapes].reverse().find(id=>board.shapes.some(s=>s.id===id));if(id&&await saveBoard({...board,shapes:board.shapes.filter(s=>s.id!==id)}))myShapes=myShapes.filter(x=>x!==id);};
  $('#clear').onclick=()=>{if(canDraw()&&confirm(tr('Clear the shared annotations for everyone?')))saveBoard({...board,shapes:[]});};
  $('#save').onclick=()=>{const out=document.createElement('canvas');out.width=W;out.height=H;const x=out.getContext('2d');x.fillStyle='white';x.fillRect(0,0,W,H);const v=$('#presentation');if(presenter&&v.readyState>=2&&v.videoWidth){const scale=Math.min(W/v.videoWidth,H/v.videoHeight),vw=v.videoWidth*scale,vh=v.videoHeight*scale;x.fillStyle='#14272e';x.fillRect(0,0,W,H);x.drawImage(v,(W-vw)/2,(H-vh)/2,vw,vh);}x.drawImage(canvas,0,0);const a=document.createElement('a');a.href=out.toDataURL('image/png');a.download='math-class-'+cid+'.png';a.click();};

  async function makeOffer(id,p,iceRestart=false){
    if(!joined||!p||p.pc.signalingState==='closed')return;
    if(p.pc.signalingState!=='stable'||p.negotiating){if(p){p.needsNegotiation=true;p.needsIceRestart=p.needsIceRestart||iceRestart;}return;}
    p.negotiating=true;p.needsNegotiation=false;const restart=iceRestart||p.needsIceRestart;p.needsIceRestart=false;
    try{console.info('[MathStudio WebRTC] sending offer to',id);const offer=await p.pc.createOffer(restart?{iceRestart:true}:undefined);await p.pc.setLocalDescription(offer);await post('signal',{to:id,signal:{description:p.pc.localDescription.toJSON()}});}
    catch(ex){p.needsNegotiation=true;note('Media renegotiation is retrying… '+ex.message);}
    finally{p.negotiating=false;if(p.needsNegotiation&&p.pc.signalingState==='stable')setTimeout(()=>makeOffer(id,p,p.needsIceRestart),80);}
  }
  async function requestNegotiation(id,p,iceRestart=false){
    if(!joined||!p)return;
    if(peer<id)await makeOffer(id,p,iceRestart);
    else await post('signal',{to:id,signal:{control:'renegotiate',iceRestart:!!iceRestart}});
  }
  async function renegotiateAll(iceRestart=false){await Promise.all([...peers].map(([id,p])=>requestNegotiation(id,p,iceRestart).catch(()=>{})));}
  // Track activation is serialized per peer. A newly-enabled video/audio sender
  // must be advertised in SDP, but repeated camera toggles must not trigger
  // competing offers while ICE is already connected.
  function scheduleTrackOffer(id,p,kind){
    if(!p.trackOfferTimers)p.trackOfferTimers={};
    clearTimeout(p.trackOfferTimers[kind]);
    p.trackOfferTimers[kind]=setTimeout(()=>{
      if(!joined||p.pc.signalingState==='closed')return;
      const sender=p.senders[kind],tr=p.transceivers[kind];
      if(!sender?.track||sender.track.readyState!=='live'||!tr)return;
      tr.direction='sendrecv';
      console.info('[MathStudio WebRTC] negotiating newly activated',kind,'sender for',id);
      requestNegotiation(id,p,false).catch(e=>console.warn('[MathStudio WebRTC] track negotiation',e));
    },350);
  }
  async function replace(kind,track){
    await Promise.all([...peers].map(async ([id,p])=>{
      const sender=p.senders[kind],tr=p.transceivers[kind];if(!sender||!tr)return;
      const previous=sender.track;
      await sender.replaceTrack(track||null);
      if(track){
        tr.direction='sendrecv';
        // An initial empty m-line can remain receive-only on some browsers.
        // Re-offer only on first activation or a known non-sending direction.
        const needsOffer=!previous || (tr.currentDirection && !tr.currentDirection.includes('send'));
        if(needsOffer)scheduleTrackOffer(id,p,kind);
      }
      console.info('[MathStudio WebRTC] local sender updated',kind,
        {track:sender.track?.readyState||'none',enabled:sender.track?.enabled??false,
         direction:tr.currentDirection||'pending'});
    }));
  }
  async function stopCamera(sync=true){
    const old=cameraTrack;cameraTrack=null;
    if(cameraStream){cameraStream.getTracks().forEach(t=>{t.onended=null;t.stop();});cameraStream=null;}else if(old){old.onended=null;old.stop();}
    $('#local').srcObject=null;await replace('camera',null);localStatus();if(sync)await syncMediaState();
  }
  $('#mic').onclick=async()=>{
    if(forcedMute){toast('Your teacher has muted your microphone.');return;}
    try{
      if(!secureMediaAvailable())throw new Error('secure-context');
      if(!audioTrack){audioTrack=(await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true},video:false})).getAudioTracks()[0];await replace('audio',audioTrack);}else audioTrack.enabled=!audioTrack.enabled;
      localStatus();await syncMediaState();
    }catch(ex){toast(ex.message==='secure-context'?mediaError('Microphone',{}):mediaError('Microphone',ex));}
  };
  $('#camera').onclick=async()=>{
    const button=$('#camera');button.disabled=true;
    try{
      if(!secureMediaAvailable())throw new Error('secure-context');
      if(cameraTrack){await stopCamera();toast('Camera stopped.');return;}
      let stream;
      try{stream=await navigator.mediaDevices.getUserMedia({video:{width:{ideal:1280},height:{ideal:720},frameRate:{ideal:24,max:30}},audio:false});}
      catch(ex){if(ex?.name==='OverconstrainedError')stream=await navigator.mediaDevices.getUserMedia({video:true,audio:false});else throw ex;}
      const track=stream.getVideoTracks()[0];if(!track)throw new DOMException('No camera track was returned.','NotFoundError');
      cameraStream=stream;cameraTrack=track;cameraTrack.enabled=true;cameraTrack.onended=()=>{if(cameraTrack===track)stopCamera().catch(()=>{});};
      const local=$('#local');local.srcObject=stream;await local.play().catch(()=>{});await replace('camera',cameraTrack);
      localStatus();await syncMediaState();toast('Camera started.');
    }catch(ex){if(cameraStream){cameraStream.getTracks().forEach(t=>t.stop());cameraStream=null;}cameraTrack=null;$('#local').srcObject=null;localStatus();toast(ex.message==='secure-context'?mediaError('Camera',{}):mediaError('Camera',ex));}
    finally{button.disabled=false;}
  };
  async function stopShare(){
    const s=screenStream;screenStream=null;screenTrack=null;if(s)s.getTracks().forEach(t=>{t.onended=null;t.stop();});await replace('screen',null);
    if(joined){try{await post('presenter',{active:false});}catch{}}
    if(presenter===peer)presenter=null;$('#share').textContent='Share screen';$('#share').classList.remove('active');$('#share').setAttribute('aria-pressed','false');updateStage();
  }
  $('#share').onclick=async()=>{
    if(screenTrack){await stopShare();return;}
    if(!window.isSecureContext||!navigator.mediaDevices?.getDisplayMedia){toast('Screen sharing needs HTTPS here. Run START STUDENT WEBSITE.bat and use its HTTPS link in desktop Chrome or Edge.');return;}
    let stream;
    try{
      stream=await navigator.mediaDevices.getDisplayMedia({video:{frameRate:{ideal:15,max:30}},audio:false,preferCurrentTab:false,selfBrowserSurface:'exclude',surfaceSwitching:'include'});
      await post('presenter',{active:true});screenStream=stream;screenTrack=stream.getVideoTracks()[0];screenTrack.onended=()=>stopShare();await replace('screen',screenTrack);presenter=peer;viewMode='call';$('#share').textContent='Stop sharing';$('#share').classList.add('active');$('#share').setAttribute('aria-pressed','true');updateStage();toast('Screen sharing started. For true desktop annotations, share Entire Screen and run the Windows desktop annotation companion.');
    }catch(ex){stream?.getTracks().forEach(t=>t.stop());if(ex.name!=='NotAllowedError')toast('Screen sharing did not start: '+ex.message);}
  };
  $('#whiteboard').onclick=()=>{if(presenter||nativeShare.active){toast('A live screen share is being shown. You can draw directly over it.');return;}viewMode=viewMode==='whiteboard'?'call':'whiteboard';updateStage();};
  $('#sound').onclick=()=>{document.querySelectorAll('audio,video').forEach(v=>v.play().catch(()=>{}));toast('Audio playback enabled.');};
  $('#allow')?.addEventListener('change',async()=>{try{await post('permissions',{drawing:$('#allow').checked});}catch(ex){toast(ex.message);}});
  $('#chatForm')?.addEventListener('submit',ev=>{ev.preventDefault();sendChat($('#chatInput').value);});
  $('#chatInput')?.addEventListener('keydown',ev=>{if(ev.key==='Enter'&&!ev.shiftKey&&!ev.isComposing){ev.preventDefault();sendChat(ev.currentTarget.value);}});
  $('#end')?.addEventListener('click',async()=>{if(!confirm(tr('End the class and disconnect everyone?')))return;try{await api('/api/admin/class-action',{class_id:cid,action:'end'});await leave();location.href='/teacher';}catch(ex){toast(ex.message);}});

  function remoteTile(person){
    const div=document.createElement('article');div.className='video-card';div.id='peer-'+person.id;
    div.innerHTML=`<div class="video-frame"><video autoplay playsinline muted></video><div class="camera-placeholder"><span data-no-translate>${esc(initials(person.name))}</span></div></div><audio autoplay></audio><div class="video-label"><span><span data-no-translate>${esc(person.name)}</span></span><small>Connecting…</small></div>`;
    $('#gallery').append(div);return div;
  }
  function updateTile(person,p){
    if(!p)return;const small=p.element.querySelector('small'),ph=p.element.querySelector('.camera-placeholder');
    const mic=person.forced_mute?'Muted by teacher':person.mic_on?'Mic on':'Mic off';
    const video=p.element.querySelector('video');
    const hasFrames=!!(video&&video.readyState>=2&&video.videoWidth>0&&video.videoHeight>0);
    const cameraReady=!!(p.cameraTrack&&p.cameraTrack.readyState==='live'&&(p.cameraReady||hasFrames));
    small.textContent=`${mic} · ${person.camera_on?(cameraReady?'Camera on':(p.cameraWaitingSince&&Date.now()-p.cameraWaitingSince>6000?'Camera reconnecting…':'Camera connecting…')):'Camera off'}`;
    ph.classList.toggle('hidden',!!person.camera_on&&cameraReady);
  }
  function renderPeople(){
    $('#participantCount').textContent=String(people.length);
    $('#peoplelist').innerHTML=people.map(person=>{
      const you=person.id===peer;
      const status=person.forced_mute?'Muted by teacher':person.mic_on?'Mic on':'Mic off';
      const hostControl=admin&&!you?`<button class="small secondary host-mute" data-peer="${esc(person.id)}" data-muted="${person.forced_mute?'1':'0'}">${person.forced_mute?'Allow mic':'Mute'}</button>`:'';
      return `<div class="person-row"><div><strong><span data-no-translate>${esc(person.name)}</span>${you?' (you)':''}</strong><span>${person.role==='admin'?'Teacher':'Student'} · ${status} · ${person.camera_on?'Camera on':'Camera off'}</span></div>${hostControl}</div>`;
    }).join('');
    document.querySelectorAll('.host-mute').forEach(b=>b.onclick=async()=>{b.disabled=true;try{const muted=b.dataset.muted!=='1';await post('mute',{target:b.dataset.peer,muted});toast(muted?'Participant muted.':'Participant may unmute now.');await pollOnce();}catch(ex){toast(ex.message);}finally{b.disabled=false;}});
    for(const person of people)if(person.id!==peer)updateTile(person,peers.get(person.id));
  }

  async function createPeer(person, initiate=true){
    if(peers.has(person.id))return peers.get(person.id);
    const pc=new RTCPeerConnection({iceServers,iceCandidatePoolSize:2,bundlePolicy:'max-bundle'});
    // Only the deterministic offerer creates transceivers. On the answering side,
    // setRemoteDescription(offer) creates m-line-matched transceivers for us.
    // Pre-creating them on both sides caused duplicate receiver-only m-lines.
    const offerer=peer<person.id;
    const aud=offerer?pc.addTransceiver('audio',{direction:'sendrecv'}):null;
    const cam=offerer?pc.addTransceiver('video',{direction:'sendrecv'}):null;
    const scr=offerer?pc.addTransceiver('video',{direction:'sendrecv'}):null;
    const p={pc,pending:[],element:remoteTile(person),screen:null,senders:{audio:aud?.sender||null,camera:cam?.sender||null,screen:scr?.sender||null},transceivers:{audio:aud,camera:cam,screen:scr},cameraTrack:null,cameraReady:false,cameraWaitingSince:0,lastCameraRetry:0,negotiating:false,needsNegotiation:false,needsIceRestart:false,restartTimer:null};peers.set(person.id,p);
    if(offerer){await aud.sender.replaceTrack(audioTrack||null);await cam.sender.replaceTrack(cameraTrack||null);await scr.sender.replaceTrack(screenTrack||null);}
    pc.onicecandidate=ev=>{if(ev.candidate&&joined)post('signal',{to:person.id,signal:{candidate:ev.candidate.toJSON()}}).catch(()=>{});};
    pc.oniceconnectionstatechange=()=>{console.info('[MathStudio WebRTC]',person.name,'ICE:',pc.iceConnectionState,'connection:',pc.connectionState);updateMediaLinkStatus();};
    pc.onicecandidateerror=ev=>{const detail=ev?.errorText||ev?.errorCode||'ICE candidate error';note('Media network warning: '+detail+(relayConfigured?'':' · A TURN relay may be required.'));};
    pc.onconnectionstatechange=()=>{updateMediaLinkStatus();if(pc.connectionState==='connected'){clearTimeout(p.restartTimer);renderPeople();}else if(pc.connectionState==='failed'){note('Reconnecting participant media…');requestNegotiation(person.id,p,true).catch(()=>{});}else if(pc.connectionState==='disconnected'){clearTimeout(p.restartTimer);p.restartTimer=setTimeout(()=>{if(pc.connectionState==='disconnected')requestNegotiation(person.id,p,true).catch(()=>{});},2500);}};
    pc.onsignalingstatechange=()=>{if(pc.signalingState==='stable'&&p.needsNegotiation&&peer<person.id)setTimeout(()=>makeOffer(person.id,p,p.needsIceRestart),50);};
    pc.ontrack=ev=>{
      const stream=new MediaStream([ev.track]);
      if(ev.track.kind==='audio'){const el=p.element.querySelector('audio');el.srcObject=stream;el.autoplay=true;el.playsInline=true;el.play().catch(()=>note('Click Enable sound if you cannot hear the class.'));ev.track.onunmute=()=>el.play().catch(()=>{});return;}
      if(ev.track.kind==='video' && (ev.transceiver===p.transceivers.camera || ev.transceiver?.mid==='1' || (!p.cameraTrack && ev.transceiver!==p.transceivers.screen && ev.transceiver?.mid!=='2'))){
        const el=p.element.querySelector('video');p.cameraTrack=ev.track;
        const attach=()=>{
          if(el.srcObject!==stream)el.srcObject=stream;
          el.muted=true;el.autoplay=true;el.playsInline=true;
          el.play().catch(ex=>console.warn('[MathStudio WebRTC] remote video play deferred',person.name,ex?.name||ex));
          if(el.videoWidth>0&&el.videoHeight>0)p.cameraReady=true;
          const current=people.find(x=>x.id===person.id);if(current)updateTile(current,p);
        };
        console.info('[MathStudio WebRTC] incoming camera track',person.name,'mid:',ev.transceiver?.mid,'muted:',ev.track.muted);
        ev.track.onunmute=()=>{p.cameraReady=true;console.info('[MathStudio WebRTC] remote camera unmuted',person.name);attach();};
        ev.track.onmute=()=>{p.cameraReady=false;const current=people.find(x=>x.id===person.id);if(current)updateTile(current,p);};
        ev.track.onended=ev.track.onmute;
        ['loadedmetadata','playing','resize','canplay'].forEach(name=>el.addEventListener(name,()=>{if(el.videoWidth>0&&el.videoHeight>0)p.cameraReady=true;const current=people.find(x=>x.id===person.id);if(current)updateTile(current,p);}));
        attach();return;
      }
      if(ev.track.kind==='video'){p.screen=stream;updateStage();}
    };
    if(initiate&&peer<person.id)await makeOffer(person.id,p,false);
    return p;
  }
  async function bindAnswerTransceivers(p){
    // The incoming SDP offer defines the m-line identity/order. Chrome/Safari
    // create these transceivers when setRemoteDescription(offer) is applied.
    const trs=p.pc.getTransceivers();
    const findMid=(mid,kind)=>trs.find(t=>t.mid===mid && t.receiver?.track?.kind===kind);
    const aud=findMid('0','audio'),cam=findMid('1','video'),scr=findMid('2','video');
    if(!aud||!cam||!scr)throw new Error('Remote offer missing expected audio/camera/screen m-lines');
    for(const [kind,tr,track] of [
      ['audio',aud,audioTrack],['camera',cam,cameraTrack],['screen',scr,screenTrack]
    ]){
      tr.direction='sendrecv';
      p.transceivers[kind]=tr;
      p.senders[kind]=tr.sender;
      if(tr.sender.track!==track)await tr.sender.replaceTrack(track||null);
      console.info('[MathStudio WebRTC] answer sender',kind,{
        track:tr.sender.track?.readyState||'none',direction:tr.direction,mid:tr.mid
      });
    }
  }
  async function signalEvent(event){
    const s=event.signal;
    if(s?.description)console.info('[MathStudio WebRTC] received',s.description.type,'from',event.from);
    if(s?.control==='host-mute'){
      forcedMute=!!s.muted;if(forcedMute&&audioTrack)audioTrack.enabled=false;localStatus();await syncMediaState();toast(forcedMute?'Your teacher muted your microphone.':'Your teacher has allowed your microphone. You can unmute when ready.');return;
    }
    let p=peers.get(event.from);
    if(!p){
      const person=people.find(item=>item.id===event.from);
      if(person){p=await createPeer(person,false);}
      if(!p){delayedSignals.push(event);return;}
    }
    if(s?.control==='renegotiate'){if(peer<event.from)await makeOffer(event.from,p,!!s.iceRestart);return;}
    if(s?.control==='camera-retry'){
      // Do not detach the live camera during a remote playback retry.
      // Detach/reattach caused unnecessary interruptions of working ICE sessions.
      if(cameraTrack?.readyState==='live'&&p.senders.camera?.track!==cameraTrack){
        await p.senders.camera.replaceTrack(cameraTrack);
      }
      console.info('[MathStudio WebRTC] playback retry requested by',event.from,
        'sender track:',p.senders.camera?.track?.readyState||'none',
        'ICE:',p.pc.iceConnectionState,'sender:',p.senders.camera?.track?.id||'none');
      return;
    }
    if(s.description){await p.pc.setRemoteDescription(s.description);for(const c of p.pending){try{await p.pc.addIceCandidate(c);}catch{}}p.pending=[];if(s.description.type==='offer'){await bindAnswerTransceivers(p);console.info('[MathStudio WebRTC] sending answer to',event.from);await p.pc.setLocalDescription(await p.pc.createAnswer());console.info('[MathStudio WebRTC] local answer directions',p.pc.getTransceivers().filter(t=>t.mid!==null).map(t=>({mid:t.mid,kind:t.receiver.track.kind,direction:t.currentDirection||t.direction,hasSender:!!t.sender.track})));await post('signal',{to:event.from,signal:{description:p.pc.localDescription.toJSON()}});}else if(s.description.type==='answer'&&p.needsNegotiation&&peer<event.from)setTimeout(()=>makeOffer(event.from,p,p.needsIceRestart),80);}
    else if(s.candidate){if(p.pc.remoteDescription)await p.pc.addIceCandidate(s.candidate);else p.pending.push(s.candidate);}
  }

  // iOS suspends video elements when Safari backgrounds or an audio route changes.
  // Resume playback without tearing down the ICE connection or camera sender.
  document.addEventListener('visibilitychange',()=>{
    if(document.visibilityState!=='visible')return;
    for(const p of peers.values()){
      for(const el of p.element.querySelectorAll('video,audio')){
        if(el.srcObject && el.paused)el.play().catch(()=>{});
      }
    }
  });
  function checkRemoteMedia(){
    if(!joined)return;
    const now=Date.now();
    for(const person of people){
      if(person.id===peer)continue;
      const p=peers.get(person.id);if(!p)continue;
      const video=p.element.querySelector('video');
      const hasFrames=!!(video&&video.videoWidth>0&&video.videoHeight>0&&video.readyState>=2);
      if(hasFrames){p.cameraReady=true;p.cameraWaitingSince=0;}
      else if(person.camera_on){
        if(!p.cameraWaitingSince)p.cameraWaitingSince=now;
        if(pcConnected(p.pc)&&now-p.cameraWaitingSince>4500&&now-p.lastCameraRetry>8000){
          p.lastCameraRetry=now;
          post('signal',{to:person.id,signal:{control:'camera-retry'}}).catch(()=>{});
        }
      }else{p.cameraReady=false;p.cameraWaitingSince=0;}
      if(person.camera_on&&p.pc.connectionState==='connected'&&now-(p.lastStatsAt||0)>10000){
        p.lastStatsAt=now;
        p.pc.getStats().then(report=>{
          const rows=[];
          report.forEach(v=>{if((v.type==='outbound-rtp'||v.type==='inbound-rtp')&&v.kind==='video')rows.push({direction:v.type,bytes:v.bytesSent??v.bytesReceived??0,frames:v.framesEncoded??v.framesDecoded??0,packets:v.packetsSent??v.packetsReceived??0,mid:v.mid||''});});
          console.info('[MathStudio WebRTC] video stats',person.name,rows,
            'sender:',{camera:p.senders.camera?.track?.readyState||'none',cameraEnabled:!!p.senders.camera?.track?.enabled,cameraDirection:p.transceivers.camera?.currentDirection||p.transceivers.camera?.direction,audio:p.senders.audio?.track?.readyState||'none',audioEnabled:!!p.senders.audio?.track?.enabled,audioDirection:p.transceivers.audio?.currentDirection||p.transceivers.audio?.direction},
            'receiver:',{track:p.transceivers.camera?.receiver?.track?.readyState||'none',muted:p.transceivers.camera?.receiver?.track?.muted});
        }).catch(()=>{});
      }
      updateTile(person,p);
    }
    mediaHealthTimer=setTimeout(checkRemoteMedia,1000);
  }
  function pcConnected(pc){return !!pc&&(pc.connectionState==='connected'||['connected','completed'].includes(pc.iceConnectionState));}

  async function pollOnce(){
    const r=await api(`/api/room/poll?class=${cid}&peer=${peer}&since=${seq}&command_since=${teacherCommandSeq}`);people=r.peers;drawingAllowed=admin||r.drawing;if($('#allow'))$('#allow').checked=r.drawing;
    if(r.nativeShare){const changed=!!r.nativeShare.active!==!!nativeShare.active||Number(r.nativeShare.seq||0)!==Number(nativeShare.seq||0);nativeShare=r.nativeShare;if(changed)updateStage();}
    if(admin&&Array.isArray(r.teacherCommands)){
      for(const cmd of r.teacherCommands){
        if(cmd.command==='mic-toggle')$('#mic')?.click();
        else if(cmd.command==='camera-toggle')$('#camera')?.click();
      }
      teacherCommandSeq=Math.max(teacherCommandSeq,Number(r.teacherCommandSeq||0));
    }
    if(r.forcedMute!==forcedMute){forcedMute=!!r.forcedMute;if(forcedMute&&audioTrack)audioTrack.enabled=false;localStatus();await syncMediaState();}
    if(!draft&&!saving&&r.version>version){board=r.board;version=r.version;render();}
    if(r.presenter!==presenter){presenter=r.presenter;updateStage();}
    for(const person of people){if(person.id!==peer)await createPeer(person);}
    for(const [id,p] of peers){if(!people.some(x=>x.id===id)){clearTimeout(p.restartTimer);p.pc.close();p.element.remove();peers.delete(id);}}
    // Process signaling after participant discovery. Do not silently discard
    // offers if presence and signaling messages arrive in different polls.
    const pending=[...delayedSignals,...r.events];delayedSignals=[];
    for(const event of pending){
      try{await signalEvent(event);signalFailures=0;}
      catch(ex){
        signalFailures++;
        console.warn('[MathStudio WebRTC] signal processing failed',event?.signal?.description?.type||'candidate/control',ex);
        note('WebRTC signaling error ('+signalFailures+'): '+ex.message);
        // Re-deliver the event on the next poll instead of acknowledging and losing it.
        if(signalFailures<5)delayedSignals.push(event);
      }
    }
    if(instant&&Array.isArray(r.chat)&&r.chat.length){for(const m of r.chat){if(!chatMessages.some(x=>x.id===m.id))chatMessages.push(m);}chatSeq=Math.max(chatSeq,Number(r.chatSeq||0));renderChat();}
    await fetchChat(false).catch(()=>{});
    seq=r.seq;renderPeople();updateMediaLinkStatus();updateBoardStatus();localStatus();
  }
  async function poll(){if(!joined||stopping)return;try{await pollOnce();roomPollFailures=0;}catch(ex){roomPollFailures++;if([401,403,404,409].includes(ex.status)){await leave();$('#joinerror').textContent=ex.message;return;}note('Reconnecting to classroom… '+ex.message);if(roomPollFailures>=8){await leave();$('#joinerror').textContent='Connection lost. Rejoin when the server is available.';return;}}if(joined)timer=setTimeout(poll,900);}
  async function join(){
    if(joined)return;$('#join').disabled=true;
    try{
      if(!window.RTCPeerConnection)throw new Error('This browser does not support WebRTC. Use a current Chrome, Edge, Safari, or Firefox browser.');
      const r=await api('/api/room/join',{class_id:cid});peer=r.peer;iceServers=r.iceServers;relayConfigured=!!r.relayConfigured;relayProvider=r.relayProvider||'';seq=0;delayedSignals=[];signalFailures=0;chatSeq=0;teacherCommandSeq=0;chatMessages=[];lastChatPoll=0;version=-1;joined=true;stopping=false;$('#prejoin').classList.add('hidden');$('#room').classList.remove('hidden');
      note(window.isSecureContext?(r.relayConfigured?`Connected. ${relayProvider||'TURN relay'} is available for camera and audio when direct WebRTC is blocked.`:(r.relayError?`Connected, but the TURN relay could not be reached: ${r.relayError}. Direct WebRTC will still be tried.`:'Connected. Direct WebRTC is active, but no TURN relay is configured. Run SETUP FREE CAMERA + AUDIO.bat on the website computer for reliable remote media.')):'Connected to the room, but this HTTP address cannot access camera/microphone. Use the secure HTTPS student link.');
      clearTimeout(mediaHealthTimer);checkRemoteMedia();await fetchChat(true).catch(()=>{});await poll();
    }catch(ex){$('#joinerror').textContent=ex.message;}finally{$('#join').disabled=false;}
  }
  async function leave(){
    if(stopping)return;stopping=true;clearTimeout(timer);clearTimeout(mediaHealthTimer);clearTimeout(nativePumpTimer);nativePumpTimer=null;closeFloatingAnnotator();const wasJoined=joined;joined=false;
    for(const t of [audioTrack,cameraTrack,screenTrack])if(t){t.onended=null;t.stop();}if(cameraStream)cameraStream.getTracks().forEach(t=>t.stop());cameraStream=null;audioTrack=cameraTrack=screenTrack=null;screenStream=null;$('#local').srcObject=null;
    for(const p of peers.values()){clearTimeout(p.restartTimer);p.pc.close();p.element.remove();}peers.clear();if(wasJoined){try{await post('leave');}catch{}}
    peer=null;presenter=null;nativeShare={active:false,seq:0,at:0};nativeFrameSeq=-1;forcedMute=false;people=[];chatSeq=0;teacherCommandSeq=0;chatMessages=[];relayConfigured=false;$('#desktopAnnotatorPanel')?.classList.add('hidden');renderChat();updateMediaLinkStatus();$('#presentation').srcObject=null;$('#room').classList.add('hidden');$('#prejoin').classList.remove('hidden');viewMode='call';stopping=false;
  }
  $('#join').onclick=join;$('#leave').onclick=leave;
  window.addEventListener('pagehide',()=>{closeFloatingAnnotator();joined=false;clearTimeout(timer);clearTimeout(mediaHealthTimer);clearTimeout(nativePumpTimer);[audioTrack,cameraTrack,screenTrack].forEach(t=>t?.stop());cameraStream?.getTracks().forEach(t=>t.stop());peers.forEach(p=>p.pc.close());});
  localStatus();render();updateStage();
  const roomParams=new URLSearchParams(location.search);
  const teacherHost=admin&&roomParams.get('teacherhost')==='1';
  const autoJoin=admin&&(roomParams.get('autojoin')==='1'||roomParams.get('teacherapp')==='1');
  if(teacherHost){
    document.body.classList.add('teacher-host-room');
    const back=$('.roomhead a');
    if(back){back.textContent='Teacher meeting';back.href='javascript:void(0)';back.style.visibility='hidden';}
  }
  if(autoJoin){
    setTimeout(()=>join().catch?.(()=>{}),250);
  }
}
