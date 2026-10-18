import {EN,ZH,KEYS} from './locales.js';
export let siteLang='en';
try{siteLang=localStorage.getItem('mathstudio_lang')==='zh'?'zh':'en';}catch{}
const rendered=new Map();
const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function tr(key,...args){
  key=EN[key]?key:KEYS[key]||key;
  const template=(siteLang==='zh'?ZH[key]:EN[key])||EN[key]||key;
  const value=template.replace(/\{(\d+)\}/g,(_,i)=>String(args[Number(i)]??''));
  if(EN[key]){rendered.set(value,{key,args});if(rendered.size>2048)rendered.delete(rendered.keys().next().value);}
  return value;
}
export function htmlText(key,...args){
  const prior=rendered.get(key);const resolved=EN[key]?key:KEYS[key]||prior?.key;if(!args.length&&prior)args=prior.args;
  if(!resolved)return escape(key);
  return `<span data-i18n="${resolved}" data-i18n-args="${escape(JSON.stringify(args))}">${escape(tr(resolved,...args))}</span>`;
}
export function uiText(element,value){
  if(!element)return;
  const binding=rendered.get(value);
  if(binding){element.dataset.i18n=binding.key;element.dataset.i18nArgs=JSON.stringify(binding.args);}
  else{delete element.dataset.i18n;delete element.dataset.i18nArgs;}
  element.textContent=value;
}
export function applySiteLanguage(root=document){
  const targetDocument=root.ownerDocument||(root.nodeType===9?root:document);
  targetDocument.documentElement.lang=siteLang==='zh'?'zh-CN':'en';
  const selector='[data-i18n],[data-i18n-title],[data-i18n-placeholder],[data-i18n-aria-label],[data-i18n-alt]';
  const nodes=[...(root.matches?.(selector)?[root]:[]),...(root.querySelectorAll?.(selector)||[])];
  for(const el of nodes){
    if(el.closest('[data-no-translate],.chat-text,code,pre,math'))continue;
    if(el.dataset.i18n){
      // Only explicitly marked UI hosts may rebind to a newly rendered UI status.
      const binding=rendered.get(el.textContent);
      if(binding&&binding.key!==el.dataset.i18n){el.dataset.i18n=binding.key;el.dataset.i18nArgs=JSON.stringify(binding.args);}
      let args=[];try{args=JSON.parse(el.dataset.i18nArgs||'[]');}catch{}
      const value=tr(el.dataset.i18n,...args);if(el.textContent!==value)el.textContent=value;
    }
    for(const attr of ['title','placeholder','aria-label','alt']){
      const key=el.getAttribute('data-i18n-'+attr);if(key){let args=[];try{args=JSON.parse(el.dataset.i18nArgs||'[]');}catch{}const value=tr(key,...args);if(el.getAttribute(attr)!==value)el.setAttribute(attr,value);}
    }
  }
}
export function setLanguage(language){
  siteLang=language==='zh'?'zh':'en';try{localStorage.setItem('mathstudio_lang',siteLang);}catch{}
  applySiteLanguage();window.dispatchEvent(new CustomEvent('mathstudio-language'));
}
export function installLanguageObserver(){
  applySiteLanguage();
  new MutationObserver(records=>{for(const record of records){
    if(record.type==='characterData')applySiteLanguage(record.target.parentElement);
    else{applySiteLanguage(record.target);for(const node of record.addedNodes)if(node.nodeType===1)applySiteLanguage(node);}
  }}).observe(document.body,{childList:true,subtree:true,characterData:true});
}
