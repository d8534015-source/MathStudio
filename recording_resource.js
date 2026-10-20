import {formatAt} from './studio_time.js';
import {siteLang} from './web_i18n.js';
export function recordingResource(bundle,host){
  const zh=siteLang==='zh',r=bundle.recording;host.replaceChildren();
  const section=document.createElement('section');section.className='panel';
  const title=document.createElement('h2');title.dataset.noTranslate='';title.textContent=r.title;
  const meta=document.createElement('p');meta.textContent=formatAt(r.date*1000,r.timezone||'America/Edmonton',zh?'zh-CN':'en-CA',{dateStyle:'medium',timeStyle:'short'})+' · '+Math.round(r.duration)+'s';
  const notice=document.createElement('p');notice.textContent=zh?'仅授权的本课缺席学生可访问，请勿转发或再分发。下载的副本无法被远程收回。':'Only authorized absent enrollees may access this lesson. Do not forward or redistribute. Downloaded copies cannot be remotely recalled.';
  const video=document.createElement('video');video.controls=true;video.playsInline=true;video.preload='metadata';video.style.width='100%';video.src='/resource/recording?grant='+encodeURIComponent(bundle.grant);
  const label=document.createElement('h3');label.textContent=zh?'在线观看':'Watch Online';section.append(title,meta,notice,label,video);
  if(r.download){const a=document.createElement('a');a.className='button';a.textContent=zh?'下载录制':'Download Recording';a.href=video.src+'&download=1';section.append(a);}
  host.append(section);
}
