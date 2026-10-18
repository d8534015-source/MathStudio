import {tr,htmlText,applySiteLanguage} from './web_i18n.js';
// Separate browser editor for PUBLIC descriptions only; every API requires admin+CSRF.
export async function mountTranslationManager({api,me,esc,toast}){
  const app=document.querySelector('#app');
  if(me?.role!=='admin'){app.innerHTML=`<p role="alert">${htmlText('translation.teacher_only')}</p><a href="/login?next=/teacher/translations">${htmlText('ui.log_in')}</a>`;return;}
  const fieldKey=key=>{const [kind,id,field]=key.split(':');return kind==='settings'?'translation.field_'+field:'translation.field_'+kind;};
  const fieldArgs=key=>key.startsWith('settings:')?[]:[key.split(':')[1]];
  const state=await api('/api/admin/content-translations');
  app.innerHTML=`<h1>${htmlText('translation.manager')}</h1><p>${htmlText(state.config.offline?'translation.offline_privacy':'translation.privacy')}</p><p>${htmlText('translation.protected_help')}</p>
  <form id="translationConfig" class="panel"><p>${htmlText('translation.provider')}: ${state.config.provider==='disabled'?htmlText('translation.disabled'):`<span data-no-translate>${esc(state.config.provider)}</span>`}</p>
  <label><input type="checkbox" id="externalTranslation" ${state.config.enabled?'checked':''}>${htmlText(state.config.offline?'translation.offline_opt_in':'translation.opt_in')}</label>
  ${state.config.offline&&!state.config.configured?`<p role="status">${htmlText('translation.offline_unavailable')}</p>`:''}
  <label for="protectedTerms">${htmlText('translation.terms')}</label><textarea id="protectedTerms">${esc(state.config.terms.join('\n'))}</textarea><button>${htmlText('ui.save')}</button></form>
  <div class="panel"><label for="translationSource">${htmlText('translation.source')}</label><select id="translationSource">${state.sources.map(s=>`<option value="${esc(s.key)}" data-i18n="${fieldKey(s.key)}" data-i18n-args="${esc(JSON.stringify(fieldArgs(s.key)))}">${esc(tr(fieldKey(s.key),...fieldArgs(s.key)))}</option>`).join('')}</select>
  <label for="translationTarget">${htmlText('translation.target')}</label><select id="translationTarget"><option value="zh" data-i18n="translation.chinese">Simplified Chinese</option><option value="en" data-i18n="ui.english">English</option></select>
  <h2>${htmlText('translation.original_label')}</h2><pre id="translationOriginal" data-no-translate></pre>
  <div id="courseEditor" hidden><label for="courseDescription">${htmlText('translation.course_description')}</label><textarea id="courseDescription"></textarea><button id="saveCourse">${htmlText('translation.save_original')}</button></div>
  <label for="translationDraft">${htmlText('translation.draft')}</label><textarea id="translationDraft" rows="8" maxlength="20000" data-no-translate></textarea>
  <p id="translationStatus" role="status"></p><div class="actions"><button id="generateTranslation" ${!state.config.enabled||!state.config.configured?'disabled':''}>${htmlText('translation.generate')}</button><button id="regenerateTranslation" ${!state.config.enabled||!state.config.configured?'disabled':''}>${htmlText(state.config.offline?'translation.offline_regenerate':'translation.regenerate')}</button><button id="saveTranslation">${htmlText('translation.save_draft')}</button><button id="approveTranslation">${htmlText('translation.approve')}</button></div><p id="translationBusy" role="status"></p><p id="translationError" role="alert"></p></div>`;
  const $=id=>document.getElementById(id);let source,row,busy=false;
  function select(){source=state.sources.find(s=>s.key===$('translationSource').value);row=state.translations.find(t=>t.source_key===source?.key&&t.target===$('translationTarget').value);
    $('translationOriginal').textContent=source?.original||'';$('translationDraft').value=row?.draft||'';
    const course=source?.key.startsWith('courses:');$('courseEditor').hidden=!course;$('courseDescription').value=course?source.original:'';
    $('translationStatus').innerHTML=htmlText(row?.approved?'translation.approved':'translation.unapproved');applySiteLanguage(app);
  }
  $('translationSource').onchange=select;$('translationTarget').onchange=select;select();
  async function run(fn){
    if(busy)return;busy=true;$('translationError').textContent='';$('translationBusy').innerHTML=htmlText('translation.working');
    const key=$('translationSource').value,target=$('translationTarget').value;
    const controls=[...app.querySelectorAll('input,textarea,select,button')].map(el=>[el,el.disabled]);
    try{const pending=fn();for(const [el] of controls)el.disabled=true;await pending;await mountTranslationManager({api,me,esc,toast});$('translationSource').value=key;$('translationTarget').value=target;$('translationSource').onchange();}
    catch(ex){$('translationError').innerHTML=htmlText('translation.action_failed')+' <span data-no-translate>'+esc(tr(ex.message))+'</span>';}
    finally{for(const [el,disabled] of controls)el.disabled=disabled;$('translationBusy').textContent='';busy=false;}
  }
  $('translationConfig').onsubmit=e=>{e.preventDefault();run(()=>api('/api/admin/content-translations',{action:'config',enabled:$('externalTranslation').checked,terms:$('protectedTerms').value.split('\n').map(x=>x.trim()).filter(Boolean)}));};
  for(const [id,action,regenerate] of [['generateTranslation','generate',false],['regenerateTranslation','generate',true],['saveTranslation','save'],['approveTranslation','approve']]){
    $(id).onclick=()=>{if(!source)return;const target=$('translationTarget').value;
      run(()=>api('/api/admin/content-translations',{action,key:source.key,target,source_hash:source.source_hash,revision:row?.revision||0,text:$('translationDraft').value,regenerate}));};
  }
  $('saveCourse').onclick=()=>run(()=>api('/api/admin/course-description',{id:Number(source.key.split(':')[1]),description:$('courseDescription').value}));
}
