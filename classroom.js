import {htmlText,uiText} from './web_i18n.js';
// Math Studio classroom v22: peer-to-peer WebRTC camera/microphone/screen sharing
// plus an optional shared annotation/whiteboard layer.
export async function mountClassroom({api,toast,me,settings,classes,esc,tr=s=>s,localize=()=>{}}) {
  const $=s=>document.querySelector(s);
  const cid=Number(new URLSearchParams(location.search).get('id'));
  const cl=classes.find(c=>c.id===cid);
  const admin=me.role==='admin';
  const instant=cl?.class_kind==='instant';
  const groupChatId=cl?.class_kind==='group'?cl.group_chat_id:null;
  if(!cl) throw new Error(tr("ui.class_not_found"));

  $('#app').classList.add('roommain');
  $('#footer').classList.add('hidden');
  $('#app').innerHTML=`
    <div class="roomhead">
      <div><p class="eyebrow" data-i18n="ui.live_classroom">Live classroom</p><h1><span data-no-translate>${esc(cl.title)}</span></h1></div>
      <a href="${instant?'/join':admin?'/teacher':'/account'}"><span data-i18n="ui.back_to">Back to</span> ${instant?htmlText("ui.join_meeting_2"):admin?htmlText("ui.teaching_calendar"):htmlText("ui.my_lessons_2")}</a>
    </div>
    <section id="prejoin" class="panel prejoin-card">
      <div>
        <h2 data-i18n="ui.ready_to_join">Ready to join?</h2>
        <p data-i18n="ui.your_camera_and_microphone_start_off_you_can_turn_them_on_after_joining">Your camera and microphone start off. You can turn them on after joining.</p>
        <div id="mediaPreflight" class="media-preflight" role="status"></div>
        <div class="actions"><button id="checkMedia" type="button" class="secondary small" data-i18n="ui.check_camera_microphone">Check camera & microphone</button></div>
        <p class="meta">${htmlText('media.other_device','http://10.x.x.x:5051')}</p>
      </div>
      <button id="join" data-i18n="ui.join_classroom">Join classroom</button>
      <p class="meta" id="joinerror" role="status"></p>
    </section>
    <section id="room" class="hidden live-room">
      <div id="roomnotice" class="notice" role="status"></div><div id="mediaLinkStatus" class="media-link-status" role="status" data-i18n="ui.media_link_waiting_for_another_participant">Media link: waiting for another participant.</div>
      <div class="roomcontrols" aria-label="Call controls" data-i18n-aria-label="ui.call_controls">
        <button id="mic" class="secondary" aria-pressed="false" data-i18n="ui.unmute">Unmute</button>
        <button id="camera" class="secondary" aria-pressed="false" data-i18n="ui.start_camera">Start camera</button>
        <button id="share" class="secondary" aria-pressed="false" data-i18n="ui.share_screen">Share screen</button>
        <button id="whiteboard" class="secondary" aria-pressed="false" data-i18n="ui.whiteboard">Whiteboard</button>
        <button id="sound" class="secondary" data-i18n="ui.enable_sound">Enable sound</button>
        <button id="leave" class="danger" data-i18n="ui.leave">Leave</button>
        ${admin?"<button id=\"end\" class=\"secondary\" data-i18n=\"ui.end_class_for_everyone\">End class for everyone</button>":''}
      </div>
      <div class="meeting-layout">
        <div class="meeting-main">
          <section id="shareStage" class="share-stage hidden" aria-label="Shared screen or whiteboard" data-i18n-aria-label="ui.shared_screen_or_whiteboard">
            <div class="shared-media" id="sharedMedia">
              <video id="presentation" class="hidden" autoplay playsinline muted></video>
              <img id="nativePresentation" class="hidden native-presentation" alt="Teacher shared screen" data-i18n-alt="ui.teacher_shared_screen">
              <canvas id="board" width="1600" height="900" aria-label="Live annotation overlay" data-i18n-aria-label="ui.live_annotation_overlay"></canvas>
              <div class="share-stage-label"><span id="stageTitle" class="stage-title" data-i18n="ui.whiteboard">Whiteboard</span><span data-i18n="ui.annotations_are_a_separate_live_overlay">Annotations are a separate live overlay</span></div>
              <div class="annotation-toolbar meeting-taskbar" aria-label="Annotation tools" data-i18n-aria-label="ui.annotation_tools">
                ${[['pen',htmlText("ui.pen")],['line',htmlText("ui.line")],['circle',htmlText("ui.circle")],['rect',htmlText("ui.rectangle")],['text',htmlText("ui.text")],['erase',htmlText("ui.eraser")]].map(([t,n])=>`<button data-tool="${t}" class="small secondary ${t==='pen'?'active':''}" aria-pressed="${t==='pen'}">${n}</button>`).join('')}
                <input type="color" id="color" value="#09695f" aria-label="Ink colour" data-i18n-aria-label="ui.ink_colour">
                <select id="width" aria-label="Line thickness" data-i18n-aria-label="ui.line_thickness"><option value="2" data-i18n="ui.thin">Thin</option><option value="4" selected data-i18n="ui.medium">Medium</option><option value="7" data-i18n="ui.thick">Thick</option></select>
                <button id="grid" class="small secondary" data-i18n="ui.grid_on">Grid on</button>
                <button id="undo" class="small secondary" data-i18n="ui.undo">Undo</button>
                <button id="clear" class="small secondary" data-i18n="ui.clear">Clear</button>
                <button id="save" class="small secondary" data-i18n="ui.snapshot">Snapshot</button>
              </div>
            </div>
            <div class="equationbar" id="equationbar">
              <div><label for="function" data-i18n="ui.graph">Graph</label><select id="function"><option value="quadratic">y = a(x − h)² + k</option><option value="linear">y = a(x − h) + k</option><option value="sine">y = a sin(x − h) + k</option><option value="absolute">y = a|x − h| + k</option></select></div>
              ${['a','h','k'].map(k=>`<div><label for="coef-${k}">${k}</label><input type="number" id="coef-${k}" min="-10" max="10" step="0.1" value="${k==='a'?1:0}"></div>`).join('')}
              <button id="plot" class="small" data-i18n="ui.add_graph">Add graph</button>
            </div>
            <div class="boardstatus"><span id="boardstatus" data-i18n="ui.connecting">Connecting…</span><span id="presenterlabel" data-i18n="ui.whiteboard">Whiteboard</span></div>
          </section>

          <section>
            <div class="meeting-section-title"><div><h2 data-i18n="ui.classroom">Classroom</h2><p class="meta" id="galleryHint" data-i18n="ui.camera_tiles_appear_here">Camera tiles appear here.</p></div></div>
            <div class="video-gallery" id="gallery">
              <article class="video-card local-video-card" id="localTile">
                <div class="video-frame"><video id="local" autoplay playsinline muted></video><div class="camera-placeholder" id="localPlaceholder"><span data-no-translate>${esc(me.name.slice(0,1).toUpperCase())}</span></div></div>
                <div class="video-label"><span data-i18n="ui.you">You</span><small id="localStatus" data-i18n="ui.mic_off_camera_off">Mic off · Camera off</small></div>
              </article>
            </div>
          </section>
        </div>

        <aside class="room-aside">
          <div class="participant-head"><h3 data-i18n="ui.participants">Participants</h3><span class="tag gray" id="participantCount">1</span></div>
          <div id="peoplelist" class="people-list"></div>
          ${admin?"<label class=\"switchrow\"><input type=\"checkbox\" id=\"allow\"> <span data-i18n=\"ui.allow_students_to_draw\">Allow students to draw</span></label>":''}
          <p class="inline-note" data-i18n="ui.teachers_can_mute_a_participant_for_privacy_allowing_their_microphone_again_does_not_turn_">Teachers can mute a participant. For privacy, allowing their microphone again does not turn it on automatically; the participant must unmute themselves.</p>
          <section class="room-chat" aria-label="Classroom chat" data-i18n-aria-label="ui.classroom_chat">
            <div class="chat-head"><div><h3>${instant?htmlText("ui.meeting_chat"):groupChatId?htmlText("ui.group_chat"):htmlText("ui.class_messages")}</h3><span id="chatStatus">${instant?htmlText("ui.live_only"):htmlText("ui.saved")}</span></div>${instant?'':`<a href="${groupChatId?`/messages?group=${groupChatId}`:`/messages?id=${cid}`}" data-i18n="ui.open_full_chat">Open full chat</a>`}</div>
            <div id="chatMessages" class="chat-messages" role="log" aria-live="polite" aria-relevant="additions"><div class="chat-empty">${instant?htmlText("ui.messages_in_an_instant_meeting_are_live_for_this_session"):htmlText("ui.messages_are_saved_with_this_lesson_and_remain_available_outside_the_meeting")}</div></div>
            <form id="chatForm" class="chat-form"><label class="sr-only" for="chatInput" data-i18n="ui.message">Message</label><div><textarea id="chatInput" maxlength="1000" rows="1" autocomplete="off" placeholder="Message the class…" data-i18n-placeholder="ui.message_the_class"></textarea><button type="submit" class="small" data-i18n="ui.send">Send</button></div><p class="inline-note" data-i18n="ui.valid_resource_codes_become_clickable_file_links_automatically">Valid resource codes become clickable file links automatically.</p></form>
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
  const note=text=>{uiText($('#roomnotice'),text);};
  const initials=name=>(String(name||'?').trim().split(/\s+/).map(x=>x[0]).join('').slice(0,2)||'?').toUpperCase();
  const chatTime=seconds=>new Intl.DateTimeFormat(undefined,{hour:'numeric',minute:'2-digit'}).format(new Date(seconds*1000));
  function chatBody(message){
    let html=esc(message.text);
    for(const item of message.codes||[]){
      const safe=item.code.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
      html=html.replace(new RegExp(`\\b${safe}\\b`,'gi'),`<a class="chat-resource-code" href="/resources?code=${encodeURIComponent(item.code)}" title="Open ${esc(item.label||tr("ui.class_resources"))}"><strong>${esc(item.code)}</strong><span data-i18n="ui.open_files">Open files →</span></a>`);
    }
    return html.replace(/\n/g,'<br>');
  }
  function renderChat(){
    const box=$('#chatMessages');if(!box)return;
    if(!chatMessages.length){box.innerHTML=`<div class="chat-empty">${instant?htmlText("ui.no_messages_yet_instant_meeting_chat_lasts_for_this_live_session"):htmlText("ui.no_messages_yet_this_chat_stays_with_the_lesson_before_and_after_the_live_meeting")}</div>`;return;}
    const nearBottom=box.scrollHeight-box.scrollTop-box.clientHeight<90;
    box.innerHTML=chatMessages.map(m=>`<article class="chat-message ${m.role==='admin'?'teacher':''}"><div class="chat-meta"><strong>${esc(m.name)}</strong>${m.role==='admin'?"<span class=\"tag\" data-i18n=\"ui.teacher\">Teacher</span>":''}<time>${chatTime(m.at)}</time></div><div class="chat-text">${chatBody(m)}</div></article>`).join('');
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
    if(!list.length){uiText(el,tr("ui.media_link_waiting_for_another_participant"));el.dataset.state='waiting';return;}
    const states=list.map(p=>p.pc.connectionState||p.pc.iceConnectionState);
    if(states.every(x=>x==='connected')){uiText(el,tr("ui.media_link_connected_to_arg0_participantarg1",list.length,list.length===1?'':'s'));el.dataset.state='connected';}
    else if(states.some(x=>x==='failed')){uiText(el,relayConfigured?tr("ui.media_link_failed_and_is_retrying_through_ice_turn"):tr("ui.direct_media_link_failed_and_is_retrying_if_the_devices_are_on_different_networks_configur"));el.dataset.state='failed';}
    else if(states.some(x=>x==='disconnected')){uiText(el,tr('media.reconnecting'));el.dataset.state='connecting';}
    else{uiText(el,tr("ui.media_link_connecting"));el.dataset.state='connecting';}
  }
  function secureMediaAvailable(){return !!(window.isSecureContext&&navigator.mediaDevices?.getUserMedia&&window.RTCPeerConnection);}
  function mediaError(kind,ex){
    if(!window.isSecureContext)return tr('media.https',kind);
    if(ex?.name==='NotAllowedError')return tr('media.permission',kind);
    if(ex?.name==='NotFoundError')return tr('media.not_found',kind);
    if(ex?.name==='NotReadableError')return tr('media.busy',kind);
    if(ex?.name==='OverconstrainedError')return tr('media.quality',kind);
    return tr('media.unavailable',kind,ex?.message||tr('media.unknown'));
  }
  async function permissionState(name){
    try{if(!navigator.permissions?.query)return 'unknown';const r=await navigator.permissions.query({name});return r.state||'unknown';}catch{return 'unknown';}
  }
  async function renderMediaPreflight(extra=''){
    const box=$('#mediaPreflight');if(!box)return;
    const secure=window.isSecureContext, gum=!!navigator.mediaDevices?.getUserMedia, display=!!navigator.mediaDevices?.getDisplayMedia, rtc=!!window.RTCPeerConnection;
    const [camPerm,micPerm]=await Promise.all([permissionState('camera'),permissionState('microphone')]);
    const row=(ok,label,detail='')=>`<div class="media-check-row ${ok?'ok':'bad'}"><span>${ok?'✓':'!'}</span><div><strong>${label}</strong>${detail?`<small>${esc(detail)}</small>`:''}</div></div>`;
    let html=row(secure,tr("ui.secure_connection"),secure?location.origin:tr("ui.this_page_is_http_use_the_https_classroom_link"));
    html+=row(gum&&rtc,tr("ui.camera_microphone_apis"),gum&&rtc?tr("ui.available_in_this_browser"):tr("ui.unavailable_on_this_origin_browser"));
    html+=row(display,tr("ui.screen_share_api"),display?tr("ui.available_when_the_browser_device_permits_it"):tr("ui.this_browser_device_does_not_expose_web_screen_sharing"));
    html+=row(camPerm!=='denied',tr("ui.camera_permission"),camPerm==='granted'?tr('media.allowed'):camPerm==='denied'?tr("ui.blocked_in_browser_settings"):tr("ui.will_ask_when_used"));
    html+=row(micPerm!=='denied',tr("ui.microphone_permission"),micPerm==='granted'?tr('media.allowed'):micPerm==='denied'?tr("ui.blocked_in_browser_settings"):tr("ui.will_ask_when_used"));
    if(extra)html+=`<div class="media-check-result">${esc(extra)}</div>`;
    box.innerHTML=html;
  }
  async function testLocalMedia(){
    const b=$('#checkMedia');b.disabled=true;
    try{
      if(!window.isSecureContext)throw new Error(tr("ui.open_the_https_classroom_address_first"));
      if(!navigator.mediaDevices?.getUserMedia)throw new Error(tr("ui.this_browser_does_not_provide_camera_microphone_access_here"));
      const stream=await navigator.mediaDevices.getUserMedia({video:true,audio:true});
      const cam=stream.getVideoTracks()[0],mic=stream.getAudioTracks()[0];
      const camName=cam?.label||'camera';const micName=mic?.label||'microphone';
      stream.getTracks().forEach(t=>t.stop());
      await renderMediaPreflight(`Device test passed: ${camName} and ${micName} opened successfully.`);
      toast(tr("ui.camera_and_microphone_opened_successfully_on_this_device"));
    }catch(ex){await renderMediaPreflight(mediaError(tr("ui.media_devices"),ex));toast(mediaError(tr("ui.media_devices"),ex));}
    finally{b.disabled=false;}
  }
  $('#checkMedia').onclick=testLocalMedia;
  renderMediaPreflight().catch(()=>{});

  function flagButton(id,on,onText,offText){const b=$(id);uiText(b,on?onText:offText);b.classList.toggle('active',on);b.setAttribute('aria-pressed',String(on));}
  function localStatus(){
    const mic=forcedMute?tr("ui.muted_by_teacher"):audioTrack?.enabled?tr("ui.mic_on"):tr("ui.mic_off");
    const cam=cameraTrack?.enabled?tr("ui.camera_on"):tr("ui.camera_off");
    uiText($('#localStatus'),tr('media.local_status',mic,cam));
    $('#localPlaceholder').classList.toggle('hidden',!!cameraTrack?.enabled);
    const micBtn=$('#mic');
    micBtn.disabled=forcedMute;
    if(forcedMute){uiText(micBtn,tr("ui.muted_by_teacher"));micBtn.classList.remove('active');micBtn.setAttribute('aria-pressed','false');}
    else flagButton('#mic',!!audioTrack?.enabled,tr("ui.mute"),tr("ui.unmute"));
    flagButton('#camera',!!cameraTrack?.enabled,tr("ui.stop_camera"),tr("ui.start_camera"));
  }
  async function syncMediaState(){
    if(!joined)return;
    try{
      const r=await post('media-state',{mic_on:!!audioTrack?.enabled&&!forcedMute,camera_on:!!cameraTrack?.enabled});
      if(r.forcedMute&&!forcedMute){forcedMute=true;if(audioTrack)audioTrack.enabled=false;localStatus();}
    }catch(ex){if(ex.status!==409)note(tr('media.status_failed',ex.message));}
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
    if(status)uiText(status,tr(nativeShare.active?tr("ui.drawing_over_the_teacher_desktop_share"):presenter?tr("ui.drawing_over_the_live_shared_screen"):viewMode==='whiteboard'?tr("ui.shared_whiteboard"):tr("ui.start_screen_sharing_or_open_the_whiteboard_first")));
  }
  function render(){
    renderInto(ctx,!presenter&&!nativeShare.active&&viewMode==='whiteboard',draft);
    uiText($('#grid'),board.background==='grid'?tr("ui.grid_on"):tr("ui.grid_off"));
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
    uiText($('#stageTitle'),nativeActive?tr("ui.teacher_is_sharing_the_desktop"):presenter?(presenter===peer?tr("ui.you_are_sharing_your_screen"):tr('media.person_sharing',people.find(p=>p.id===presenter)?.name||tr('media.participant'))):tr("ui.shared_whiteboard"));
    uiText($('#presenterlabel'),nativeActive?tr("ui.teacher_desktop_share"):presenter?tr("ui.live_screen_share"):tr("ui.shared_whiteboard"));
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
    if(!joined){toast(tr("ui.join_the_classroom_first"));return;}
    if(!presenter&&!nativeShare.active&&viewMode!=='whiteboard'){toast(tr("ui.start_screen_sharing_or_open_the_whiteboard_first_2"));return;}
    if(annotatorWindow&&!annotatorWindow.closed){try{annotatorWindow.focus();}catch{}return;}
    let w=null;
    try{
      if(window.documentPictureInPicture?.requestWindow){
        w=await window.documentPictureInPicture.requestWindow({width:620,height:470});
      }else{
        w=window.open('','MathStudioAnnotator','popup=yes,width=620,height=470,resizable=yes');
        if(!w)throw new Error(tr("ui.the_browser_blocked_the_annotation_window_allow_pop_ups_for_mathstudio_and_try_again"));
      }
    }catch(ex){toast(tr('media.annotator_failed',ex.message));return;}
    annotatorWindow=w;const d=w.document;d.title=tr("ui.mathstudio_annotations");
    d.head.innerHTML=`<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
      *{box-sizing:border-box}html,body{margin:0;background:#102a33;color:#fff;font:14px/1.35 system-ui,-apple-system,"Segoe UI",sans-serif;overflow:hidden}button,select,input{font:inherit}button{border:1px solid #55717a;border-radius:8px;background:#173b45;color:#fff;padding:7px 10px;cursor:pointer}button.active{background:#bce7d9;color:#102a33;border-color:#bce7d9}.bar{height:48px;display:flex;align-items:center;gap:6px;padding:6px 8px;background:#102a33;overflow-x:auto;white-space:nowrap}.bar input[type=color]{width:34px;height:34px;padding:1px;border:1px solid #6c858c;border-radius:7px;background:transparent}.bar select{height:34px;background:#173b45;color:#fff;border:1px solid #55717a;border-radius:7px}.stage{position:relative;width:100%;aspect-ratio:16/9;background:#07171c;overflow:hidden}.stage video,.stage canvas{position:absolute;inset:0;width:100%;height:100%}.stage video{object-fit:contain;background:#07171c}.stage canvas{touch-action:none}.hidden{display:none!important}.foot{height:32px;padding:7px 10px;background:#102a33;color:#c7dadd;font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    </style>`;
    d.body.innerHTML=`<div class="bar"><button data-atool="pen" class="active" data-i18n="ui.pen">Pen</button><button data-atool="line" data-i18n="ui.line">Line</button><button data-atool="circle" data-i18n="ui.circle">Circle</button><button data-atool="rect" data-i18n="ui.rectangle">Rectangle</button><button data-atool="erase" data-i18n="ui.eraser">Eraser</button><input id="aColor" type="color" value="${annotatorColor}" title="Ink colour" data-i18n-title="ui.ink_colour"><select id="aWidth" aria-label="Line thickness" data-i18n-aria-label="ui.line_thickness"><option value="2" data-i18n="ui.thin">Thin</option><option value="4" selected data-i18n="ui.medium">Medium</option><option value="7" data-i18n="ui.thick">Thick</option></select><button id="aUndo" data-i18n="ui.undo">Undo</button><button id="aClear" data-i18n="ui.clear">Clear</button><button id="aBack">MathStudio</button></div><div class="stage"><video id="annotatorVideo" autoplay playsinline muted></video><canvas id="annotatorCanvas" width="1600" height="900"></canvas></div><div class="foot" id="annotatorStatus" data-i18n="ui.floating_annotations">Floating annotations</div>`;
    localize(d.body);
    annotatorCanvas=d.getElementById('annotatorCanvas');annotatorCtx=annotatorCanvas.getContext('2d');
    d.querySelectorAll('[data-atool]').forEach(b=>b.addEventListener('click',()=>{annotatorTool=b.dataset.atool;d.querySelectorAll('[data-atool]').forEach(x=>x.classList.toggle('active',x===b));}));
    d.getElementById('aColor').addEventListener('input',ev=>{annotatorColor=ev.target.value;});
    d.getElementById('aWidth').addEventListener('change',ev=>{annotatorWidth=Number(ev.target.value)||4;});
    d.getElementById('aUndo').addEventListener('click',async()=>{if(!canDraw())return;const id=[...myShapes].reverse().find(id=>board.shapes.some(s=>s.id===id));if(id&&await saveBoard({...board,shapes:board.shapes.filter(s=>s.id!==id)}))myShapes=myShapes.filter(x=>x!==id);});
    d.getElementById('aClear').addEventListener('click',()=>{if(canDraw()&&confirm(tr("ui.clear_the_shared_annotations_for_everyone")))saveBoard({...board,shapes:[]});});
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
    toast(window.documentPictureInPicture?.window===w?tr("ui.floating_annotator_is_always_on_top_while_you_change_tabs"):tr("ui.floating_annotator_opened_keep_this_small_window_visible_while_changing_tabs"));
  }
  async function saveBoard(next){if(saving)return false;saving=true;uiText($('#boardstatus'),tr('media.saving'));try{const r=await post('board',{version,board:next});board=next;version=r.version;render();return true;}catch(ex){toast(ex.message);return false;}finally{saving=false;updateBoardStatus();}}
  function updateBoardStatus(){uiText($('#boardstatus'),!joined?tr('media.disconnected'):saving?tr('media.saving'):drawingAllowed?tr("ui.draw_with_mouse_touch_or_pen"):tr('media.viewing_only'));}
  function fresh(type){return {id:crypto.randomUUID(),type,color:$('#color').value,width:Number($('#width').value)};}
  function canDraw(){if(!joined||saving||(!presenter&&!nativeShare.active&&viewMode!=='whiteboard'))return false;if(!drawingAllowed){toast(tr("ui.the_teacher_has_not_enabled_student_drawing"));return false;}return true;}
  async function addShape(s){if(await saveBoard({...board,shapes:[...board.shapes,s]}))myShapes.push(s.id);}
  canvas.addEventListener('pointerdown',async ev=>{if(ev.button!==0&&ev.pointerType==='mouse')return;if(!canDraw())return;ev.preventDefault();const [x,y]=coordinates(ev);if(tool==='text'){const text=prompt(tr("ui.text_or_math_symbols"));if(text?.trim())await addShape({...fresh('text'),x,y,text:text.trim().slice(0,300)});return;}if(tool==='erase'){const found=[...board.shapes].reverse().find(s=>hit(s,x,y));if(found)await saveBoard({...board,shapes:board.shapes.filter(s=>s.id!==found.id)});return;}canvas.setPointerCapture(ev.pointerId);draft=tool==='pen'?{...fresh(tool),points:[[x,y]]}:{...fresh(tool),x,y,x2:x,y2:y};render();});
  canvas.addEventListener('pointermove',ev=>{if(!draft)return;ev.preventDefault();const [x,y]=coordinates(ev);if(draft.type==='pen'){if(draft.points.length<1500)draft.points.push([x,y]);}else{draft.x2=x;draft.y2=y;}render();});
  const finish=async()=>{if(!draft)return;const s=draft;draft=null;await addShape(s);render();};canvas.addEventListener('pointerup',finish);canvas.addEventListener('pointercancel',()=>{draft=null;render();});
  function distance(x,y,x1,y1,x2,y2){const a=(x-x1)*W,b=(y-y1)*H,c=(x2-x1)*W,d=(y2-y1)*H,t=Math.max(0,Math.min(1,(a*c+b*d)/(c*c+d*d||1)));return Math.hypot(a-t*c,b-t*d);}
  function hit(s,x,y){if(s.type==='pen')return s.points.some((p,i)=>distance(x,y,p[0],p[1],...(s.points[i+1]||p))<20);if(s.type==='line')return distance(x,y,s.x,s.y,s.x2,s.y2)<20;if(s.type==='circle')return Math.abs(Math.hypot((x-s.x)*W,(y-s.y)*H)-Math.hypot((s.x2-s.x)*W,(s.y2-s.y)*H))<20;if(s.type==='rect')return [[s.x,s.y,s.x2,s.y],[s.x2,s.y,s.x2,s.y2],[s.x2,s.y2,s.x,s.y2],[s.x,s.y2,s.x,s.y]].some(p=>distance(x,y,...p)<20);if(s.type==='text')return x>=s.x&&x<=s.x+.4&&Math.abs(y-s.y)<.05;return false;}
  document.querySelectorAll('[data-tool]').forEach(b=>b.onclick=()=>{tool=b.dataset.tool;document.querySelectorAll('[data-tool]').forEach(x=>{x.classList.toggle('active',x===b);x.setAttribute('aria-pressed',String(x===b));});});
  $('#grid').onclick=()=>{if(canDraw())saveBoard({...board,background:board.background==='grid'?'blank':'grid'});};
  $('#plot').onclick=()=>{if(!canDraw())return;const coeffs={};for(const key of ['a','h','k']){coeffs[key]=Number($('#coef-'+key).value);if(!Number.isFinite(coeffs[key])||Math.abs(coeffs[key])>10){toast(tr("ui.graph_values_must_be_between_10_and_10"));return;}}addShape({...fresh('graph'),fn:$('#function').value,...coeffs});};
  $('#undo').onclick=async()=>{if(!canDraw())return;const id=[...myShapes].reverse().find(id=>board.shapes.some(s=>s.id===id));if(id&&await saveBoard({...board,shapes:board.shapes.filter(s=>s.id!==id)}))myShapes=myShapes.filter(x=>x!==id);};
  $('#clear').onclick=()=>{if(canDraw()&&confirm(tr("ui.clear_the_shared_annotations_for_everyone")))saveBoard({...board,shapes:[]});};
  $('#save').onclick=()=>{const out=document.createElement('canvas');out.width=W;out.height=H;const x=out.getContext('2d');x.fillStyle='white';x.fillRect(0,0,W,H);const v=$('#presentation');if(presenter&&v.readyState>=2&&v.videoWidth){const scale=Math.min(W/v.videoWidth,H/v.videoHeight),vw=v.videoWidth*scale,vh=v.videoHeight*scale;x.fillStyle='#14272e';x.fillRect(0,0,W,H);x.drawImage(v,(W-vw)/2,(H-vh)/2,vw,vh);}x.drawImage(canvas,0,0);const a=document.createElement('a');a.href=out.toDataURL('image/png');a.download='math-class-'+cid+'.png';a.click();};

  async function makeOffer(id,p,iceRestart=false){
    if(!joined||!p||p.pc.signalingState==='closed')return;
    if(p.pc.signalingState!=='stable'||p.negotiating){if(p){p.needsNegotiation=true;p.needsIceRestart=p.needsIceRestart||iceRestart;}return;}
    p.negotiating=true;p.needsNegotiation=false;const restart=iceRestart||p.needsIceRestart;p.needsIceRestart=false;
    try{console.info('[MathStudio WebRTC] sending offer to',id);const offer=await p.pc.createOffer(restart?{iceRestart:true}:undefined);await p.pc.setLocalDescription(offer);await post('signal',{to:id,signal:{description:p.pc.localDescription.toJSON()}});}
    catch(ex){p.needsNegotiation=true;note(tr('media.retrying',ex.message));}
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
    if(forcedMute){toast(tr("ui.your_teacher_has_muted_your_microphone"));return;}
    try{
      if(!secureMediaAvailable())throw new Error('secure-context');
      if(!audioTrack){audioTrack=(await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true},video:false})).getAudioTracks()[0];await replace('audio',audioTrack);}else audioTrack.enabled=!audioTrack.enabled;
      localStatus();await syncMediaState();
    }catch(ex){toast(ex.message==='secure-context'?mediaError(tr('media.microphone'),{}):mediaError(tr('media.microphone'),ex));}
  };
  $('#camera').onclick=async()=>{
    const button=$('#camera');button.disabled=true;
    try{
      if(!secureMediaAvailable())throw new Error('secure-context');
      if(cameraTrack){await stopCamera();toast(tr("ui.camera_stopped"));return;}
      let stream;
      try{stream=await navigator.mediaDevices.getUserMedia({video:{width:{ideal:1280},height:{ideal:720},frameRate:{ideal:24,max:30}},audio:false});}
      catch(ex){if(ex?.name==='OverconstrainedError')stream=await navigator.mediaDevices.getUserMedia({video:true,audio:false});else throw ex;}
      const track=stream.getVideoTracks()[0];if(!track)throw new DOMException(tr("ui.no_camera_track_was_returned"),'NotFoundError');
      cameraStream=stream;cameraTrack=track;cameraTrack.enabled=true;cameraTrack.onended=()=>{if(cameraTrack===track)stopCamera().catch(()=>{});};
      const local=$('#local');local.srcObject=stream;await local.play().catch(()=>{});await replace('camera',cameraTrack);
      localStatus();await syncMediaState();toast(tr("ui.camera_started"));
    }catch(ex){if(cameraStream){cameraStream.getTracks().forEach(t=>t.stop());cameraStream=null;}cameraTrack=null;$('#local').srcObject=null;localStatus();toast(ex.message==='secure-context'?mediaError(tr("ui.camera"),{}):mediaError(tr("ui.camera"),ex));}
    finally{button.disabled=false;}
  };
  async function stopShare(){
    const s=screenStream;screenStream=null;screenTrack=null;if(s)s.getTracks().forEach(t=>{t.onended=null;t.stop();});await replace('screen',null);
    if(joined){try{await post('presenter',{active:false});}catch{}}
    if(presenter===peer)presenter=null;uiText($('#share'),tr("ui.share_screen"));$('#share').classList.remove('active');$('#share').setAttribute('aria-pressed','false');updateStage();
  }
  $('#share').onclick=async()=>{
    if(screenTrack){await stopShare();return;}
    if(!window.isSecureContext||!navigator.mediaDevices?.getDisplayMedia){toast(tr("ui.screen_sharing_needs_https_here_run_start_student_website_bat_and_use_its_https_link_in_de"));return;}
    let stream;
    try{
      stream=await navigator.mediaDevices.getDisplayMedia({video:{frameRate:{ideal:15,max:30}},audio:false,preferCurrentTab:false,selfBrowserSurface:'exclude',surfaceSwitching:'include'});
      await post('presenter',{active:true});screenStream=stream;screenTrack=stream.getVideoTracks()[0];screenTrack.onended=()=>stopShare();await replace('screen',screenTrack);presenter=peer;viewMode='call';uiText($('#share'),tr("ui.stop_sharing"));$('#share').classList.add('active');$('#share').setAttribute('aria-pressed','true');updateStage();toast(tr("ui.screen_sharing_started_for_true_desktop_annotations_share_entire_screen_and_run_the_window"));
    }catch(ex){stream?.getTracks().forEach(t=>t.stop());if(ex.name!=='NotAllowedError')toast(tr('media.share_failed',ex.message));}
  };
  $('#whiteboard').onclick=()=>{if(presenter||nativeShare.active){toast(tr("ui.a_live_screen_share_is_being_shown_you_can_draw_directly_over_it"));return;}viewMode=viewMode==='whiteboard'?'call':'whiteboard';updateStage();};
  $('#sound').onclick=()=>{document.querySelectorAll('audio,video').forEach(v=>v.play().catch(()=>{}));toast(tr("ui.audio_playback_enabled"));};
  $('#allow')?.addEventListener('change',async()=>{try{await post('permissions',{drawing:$('#allow').checked});}catch(ex){toast(ex.message);}});
  $('#chatForm')?.addEventListener('submit',ev=>{ev.preventDefault();sendChat($('#chatInput').value);});
  $('#chatInput')?.addEventListener('keydown',ev=>{if(ev.key==='Enter'&&!ev.shiftKey&&!ev.isComposing){ev.preventDefault();sendChat(ev.currentTarget.value);}});
  $('#end')?.addEventListener('click',async()=>{if(!confirm(tr("ui.end_the_class_and_disconnect_everyone")))return;try{await api('/api/admin/class-action',{class_id:cid,action:'end'});await leave();location.href='/teacher';}catch(ex){toast(ex.message);}});

  function remoteTile(person){
    const div=document.createElement('article');div.className='video-card';div.id='peer-'+person.id;
    div.innerHTML=`<div class="video-frame"><video autoplay playsinline muted></video><div class="camera-placeholder"><span data-no-translate>${esc(initials(person.name))}</span></div></div><audio autoplay></audio><div class="video-label"><span><span data-no-translate>${esc(person.name)}</span></span><small data-i18n="ui.connecting">Connecting…</small></div>`;
    $('#gallery').append(div);return div;
  }
  function updateTile(person,p){
    if(!p)return;const small=p.element.querySelector('small'),ph=p.element.querySelector('.camera-placeholder');
    const mic=person.forced_mute?tr("ui.muted_by_teacher"):person.mic_on?tr("ui.mic_on"):tr("ui.mic_off");
    const video=p.element.querySelector('video');
    const hasFrames=!!(video&&video.readyState>=2&&video.videoWidth>0&&video.videoHeight>0);
    const cameraReady=!!(p.cameraTrack&&p.cameraTrack.readyState==='live'&&(p.cameraReady||hasFrames));
    uiText(small,`${mic} · ${person.camera_on?(cameraReady?tr("ui.camera_on"):(p.cameraWaitingSince&&Date.now()-p.cameraWaitingSince>6000?tr("ui.camera_reconnecting"):tr("ui.camera_connecting"))):tr("ui.camera_off")}`);
    ph.classList.toggle('hidden',!!person.camera_on&&cameraReady);
  }
  function renderPeople(){
    $('#participantCount').textContent=String(people.length);
    $('#peoplelist').innerHTML=people.map(person=>{
      const you=person.id===peer;
      const status=person.forced_mute?htmlText("ui.muted_by_teacher"):person.mic_on?htmlText("ui.mic_on"):htmlText("ui.mic_off");
      const hostControl=admin&&!you?`<button class="small secondary host-mute" data-peer="${esc(person.id)}" data-muted="${person.forced_mute?'1':'0'}">${person.forced_mute?htmlText("ui.allow_mic"):htmlText("ui.mute")}</button>`:'';
      return `<div class="person-row"><div><strong><span data-no-translate>${esc(person.name)}</span>${you?htmlText('media.you'):''}</strong><span>${person.role==='admin'?htmlText("ui.teacher"):htmlText("ui.student")} · ${status} · ${person.camera_on?htmlText("ui.camera_on"):htmlText("ui.camera_off")}</span></div>${hostControl}</div>`;
    }).join('');
    document.querySelectorAll('.host-mute').forEach(b=>b.onclick=async()=>{b.disabled=true;try{const muted=b.dataset.muted!=='1';await post('mute',{target:b.dataset.peer,muted});toast(muted?tr("ui.participant_muted"):tr("ui.participant_may_unmute_now"));await pollOnce();}catch(ex){toast(ex.message);}finally{b.disabled=false;}});
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
    pc.onicecandidateerror=ev=>{const detail=ev?.errorText||ev?.errorCode||tr('media.ice_error');note(tr('media.network_warning',detail)+(relayConfigured?'':tr('media.turn_required')));};
    pc.onconnectionstatechange=()=>{updateMediaLinkStatus();if(pc.connectionState==='connected'){clearTimeout(p.restartTimer);renderPeople();}else if(pc.connectionState==='failed'){note(tr("ui.reconnecting_participant_media"));requestNegotiation(person.id,p,true).catch(()=>{});}else if(pc.connectionState==='disconnected'){clearTimeout(p.restartTimer);p.restartTimer=setTimeout(()=>{if(pc.connectionState==='disconnected')requestNegotiation(person.id,p,true).catch(()=>{});},2500);}};
    pc.onsignalingstatechange=()=>{if(pc.signalingState==='stable'&&p.needsNegotiation&&peer<person.id)setTimeout(()=>makeOffer(person.id,p,p.needsIceRestart),50);};
    pc.ontrack=ev=>{
      const stream=new MediaStream([ev.track]);
      if(ev.track.kind==='audio'){const el=p.element.querySelector('audio');el.srcObject=stream;el.autoplay=true;el.playsInline=true;el.play().catch(()=>note(tr("ui.click_enable_sound_if_you_cannot_hear_the_class")));ev.track.onunmute=()=>el.play().catch(()=>{});return;}
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
      forcedMute=!!s.muted;if(forcedMute&&audioTrack)audioTrack.enabled=false;localStatus();await syncMediaState();toast(forcedMute?tr("ui.your_teacher_muted_your_microphone"):tr("ui.your_teacher_has_allowed_your_microphone_you_can_unmute_when_ready"));return;
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
        note(tr('media.signaling_error',signalFailures,ex.message));
        // Re-deliver the event on the next poll instead of acknowledging and losing it.
        if(signalFailures<5)delayedSignals.push(event);
      }
    }
    if(instant&&Array.isArray(r.chat)&&r.chat.length){for(const m of r.chat){if(!chatMessages.some(x=>x.id===m.id))chatMessages.push(m);}chatSeq=Math.max(chatSeq,Number(r.chatSeq||0));renderChat();}
    await fetchChat(false).catch(()=>{});
    seq=r.seq;renderPeople();updateMediaLinkStatus();updateBoardStatus();localStatus();
  }
  async function poll(){if(!joined||stopping)return;try{await pollOnce();roomPollFailures=0;}catch(ex){roomPollFailures++;if([401,403,404,409].includes(ex.status)){await leave();uiText($('#joinerror'),ex.message);return;}note(tr('media.room_reconnecting',ex.message));if(roomPollFailures>=8){await leave();uiText($('#joinerror'),tr("ui.connection_lost_rejoin_when_the_server_is_available"));return;}}if(joined)timer=setTimeout(poll,900);}
  async function join(){
    if(joined)return;$('#join').disabled=true;
    try{
      if(!window.RTCPeerConnection)throw new Error(tr("ui.this_browser_does_not_support_webrtc_use_a_current_chrome_edge_safari_or_firefox_browser"));
      const r=await api('/api/room/join',{class_id:cid});peer=r.peer;iceServers=r.iceServers;relayConfigured=!!r.relayConfigured;relayProvider=r.relayProvider||'';seq=0;delayedSignals=[];signalFailures=0;chatSeq=0;teacherCommandSeq=0;chatMessages=[];lastChatPoll=0;version=-1;joined=true;stopping=false;$('#prejoin').classList.add('hidden');$('#room').classList.remove('hidden');
      note(window.isSecureContext?(r.relayConfigured?tr('media.connected_turn',relayProvider||'TURN'):(r.relayError?tr('media.turn_failed',r.relayError):tr('media.no_turn'))):tr('media.http_room'));
      clearTimeout(mediaHealthTimer);checkRemoteMedia();await fetchChat(true).catch(()=>{});await poll();
    }catch(ex){uiText($('#joinerror'),ex.message);}finally{$('#join').disabled=false;}
  }
  async function leave(){
    if(stopping)return;stopping=true;clearTimeout(timer);clearTimeout(mediaHealthTimer);clearTimeout(nativePumpTimer);nativePumpTimer=null;closeFloatingAnnotator();const wasJoined=joined;joined=false;
    for(const t of [audioTrack,cameraTrack,screenTrack])if(t){t.onended=null;t.stop();}if(cameraStream)cameraStream.getTracks().forEach(t=>t.stop());cameraStream=null;audioTrack=cameraTrack=screenTrack=null;screenStream=null;$('#local').srcObject=null;
    for(const p of peers.values()){clearTimeout(p.restartTimer);p.pc.close();p.element.remove();}peers.clear();if(wasJoined){try{await post('leave');}catch{}}
    peer=null;presenter=null;nativeShare={active:false,seq:0,at:0};nativeFrameSeq=-1;forcedMute=false;people=[];chatSeq=0;teacherCommandSeq=0;chatMessages=[];relayConfigured=false;$('#desktopAnnotatorPanel')?.classList.add('hidden');renderChat();updateMediaLinkStatus();$('#presentation').srcObject=null;$('#room').classList.add('hidden');$('#prejoin').classList.remove('hidden');viewMode='call';stopping=false;
  }
  $('#join').onclick=join;$('#leave').onclick=leave;
  window.addEventListener('pagehide',()=>{closeFloatingAnnotator();joined=false;clearTimeout(timer);clearTimeout(mediaHealthTimer);clearTimeout(nativePumpTimer);[audioTrack,cameraTrack,screenTrack].forEach(t=>t?.stop());cameraStream?.getTracks().forEach(t=>t.stop());peers.forEach(p=>p.pc.close());});
  window.addEventListener('mathstudio-language',()=>{localStatus();renderPeople();updateMediaLinkStatus();renderAnnotator();if(annotatorWindow&&!annotatorWindow.closed)localize(annotatorWindow.document.body);renderMediaPreflight().catch(()=>{});});
  localStatus();render();updateStage();
  const roomParams=new URLSearchParams(location.search);
  const teacherHost=admin&&roomParams.get('teacherhost')==='1';
  const autoJoin=admin&&(roomParams.get('autojoin')==='1'||roomParams.get('teacherapp')==='1');
  if(teacherHost){
    document.body.classList.add('teacher-host-room');
    const back=$('.roomhead a');
    if(back){uiText(back,tr("ui.teacher_meeting"));back.href='javascript:void(0)';back.style.visibility='hidden';}
  }
  if(autoJoin){
    setTimeout(()=>join().catch?.(()=>{}),250);
  }
}
