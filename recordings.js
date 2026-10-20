import {management} from './recording_management.js';
import {tr} from './web_i18n.js';
// Authenticated teacher-only listing; access URLs expire and require this session.
const zh=localStorage.getItem('mathstudio_lang')==='zh';document.documentElement.lang=zh?'zh-CN':'en';
const text=(en,cn)=>zh?cn:en;const $=s=>document.querySelector(s);let csrf='';
$('#title').textContent=text('Recordings','录制');$('#reload').textContent=text('Refresh','刷新');$('#back').textContent=text('Teacher dashboard','教师主页');
async function api(path,data){const r=await fetch(path,{method:data?'POST':'GET',credentials:'same-origin',headers:data?{'Content-Type':'application/json','X-CSRF-Token':csrf}:{},body:data?JSON.stringify(data):undefined});const out=await r.json();if(!r.ok)throw new Error(tr(out.error||text('Request failed','请求失败')));return out;}
function showError(e){$('#status').textContent=e.message;}
function button(host,label,fn){const b=document.createElement('button');b.textContent=label;b.onclick=async()=>{b.disabled=true;try{await fn();}catch(e){showError(e);}finally{b.disabled=false;}};host.append(b);}
async function access(id,download){const r=await api('/api/admin/recordings/access',{id});if(download){const a=document.createElement('a');a.href=r.url+'&download=1';a.download='';a.click();}else{$('#player').src=r.url;$('#player').play().catch(()=>{});}}
async function reload(){
  const me=await api('/api/me');csrf=me.csrf;if(me.user?.role!=='admin')throw new Error(text('Sign in as an authorized teacher.','请使用已授权教师账户登录。'));
  const r=await api('/api/admin/recordings');$('#list').replaceChildren();
  $('#status').textContent=text('Private cloud recordings. Playback links expire after 60 seconds; reopen playback if seeking fails. Interrupted recordings may be incomplete.','私有云录制。播放链接 60 秒后过期；若拖动播放失败，请重新打开。中断的录制可能不完整。');
  for(const row of r.recordings){
    const box=document.createElement('section');box.className='panel';const title=document.createElement('h2');title.dataset.noTranslate='';title.textContent=row.meeting||text('Meeting','会议');box.append(title);
    const info=document.createElement('p');info.textContent=`${new Date(row.created*1000).toLocaleString()} · ${Math.round(row.duration)}s · ${text(row.state,({capturing:'正在录制',finalizing:'正在完成录制',indexing:'正在生成可拖动播放的视频',processing:'正在处理',uploading:'正在上传',ready:'已完成',failed:'失败',deleting:'正在删除',importing:'正在上传本地文件',local:'已保存到本地',empty:'无内容'})[row.state]||row.state)} · ${((row.mode==='local'?row.local_bytes:row.bytes)/1e9).toFixed(3)} GB${row.interrupted?text(' · interrupted',' · 已中断'):''}`;box.append(info);
    if(row.error){const diagnostic=document.createElement('p');diagnostic.textContent=tr(row.error);box.append(diagnostic);}
    if(row.state==='ready'){button(box,text('Play','播放'),()=>access(row.id,false));button(box,text('Download','下载'),()=>access(row.id,true));}
    if(row.state!=='capturing')button(box,text('Delete','删除'),async()=>{if(!confirm(text('Permanently delete this private recording?','永久删除此私有录制？')))return;await api('/api/admin/recordings/delete',{id:row.id});if($('#player').src.includes(row.id))$('#player').removeAttribute('src');await reload();});
    management(row,box,api,reload,zh);$('#list').append(box);
  }
  const selected=new URLSearchParams(location.search).get('selected');if(selected){const download=new URLSearchParams(location.search).get('download')==='1';history.replaceState(null,'','/recordings');await access(selected,download);}
}
$('#reload').onclick=()=>reload().catch(showError);reload().catch(showError);
