import {siteLang,tr} from './web_i18n.js';
const catalogs={en:{},zh:{}};
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export async function refreshPublicContent(api,pub){
  if(pub?.content_translations){for(const lang of ['en','zh'])catalogs[lang]=pub.content_translations[lang]||{};}
  else await Promise.all(['en','zh'].map(async lang=>{try{catalogs[lang]=(await api('/api/content-translations?lang='+lang)).translations;}catch{catalogs[lang]={};}}));
  updatePublicContent();
}
export function publicContent(kind,id,field,original){
  const key=`${kind}:${id}:${field}`;
  return `<span data-no-translate data-public-content="${esc(key)}" data-original="${esc(original)}">${render(key,String(original??''))}</span>`;
}
function render(key,original){
  if(!original)return '';
  const entry=catalogs[siteLang][key];
  if(entry&&entry.original===original)return esc(entry.text);
  return esc(original)+` <small class="translation-fallback">${esc(tr('translation.original'))}</small>`;
}
export function updatePublicContent(){
  for(const el of document.querySelectorAll('[data-public-content]')){
    const value=render(el.dataset.publicContent,el.dataset.original);
    if(el.innerHTML!==value)el.innerHTML=value;
  }
}
window.addEventListener('mathstudio-language',updatePublicContent);
