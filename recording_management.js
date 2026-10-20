// Teacher-only controls reuse the existing authenticated recording library.
export function management(row,box,api,reload,zh){
  const t=(en,cn)=>zh?cn:en;
  const btn=(label,fn)=>{const b=document.createElement('button');b.textContent=label;b.onclick=async()=>{b.disabled=true;try{await fn();}catch(e){status.textContent=e.message;}finally{b.disabled=false;}};box.append(b);return b;};
  const status=document.createElement('p');status.setAttribute('role','status');box.append(status);
  if(row.error)status.textContent=row.error;else if(row.state==='ready'&&row.playback_state!=='ready')status.textContent=t('Original saved. Seekable playback preparation needs the trusted OWNER processor before sharing.','原始文件已保存，分享前需由 OWNER 配置的可信处理器完成可跳转播放准备。');
  if(['local','importing'].includes(row.state)){
    const scope=JSON.parse(row.scope||'{}');
    btn(t('Watch a local file (no upload)','观看本地文件（不上传）'),async()=>{const input=document.createElement('input');input.type='file';input.accept=row.mime;input.onchange=()=>{const file=input.files[0];if(!file)return;const video=document.createElement('video');video.controls=true;video.style.width='100%';const url=URL.createObjectURL(file);video.src=url;video.onended=()=>URL.revokeObjectURL(url);box.append(video);};input.click();});
    if(scope.storage?.includes('cloud'))btn(t('Upload this local recording to private R2','将此本地录制上传到私有 R2'),async()=>{
      const input=document.createElement('input');input.type='file';input.accept=row.mime;
      input.onchange=async()=>{const file=input.files[0];if(!file)return;
        try{
          const manifest=await api('/api/admin/recordings/local-manifest',{id:row.id});
          if(!manifest.chunks.length||manifest.chunks.reduce((n,c)=>n+c.size,0)!==file.size)throw new Error(t('Selected file does not match this authorized recording.','所选文件与此已授权录制不匹配。'));
          const resume=await api('/api/admin/recordings/import',{id:row.id});let offset=0;
          for(const part of manifest.chunks){
            const blob=file.slice(offset,offset+part.size),digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',await blob.arrayBuffer()))).map(x=>x.toString(16).padStart(2,'0')).join('');
            if(digest!==part.digest)throw new Error(t('Local recording integrity mismatch.','本地录制完整性不匹配。'));
            if(part.sequence<resume.sequence){offset+=part.size;continue;}
            let ok=false;for(let attempt=0;attempt<3;attempt++){
              const me=await api('/api/me');const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),20000);
              try{const response=await fetch(`/api/admin/recordings/chunk?id=${row.id}&sequence=${part.sequence}`,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/octet-stream','X-CSRF-Token':me.csrf},body:blob,signal:controller.signal});if(response.ok){ok=true;break;}}finally{clearTimeout(timeout);}
            }
            if(!ok)throw new Error(t('Upload interrupted. OWNER retains acknowledged chunks.','上传中断，OWNER 保留已确认的片段。'));
            offset+=part.size;status.textContent=(100*offset/file.size).toFixed(1)+'%';
          }
          await api('/api/admin/recordings/finish',{id:row.id,complete:true,duration:row.duration});await reload();
        }catch(e){status.textContent=e.message;}
      };input.click();
    });
  }
  if(row.state!=='ready')return;
  btn(t('Manage absentee sharing','管理缺席学生分享'),async()=>{
    const result=await api('/api/admin/recordings/roster',{id:row.id});const form=document.createElement('section');box.append(form);
    const heading=document.createElement('h3');heading.dataset.noTranslate='';heading.textContent=result.lesson.title;form.append(heading);
    const inputs=[];
    for(const person of result.students){const label=document.createElement('label'),input=document.createElement('input');input.type='checkbox';input.disabled=!person.enrolled_at_capture||person.attendance==='present';input.value=person.id;inputs.push({input,person});const name=document.createElement('span');name.dataset.noTranslate='';name.textContent=person.name;label.append(input,name,document.createTextNode(' · '+t(person.attendance,({unknown:'待教师核实',present:'已出席',verified_absent:'已核实缺席'})[person.attendance]||person.attendance)));form.append(label,document.createElement('br'));}
    const selected=()=>inputs.filter(x=>x.input.checked);
    const verify=document.createElement('button');verify.textContent=t('Verify selected students were absent','核实所选学生确实缺席');verify.onclick=async()=>{try{if(!confirm(t('Confirm you independently verified absence; do not infer it merely from missing attendance data.','确认您已独立核实缺席，不能仅因没有出席记录就推断缺席。')))return;for(const x of selected()){await api('/api/admin/recordings/verify-absence',{id:row.id,user_id:x.person.id,confirmed:true});x.person.attendance='verified_absent';}status.textContent=t('Absence verified. You can now generate a restricted code.','缺席已核实，现在可生成受限分享码。');}catch(e){status.textContent=e.message;}};form.append(verify);
    const dlabel=document.createElement('label'),download=document.createElement('input');download.type='checkbox';dlabel.append(download,document.createTextNode(t('Allow downloads (only if original consent permits)','允许下载（仅在原始授权允许时）')));form.append(dlabel);
    const hours=document.createElement('input');hours.type='number';hours.min=1;hours.max=720;hours.value=24;hours.setAttribute('aria-label',t('Code lifetime in hours','分享码有效小时数'));form.append(hours);
    const create=document.createElement('button');create.textContent=t('Generate code for selected verified absentees','为所选已核实缺席学生生成分享码');create.onclick=async()=>{try{
      const viewers=selected();if(!viewers.length||viewers.some(x=>x.person.attendance!=='verified_absent'))throw new Error(t('Verify each selected absence first.','请先核实每位所选学生缺席。'));
      const r=await api('/api/admin/recordings/share',{id:row.id,viewers:viewers.map(x=>x.person.id),download:download.checked,expires:Math.min(row.expires,Date.now()/1000+Number(hours.value)*3600)});
      const code=document.createElement('input');code.readOnly=true;code.value=r.code;code.dataset.noTranslate='';form.append(code);
      const copy=document.createElement('button');copy.textContent=t('Copy code','复制分享码');copy.onclick=()=>navigator.clipboard.writeText(r.code).catch(()=>{code.select();});form.append(copy);
      const message=document.createElement('a');message.href='/messages';message.textContent=t('Open Messages (send manually)','打开消息（手动发送）');form.append(message);
      status.textContent=t('Code created for selected accounts only. Nothing was sent automatically.','分享码仅限所选账户使用，未自动发送。');
    }catch(e){status.textContent=e.message;}};form.append(create);
    const grants=await api('/api/admin/recordings/grants',{id:row.id});for(const grant of grants.grants){if(grant.revoked)continue;const revoke=document.createElement('button');revoke.textContent=t('Revoke grant from ','撤销分享授权，创建于 ')+new Date(grant.created*1000).toLocaleString();revoke.onclick=async()=>{await api('/api/admin/recordings/revoke',{id:row.id,grant_id:grant.grant_id});revoke.disabled=true;};form.append(revoke);}
  });
}
