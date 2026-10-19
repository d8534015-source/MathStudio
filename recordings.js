import {tr} from './web_i18n.js';
// Authenticated teacher-only listing; access URLs expire and require this session.
const zh=localStorage.getItem('mathstudio_lang')==='zh';document.documentElement.lang=zh?'zh-CN':'en';
const text=(en,cn)=>zh?cn:en;const $=s=>document.querySelector(s);let csrf='';
$('#title').textContent=text('Recordings','录制');$('#reload').textContent=text('Refresh','刷新');$('#back').textContent=text('Teacher dashboard','教师主页');
async function api(path,data){const r=await fetch(path,{method:data?'POST':'GET',credentials:'same-origin',headers:data?{'Content-Type':'application/json','X-CSRF-Token':csrf}:{},body:data?JSON.stringify(data):undefined});const out=await r.json();if(!r.ok)throw new Error(tr(out.error||text('Request failed','请求失败')));return out;}
function showError(e){$('#status').textContent=e.message;}
function button(host,label,fn){const b=document.createElement('button');b.textContent=label;b.onclick=()=>Promise.resolve(fn()).catch(showError);host.append(b);}
async function access(id,download){const r=await api('/api/admin/recordings/access',{id});if(download){const a=document.createElement('a');a.href=r.url+'&download=1';a.download='';a.click();}else{$('#player').src=r.url;$('#player').play().catch(()=>{});}}
async function reload(){
  const me=await api('/api/me');csrf=me.csrf;if(me.user?.role!=='admin')throw new Error(text('Sign in as an authorized teacher.','请使用已授权教师账户登录。'));
  const r=await api('/api/admin/recordings');$('#list').replaceChildren();
  $('#status').textContent=text('Private cloud recordings. Playback links expire after 60 seconds; reopen playback if seeking fails. Interrupted recordings may be incomplete.','私有云录制。播放链接 60 秒后过期；若拖动播放失败，请重新打开。中断的录制可能不完整。');
  for(const row of r.recordings){
    const box=document.createElement('section');box.className='panel';const title=document.createElement('h2');title.dataset.noTranslate='';title.textContent=row.meeting||text('Meeting','会议');box.append(title);
    const info=document.createElement('p');info.textContent=`${new Date(row.created*1000).toLocaleString()} · ${Math.round(row.duration)}s · ${text(row.state,({capturing:'正在录制',uploading:'正在上传',ready:'就绪',empty:'无内容'})[row.state]||row.state)} · ${(row.bytes/1024**2).toFixed(1)} MiB${row.interrupted?text(' · interrupted',' · 已中断'):''}`;box.append(info);
    if(row.state==='ready'){button(box,text('Play','播放'),()=>access(row.id,false));button(box,text('Download','下载'),()=>access(row.id,true));}
    if(row.state!=='capturing')button(box,text('Delete','删除'),async()=>{if(!confirm(text('Permanently delete this private recording?','永久删除此私有录制？')))return;await api('/api/admin/recordings/delete',{id:row.id});if($('#player').src.includes(row.id))$('#player').removeAttribute('src');await reload();});
    $('#list').append(box);
  }
  const selected=new URLSearchParams(location.search).get('selected');if(selected){const download=new URLSearchParams(location.search).get('download')==='1';history.replaceState(null,'','/recordings');await access(selected,download);}
}
$('#reload').onclick=()=>reload().catch(showError);reload().catch(showError);
