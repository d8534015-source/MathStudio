window.__MATHSTUDIO_SCRIPT_STARTED__ = true;
window.__MATHSTUDIO_BUILD__ = 'v41.6-session-media-l10n';
const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let me=null,csrf='',settings={},posts=[],classes=[],schedule={lesson_types:[],availability:[],busy:[]};
let toastTimer,accountWatchTimer=null,accountWatchBusy=false,messageWatchTimer=null,globalRefreshTimer=null,globalRefreshBusy=false,globalRefreshSig='';
const siteLang=localStorage.getItem('mathstudio_lang')==='zh'?'zh':'en';
const SITE_ZH={
  'Media link: connected to 1 participant.':'媒体连接：已连接 1 位参与者。',
  'Media link: waiting for another participant.':'媒体连接：等待其他参与者。',
  'Media link: connecting…':'媒体连接：正在连接…',
  'Media network warning: TURN allocate request timed out.':'媒体网络警告：TURN 中继分配请求超时。',
  'Ready to join?':'准备加入课堂？',
  'Teacher meeting':'教师会议',
  'Media link':'媒体连接',
  'No video frames yet':'尚未收到视频画面',
  'Waiting for video':'正在等待视频',
  'Receiving video':'正在接收视频',
  'Camera reconnecting…':'摄像头正在重连…',
  'Camera connecting…':'摄像头正在连接…',
  'Mic on · Camera on':'麦克风开启 · 摄像头开启',
  'Mic off · Camera on':'麦克风关闭 · 摄像头开启',
  'Mic on · Camera off':'麦克风开启 · 摄像头关闭',
  'Mic off · Camera off':'麦克风关闭 · 摄像头关闭',
  'Grid':'网格', 'Blank':'空白',
  'Mute':'静音', 'Allow mic':'允许麦克风',
  'Participant muted.':'参与者已静音。',
  'Participant may unmute now.':'参与者现在可以自行解除静音。',
  'Camera and microphone opened successfully on this device.':'本设备上的摄像头与麦克风已成功打开。',
  'Teacher has not enabled student drawing.':'老师尚未允许学生绘画。',
  'The teacher has not enabled student drawing.':'老师尚未允许学生绘画。',
  'Reconnecting participant media…':'正在重新连接参与者媒体…',
  'Reconnecting to classroom…':'正在重新连接课堂…',
  'Media renegotiation is retrying…':'正在重试媒体协商…',
  'Could not update media status:':'无法更新媒体状态：',
  'Click Enable sound if you cannot hear the class.':'如果听不到声音，请点击“启用声音”。',
  'Connection lost. Rejoin when the server is available.':'连接已断开，服务器恢复后请重新加入。',
  'Clear the shared annotations for everyone?':'确定为所有人清空共享标注吗？',
  'Text or math symbols:':'请输入文字或数学符号：',
  'Graph values must be between −10 and 10.':'函数参数必须在 −10 到 10 之间。',
  'No text-based files in this bundle can be translated automatically.':'此资料包中没有可自动翻译的文本文件。',
  'Live classroom':'在线课堂',
  'Back to join meeting':'返回加入课堂',
  'Back to teaching calendar':'返回教学日历',
  'Back to my lessons':'返回我的课程',
  'Media link: waiting for another participant.':'媒体连接：等待其他参与者。',
  'Media link: connecting…':'媒体连接：正在连接…',
  'Call controls':'通话控制',
  'Unmute':'打开麦克风',
  'Mute':'关闭麦克风',
  'Start camera':'开启摄像头',
  'Stop camera':'关闭摄像头',
  'Share screen':'共享屏幕',
  'Stop sharing':'停止共享',
  'Whiteboard':'白板',
  'Enable sound':'启用声音',
  'Leave':'离开课堂',
  'End class for everyone':'结束所有人的课堂',
  'Shared screen or whiteboard':'共享屏幕或白板',
  'Teacher shared screen':'老师共享的屏幕',
  'Live annotation overlay':'实时标注图层',
  'Annotations are a separate live overlay':'标注显示在独立的实时图层上',
  'Annotation tools':'标注工具',
  'Pen':'画笔',
  'Line':'直线',
  'Circle':'圆形',
  'Rectangle':'矩形',
  'Text':'文字',
  'Eraser':'橡皮擦',
  'Ink colour':'画笔颜色',
  'Line thickness':'线条粗细',
  'Thin':'细',
  'Medium':'中',
  'Thick':'粗',
  'Grid on':'显示网格',
  'Grid off':'隐藏网格',
  'Undo':'撤销',
  'Clear':'清空',
  'Snapshot':'保存快照',
  'Graph':'函数图像',
  'Add graph':'添加函数图像',
  'Connecting…':'正在连接…',
  'Classroom':'课堂',
  'Camera tiles appear here.':'摄像头画面会显示在这里。',
  'You':'你',
  'Mic off · Camera off':'麦克风关闭 · 摄像头关闭',
  'Mic on':'麦克风已开启',
  'Mic off':'麦克风已关闭',
  'Camera on':'摄像头已开启',
  'Camera off':'摄像头已关闭',
  'Muted by teacher':'已被老师静音',
  'Camera reconnecting…':'摄像头正在重连…',
  'Camera connecting…':'摄像头正在连接…',
  'Participants':'参与者',
  'Allow students to draw':'允许学生标注',
  'Teachers can mute a participant. For privacy, allowing their microphone again does not turn it on automatically; the participant must unmute themselves.':'老师可以将参与者静音。为保护隐私，解除老师静音限制后，不会自动开启对方麦克风；参与者需要自己开启。',
  'Meeting chat':'会议聊天',
  'Group chat':'群聊',
  'Class messages':'课堂消息',
  'Live only':'仅限本次直播',
  'Saved':'已保存',
  'Open full chat':'打开完整聊天',
  'Messages in an instant meeting are live for this session.':'即时课堂消息只在本次课堂期间可见。',
  'Messages are saved with this lesson and remain available outside the meeting.':'消息会保存在该课程中，课后仍可查看。',
  'Message':'消息',
  'Message the class…':'发送课堂消息…',
  'Send':'发送',
  'Valid resource codes become clickable file links automatically.':'有效的资料码会自动变为可点击的文件链接。',
  'No messages yet. Instant meeting chat lasts for this live session.':'暂无消息。即时课堂聊天只在本次课堂中保留。',
  'No messages yet. This chat stays with the lesson before and after the live meeting.':'暂无消息。此聊天会在课前和课后保留。',
  'Teacher':'老师',
  'Student':'学生',
  'Guest':'访客',
  'Open files →':'打开文件 →',
  'class resources':'课堂资料',
  'Ready to join?':'准备加入课堂？',
  'Your camera and microphone start off. You can turn them on after joining.':'摄像头和麦克风默认关闭。加入后可自行开启。',
  'Check camera & microphone':'检查摄像头和麦克风',
  'Join classroom':'加入课堂',
  'For another device, use the':'在其他设备上，请使用',
  'address printed by':'显示的地址',
  'is not a secure browser origin.':'不是安全的浏览器来源。',
  'Your camera and microphone are off.':'你的摄像头和麦克风已关闭。',
  'Ready':'就绪',
  'Cancel':'取消',
  'Close':'关闭',
  'Dismiss':'关闭',
  'Join':'加入',
  'Leave meeting':'离开会议',
  'No camera':'没有摄像头',
  'No microphone':'没有麦克风',
  'Start sharing':'开始共享',
  'Stop sharing screen':'停止共享屏幕',
  'Share code':'分享码',

  'Home':'首页','Book a lesson':'预约课程','Join meeting':'加入课堂','Resources':'学习资料','Messages':'消息','My lessons':'我的课程','Log out':'退出登录','Log in':'登录','Guest':'访客','Leave guest session':'退出访客模式',
  'Personalized online math tutoring':'个性化在线数学辅导','Find a lesson time':'选择上课时间','View my lessons':'查看我的课程','Create an account':'创建账号','School & advanced math':'校内与进阶数学','Waterloo & AMC prep':'Waterloo 与 AMC 竞赛','Live online lessons':'在线实时课堂',
  'Online tutoring':'在线辅导','One place for lessons, practice, and class resources.':'课程、练习和课堂资料集中在一个地方。','Choose the right lesson':'选择合适的课程','Book around your schedule':'按照你的时间预约','Everything stays together':'所有内容集中管理',
  'What we can work on':'学习内容','Focused support for the math in front of you.':'针对当前数学学习提供专注支持。','School math':'校内数学','Contest math':'竞赛数学','Online lessons':'在线课程',
  'Understand the topic, not just the answer.':'理解知识，而不只是得到答案。','Build stronger problem-solving habits.':'培养更强的问题解决能力。','Book, meet, and keep resources together.':'预约、上课和资料管理都在一起。',
  'Instant classroom':'即时课堂','Join a meeting':'加入课堂','Meeting code':'课堂码','Your name':'你的姓名','Join meeting':'加入课堂','Joining as':'当前身份','Guest access does not require creating an account.':'访客加入无需创建账号。',
  'Class resources':'课堂资料','Download your files':'下载学习资料','Access code':'资料码','Get files':'获取文件','Access code accepted':'资料码有效','Download file':'下载文件','Download':'下载','Open':'打开','Automatic translation':'自动翻译','Translated reading view':'翻译阅读视图','Translate again':'重新翻译',
  'Communication':'沟通','Group chats':'群聊','Lesson messages':'课程消息','Lesson conversation':'课程对话','Group chat':'群聊','Message':'消息','Send':'发送','No messages yet. Start the conversation here.':'还没有消息，可以从这里开始聊天。','Write a message…':'输入消息…',
  'Book a lesson':'预约课程','Choose private or small-group learning.':'选择一对一或小班课程。','Private lessons':'一对一课程','Book one-to-one time':'预约一对一时间','Lesson':'课程','Lesson price':'课程价格','Weekly availability':'每周可预约时间','Previous week':'上一周','Next week':'下一周',
  'My lessons':'我的课程','Upcoming lessons':'即将开始的课程','Waiting for teacher':'等待老师确认','Waiting for teacher to start':'等待老师开始课堂','Confirmed':'已确认','Join classroom':'进入课堂','Cancel booking':'取消预约','Cancel seat':'取消座位',
  'No conversations yet':'还没有对话','View lessons':'查看课程','No availability has been added for this week.':'本周暂未添加可预约时间。','Available':'可预约','Unavailable':'不可用','Time':'时间',
  'Teacher':'老师','Student':'学生','Classroom open':'课堂已开启','Today':'今天','Tomorrow':'明天','Yesterday':'昨天',
  'Send':'发送','Close':'关闭','Refresh':'刷新','Camera':'摄像头','Start camera':'开启摄像头','Stop camera':'关闭摄像头','Mute':'静音','Unmute':'取消静音','Share screen':'共享屏幕','Stop sharing':'停止共享','Whiteboard':'白板','Participants':'参与者','Class chat':'课堂聊天','Teacher available':'老师可预约','Available start':'可预约开始时间','Teacher':'老师','You':'你',
  'Student account':'学生账号','Welcome back':'欢迎回来','Name':'姓名','Username':'用户名','Password':'密码','Confirm password':'确认密码','Already have an account?':'已经有账号？','New here?':'还没有账号？','Use a unique password with at least 12 characters.':'请使用至少 12 位且不重复使用的密码。','Forgot your password? Contact your teacher for a reset.':'忘记密码？请联系老师重置。','Sign in':'登录','Sign up':'注册','Create account':'创建账号',
  'Enter the 10-digit code from your teacher. You can join with your MathStudio account or continue as a guest.':'输入老师提供的 10 位课堂码。你可以使用 MathStudio 账号加入，也可以作为访客加入。','Name shown in the meeting':'课堂中显示的姓名','You are signed in. Your account name will be used in the meeting.':'你已登录，课堂中将使用你的账号姓名。',
  'Live classroom':'在线课堂','Ready to join?':'准备加入课堂？','Your camera and microphone start off. You can turn them on after joining.':'摄像头和麦克风默认关闭。加入后可自行开启。','Check camera & microphone':'检查摄像头和麦克风','Join classroom':'加入课堂','Enable sound':'启用声音','Leave':'离开课堂','End class for everyone':'结束所有人的课堂','Allow students to draw':'允许学生标注','No messages yet. Instant meeting chat lasts for this live session.':'暂无消息。即时课堂聊天只保留到本次课堂结束。','Message the class…':'发送课堂消息…','Valid resource codes become clickable file links automatically.':'有效的资料码会自动变成可点击的文件链接。',
  'Classroom':'课堂','Camera tiles appear here.':'摄像头画面会显示在这里。','Ready':'就绪','Status':'状态','Share code':'课堂码'
};

Object.assign(SITE_ZH, {
  'Media link: waiting for another participant.':'媒体连接：等待其他参与者。',
  'Camera reconnecting':'摄像头正在重新连接',
  'Camera connecting':'摄像头正在连接',
  'Reconnecting to classroom…':'正在重新连接课堂…',
  'Connecting…':'正在连接…',
  'Media renegotiation is retrying…':'正在重新协商媒体连接…',
  'Media network warning: TURN host lookup received error.':'媒体网络警告：TURN 服务器地址解析失败。',
  'Media network warning: TURN allocate request timed out.':'媒体网络警告：TURN 中继分配请求超时。',
  'Waiting for camera':'正在等待摄像头',
  'Enable sound':'开启声音',
  'Stop sharing':'停止共享',
  'Stop camera':'关闭摄像头',
  'Start camera':'开启摄像头',
  'Teacher meeting':'教师课堂',
  'Mic off · Camera on':'麦克风关闭 · 摄像头开启',
  'Mic on · Camera off':'麦克风开启 · 摄像头关闭',
  'Mic on · Camera on':'麦克风开启 · 摄像头开启'
});
function translateLiveStatus(s){
  if(siteLang!=='zh')return s;
  if(Object.prototype.hasOwnProperty.call(SITE_ZH,s))return SITE_ZH[s];
  let m=s.match(/^Media link: connected to (\d+) participants?\.$/);
  if(m)return `媒体连接：已连接 ${m[1]} 位参与者。`;
  m=s.match(/^Media link: (?:waiting for|connecting to) (\d+) participants?\.?$/);
  if(m)return `媒体连接：正在等待或连接 ${m[1]} 位参与者。`;
  m=s.match(/^(Teacher|Student|Guest) · (Mic on|Mic off|Muted by teacher) · (Camera on|Camera off)$/);
  if(m)return [m[1],m[2],m[3]].map(x=>SITE_ZH[x]||x).join(' · ');
  m=s.match(/^(Mic on|Mic off|Muted by teacher) · (Camera on|Camera off|Camera connecting…|Camera reconnecting…)$/);
  if(m)return [m[1],m[2]].map(x=>SITE_ZH[x]||x).join(' · ');
  m=s.match(/^Media network warning: (.*)$/);
  if(m)return '媒体网络警告：'+(SITE_ZH[m[1]]||m[1]);
  m=s.match(/^Media link: (.*)$/);
  if(m)return '媒体连接：'+(SITE_ZH[m[1]]||m[1]);
  m=s.match(/^Connected\. (.*)$/);
  if(m)return '已连接。'+m[1].replace('is available for camera and audio when direct WebRTC is blocked.','可在直连失败时中继摄像头和音频。');
  return s;
}

const tr=s=>siteLang==='zh'?(SITE_ZH[String(s)]||String(s)):String(s);
function applySiteLanguage(root=document){
  if(siteLang!=='zh')return;
  const targets=[];
  if(root.nodeType===Node.TEXT_NODE)targets.push(root);else{
    const w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);let n;while(n=w.nextNode())targets.push(n);
  }
  for(const node of targets){
    if(node.parentElement?.closest('script,style,textarea,.chat-message,.chat-text,[data-no-translate]'))continue;
    const raw=node.nodeValue,trim=raw.trim();if(!trim)continue;
    const translated=translateLiveStatus(trim);if(translated!==trim)node.nodeValue=raw.replace(trim,translated);
  }
  const scope=root.nodeType===1?root:root.parentElement;
  if(scope){
    const els=[scope,...scope.querySelectorAll?.('[placeholder],[aria-label],[title]')||[]];
    for(const el of els){
      for(const attr of ['placeholder','aria-label','title']){
        const raw=el.getAttribute?.(attr);if(raw){const translated=translateLiveStatus(raw);if(translated!==raw)el.setAttribute(attr,translated);}
      }
    }
  }
  document.documentElement.lang='zh-CN';
}
function installLanguageObserver(){
  const root=document.body;if(!root)return;
  const obs=new MutationObserver(ms=>{for(const m of ms){if(m.type==='characterData'||m.type==='attributes'){applySiteLanguage(m.target);continue;}for(const n of m.addedNodes)if(n.nodeType===1||n.nodeType===3)applySiteLanguage(n);}});
  obs.observe(root,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['placeholder','aria-label','title']});applySiteLanguage(root);
}
export function toast(text){$('#toast').textContent=text;$('#toast').classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('#toast').classList.remove('show'),6000);}
export async function api(path,data){const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);try{const r=await fetch(path,{method:data===undefined?'GET':'POST',signal:controller.signal,headers:data===undefined?{}:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:data===undefined?undefined:JSON.stringify(data)});const j=await r.json();if(!r.ok){const ex=new Error(j.error||'Request failed');ex.status=r.status;throw ex;}return j;}catch(ex){if(ex.name==='AbortError')throw new Error('The server took too long to respond. Check that it is running.');throw ex;}finally{clearTimeout(timer);}}
const isAdmin=()=>me?.role==='admin';
function input(key,label,type='text',value='',extra=''){return `<label for="${key}">${tr(label)}</label><input id="${key}" name="${key}" type="${type}" value="${esc(value)}" ${extra}>`;}
function area(key,label,value='',max=2000){return `<label for="${key}">${tr(label)}</label><textarea id="${key}" name="${key}" maxlength="${max}" required>${esc(value)}</textarea>`;}
function values(form){return Object.fromEntries(new FormData(form));}
function formHandler(id,fn){const form=$(id);if(!form)return;form.addEventListener('submit',async ev=>{ev.preventDefault();const b=form.querySelector('button[type=submit],button:not([type])');if(b)b.disabled=true;const err=form.querySelector('.error');if(err)err.classList.add('hidden');try{await fn(values(form));}catch(ex){if(err){err.textContent=ex.message;err.classList.remove('hidden');}else toast(ex.message);}finally{if(b)b.disabled=false;}});}
const errors='<div class="error hidden" role="alert"></div>';
function date(ts,opts={}){return new Intl.DateTimeFormat(siteLang==='zh'?'zh-CN':'en-CA',{timeZone:settings.timezone||'America/Edmonton',...opts}).format(new Date(ts*1000));}
const when=c=>date(c.start,{weekday:'short',month:'short',day:'numeric',hour:'numeric',minute:'2-digit'})+' · '+c.minutes+' min';
const timeOnly=ts=>date(ts,{hour:'numeric',minute:'2-digit'});
const dayKey=ts=>date(ts,{year:'numeric',month:'2-digit',day:'2-digit'});
function localDateTimeValue(d){
  const p=n=>String(n).padStart(2,'0');
  return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
}
function ceilToQuarter(d){
  const x=new Date(d);
  x.setSeconds(0,0);
  const r=x.getMinutes()%15;
  if(r)x.setMinutes(x.getMinutes()+(15-r));
  return x;
}
function normalizeQuarterInput(el){
  if(!el?.value)return null;
  const d=new Date(el.value);
  if(Number.isNaN(d.getTime()))return null;
  const snapped=ceilToQuarter(d);
  if(localDateTimeValue(snapped)!==el.value){
    el.value=localDateTimeValue(snapped);
    toast(`Time adjusted to ${snapped.toLocaleTimeString([], {hour:'numeric',minute:'2-digit'})} to match the 15-minute calendar.`);
  }
  return snapped;
}
function localDateValue(d){
  const p=n=>String(n).padStart(2,'0');
  return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())}`;
}
function quarterTimeValue(d){return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;}
function quarterTimeOptions(selected=''){
  let html='';
  for(let h=0;h<24;h++)for(const m of [0,15,30,45]){
    const value=`${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`;
    const label=new Date(2000,0,1,h,m).toLocaleTimeString([], {hour:'numeric',minute:'2-digit'});
    html+=`<option value="${value}" ${value===selected?'selected':''}>${esc(label)}</option>`;
  }
  return html;
}
function combineLocalDateTime(dateValue,timeValue){
  if(!dateValue||!timeValue)return null;
  const d=new Date(`${dateValue}T${timeValue}:00`);
  return Number.isNaN(d.getTime())?null:d;
}
function nav(){
  const path=location.pathname;
  const guest=me?.role==='guest';
  const accountLinks=me&&!guest?`<a href="/messages" ${path==='/messages'?'aria-current="page"':''}>Messages</a><a href="/account" ${path==='/account'?'aria-current="page"':''}>My lessons</a><button id="logout" class="secondary small">Log out</button>`:guest?`<span class="guest-chip">Guest</span><button id="logout" class="secondary small">Leave guest session</button>`:'<a class="button small" href="/login">Log in</a>';
  $('#header').innerHTML=`<nav><a class="brand" href="/"><img src="/favicon.svg" alt="">${esc(settings.name)}</a><div class="navlinks"><a href="/" ${path==='/'?'aria-current="page"':''}>Home</a><a href="/booking" ${path==='/booking'?'aria-current="page"':''}>Book a lesson</a><a href="/join" ${path==='/join'?'aria-current="page"':''}>Join meeting</a><a href="/resources" ${path==='/resources'?'aria-current="page"':''}>Resources</a>${accountLinks}<button id="langToggle" class="secondary small" data-no-translate>${siteLang==='zh'?'EN':'中文'}</button></div></nav>`;
  $('#logout')?.addEventListener('click',async()=>{try{await api('/api/logout',{});location.href='/';}catch(ex){toast(ex.message);}});
  $('#langToggle')?.addEventListener('click',()=>{localStorage.setItem('mathstudio_lang',siteLang==='zh'?'en':'zh');location.reload();});
  $('#footer').innerHTML=`<span>${esc(settings.name)} · Thoughtful mathematics tutoring, built around the student.</span><span>${settings.contact?esc(settings.contact):'Online mathematics tutoring'}</span>`;document.title=settings.name;
}

function formatBytes(bytes){const n=Number(bytes)||0;if(n<1024)return `${n} B`;if(n<1024*1024)return `${(n/1024).toFixed(n<10*1024?1:0)} KB`;if(n<1024*1024*1024)return `${(n/(1024*1024)).toFixed(n<10*1024*1024?1:0)} MB`;return `${(n/(1024*1024*1024)).toFixed(1)} GB`;}
function isIOSDevice(){return /iPad|iPhone|iPod/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);}
function resourceFileIcon(file){const name=(file.name||'').toLowerCase();if(file.mime==='application/pdf'||name.endsWith('.pdf'))return 'PDF';if((file.mime||'').startsWith('image/'))return 'IMG';if((file.mime||'').startsWith('video/'))return 'VID';if(/\.(doc|docx)$/.test(name))return 'DOC';if(/\.(ppt|pptx)$/.test(name))return 'PPT';if(/\.(xls|xlsx|csv)$/.test(name))return 'XLS';if(/\.zip$/.test(name))return 'ZIP';return 'FILE';}
function previewable(file){const m=file.mime||'',n=(file.name||'').toLowerCase();return m==='application/pdf'||m.startsWith('image/')||m.startsWith('video/')||m.startsWith('text/')||/\.(doc|docx|ppt|pptx|xls|xlsx)$/.test(n);}
function canTranslateFile(file){const n=(file.name||'').toLowerCase(),m=(file.mime||'').toLowerCase();return m.startsWith('text/')||m==='application/pdf'||/\.(txt|md|csv|json|html?|docx|pdf)$/.test(n);}
async function translateBundleFile(bundle,file,target,container){
  container.innerHTML='<div class="translation-loading">Translating document…</div>';
  try{
    const r=await api('/api/resources/translate',{grant:bundle.grant,file_id:file.id,target});
    container.innerHTML=`<div class="translation-head"><strong>${siteLang==='zh'?'翻译阅读视图':'Translated reading view'}</strong><span>${target==='zh-CN'?'中文':'English'} · ${esc(file.name)}</span></div><div class="translation-text">${esc(r.text).replace(/\n/g,'<br>')}</div>`;
    applySiteLanguage(container);
  }catch(ex){container.innerHTML=`<div class="notice translation-error">${esc(ex.message)}</div>`;}
}
function renderResourceBundle(bundle){
  const box=$('#resourceResult');if(!box)return;const ios=isIOSDevice();const grant=encodeURIComponent(bundle.grant);const primary=bundle.files.length>1?`<a class="button" href="/resource/download-all?grant=${grant}">Download all (${bundle.files.length}) as ZIP</a>`:`<a class="button" href="/resource/download?grant=${grant}&file=${bundle.files[0].id}">Download file</a>`;
  const translation=bundle.translate_enabled?`<section class="translation-panel"><div class="translation-panel-head"><div><p class="eyebrow">Automatic translation</p><h3>${siteLang==='zh'?'已为此资料码开启文档翻译':'Document translation is enabled for this share code'}</h3><p class="muted">${siteLang==='zh'?'支持文本、DOCX 和可读取文字的 PDF。翻译内容会发送到在线翻译服务。':'Supports text, DOCX, and text-based PDFs. Document text is sent to an online translation service.'}</p></div><select id="translationTarget" aria-label="Translation language"><option value="en" ${siteLang==='en'?'selected':''}>English</option><option value="zh-CN" ${siteLang==='zh'?'selected':''}>中文</option></select></div><div id="translationResults" class="translation-results"></div></section>`:'';
  box.innerHTML=`<div class="resource-success"><div><p class="eyebrow">Access code accepted</p><h2>${esc(bundle.label)}</h2><p class="muted">${bundle.files.length} file${bundle.files.length===1?'':'s'} ready. Download links remain available for 30 minutes on this device.</p></div>${primary}</div>${ios?`<div class="ios-help"><strong>iPhone / iPad</strong><p>For PDFs and images, <b>Open</b> lets you preview the file in Safari, then use Share → Save to Files. For several files, <b>Download all</b> saves one ZIP in the Files app’s Downloads folder.</p></div>`:''}<div class="resource-download-list">${bundle.files.map(f=>`<article class="resource-download-row"><span class="file-kind">${resourceFileIcon(f)}</span><div><strong>${esc(f.name)}</strong><span>${formatBytes(f.size)}</span></div><div class="actions">${previewable(f)?`<a class="button secondary small" target="_blank" rel="noopener" href="/resource/open?grant=${grant}&file=${f.id}">Open</a>`:''}<a class="button small" href="/resource/download?grant=${grant}&file=${f.id}">Download</a></div></article>`).join('')}</div>${translation}`;
  box.scrollIntoView({behavior:'smooth',block:'nearest'});applySiteLanguage(box);
  if(bundle.translate_enabled){
    const results=$('#translationResults'),select=$('#translationTarget');
    const run=()=>{results.innerHTML='';for(const f of bundle.files.filter(canTranslateFile)){const card=document.createElement('article');card.className='translation-card';results.appendChild(card);translateBundleFile(bundle,f,select.value,card);}if(!results.children.length)results.innerHTML='<div class="notice">No text-based files in this bundle can be translated automatically.</div>';};
    select.addEventListener('change',run);run();
  }
}

async function instantJoin(){
  stopAccountWatcher();
  const qs=new URLSearchParams(location.search), preset=(qs.get('code')||'').replace(/\D/g,'').slice(0,10);
  const guest=!me||me.role==='guest';
  $('#app').innerHTML=`<div class="join-meeting-shell"><section class="join-meeting-card"><div class="join-meeting-mark">10</div><p class="eyebrow">${tr('Instant classroom')}</p><h1>${tr('Join a meeting')}</h1><p class="muted">${tr('Enter the 10-digit code from your teacher. You can join with your MathStudio account or continue as a guest.')}</p><form id="instantJoinForm">${errors}<label for="meeting_code">${tr('Meeting code')}</label><input id="meeting_code" name="code" inputmode="numeric" autocomplete="one-time-code" maxlength="10" pattern="[0-9]{10}" placeholder="1234567890" value="${esc(preset)}" required>${guest?`<label for="guest_name">${tr('Your name')}</label><input id="guest_name" name="name" maxlength="80" autocomplete="name" placeholder="${tr('Name shown in the meeting')}" required>`:`<div class="signed-in-join"><span>${tr('Joining as')}</span><strong>${esc(me.name)}</strong></div>`}<button type="submit">${tr('Join meeting')}</button></form>${!guest?`<p class="meta">${tr('You are signed in. Your account name will be used in the meeting.')}</p>`:`<p class="meta">${tr('Guest access does not require creating an account.')}</p>`}</section></div>`;
  const code=$('#meeting_code');code?.focus();code?.addEventListener('input',()=>{code.value=code.value.replace(/\D/g,'').slice(0,10);});
  formHandler('#instantJoinForm',async d=>{
    const payload={code:String(d.code||'').replace(/\D/g,'')};
    if(guest)payload.name=String(d.name||'').trim();
    const r=await api('/api/instant/join',payload);
    location.href=`/classroom?id=${encodeURIComponent(r.class_id)}&instant=1`;
  });
}

async function resources(){
  stopAccountWatcher();
  const linkedCode=(new URLSearchParams(location.search).get('code')||'').trim();
  $('#app').innerHTML=`<div class="pagehead resource-head"><div><p class="eyebrow">Class resources</p><h1>Download your files</h1><p class="muted">Enter the access code your teacher gave you, or open a resource code directly from classroom chat.</p></div></div><section class="resource-code-panel"><form id="resourceCodeForm">${errors}<label for="resource_code">Access code</label><div class="resource-code-entry"><input id="resource_code" name="code" autocomplete="off" autocapitalize="characters" spellcheck="false" maxlength="20" placeholder="Example: 7K4M9Q" required><button>Get files</button></div><p class="field-help">Codes are not case-sensitive. Spaces or hyphens are ignored. The code box stays available even if you arrived from classroom chat.</p></form></section><section id="resourceResult" class="section resource-result"><div class="empty"><h3>Notes, homework, and class files</h3><p>Your teacher can bundle several files under one code, so one code can download an entire unit’s materials.</p></div></section>`;
  const redeem=async code=>{const r=await api('/api/resources/redeem',{code});renderResourceBundle(r);};
  formHandler('#resourceCodeForm',async d=>redeem(d.code));
  const input=$('#resource_code');
  if(linkedCode){input.value=linkedCode;try{await redeem(linkedCode);history.replaceState(null,'','/resources');}catch(ex){const err=$('#resourceCodeForm .error');if(err){err.textContent=ex.message;err.classList.remove('hidden');}toast(ex.message);input.focus();}}
  else input?.focus();
}
async function uploadTeacherFile(file){const r=await fetch('/api/admin/files/upload',{method:'POST',headers:{'Content-Type':'application/octet-stream','X-CSRF-Token':csrf,'X-File-Name':encodeURIComponent(file.name),'X-File-Type':encodeURIComponent(file.type||'')},body:file});let j={};try{j=await r.json();}catch{}if(!r.ok)throw new Error(j.error||`Could not upload ${file.name}.`);return j;}
function fileUploadQuickHTML(info){
  const storage=info.storage.cloud?`<span class="storage-badge cloud">Cloud storage · ${esc(info.storage.label)}</span>`:`<span class="storage-badge local">Test storage · ${esc(info.storage.label)}</span>`;
  return `<section class="admin-action-card admin-file-upload-card"><div class="admin-card-head"><div><p class="eyebrow">Class resources</p><h2>Upload files</h2><p class="meta">Add notes, homework, worksheets, recordings, or other class materials to the teacher library.</p></div>${storage}</div>${!info.storage.cloud?'<div class="storage-warning compact"><strong>Testing mode:</strong> uploads are stored with this MathStudio copy. Configure Cloudflare R2 before using this as permanent storage.</div>':''}<ol class="instruction-list"><li><strong>Choose one or more files.</strong><span>Each file is uploaded once and can be reused in many access-code bundles.</span></li><li><strong>Go to File library below.</strong><span>Select the exact files students should receive.</span></li><li><strong>Generate a code.</strong><span>Paste that code into a group chat or send it another way.</span></li></ol><div class="file-upload-quick-actions"><label class="button upload-button" for="teacherFileInput">Choose files to upload</label><input id="teacherFileInput" class="visually-hidden" type="file" multiple><span id="uploadStatus" class="meta">Up to ${info.max_upload_mb} MB per file.</span></div></section>`;
}
function fileLibraryHTML(info){
  const active=info.codes.filter(c=>c.active),revoked=info.codes.filter(c=>!c.active);
  return `<section id="admin-files" class="section file-library admin-wide-section"><div class="sectionhead"><div><p class="eyebrow">Resources</p><h2>File library & access codes</h2><p class="meta">Manage uploaded files and decide exactly which files each student code unlocks. Uploading happens in the quick-action card above; this area is for organizing and sharing.</p></div><span class="tag gray">${info.files.length} file${info.files.length===1?'':'s'} · ${active.length} active code${active.length===1?'':'s'}</span></div><div class="admin-help-box"><strong>How to send files to a class</strong><span>1. Select one or more files below. 2. Add an optional label such as “Grade 7 · Unit 1”. 3. Generate a code. 4. Send the code in Messages; students can click it to open the download page.</span></div><div class="code-builder"><div><h3>Create a student access code</h3><p class="meta"><span id="selectedFileCount">0 files selected</span> · A single code can unlock one file or an entire bundle.</p></div><div class="code-builder-fields"><input id="codeLabel" maxlength="120" placeholder="Optional label, e.g. Grade 7 · Unit 1"><button id="generateFileCode" disabled>Generate code</button></div></div>${info.files.length?`<div class="file-table"><div class="file-row file-row-head"><label><input id="selectAllFiles" type="checkbox"> Select</label><span>File</span><span>Size</span><span>Codes</span><span></span></div>${info.files.map(f=>`<div class="file-row"><label class="file-check"><input type="checkbox" data-file-select value="${f.id}"><span class="sr-only">Select ${esc(f.name)}</span></label><div class="file-name"><span class="file-kind">${resourceFileIcon(f)}</span><div><strong title="${esc(f.name)}">${esc(f.name)}</strong><small>${esc(f.mime||'File')}</small></div></div><span>${formatBytes(f.size)}</span><span>${f.code_count}</span><button class="secondary small danger-text" data-deletefile="${f.id}" data-filename="${esc(f.name)}">Delete</button></div>`).join('')}</div>`:'<div class="empty compact"><h3>Your library is empty</h3><p>Use the Upload files card near the top of Admin to add notes, homework, or other materials.</p></div>'}<div class="access-code-section"><div class="sectionhead"><div><h3>Access codes</h3><p class="meta">Revoke a code at any time without deleting the original files.</p></div><span class="tag">${active.length} active</span></div>${info.codes.length?`<div class="code-card-grid">${[...active,...revoked].map(c=>`<article class="code-card ${c.active?'':'revoked'}"><div class="code-card-top"><div><span class="code-label">${esc(c.label)}</span><button class="access-code" data-copycode="${esc(c.code)}" title="Copy code">${esc(c.code)}</button></div><span class="tag ${c.active?'':'gray'}">${c.active?'Active':'Revoked'}</span></div><p>${c.files.map(f=>esc(f.name)).join(' · ')||'No files'}</p><div class="code-card-bottom"><span>${c.files.length} file${c.files.length===1?'':'s'} · ${date(c.created,{month:'short',day:'numeric',year:'numeric'})}</span><button class="secondary small" data-codeaction="${c.active?'revoke':'restore'}" data-codeid="${c.id}">${c.active?'Revoke':'Restore'}</button></div></article>`).join('')}</div>`:'<div class="empty compact">No access codes yet. Select files above and generate one.</div>'}</div></section>`;
}
function mountFileLibrary(info){const page=$('#app');const head=page?.querySelector('.pagehead');if(!page||!head)return;const anchor=$('#adminFileAnchor');if(anchor)anchor.insertAdjacentHTML('afterend',fileLibraryHTML(info));else head.insertAdjacentHTML('afterend',fileLibraryHTML(info));const selected=()=>[...document.querySelectorAll('[data-file-select]:checked')];const updateSelection=()=>{const n=selected().length;$('#selectedFileCount').textContent=`${n} file${n===1?'':'s'} selected`;$('#generateFileCode').disabled=!n;const all=[...document.querySelectorAll('[data-file-select]')];if($('#selectAllFiles')){$('#selectAllFiles').checked=all.length>0&&n===all.length;$('#selectAllFiles').indeterminate=n>0&&n<all.length;}};document.querySelectorAll('[data-file-select]').forEach(x=>x.addEventListener('change',updateSelection));$('#selectAllFiles')?.addEventListener('change',ev=>{document.querySelectorAll('[data-file-select]').forEach(x=>x.checked=ev.target.checked);updateSelection();});$('#teacherFileInput')?.addEventListener('change',async ev=>{const files=[...ev.target.files];if(!files.length)return;const status=$('#uploadStatus');ev.target.disabled=true;try{for(let i=0;i<files.length;i++){status.textContent=`Uploading ${i+1} of ${files.length}: ${files[i].name}`;await uploadTeacherFile(files[i]);}toast(`${files.length} file${files.length===1?'':'s'} uploaded.`);await admin();}catch(ex){toast(ex.message);status.textContent=ex.message;}finally{ev.target.disabled=false;}});$('#generateFileCode')?.addEventListener('click',async()=>{const ids=selected().map(x=>+x.value);if(!ids.length)return;const button=$('#generateFileCode');button.disabled=true;try{const r=await api('/api/admin/files/code',{file_ids:ids,label:$('#codeLabel').value});try{await navigator.clipboard.writeText(r.code);toast(`Access code ${r.code} generated and copied.`);}catch{toast(`Access code ${r.code} generated.`);}await admin();}catch(ex){toast(ex.message);button.disabled=false;}});document.querySelectorAll('[data-copycode]').forEach(b=>b.addEventListener('click',async()=>{const code=b.dataset.copycode;try{await navigator.clipboard.writeText(code);toast(`Copied ${code}.`);}catch{window.prompt('Copy this access code:',code);}}));document.querySelectorAll('[data-codeaction]').forEach(b=>b.addEventListener('click',async()=>{const action=b.dataset.codeaction;if(action==='revoke'&&!confirm('Revoke this code? Students using it will no longer be able to download its files.'))return;try{await api('/api/admin/files/code-action',{code_id:+b.dataset.codeid,action});await admin();toast(action==='revoke'?'Code revoked.':'Code restored.');}catch(ex){toast(ex.message);}}));document.querySelectorAll('[data-deletefile]').forEach(b=>b.addEventListener('click',async()=>{if(!confirm(`Delete “${b.dataset.filename}” from the library? It will also be removed from any access codes that use it.`))return;try{await api('/api/admin/files/delete',{file_id:+b.dataset.deletefile});await admin();toast('File deleted.');}catch(ex){toast(ex.message);}}));}

function stopMessageWatcher(){if(messageWatchTimer!==null){clearInterval(messageWatchTimer);messageWatchTimer=null;}}
function messageTime(seconds){return new Intl.DateTimeFormat(undefined,{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}).format(new Date(seconds*1000));}
function messageBody(message){
  let html=esc(message.text);
  for(const item of message.codes||[]){
    const safe=item.code.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
    html=html.replace(new RegExp(`\\b${safe}\\b`,'gi'),`<a class="chat-resource-code" href="/resources?code=${encodeURIComponent(item.code)}" title="Open ${esc(item.label||'class resources')}"><strong>${esc(item.code)}</strong><span>Open files →</span></a>`);
  }
  return html.replace(/\n/g,'<br>');
}
async function messagesPage(){
  stopAccountWatcher();stopMessageWatcher();
  if(!me){location.href='/login?next=/messages';return;}
  const groupData=await api('/api/groups');
  const groups=groupData.groups||[];
  const accessible=classes.filter(c=>c.class_kind!=='group'&&c.approval==='confirmed'&&c.status!=='cancelled'&&(isAdmin()||c.mine)).sort((a,b)=>b.start-a.start);
  const q=new URLSearchParams(location.search),requestedGroup=Number(q.get('group')),requestedClass=Number(q.get('id'));
  let mode=null,selected=null;
  if(requestedGroup&&groups.some(g=>g.id===requestedGroup)){mode='group';selected=groups.find(g=>g.id===requestedGroup);}
  else if(requestedClass&&accessible.some(c=>c.id===requestedClass)){mode='class';selected=accessible.find(c=>c.id===requestedClass);}
  else if(groups.length){mode='group';selected=groups[0];}
  else if(accessible.length){mode='class';selected=accessible[0];}
  const groupLinks=groups.map(g=>`<a class="message-thread ${mode==='group'&&selected?.id===g.id?'active':''}" href="/messages?group=${g.id}"><strong>${esc(g.name)}</strong><span>${g.member_count} member${g.member_count===1?'':'s'}</span>${g.kind==='lesson'?'<em>Lesson group</em>':''}</a>`).join('');
  const lessonLinks=accessible.map(c=>`<a class="message-thread ${mode==='class'&&selected?.id===c.id?'active':''}" href="/messages?id=${c.id}"><strong>${esc(c.title)}</strong><span>${esc(when(c))}</span>${c.live?'<em>Live now</em>':''}</a>`).join('');
  const hasAny=groups.length||accessible.length;
  const title=mode==='group'?selected.name:selected?.title;
  const subtitle=mode==='group'?`${selected.member_count} members`:selected?when(selected):'';
  $('#app').innerHTML=`<div class="pagehead"><div><p class="eyebrow">Communication</p><h1>Messages</h1><p class="muted">Use group chats for ongoing class communication, or lesson conversations for individual tutoring. Active resource codes open the matching files directly.</p></div></div>${hasAny?`<section class="messages-layout"><aside class="message-threads">${groups.length?`<h2>Group chats</h2>${groupLinks}`:''}${accessible.length?`<h2 class="thread-section-title">Lesson messages</h2>${lessonLinks}`:''}</aside><section class="message-panel"><div class="message-panel-head"><div><p class="eyebrow">${mode==='group'?'Group chat':'Lesson conversation'}</p><h2>${esc(title||'Messages')}</h2><p class="meta">${esc(subtitle)}</p></div>${mode==='class'&&selected.live?`<a class="button small" href="/classroom?id=${selected.id}">${isAdmin()?'Enter':'Join'} classroom</a>`:''}</div><div id="persistentMessages" class="persistent-messages" role="log" aria-live="polite"><div class="chat-empty">Loading messages…</div></div><form id="persistentMessageForm" class="persistent-message-form"><label for="persistentMessageInput">Message</label><div><textarea id="persistentMessageInput" maxlength="1000" placeholder="Write a message…" required></textarea><button type="submit">Send</button></div><p class="field-help">Paste an active resource code anywhere in a message and it becomes a direct file link.</p></form></section></section>`:'<div class="empty"><h3>No conversations yet</h3><p>Your teacher can create a group chat, or a lesson conversation appears after a private lesson is confirmed.</p><a class="button" href="/booking">View lessons</a></div>'}`;
  if(!selected)return;
  let seq=0,busy=false,messages=[];
  const render=()=>{const box=$('#persistentMessages');if(!box)return;if(!messages.length){box.innerHTML='<div class="chat-empty">No messages yet. Start the conversation here.</div>';return;}const near=box.scrollHeight-box.scrollTop-box.clientHeight<100;box.innerHTML=messages.map(m=>`<article class="chat-message ${m.role==='admin'?'teacher':''}"><div class="chat-meta"><strong>${esc(m.name)}</strong>${m.role==='admin'?'<span class="tag">Teacher</span>':''}<time>${messageTime(m.at)}</time></div><div class="chat-text">${messageBody(m)}</div></article>`).join('');if(near)box.scrollTop=box.scrollHeight;};
  const load=async()=>{if(busy||location.pathname!=='/messages')return;busy=true;try{const path=mode==='group'?`/api/group-messages?group=${selected.id}&since=${seq}`:`/api/messages?class=${selected.id}&since=${seq}`;const r=await api(path);if(r.messages.length){messages.push(...r.messages);if(messages.length>500)messages=messages.slice(-500);seq=Math.max(seq,r.seq||0);render();}else if(seq===0)render();}catch(ex){if(seq===0)$('#persistentMessages').innerHTML=`<div class="error">${esc(ex.message)}</div>`;}finally{busy=false;}};
  $('#persistentMessageForm').addEventListener('submit',async ev=>{ev.preventDefault();const input=$('#persistentMessageInput'),button=ev.currentTarget.querySelector('button');const text=input.value.trim();if(!text)return;button.disabled=input.disabled=true;try{await api(mode==='group'?'/api/group-messages/send':'/api/messages/send',mode==='group'?{group_id:selected.id,text}:{class_id:selected.id,text});input.value='';await load();input.focus();}catch(ex){toast(ex.message);}finally{button.disabled=input.disabled=false;}});
  $('#persistentMessageInput').addEventListener('keydown',ev=>{if(ev.key==='Enter'&&!ev.shiftKey&&!ev.isComposing){ev.preventDefault();$('#persistentMessageForm').requestSubmit();}});
  await load();messageWatchTimer=setInterval(()=>{if(!document.hidden)load();},2500);
}
function home(){
  const next=classes.filter(c=>c.mine&&c.status==='scheduled').sort((a,b)=>a.start-b.start)[0];
  $('#app').innerHTML=`
    <section class="hero hero-v32">
      <div class="hero-copy">
        <p class="eyebrow">Personalized online math tutoring</p>
        <h1>${esc(settings.headline)}</h1>
        <p class="lead">${esc(settings.intro)}</p>
        <div class="actions hero-actions">
          <a class="button" href="/booking">Find a lesson time</a>
          ${me?'<a class="button secondary" href="/account">View my lessons</a>':'<a class="button secondary" href="/signup">Create an account</a>'}
        </div>
        <div class="hero-points" aria-label="MathStudio benefits">
          <span><b>01</b> School & advanced math</span>
          <span><b>02</b> Waterloo & AMC prep</span>
          <span><b>03</b> Live online lessons</span>
        </div>
      </div>
      <aside class="hero-info-card">
        <div class="hero-info-top">
          <span class="hero-info-badge">MathStudio</span>
          <span class="hero-info-status">Online tutoring</span>
        </div>
        <h2>One place for lessons, practice, and class resources.</h2>
        <div class="hero-info-list">
          <div><span class="hero-info-icon">✓</span><p><strong>Choose the right lesson</strong><small>Pick your course, contest focus, and session length.</small></p></div>
          <div><span class="hero-info-icon">⌚</span><p><strong>Book around your schedule</strong><small>See the teacher’s available times before requesting a lesson.</small></p></div>
          <div><span class="hero-info-icon">↗</span><p><strong>Everything stays together</strong><small>Messages, class files, and upcoming lessons are in your account.</small></p></div>
        </div>
        ${next?`<a class="next-lesson-card" href="/account"><span>Next lesson</span><strong>${esc(when(next))}</strong><small>Open My lessons →</small></a>`:`<a class="next-lesson-card" href="/booking"><span>Ready when you are</span><strong>Choose a lesson and find a time.</strong><small>Open booking →</small></a>`}
      </aside>
    </section>
    <section class="section section-v32">
      <div class="sectionhead sectionhead-v32"><div><p class="eyebrow">What we can work on</p><h2>Focused support for the math in front of you.</h2></div><p class="muted">Clear explanations, structured practice, and problem-solving strategies without unnecessary clutter.</p></div>
      <div class="three feature-grid-v32">
        <article class="card program feature-card-v32"><span class="feature-icon">A</span><span class="feature-kicker">School math</span><h3>Understand the topic, not just the answer.</h3><p>Work through Alberta and Canadian curriculum topics with explanations matched to what you are learning now.</p></article>
        <article class="card program feature-card-v32"><span class="feature-icon">∑</span><span class="feature-kicker">Contest math</span><h3>Build stronger problem-solving habits.</h3><p>Practice Waterloo and AMC-style questions while learning how to recognize patterns and choose useful strategies.</p></article>
        <article class="card program feature-card-v32"><span class="feature-icon">↗</span><span class="feature-kicker">Online lessons</span><h3>Book, meet, and keep resources together.</h3><p>Choose 60- or 90-minute lessons, join online, and return to shared files and messages afterward.</p></article>
      </div>
    </section>
    <section class="section about-v32">
      <div class="about-copy"><p class="eyebrow">About the teacher</p><h2>${esc(settings.teacher)}</h2><p class="muted prewrap">${esc(settings.about)}</p></div>
      <div class="callout callout-v32"><span class="callout-label">${next?'Upcoming lesson':'Booking'}</span><h2>${next?'You’re all set for your next class.':'Find a time that works for you.'}</h2><p>${next?esc(when(next)):'Select a lesson type, check the live schedule, and send your request.'}</p><a class="button" href="${next?'/account':'/booking'}">${next?'Open my lessons':'View available times'}</a></div>
    </section>
    ${posts.length?`<section class="section announcements-v32"><div class="sectionhead"><div><p class="eyebrow">Updates</p><h2>Announcements</h2></div></div><div class="announcement-grid">${posts.slice(0,4).map(p=>`<article class="card announcement-card"><span class="announcement-date">${esc(p.created)}</span><h3>${esc(p.title)}</h3><p class="prewrap">${esc(p.body)}</p><p class="meta">${esc(p.author)}</p></article>`).join('')}</div></section>`:''}
  `;
}
function auth(signup=false){
  const title=signup?'Create account':'Log in';
  const eyebrow=signup?'Student account':'Welcome back';
  const below=signup
    ? `${tr('Already have an account?')} <a href="/login">${tr('Log in')}</a>`
    : `${tr('New here?')} <a href="/signup">${tr('Create account')}</a>`;
  const help=signup?'Use a unique password with at least 12 characters.':'Forgot your password? Contact your teacher for a reset.';
  $('#app').innerHTML=`<section class="auth panel"><p class="eyebrow">${tr(eyebrow)}</p><h1>${tr(title)}</h1><form id="auth">${errors}${signup?input('name','Name','text','','required maxlength="80" autocomplete="name"'):''}${input('username','Username','text','','required minlength="3" maxlength="40" autocomplete="username" pattern="[a-zA-Z0-9_]+"')}${input('password','Password','password','',`required ${signup?'minlength="12"':''} maxlength="256" autocomplete="${signup?'new':'current'}-password"`)}${signup?input('confirm','Confirm password','password','','required minlength="12" autocomplete="new-password"'):''}<button>${tr(title)}</button></form><p>${below}</p><p class="meta">${tr(help)}</p></section>`;
  formHandler('#auth',async d=>{if(signup&&d.password!==d.confirm)throw new Error(siteLang==='zh'?'两次输入的密码不一致。':'Passwords do not match.');const r=await api(signup?'/api/signup':'/api/login',d);csrf=r.csrf;me=r.user;const next=new URLSearchParams(location.search).get('next');location.href=next==='/booking'?next:'/account';});
}

function groupLessonCard(c){
  const left=Math.max(0,(c.capacity||0)-(c.booked||0));
  const full=left<=0;
  const mine=!!c.mine;
  const chat=mine&&c.group_chat_id?`<a class="button secondary small" href="/messages?group=${c.group_chat_id}">Group chat</a>`:'';
  let action='';
  if(mine)action=`<span class="tag">Seat reserved</span>${chat}${c.start>Date.now()/1000?`<button class="secondary small" data-unbook="${c.id}">Cancel seat</button>`:''}`;
  else if(!me)action=`<a class="button small" href="/login?next=/booking">Log in to book</a>`;
  else action=`<button class="small" data-groupjoin="${c.id}" ${full?'disabled':''}>${full?'Full':'Reserve a seat'}</button>`;
  return `<article class="group-lesson-card"><div class="group-lesson-main"><div class="group-lesson-badges"><span class="tag">Group lesson</span><span class="tag gray">${c.booked||0}/${c.capacity} seats</span>${c.price_label?`<span class="tag gray">${esc(c.price_label)}</span>`:''}</div><h3>${esc(c.title)}</h3><p class="meta">${esc(when(c))}</p><p>${esc(c.description||'Small-group mathematics lesson')}</p><div class="seat-meter" aria-label="${left} seats remaining"><span style="width:${Math.min(100,Math.round(((c.booked||0)/(c.capacity||1))*100))}%"></span></div><small>${full?'No seats remaining':`${left} seat${left===1?'':'s'} remaining`}</small></div><div class="actions">${action}</div></article>`;
}
function classCard(c,admin=false){
  const now=Date.now()/1000,future=c.start>now,scheduledTimePassed=c.start<=now,scheduledEndPassed=c.start+c.minutes*60<=now;
  const approval=c.approval||'confirmed';let actions='';
  const messageLink=approval==='confirmed'&&c.status!=='cancelled'?(c.class_kind==='group'&&c.group_chat_id?`<a class="button secondary small" href="/messages?group=${c.group_chat_id}">Group chat</a>`:`<a class="button secondary small" href="/messages?id=${c.id}">Messages</a>`):'';
  if(admin){
    if(c.status==='scheduled'&&approval==='confirmed'){
      const tooEarly=now<c.start-1800;
      const openLabel=scheduledTimePassed?'Start late in teacher app':'Start teacher app';
      actions=`${messageLink}${!c.live?`<button class="small" data-teacherlaunch="${c.id}" ${tooEarly?'disabled':''}>${openLabel}</button>`:`<button class="small" data-teacherlaunch="${c.id}">Open teacher app</button><button class="small secondary" data-classaction="end" data-id="${c.id}">End class</button>`}<button class="small secondary" data-classaction="cancel" data-id="${c.id}">Cancel</button>`;
    }else actions=messageLink;
  }else if(c.mine&&c.status==='scheduled'){
    const waitingLate=approval==='confirmed'&&!c.live&&scheduledTimePassed;
    actions=`${approval==='pending'?'<span class="tag orange">Waiting for teacher</span>':waitingLate?'<span class="tag orange">Waiting for teacher to start</span>':'<span class="tag">Confirmed</span>'}${approval==='confirmed'?messageLink:''}${approval==='confirmed'&&c.live?`<a class="button small" href="/classroom?id=${c.id}">Join classroom</a>`:''}${future?`<button class="secondary small" data-unbook="${c.id}">${c.class_kind==='group'?'Cancel seat':'Cancel booking'}</button>`:''}`;
  }
  const groupTag=c.class_kind==='group'?`<span class="tag orange">Group · ${c.booked||0}/${c.capacity}</span>`:'';
  const timingTag=c.status==='scheduled'&&approval==='confirmed'&&!c.live&&scheduledEndPassed?'<span class="tag orange">Scheduled time passed</span>':'';
  return `<article class="card class-row"><div class="datebox">${date(c.start,{month:'short'})}<strong>${date(c.start,{day:'numeric'})}</strong>${date(c.start,{weekday:'short'})}</div><div><span class="tag">${esc(c.minutes)} min</span> ${groupTag} ${c.price_label?`<span class="tag gray">${esc(c.price_label)}</span>`:''} ${c.status!=='scheduled'?`<span class="tag gray">${esc(c.status)}</span>`:approval==='pending'?'<span class="tag orange">Pending</span>':c.live?'<span class="tag orange">Classroom open</span>':timingTag}<h3>${esc(c.title)}</h3><p class="meta">${esc(when(c))}</p></div><div class="actions">${actions}</div></article>`;
}
async function refreshClasses(){classes=(await api('/api/classes')).classes;}
async function refreshSchedule(){schedule=await api('/api/schedule');}
function weekStartFromParam(){const q=new URLSearchParams(location.search).get('week');let d=q?new Date(+q*1000):new Date();if(Number.isNaN(d.getTime()))d=new Date();d.setHours(0,0,0,0);const day=d.getDay();d.setDate(d.getDate()-((day+6)%7));return d;}
function shiftWeek(start,delta){const d=new Date(start);d.setDate(d.getDate()+delta*7);return Math.floor(d.getTime()/1000);}
function weekKeys(start){const out=[];for(let i=0;i<7;i++){const d=new Date(start);d.setDate(d.getDate()+i);out.push(dayKey(d.getTime()/1000));}return out;}
function slotFits(start,minutes){const end=start+minutes*60;return !schedule.busy.some(b=>b.status==='scheduled'&&b.start<end&&b.start+b.minutes*60>start);}
function slotsFor(a,lesson){const out=[];const first=Math.ceil(a.start/(15*60))*(15*60);for(let st=first;st+lesson.minutes*60<=a.end+0.001;st+=15*60){if(st>Date.now()/1000+30&&slotFits(st,lesson.minutes))out.push(st);}return out;}
function lessonLabel(l){return `${l.name} — ${l.minutes} min`;}
function minuteOfDay(ts){const d=new Date(ts*1000);return d.getHours()*60+d.getMinutes();}
function gridTimestamp(start,dayIndex,minute){const d=new Date(start);d.setDate(d.getDate()+dayIndex);d.setHours(Math.floor(minute/60),minute%60,0,0);return Math.floor(d.getTime()/1000);}
function calendarBounds(start,adminBookings=[]){const keys=weekKeys(start);let low=8*60,high=22*60;const points=[];for(const a of schedule.availability){if(keys.includes(dayKey(a.start))){points.push(minuteOfDay(a.start),minuteOfDay(a.end));}}const source=adminBookings.length?adminBookings:schedule.busy;for(const b of source){if(b.status==='scheduled'&&keys.includes(dayKey(b.start))){points.push(minuteOfDay(b.start),minuteOfDay(b.start+b.minutes*60));}}if(points.length){low=Math.min(low,Math.floor((Math.min(...points)-30)/60)*60);high=Math.max(high,Math.ceil((Math.max(...points)+30)/60)*60);}return [Math.max(0,low),Math.min(24*60,high)];}
function sameCalendarDay(tsA,tsB){return dayKey(tsA)===dayKey(tsB);}
function calendarLegendHTML(admin=false){return `<div class="calendar-legend">${admin?'<span><i class="legend-swatch open"></i>Teacher available</span><span><i class="legend-swatch confirmed"></i>Confirmed lesson</span><span><i class="legend-swatch pending"></i>Pending request</span>':'<span><i class="legend-swatch available"></i>Available start</span><span><i class="legend-swatch open"></i>Teacher available</span><span><i class="legend-swatch blocked"></i>Unavailable</span>'}</div>`;}
function availabilityManagerHTML(start){const keys=weekKeys(start);const list=schedule.availability.filter(a=>keys.includes(dayKey(a.start))).sort((a,b)=>a.start-b.start);if(!list.length)return '<div class="availability-manager empty-compact">No availability has been added for this week.</div>';return `<div class="availability-manager"><div class="availability-manager-head"><strong>Availability this week</strong><span>${list.length} block${list.length===1?'':'s'}</span></div>${list.map(a=>`<div class="availability-manager-row"><div><strong>${date(a.start,{weekday:'short',month:'short',day:'numeric'})}</strong><span>${timeOnly(a.start)}–${timeOnly(a.end)}</span></div><button class="secondary small" data-closeavail="${a.id}">Close availability</button></div>`).join('')}</div>`;}
function scheduleWeekHTML(start,lesson,admin=false,adminBookings=[]){const [fromMinute,toMinute]=calendarBounds(start,adminBookings);const rows=[];for(let minute=fromMinute;minute<toMinute;minute+=15){const sample=gridTimestamp(start,0,minute);rows.push(`<div class="calendar-time ${minute%60===0?'hour':''}">${timeOnly(sample)}</div>`);for(let dayIndex=0;dayIndex<7;dayIndex++){const ts=gridTimestamp(start,dayIndex,minute);const cellEnd=ts+15*60;if(admin){const booking=adminBookings.find(b=>b.status==='scheduled'&&b.start<cellEnd&&b.start+b.minutes*60>ts);const av=schedule.availability.find(a=>a.start<cellEnd&&a.end>ts);if(booking){const first=booking.start>=ts&&booking.start<cellEnd;const status=booking.approval==='pending'?'pending':'confirmed';const names=(booking.attendees||[]).map(x=>x.name).filter(Boolean);const who=names.length?names.join(', '):(booking.name||((booking.class_kind==='group')?'No seats reserved':'Student'));const groupInfo=booking.class_kind==='group'?`${booking.booked||names.length}/${booking.capacity||'?'} seats · ${who}`:who;rows.push(`<div class="calendar-cell booking ${status}" title="${esc(booking.title)} · ${esc(groupInfo)} · ${timeOnly(booking.start)}–${timeOnly(booking.start+booking.minutes*60)}">${first?`<span class="calendar-cell-label"><strong>${esc(groupInfo)}</strong><small>${esc(booking.title)} · ${timeOnly(booking.start)}</small></span>`:''}</div>`);}else if(av){const first=av.start>=ts&&av.start<cellEnd;rows.push(`<div class="calendar-cell teacher-open" title="Teacher available ${timeOnly(av.start)}–${timeOnly(av.end)}">${first?'<span class="calendar-cell-label subtle">Available</span>':''}</div>`);}else rows.push('<div class="calendar-cell"></div>');}else{const availability=schedule.availability.find(a=>a.start<=ts&&a.end>=cellEnd);const occupied=schedule.busy.find(b=>b.status==='scheduled'&&b.start<cellEnd&&b.start+b.minutes*60>ts);const canStart=availability&&ts+lesson.minutes*60<=availability.end+0.001&&ts>Date.now()/1000+30&&slotFits(ts,lesson.minutes);if(canStart){const label=`${date(ts,{weekday:'long',month:'short',day:'numeric'})}, ${timeOnly(ts)}–${timeOnly(ts+lesson.minutes*60)}`;rows.push(`<button type="button" class="calendar-cell slot-cell" data-requestslot="${ts}" data-availability="${availability.id}" aria-label="Book ${esc(lesson.name)} on ${esc(label)}" title="Book ${esc(label)}"><span class="slot-plus" aria-hidden="true">+</span></button>`);}else if(occupied){rows.push('<div class="calendar-cell blocked" title="Unavailable"></div>');}else if(availability){rows.push('<div class="calendar-cell teacher-open student-open" title="Teacher is available, but the selected lesson cannot start here."></div>');}else rows.push('<div class="calendar-cell"></div>');}}}
const headers=[];const now=Math.floor(Date.now()/1000);for(let i=0;i<7;i++){const d=new Date(start);d.setDate(d.getDate()+i);const ts=Math.floor(d.getTime()/1000);headers.push(`<div class="calendar-day ${sameCalendarDay(ts,now)?'today':''}"><span>${date(ts,{weekday:'short'})}</span><strong>${date(ts,{day:'numeric'})}</strong><small>${date(ts,{month:'short'})}</small></div>`);}return `<div class="weekly-calendar ${admin?'admin-calendar':''}"><div class="calendar-grid"><div class="calendar-corner">Time</div>${headers.join('')}${rows.join('')}</div></div>`;}
function dayHeading(ts){const now=Date.now()/1000,today=dayKey(now),tomorrow=dayKey(now+86400),yesterday=dayKey(now-86400),key=dayKey(ts);if(key===today)return `Today · ${date(ts,{weekday:'long',month:'short',day:'numeric'})}`;if(key===tomorrow)return `Tomorrow · ${date(ts,{weekday:'long',month:'short',day:'numeric'})}`;if(key===yesterday)return `Yesterday · ${date(ts,{weekday:'long',month:'short',day:'numeric'})}`;return date(ts,{weekday:'long',month:'short',day:'numeric',year:'numeric'});}
function byDayHTML(list,renderer){const groups=[];for(const item of [...list].sort((a,b)=>a.start-b.start)){const key=dayKey(item.start);let group=groups.at(-1);if(!group||group.key!==key){group={key,start:item.start,items:[]};groups.push(group);}group.items.push(item);}return groups.map(g=>`<section class="class-day-group"><div class="class-day-heading"><span>${esc(dayHeading(g.start))}</span><small>${g.items.length} class${g.items.length===1?'':'es'}</small></div><div class="class-day-items">${g.items.map(renderer).join('')}</div></section>`).join('');}

function classWatchSignature(list){return JSON.stringify(list.filter(c=>c.mine).map(c=>[c.id,c.live,c.status,c.approval,c.start,c.minutes]));}
function stopAccountWatcher(){
  if(accountWatchTimer!==null){clearInterval(accountWatchTimer);accountWatchTimer=null;}
  accountWatchBusy=false;
}
function startAccountWatcher(){
  clearInterval(accountWatchTimer);
  let signature=classWatchSignature(classes);
  const check=async()=>{
    if(accountWatchBusy||document.hidden||location.pathname!=='/account')return;
    accountWatchBusy=true;
    try{
      const next=(await api('/api/classes')).classes;
      const nextSignature=classWatchSignature(next);
      if(nextSignature!==signature){classes=next;signature=nextSignature;await booking(true);}
    }catch{}finally{accountWatchBusy=false;}
  };
  accountWatchTimer=setInterval(check,2000);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)check();},{once:true});
}
async function booking(account=false){
  if(account&&!me){location.href='/login';return;}
  if(account){
    const visible=classes.filter(c=>c.mine).sort((a,b)=>a.start-b.start);
    $('#app').innerHTML=`<div class="pagehead"><div><p class="eyebrow">Student dashboard</p><h1>My lessons</h1><p class="muted">Lessons are grouped by day so it is easier to see what is happening today and later in the week.</p><p class="meta auto-status"><span class="status-dot"></span> Classroom status updates automatically every few seconds.</p></div><a href="/booking" class="button">Book another lesson</a></div>${visible.length?byDayHTML(visible,c=>classCard(c)):'<div class="empty"><h3>No lessons booked yet</h3><p>Choose a private lesson time or reserve a seat in an upcoming group lesson.</p><a class="button" href="/booking">Find a lesson</a></div>'}`;
    bindClassActions(()=>booking(true));startAccountWatcher();return;
  }
  await refreshSchedule();
  const groupLessons=classes.filter(c=>c.class_kind==='group'&&c.approval==='confirmed'&&c.status==='scheduled'&&c.start>Date.now()/1000).sort((a,b)=>a.start-b.start);
  const params=new URLSearchParams(location.search);const selectedId=+(params.get('lesson')||schedule.lesson_types[0]?.id||0);const lesson=schedule.lesson_types.find(x=>x.id===selectedId)||schedule.lesson_types[0];const start=weekStartFromParam();
  const groupSection=`<section class="section group-booking-section"><div class="sectionhead"><div><p class="eyebrow">Small-group lessons</p><h2>Join a scheduled group</h2><p class="muted">The teacher sets the time and number of seats. Reserve one seat instantly; everyone booked into the group gets a shared chat.</p></div></div>${groupLessons.length?`<div class="group-lessons-by-day">${byDayHTML(groupLessons,c=>groupLessonCard(c))}</div>`:'<div class="empty compact"><h3>No group lessons posted yet</h3><p>New group sessions will appear here when the teacher opens them.</p></div>'}</section>`;
  if(!lesson){$('#app').innerHTML=`<div class="pagehead"><div><h1>Book a lesson</h1></div></div>${groupSection}`;bindClassActions(()=>booking(false));return;}
  $('#app').innerHTML=`<div class="pagehead booking-head"><div><p class="eyebrow">Book a lesson</p><h1>Choose private or small-group learning.</h1><p class="muted">Reserve a seat in a posted group lesson, or choose a private lesson and select an available start time.</p></div>${me?'<a class="button secondary" href="/account">My lessons</a>':'<a class="button" href="/login?next=/booking">Log in to book</a>'}</div>${groupSection}<section class="section private-booking"><div class="sectionhead"><div><p class="eyebrow">Private lessons</p><h2>Book one-to-one time</h2></div></div><section class="booking-picker panel"><div><label for="lessonChoice">Lesson</label><select id="lessonChoice">${schedule.lesson_types.map(l=>`<option value="${l.id}" ${l.id===lesson.id?'selected':''}>${esc(lessonLabel(l))}</option>`).join('')}</select><p class="field-help">Available starts update automatically for the selected duration.</p></div><div class="price-box"><span>Lesson price</span><strong>${esc(lesson.price_label)}</strong><small>Final pricing will be confirmed by the teacher.</small></div></section><div class="week-toolbar"><a class="button secondary small" href="/booking?lesson=${lesson.id}&week=${shiftWeek(start,-1)}">← Previous week</a><div><span class="toolbar-kicker">Weekly availability</span><h2>${date(start.getTime()/1000,{month:'short',day:'numeric'})} – ${date(shiftWeek(start,1)-86400,{month:'short',day:'numeric',year:'numeric'})}</h2></div><a class="button secondary small" href="/booking?lesson=${lesson.id}&week=${shiftWeek(start,1)}">Next week →</a></div>${calendarLegendHTML(false)}<div class="calendar-note"><strong>${esc(lesson.name)}</strong><span>${lesson.minutes} minutes</span><span>Times are shown in ${esc(settings.timezone||'the studio timezone')}</span></div>${scheduleWeekHTML(start,lesson)}<p class="calendar-help">The calendar is divided into 15-minute intervals. Green <strong>+</strong> cells are valid start times for your selected lesson. A requested time is held while the teacher reviews it.</p></section>`;
  $('#lessonChoice').onchange=e=>{const q=new URLSearchParams(location.search);q.set('lesson',e.target.value);location.href='/booking?'+q.toString();};
  document.querySelectorAll('[data-requestslot]').forEach(b=>b.onclick=async()=>{if(!me){location.href='/login?next=/booking';return;}const st=+b.dataset.requestslot;const message=`Request ${lesson.name} (${lesson.minutes} min) on ${date(st,{weekday:'long',month:'short',day:'numeric'})} at ${timeOnly(st)}?`;if(!confirm(message))return;b.disabled=true;try{await api('/api/request-booking',{lesson_type_id:lesson.id,availability_id:+b.dataset.availability,start:st});await refreshClasses();toast('Booking request sent. The time is now held for you pending teacher confirmation.');location.href='/account';}catch(ex){toast(ex.message);await booking(false);}});
  document.querySelectorAll('[data-groupjoin]').forEach(b=>b.onclick=async()=>{if(!me){location.href='/login?next=/booking';return;}const c=classes.find(x=>x.id===+b.dataset.groupjoin);if(!c)return;if(!confirm(`Reserve a seat in ${c.title} on ${when(c)}?`))return;b.disabled=true;try{const r=await api('/api/group-booking/join',{class_id:c.id});await refreshClasses();toast('Your seat is reserved. You have also been added to the group chat.');location.href=r.group_chat_id?`/messages?group=${r.group_chat_id}`:'/account';}catch(ex){toast(ex.message);b.disabled=false;}});
  bindClassActions(()=>booking(false));
}
function bindClassActions(rerender){
  document.querySelectorAll('[data-unbook],[data-classaction]').forEach(b=>b.onclick=async()=>{if(b.dataset.unbook&&!confirm('Cancel this booking?'))return;if(['cancel','end'].includes(b.dataset.classaction)&&!confirm(b.dataset.classaction==='cancel'?'Cancel this class?':'End this class and close the classroom?'))return;b.disabled=true;try{if(b.dataset.classaction)await api('/api/admin/class-action',{class_id:+b.dataset.id,action:b.dataset.classaction});else await api('/api/unbook',{class_id:+b.dataset.unbook});await refreshClasses();await refreshSchedule();await rerender();toast('Updated.');}catch(ex){toast(ex.message);b.disabled=false;}});
  document.querySelectorAll('[data-teacherlaunch]').forEach(b=>b.onclick=async()=>{b.disabled=true;try{const r=await api('/api/admin/teacher-app-launch',{class_id:+b.dataset.teacherlaunch});if(r.launched)toast('Teacher Meeting app opened on this computer.');else if(r.already_running)toast('The Teacher Meeting app is already open for this class.');else if(!r.windows_app_supported)toast('The native teacher app is Windows-only. Use the web classroom on this device.');else toast('The classroom opened, but Windows could not start the teacher app. '+(r.launch_error||'Run teacher_meeting_app.py from the MathStudio folder.'));await refreshClasses();await refreshSchedule();await rerender();}catch(ex){toast(ex.message);b.disabled=false;}});
}
async function admin(){
  if(!isAdmin()){location.href='/login';return;}
  const [info,fileInfo]=await Promise.all([api('/api/admin'),api('/api/admin/files'),refreshSchedule(),refreshClasses()]);
  const tz=Intl.DateTimeFormat().resolvedOptions().timeZone,start=weekStartFromParam();
  const pending=info.bookings.filter(b=>b.status==='scheduled'&&b.approval==='pending');
  const scheduledClasses=classes.filter(c=>c.status==='scheduled').sort((a,b)=>{const now=Date.now()/1000;const ar=a.live?0:(a.start<=now?1:2),br=b.live?0:(b.start<=now?1:2);return ar-br||a.start-b.start;});
  const selectableUsers=info.users.filter(u=>u.id!==me.id);
  const userChecks=(prefix,selected=[])=>`<div class="user-check-grid">${selectableUsers.map(u=>`<label class="user-check"><input type="checkbox" name="${prefix}" value="${u.id}" ${selected.includes(u.id)?'checked':''}><span><strong>${esc(u.name)}</strong><small>@${esc(u.username)} · ${esc(u.role)}</small></span></label>`).join('')}</div>`;
  const manualGroups=info.groups.filter(g=>g.kind==='manual'),lessonGroups=info.groups.filter(g=>g.kind==='lesson');
  const groupCards=manualGroups.length?manualGroups.map(g=>`<details class="admin-group-card" data-admin-group="${g.id}"><summary><span><strong>${esc(g.name)}</strong><small>${g.member_count} members</small></span><span class="tag gray">Custom group</span></summary><div><label>Group name</label><input class="group-edit-name" value="${esc(g.name)}" maxlength="100">${userChecks('group_member_'+g.id,g.members.map(m=>m.id))}<div class="actions"><button type="button" class="small" data-savegroup="${g.id}">Save group</button><button type="button" class="small danger" data-deletegroup="${g.id}">Delete group</button><a class="button secondary small" href="/messages?group=${g.id}">Open chat</a></div></div></details>`).join(''):'<div class="empty compact"><p>No custom group chats yet.</p></div>';
  const lessonGroupCards=lessonGroups.length?`<div class="lesson-group-list">${lessonGroups.map(g=>`<article class="mini-group-card"><div><strong>${esc(g.name)}</strong><span>${g.members.map(m=>esc(m.name)).join(', ')||'Teacher only'}</span></div><div><span class="tag">Lesson group</span><a class="button secondary small" href="/messages?group=${g.id}">Open chat</a></div></article>`).join('')}</div>`:'';
  const confirmedScheduled=scheduledClasses.filter(c=>c.approval==='confirmed');
  $('#app').innerHTML=`<div class="pagehead admin-pagehead"><div><p class="eyebrow">Teacher workspace</p><h1>Admin dashboard</h1><p class="muted">Manage the studio from one place. Start with the quick actions, then use the full-width schedule and management sections below.</p></div><a class="button secondary" href="/booking">Preview student booking page</a></div>
  <div class="admin-stat-grid"><article><span>Registered users</span><strong>${info.users.length}</strong><small>Accounts available for groups</small></article><article><span>Pending requests</span><strong>${pending.length}</strong><small>Private lessons waiting for review</small></article><article><span>Group chats</span><strong>${info.groups.length}</strong><small>Custom and lesson groups</small></article><article><span>Classes to handle</span><strong>${confirmedScheduled.length}</strong><small>Upcoming, live, or waiting to be started</small></article></div>
  <section class="admin-guide"><div><p class="eyebrow">Recommended workflow</p><h2>What to do from this page</h2></div><ol class="admin-guide-steps"><li><span>1</span><div><strong>Set teaching times</strong><small>Add private availability or post a group lesson.</small></div></li><li><span>2</span><div><strong>Prepare materials</strong><small>Upload files, bundle them, and generate student access codes.</small></div></li><li><span>3</span><div><strong>Organize students</strong><small>Review accounts and create persistent group chats.</small></div></li><li><span>4</span><div><strong>Run the week</strong><small>Review requests, start the Teacher Meeting app, and message students.</small></div></li></ol></section>
  <div class="admin-jump-links" role="navigation" aria-label="Admin page sections"><a href="#admin-quick-actions">Quick actions</a><a href="#admin-schedule">Schedule</a><a href="#admin-bookings">Bookings</a><a href="#admin-users">Users</a><a href="#admin-groups">Group chats</a><a href="#admin-files">Files</a><a href="#admin-site">Website</a></div>
  <section class="section admin-wide-section teacher-app-callout"><div class="teacher-app-icon" aria-hidden="true">✎</div><div><p class="eyebrow">Live teaching</p><h2>Teacher Meeting app</h2><p>The teacher no longer needs to copy annotation codes or keep MathStudio open just to draw. Starting a confirmed class launches the Windows Teacher Meeting app automatically on the computer running this MathStudio server.</p><ul class="teacher-app-points"><li>Draw directly over Chrome, PowerPoint, PDFs, or any other Windows app.</li><li>Student annotations from the website appear on the teacher’s desktop overlay automatically.</li><li>Use <strong>Interact</strong> mode to click through the overlay, then switch to <strong>Draw</strong> when you want to annotate.</li></ul><p class="meta">Students still join from My lessons in their browser. Camera, microphone, and screen-share controls remain available from the app’s “Camera / screen share” button.</p></div></section>
  <section id="admin-quick-actions" class="section admin-quick-section"><div class="sectionhead"><div><p class="eyebrow">Quick actions</p><h2>Create lessons and prepare files</h2><p class="meta">These are the two tasks you will use most often. They sit side by side on larger screens and stack automatically on smaller devices.</p></div></div><div class="admin-action-grid"><section class="admin-action-card group-lesson-admin"><div class="admin-card-head"><div><p class="eyebrow">Small-group booking</p><h2>Post a group lesson</h2><p class="meta">Students reserve seats instantly until the class is full. Everyone who books is added to the lesson group chat.</p></div></div><ol class="instruction-list"><li><strong>Name the lesson and choose its duration.</strong><span>Use a clear title students will recognize.</span></li><li><strong>Pick the date, time, seats, and price.</strong><span>Times use 15-minute increments.</span></li><li><strong>Choose whether it repeats weekly.</strong><span>One shared group chat is created for the whole series.</span></li></ol><form id="groupLessonForm" class="admin-compact-form">${errors}<div class="two"><div>${input('group_lesson_title','Lesson title','text','','required maxlength="140"')}</div><div><label for="group_lesson_type">Lesson type & duration</label><select id="group_lesson_type" name="lesson_type_id">${schedule.lesson_types.map(l=>`<option value="${l.id}">${esc(lessonLabel(l))}</option>`).join('')}</select></div></div><div class="group-lesson-form-grid"><div><label for="group_lesson_date">Date</label><input id="group_lesson_date" name="date" type="date" required></div><div><label for="group_lesson_time">Start time</label><select id="group_lesson_time" name="time">${quarterTimeOptions()}</select></div><div><label for="group_lesson_capacity">Student seats</label><select id="group_lesson_capacity" name="capacity">${[2,3,4,5].map(n=>`<option value="${n}">${n} students</option>`).join('')}</select></div><div>${input('group_price_label','Price per student','text','Price TBD','maxlength="80"')}</div></div><label for="group_lesson_description">What will students work on?</label><textarea id="group_lesson_description" name="description" maxlength="2000" placeholder="Example: Linear equations review and contest-style practice"></textarea><div class="repeat-row"><label><input id="group_repeat_weekly" type="checkbox"> Repeat this lesson weekly</label><div id="groupRepeatWeeksWrap" class="hidden">${input('group_weeks','Number of weeks','number','6','min="2" max="24"')}</div></div><button>Post group lesson</button></form></section>${fileUploadQuickHTML(fileInfo)}</div></section>
  <section id="admin-schedule" class="section admin-wide-section"><div class="sectionhead"><div><p class="eyebrow">Schedule</p><h2>Private availability & weekly calendar</h2><p class="meta">Add the hours students may use for private bookings. The calendar stays full width so the 15-minute grid remains easy to read.</p></div></div><div class="admin-help-box"><strong>Private availability is different from a group lesson.</strong><span>Availability opens a block of time that private students can request. Group lessons are fixed sessions you post yourself and automatically occupy their scheduled time.</span></div><div class="panel admin-availability-panel"><div class="panel-heading"><div><h3>Add private-lesson availability</h3><p class="meta">Choose a start and end time. Students will only see lesson starts that fully fit inside this block.</p></div></div><form id="availabilityForm">${errors}<div class="availability-time-grid"><div><label>Available from — your device timezone: ${esc(tz)}</label><div class="date-time-picker"><input id="start_date" name="start_date" type="date" required><select id="start_time" name="start_time" required aria-label="Start time">${quarterTimeOptions()}</select></div><p class="field-help">Only :00, :15, :30, and :45 can be selected.</p></div><div><label>Available until</label><div class="date-time-picker"><input id="end_date" name="end_date" type="date" required><select id="end_time" name="end_time" required aria-label="End time">${quarterTimeOptions()}</select></div><p class="field-help">Make the block long enough for the lesson lengths you want students to book.</p></div></div><div class="repeat-row"><label><input id="repeat_weekly" name="repeat_weekly" type="checkbox"> Repeat this availability weekly</label><div id="repeatWeeksWrap" class="hidden">${input('weeks','Number of weeks','number','8','min="2" max="24"')}</div></div><button>Add availability</button></form></div><div class="week-toolbar"><a class="button secondary small" href="/admin?week=${shiftWeek(start,-1)}#admin-schedule">← Previous</a><div><span class="toolbar-kicker">Teaching calendar</span><h2>${date(start.getTime()/1000,{month:'short',day:'numeric'})} – ${date(shiftWeek(start,1)-86400,{month:'short',day:'numeric',year:'numeric'})}</h2></div><a class="button secondary small" href="/admin?week=${shiftWeek(start,1)}#admin-schedule">Next →</a></div>${calendarLegendHTML(true)}${scheduleWeekHTML(start,schedule.lesson_types[0],true,info.calendar_classes||info.bookings)}${availabilityManagerHTML(start)}</section>
  <section id="admin-bookings" class="section admin-wide-section"><div class="sectionhead"><div><p class="eyebrow">Bookings</p><h2>Private lesson requests</h2><p class="meta">A pending request already holds its time. Confirm it once, turn it into a weekly series, or decline it to release the slot.</p></div><span class="tag orange">${pending.length} pending</span></div>${pending.length?pending.map(b=>`<article class="card request-card"><div><span class="tag orange">Pending</span><h3>${esc(b.title)}</h3><p><strong>${esc(b.name)}</strong> <span class="muted">@${esc(b.username)}</span></p><p class="meta">${esc(date(b.start,{weekday:'long',month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}))} · ${b.minutes} min · ${esc(b.price_label)}</p></div><div class="actions"><button class="small" data-bookingaction="confirm" data-id="${b.class_id}">Confirm once</button><button class="small secondary" data-bookingaction="confirm_weekly" data-id="${b.class_id}">Confirm + repeat weekly</button><button class="small danger" data-bookingaction="reject" data-id="${b.class_id}">Decline</button></div></article>`).join(''):'<div class="empty compact"><h3>No requests waiting</h3><p>New private lesson requests will appear here automatically.</p></div>'}<div class="admin-subsection"><div class="sectionhead"><div><h3>Confirmed classes to handle</h3><p class="meta">Classes stay here after their scheduled start until you start/end them or cancel them. Starting a class opens the Windows Teacher Meeting app automatically. If you are late, use <strong>Start late in teacher app</strong>.</p></div><span class="tag gray">${confirmedScheduled.length} scheduled</span></div>${confirmedScheduled.length?byDayHTML(confirmedScheduled,c=>classCard(c,true)):'<div class="empty compact">No confirmed classes to handle.</div>'}</div></section>
  <section id="admin-users" class="section admin-user-section admin-wide-section"><div class="sectionhead"><div><p class="eyebrow">Accounts</p><h2>Users</h2><p class="meta">Every registered account appears here. Use this list to identify students before adding them to a group chat. Only give Admin access to another trusted teacher or site manager.</p></div><span class="tag gray">${info.users.length} accounts</span></div><div class="admin-help-box"><strong>Tip:</strong><span>You do not need to make a student an admin to put them in a group. Group membership is managed in the next section.</span></div><div class="tablewrap"><table><thead><tr><th>Name</th><th>Username</th><th>Role</th><th>Bookings</th><th>Groups</th><th>Access</th></tr></thead><tbody>${info.users.map(u=>`<tr><td><strong>${esc(u.name)}</strong></td><td>@${esc(u.username)}</td><td>${esc(u.role)}</td><td>${u.booking_count||0}</td><td>${u.group_count||0}</td><td>${u.id!==me.id?`<button class="secondary small" data-role="${u.role==='admin'?'student':'admin'}" data-id="${u.id}">${u.role==='admin'?'Remove admin':'Make admin'}</button>`:'You'}</td></tr>`).join('')}</tbody></table></div></section>
  <section id="admin-groups" class="section admin-groups admin-wide-section"><div class="sectionhead"><div><p class="eyebrow">Communication</p><h2>Group chats</h2><p class="meta">Create long-term groups such as “Grade 7 Class 1”. Members can keep using the chat before and after live meetings, and resource codes become clickable file links.</p></div><a class="button secondary small" href="/messages">Open Messages</a></div><div class="admin-group-layout"><form id="createGroupForm" class="panel group-create-panel">${errors}<h3>Create a group chat</h3><p class="meta">Give the group a clear name, then check every student who should receive its messages.</p>${input('group_name','Group name','text','','required maxlength="100"')}<label>Members</label>${userChecks('new_group_member')}<p class="field-help">You are included automatically as the teacher. You can change the member list later.</p><button>Create group chat</button></form><div class="admin-existing-groups"><h3>Existing custom groups</h3><p class="meta">Expand a group to rename it, change members, delete it, or open its conversation.</p>${groupCards}${lessonGroupCards?`<h3 class="subsection-title">Automatic lesson groups</h3><p class="meta">These are created by group lesson bookings and share membership with the booked students.</p>${lessonGroupCards}`:''}</div></div></section>
  <div id="adminFileAnchor"></div>
  <section id="admin-site" class="section admin-wide-section"><div class="sectionhead"><div><p class="eyebrow">Website management</p><h2>Studio settings & announcements</h2><p class="meta">These tools change public website content. They do not affect bookings or student accounts.</p></div></div><div class="admin-settings-grid"><details open><summary><span>Home page & teacher details</span><small>Studio name, introduction, contact details, and timezone</small></summary><div><form id="settings">${errors}${input('name','Studio name','text',settings.name,'required maxlength="100"')}${input('headline','Home page headline','text',settings.headline,'required maxlength="200"')}${area('intro','Introduction',settings.intro,1500)}${input('teacher','Teacher name','text',settings.teacher,'required maxlength="100"')}${area('about','About the teacher',settings.about,1500)}${input('contact','Public contact information','text',settings.contact,'maxlength="200"')}<label for="timezone">Display timezone</label><select id="timezone" name="timezone">${['America/Edmonton','America/Vancouver','America/Toronto','UTC'].map(t=>`<option ${settings.timezone===t?'selected':''}>${t}</option>`).join('')}</select><button>Save website details</button></form></div></details><details open><summary><span>Publish an announcement</span><small>Post a notice on the home page for students and families</small></summary><div><p class="meta">Use announcements for schedule changes, reminders, registration notices, or general updates.</p><form id="newpost">${errors}${input('posttitle','Title','text','','required maxlength="160"')}${area('postbody','Announcement','',20000)}<button>Publish on home page</button></form></div></details></div></section>
  <section class="section admin-wide-section admin-secondary-tools"><div class="sectionhead"><div><p class="eyebrow">Reference</p><h2>Advanced records</h2><p class="meta">These sections are useful occasionally, so they stay collapsed to keep the main admin workflow easier to scan.</p></div></div><details><summary><span>Lesson options & pricing (${schedule.lesson_types.length})</span><small>Review the lesson names, durations, and price labels students can choose</small></summary><div><p class="meta">Private and group lessons can use the same lesson types. Prices can remain placeholders until your final rates are set.</p><div class="lesson-list">${schedule.lesson_types.map(l=>`<div><strong>${esc(l.name)}</strong><span>${l.minutes} min</span><span>${esc(l.price_label)}</span></div>`).join('')}</div></div></details><details><summary><span>All bookings (${info.bookings.length})</span><small>Complete booking history for private and group lessons</small></summary><div class="tablewrap"><table><thead><tr><th>Student</th><th>Class</th><th>Type</th><th>Status</th><th>Date</th></tr></thead><tbody>${info.bookings.map(b=>`<tr><td>${esc(b.name)}</td><td>${esc(b.title)} · ${b.minutes} min</td><td>${b.class_kind==='group'?'Group':'Private'}</td><td>${esc(b.approval)}${b.series_id?' · weekly series':''}</td><td>${esc(date(b.start,{dateStyle:'medium',timeStyle:'short'}))}</td></tr>`).join('')}</tbody></table>${!info.bookings.length?'<p class="muted">No bookings yet.</p>':''}</div></details></section>`;
  mountFileLibrary(fileInfo);
  const repeat=$('#repeat_weekly'),wrap=$('#repeatWeeksWrap'),startDate=$('#start_date'),startTime=$('#start_time'),endDate=$('#end_date'),endTime=$('#end_time');
  repeat.onchange=()=>wrap.classList.toggle('hidden',!repeat.checked);
  const firstStart=ceilToQuarter(new Date(Date.now()+15*60*1000)),firstEnd=new Date(firstStart.getTime()+2*60*60*1000);startDate.value=localDateValue(firstStart);startTime.value=quarterTimeValue(firstStart);endDate.value=localDateValue(firstEnd);endTime.value=quarterTimeValue(firstEnd);
  const keepEndAfterStart=()=>{const st=combineLocalDateTime(startDate.value,startTime.value),en=combineLocalDateTime(endDate.value,endTime.value);if(st&&(!en||en<=st)){const next=new Date(st.getTime()+2*60*60*1000);endDate.value=localDateValue(next);endTime.value=quarterTimeValue(next);}};startDate.addEventListener('change',keepEndAfterStart);startTime.addEventListener('change',keepEndAfterStart);
  formHandler('#availabilityForm',async d=>{const st=combineLocalDateTime(d.start_date,d.start_time),en=combineLocalDateTime(d.end_date,d.end_time);if(!st||!en)throw new Error('Choose a valid start and end date and time.');if(en<=st)throw new Error('Available until must be later than Available from.');await api('/api/admin/availability',{start:st.getTime()/1000,end:en.getTime()/1000,repeat_weekly:repeat.checked,weeks:repeat.checked?(+d.weeks||8):1});await refreshSchedule();await admin();toast('Availability added.');});
  const groupRepeat=$('#group_repeat_weekly'),groupRepeatWrap=$('#groupRepeatWeeksWrap');groupRepeat.onchange=()=>groupRepeatWrap.classList.toggle('hidden',!groupRepeat.checked);const groupStart=ceilToQuarter(new Date(Date.now()+60*60*1000));$('#group_lesson_date').value=localDateValue(groupStart);$('#group_lesson_time').value=quarterTimeValue(groupStart);
  formHandler('#groupLessonForm',async d=>{const st=combineLocalDateTime(d.date,d.time);if(!st)throw new Error('Choose a valid group lesson date and time.');const r=await api('/api/admin/group-class',{title:d.group_lesson_title,lesson_type_id:+d.lesson_type_id,start:st.getTime()/1000,capacity:+d.capacity,price_label:d.group_price_label,description:d.description,repeat_weekly:groupRepeat.checked,weeks:groupRepeat.checked?(+d.group_weeks||6):1});toast(`Posted ${r.created} group lesson${r.created===1?'':'s'} and created its group chat.`);await admin();});
  $('#createGroupForm')?.addEventListener('submit',async ev=>{ev.preventDefault();const form=ev.currentTarget,button=form.querySelector('button'),name=$('#group_name').value.trim();const user_ids=[...form.querySelectorAll('input[name="new_group_member"]:checked')].map(x=>+x.value);button.disabled=true;try{await api('/api/admin/groups/create',{name,user_ids});toast('Group chat created.');await admin();}catch(ex){form.querySelector('.error').textContent=ex.message;form.querySelector('.error').classList.remove('hidden');button.disabled=false;}});
  document.querySelectorAll('[data-savegroup]').forEach(b=>b.onclick=async()=>{const card=b.closest('[data-admin-group]'),gid=+b.dataset.savegroup,name=card.querySelector('.group-edit-name').value.trim(),user_ids=[...card.querySelectorAll(`input[name="group_member_${gid}"]:checked`)].map(x=>+x.value);b.disabled=true;try{await api('/api/admin/groups/update',{group_id:gid,name,user_ids});toast('Group updated.');await admin();}catch(ex){toast(ex.message);b.disabled=false;}});
  document.querySelectorAll('[data-deletegroup]').forEach(b=>b.onclick=async()=>{if(!confirm('Delete this group chat and its message history?'))return;b.disabled=true;try{await api('/api/admin/groups/delete',{group_id:+b.dataset.deletegroup});toast('Group deleted.');await admin();}catch(ex){toast(ex.message);b.disabled=false;}});
  formHandler('#settings',async d=>{await api('/api/admin/settings',d);settings=(await api('/api/public')).settings;nav();toast('Website details saved.');});
  formHandler('#newpost',async d=>{await api('/api/admin/post',{title:d.posttitle,body:d.postbody});$('#newpost').reset();toast('Announcement published.');});
  bindClassActions(admin);
  document.querySelectorAll('[data-closeavail]').forEach(b=>b.onclick=async()=>{if(!confirm('Close this availability block to new bookings? Existing bookings stay scheduled.'))return;try{await api('/api/admin/availability-action',{availability_id:+b.dataset.closeavail,action:'close'});await admin();toast('Availability closed.');}catch(ex){toast(ex.message);}});
  document.querySelectorAll('[data-bookingaction]').forEach(b=>b.onclick=async()=>{let weeks=1;if(b.dataset.bookingaction==='confirm_weekly'){const raw=prompt('Repeat for how many weeks total? (2–24)','8');if(raw===null)return;weeks=+raw;if(!Number.isInteger(weeks)||weeks<2||weeks>24){toast('Enter a whole number from 2 to 24.');return;}}if(b.dataset.bookingaction==='reject'&&!confirm('Decline this booking request?'))return;b.disabled=true;try{const r=await api('/api/admin/booking-action',{class_id:+b.dataset.id,action:b.dataset.bookingaction,weeks});await admin();toast(b.dataset.bookingaction==='confirm_weekly'?`Confirmed ${r.created} weekly classes.`:b.dataset.bookingaction==='confirm'?'Booking confirmed.':'Booking declined.');}catch(ex){toast(ex.message);b.disabled=false;}});
  document.querySelectorAll('[data-role]').forEach(b=>b.onclick=async()=>{if(!confirm(b.dataset.role==='admin'?'Give this user admin access?':'Remove admin access from this user?'))return;try{await api('/api/admin/role',{user_id:+b.dataset.id,role:b.dataset.role});await admin();toast('Role updated.');}catch(ex){toast(ex.message);}});
}
function pageRefreshSignature(){
  return JSON.stringify({
    classes:classes.map(c=>[c.id,c.status,c.live,c.approval,c.start,c.minutes,c.booked,c.capacity,c.share_code||'']),
    availability:(schedule.availability||[]).map(a=>[a.id,a.start,a.end,a.status]),
    busy:(schedule.busy||[]).map(b=>[b.id,b.start,b.minutes,b.status,b.approval]),
    posts:(posts||[]).map(p=>[p.id,p.title,p.created])
  });
}
function userIsEditing(){
  const el=document.activeElement;
  return !!el&&['INPUT','TEXTAREA','SELECT'].includes(el.tagName)&&!el.disabled;
}
async function autoRefreshCurrentPage(){
  if(globalRefreshBusy||document.hidden||location.pathname==='/classroom'||location.pathname==='/login'||location.pathname==='/signup')return;
  globalRefreshBusy=true;
  try{
    const path=location.pathname;
    if(path==='/'||path==='/booking'||path==='/account'){
      const [nextClasses,nextSchedule,pub]=await Promise.all([api('/api/classes'),api('/api/schedule'),api('/api/public')]);
      classes=nextClasses.classes;schedule=nextSchedule;settings=pub.settings;posts=pub.posts;
      const sig=pageRefreshSignature();
      if(sig!==globalRefreshSig&&!userIsEditing()){
        globalRefreshSig=sig;
        if(path==='/')home();
        else if(path==='/booking')await booking(false);
        else if(path==='/account')await booking(true);
      }
    }else if(path==='/resources'&&!userIsEditing()){
      // Refresh access-code state so revocations/new translations appear without a manual reload.
      await resources();
    }
    nav();
  }catch{}finally{globalRefreshBusy=false;}
}
function startGlobalAutoRefresh(){
  if(globalRefreshTimer)clearInterval(globalRefreshTimer);
  globalRefreshSig=pageRefreshSignature();
  globalRefreshTimer=setInterval(autoRefreshCurrentPage,3000);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)autoRefreshCurrentPage();});
}
async function boot(){try{const r=await api('/api/me');me=r.user;csrf=r.csrf;const pub=await api('/api/public');settings=pub.settings;posts=pub.posts;nav();await refreshClasses();switch(location.pathname){case '/login':auth();break;case '/signup':auth(true);break;case '/booking':await booking();break;case '/account':await booking(true);break;case '/join':await instantJoin();break;case '/resources':await resources();break;case '/messages':if(me?.role==='guest'){location.href='/join';return;}await messagesPage();break;case '/classroom':if(!me){location.href='/join';return;}const {mountClassroom}=await import('./classroom.js?v=41_65');await mountClassroom({api,toast,me,settings,classes,esc});break;default:home();}startGlobalAutoRefresh();window.__MATHSTUDIO_BOOTED__=true;}catch(ex){window.__MATHSTUDIO_BOOT_ERROR__=String(ex?.stack||ex);$('#app').innerHTML=`<div class="error"><strong>Math Studio could not start.</strong><br>${esc(ex.message)}</div><p class="meta">Build v41.6-session-media-l10n</p><a href="/">Try again</a>`;}}
installLanguageObserver();
boot();
