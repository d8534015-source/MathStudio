import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const app=fs.readFileSync(process.env.MATHSTUDIO_APP_SOURCE||new URL('./app.js',import.meta.url),'utf8');
const zoneModule=new URL('./studio_time.js',import.meta.url);
const zoneHelpers=fs.existsSync(zoneModule)?await import(zoneModule):{};
if(zoneHelpers.setTimezoneRules)zoneHelpers.setTimezoneRules({
  zone:'America/Vancouver',start:Date.parse('2026-10-01T00:00:00Z')/1000,
  end:Date.parse('2028-01-01T00:00:00Z')/1000,
  transitions:[{at:Date.parse('2026-10-01T00:00:00Z')/1000,offset:-7*3600}]});

// Pinned tzdata 2026d: Alberta stays at UTC-6; Toronto retains DST.
if(zoneHelpers.setTimezoneRules){
  zoneHelpers.setTimezoneRules({zone:'America/Edmonton',start:Date.parse('2026-10-01T00:00:00Z')/1000,
    end:Date.parse('2028-01-01T00:00:00Z')/1000,transitions:[{at:Date.parse('2026-10-01T00:00:00Z')/1000,offset:-6*3600}]});
  zoneHelpers.setTimezoneRules({zone:'America/Toronto',start:Date.parse('2026-10-01T00:00:00Z')/1000,
    end:Date.parse('2028-01-01T00:00:00Z')/1000,transitions:[
      {at:Date.parse('2026-10-01T00:00:00Z')/1000,offset:-4*3600},
      {at:Date.parse('2026-11-01T06:00:00Z')/1000,offset:-5*3600},
      {at:Date.parse('2027-03-14T07:00:00Z')/1000,offset:-4*3600},
      {at:Date.parse('2027-11-07T06:00:00Z')/1000,offset:-5*3600}]});
}

function scheduleContext(zone='America/Edmonton'){
  const context={...zoneHelpers,URLSearchParams,settings:{timezone:zone},siteLang:'en',
    location:{search:'?week='+Date.parse('2026-10-26T18:00:00Z')/1000},
    schedule:{busy:[],availability:[]},esc:String,toast(){}};
  vm.createContext(context);
  vm.runInContext(app.slice(app.indexOf('function date('),app.indexOf('function nav()')),context);
  vm.runInContext(app.slice(app.indexOf('function weekStartFromParam()'),app.indexOf('function classWatchSignature(')),context);
  return context;
}

test('BOOK-02 calendar and inputs use studio timezone independently of device zone',()=>{
  const oldTZ=process.env.TZ;
  try{
    for(const device of ['UTC','Asia/Shanghai','America/Toronto']){
      process.env.TZ=device;
      const c=scheduleContext();
      assert.equal(c.weekStartFromParam().toISOString(),'2026-10-26T06:00:00.000Z',device);
      assert.equal(c.combineLocalDateTime('2026-11-01','16:00').toISOString(),'2026-11-01T22:00:00.000Z',device);
      assert.equal(c.minuteOfDay(Date.parse('2026-11-01T22:00:00Z')/1000),960);
      assert.equal(c.gridTimestamp(c.weekStartFromParam(),6,960),Date.parse('2026-11-01T22:00:00Z')/1000);
      assert.equal(c.localDateValue(new Date('2026-11-02T01:00:00Z')),'2026-11-01');
      assert.equal(c.quarterTimeValue(new Date('2026-11-02T01:00:00Z')),'19:00');
    }
  }finally{if(oldTZ===undefined)delete process.env.TZ;else process.env.TZ=oldTZ;}
});

test('BOOK-02 DST gaps are disabled and repeated times choose the earlier occurrence',()=>{
  const c=scheduleContext('America/Toronto');
  assert.equal(c.combineLocalDateTime('2027-03-14','02:30'),null);
  assert.equal(c.combineLocalDateTime('2026-11-01','01:30').toISOString(),'2026-11-01T05:30:00.000Z');
  assert.equal(c.combineLocalDateTime('2026-02-30','16:00'),null);
  c.location.search='?week='+Date.parse('2027-03-08T07:00:00Z')/1000;
  assert.equal(c.gridTimestamp(c.weekStartFromParam(),6,150),null);
  assert.doesNotThrow(()=>c.scheduleWeekHTML(c.weekStartFromParam(),{minutes:60,name:'Synthetic'}));
});

test('BOOK-02 booking cells submit the exact studio instant in every supported zone',()=>{
  for(const [zone,expected] of Object.entries({'America/Edmonton':'2026-11-01T22:00:00Z',
    'America/Vancouver':'2026-11-01T23:00:00Z','America/Toronto':'2026-11-01T21:00:00Z','UTC':'2026-11-01T16:00:00Z'})){
    const c=scheduleContext(zone),start=Date.parse(expected)/1000;
    c.schedule.availability=[{id:1,start,end:start+7200}];
    const html=c.scheduleWeekHTML(c.weekStartFromParam(),{minutes:60,name:'Synthetic'});
    assert.ok(html.includes('data-requestslot="'+start+'"'),zone);
    assert.equal(c.quarterTimeValue(new Date(start*1000)),'16:00',zone);
  }
});

test('BOOK-02 a changed studio timezone invalidates the displayed calendar',()=>{
  const c=scheduleContext();c.classes=[];c.posts=[];
  vm.runInContext(app.slice(app.indexOf('function pageRefreshSignature()'),app.indexOf('function userIsEditing()')),c);
  const before=c.pageRefreshSignature();c.settings.timezone='America/Toronto';
  assert.notEqual(c.pageRefreshSignature(),before);
});

test('UI-02 background refresh retains redeemed downloads and translation state',async()=>{
  const source=app.slice(app.indexOf('async function autoRefreshCurrentPage()'),app.indexOf('function startGlobalAutoRefresh()'));
  for(const mode of ['manual','linked','translated']){
    const result={grant:'synthetic',mode,language:'zh',translation:'Student content',downloads:['synthetic.pdf']};
    const context={globalRefreshBusy:false,document:{hidden:false},location:{pathname:'/resources'},
      userIsEditing:()=>false,nav(){},resources(){context.result=null;context.redemptions++;},result,redemptions:0};
    vm.createContext(context);vm.runInContext(source,context);
    for(let i=0;i<5;i++)await context.autoRefreshCurrentPage();
    assert.equal(context.result,result,mode+' resource DOM/state was replaced');
    assert.equal(context.redemptions,0,'refresh must not redeem the same code repeatedly');
  }
});


test('MEDIA-02 native sharing allows authorized drawing without changing media negotiation',()=>{
  const source=fs.readFileSync(new URL('./classroom.js',import.meta.url),'utf8');
  const c={joined:true,saving:false,presenter:null,viewMode:'call',nativeShare:{active:true},drawingAllowed:true,toast(){}};
  vm.createContext(c);
  vm.runInContext(source.slice(source.indexOf('function canDraw()'),source.indexOf('\n',source.indexOf('function canDraw()'))),c);
  assert.equal(c.canDraw(),true);
  c.drawingAllowed=false;assert.equal(c.canDraw(),false);
  c.drawingAllowed=true;c.nativeShare.active=false;assert.equal(c.canDraw(),false);
  c.viewMode='whiteboard';assert.equal(c.canDraw(),true);
  c.saving=true;assert.equal(c.canDraw(),false);
  c.saving=false;c.joined=false;assert.equal(c.canDraw(),false);
});

// Minimal DOM doubles exercise the actual live translator without a browser package.
class LanguageElement {
  constructor(tag='div',attrs={},children=[]){
    this.tag=tag;this.attrs={...attrs};this.nodeType=1;this.children=children;
    for(const child of children)child.parentElement=this;
  }
  getAttribute(key){return this.attrs[key]??null;}
  setAttribute(key,value){this.attrs[key]=value;}
  closest(selector){
    for(let el=this;el;el=el.parentElement){
      if(selector.split(',').some(s=>s==='[data-no-translate]'?'data-no-translate' in el.attrs:
        s.startsWith('.')?(el.attrs.class||'').split(' ').includes(s.slice(1)):s===el.tag))return el;
    }
    return null;
  }
  querySelectorAll(){return this.children.flatMap(x=>x.nodeType===1?[x,...x.querySelectorAll()]:[]);}
}
const languageText=value=>({nodeType:3,nodeValue:value});
function languageContext(){
  const document={documentElement:{lang:'en'},createTreeWalker(root){
    const nodes=[];const visit=n=>{for(const child of n.children||[])child.nodeType===3?nodes.push(child):visit(child);};
    visit(root);let i=0;return {nextNode:()=>nodes[i++]||null};
  }};
  const c={siteLang:'zh',document,Node:{TEXT_NODE:3},NodeFilter:{SHOW_TEXT:4}};
  vm.createContext(c);
  vm.runInContext(app.slice(app.indexOf('const SITE_ZH='),app.indexOf('function installLanguageObserver()')),c);
  vm.runInContext(app.slice(app.indexOf('const esc='),app.indexOf('let me=null')),c);
  vm.runInContext('globalThis.renderContent=content;globalThis.translateTemplate=tr',c);
  return c;
}

test('L10N-01 live translation preserves names, messages, labels, filenames and titles',()=>{
  const c=languageContext();
  for(const value of ['Teacher','Home','Schedule','Members: Teacher','学生','<script>alert(1)</script>']){
    const text=languageText(value),protectedEl=new LanguageElement('span',{'data-no-translate':'',title:value},[text]);
    const root=new LanguageElement('section',{},[protectedEl]);
    for(const lang of ['zh','en','zh']){c.siteLang=lang;c.applySiteLanguage(root);assert.equal(text.nodeValue,value);assert.equal(protectedEl.attrs.title,value);}
  }
  const message=languageText('Teacher');const bubble=new LanguageElement('div',{class:'chat-text'},[message]);
  c.applySiteLanguage(bubble);assert.equal(message.nodeValue,'Teacher');
  assert.equal(c.renderContent('<Teacher>'),'\x3cspan data-no-translate>&lt;Teacher&gt;</span>');
});

test('L10N-02 text, attributes and refreshed statuses survive English/Chinese round trips',()=>{
  const c=languageContext(),text=languageText('Schedule');
  const root=new LanguageElement('button',{title:'Teacher'},[text]);
  c.applySiteLanguage(root);assert.equal(text.nodeValue,'课表');assert.equal(root.attrs.title,'老师');
  c.siteLang='en';c.applySiteLanguage(root);assert.equal(text.nodeValue,'Schedule');assert.equal(root.attrs.title,'Teacher');
  c.siteLang='zh';text.nodeValue='Loading messages…';c.applySiteLanguage(root);assert.equal(text.nodeValue,'正在加载消息…');
  c.siteLang='en';c.applySiteLanguage(root);assert.equal(text.nodeValue,'Loading messages…');assert.equal(c.document.documentElement.lang,'en');
});

test('L10N-03 dialogs translate templates before substituting student content',()=>{
  const c=languageContext();
  assert.equal(c.translateTemplate('Reserve a seat in {0} on {1}?','Teacher','Home'),'预约 Home 的“Teacher”课程席位吗？');
  assert.equal(c.translateTemplate('Delete “{0}” from the library? It will also be removed from any access codes that use it.','Schedule'),
    '从资料库中删除“Schedule”吗？此文件也将从相关分享码中移除。');
  for(const label of ['Incorrect username or password.','Passwords do not match.','End the class and disconnect everyone?',
    'Repeat for how many weeks total? (2–24)','MathStudio annotations','Drawing over the teacher desktop share']){
    assert.notEqual(c.translateTemplate(label),label);
  }
  c.siteLang='en';assert.equal(c.translateTemplate('Reserve a seat in {0} on {1}?','Teacher','Home'),'Reserve a seat in Teacher on Home?');
});

test('L10N-01 resource renderer marks data even when it matches interface labels',()=>{
  const c=languageContext();Object.assign(c,{date:()=>'',formatBytes:()=>'',resourceFileIcon:()=>'',});
  vm.runInContext(app.slice(app.indexOf('function fileLibraryHTML('),app.indexOf('function mountFileLibrary(')),c);
  const html=c.fileLibraryHTML({files:[{id:1,name:'Teacher',mime:'text/plain',size:1,code_count:1}],
    codes:[{id:1,label:'Schedule',code:'Home',active:true,files:[{name:'Teacher'}],created:0}],storage:{label:'Local'}});
  for(const value of ['Teacher','Schedule','Home'])assert.ok(html.includes(`<span data-no-translate>${value}</span>`),value);
  assert.ok(html.includes('data-no-translate title="Teacher"'));
});


test('MEDIA-02 floating annotator accepts an active native screen share',async()=>{
  const source=fs.readFileSync(new URL('./classroom.js',import.meta.url),'utf8');
  let focused=0;
  const c={joined:true,presenter:null,nativeShare:{active:true},viewMode:'call',
    annotatorWindow:{closed:false,focus(){focused++;}},toast(){}};
  vm.createContext(c);
  vm.runInContext(source.slice(source.indexOf('async function openFloatingAnnotator()'),source.indexOf('async function saveBoard(')),c);
  await c.openFloatingAnnotator();assert.equal(focused,1);
  c.nativeShare.active=false;await c.openFloatingAnnotator();assert.equal(focused,1);
});


test('L10N-03 browser translation placeholders preserve supplied values',()=>{
  const c=languageContext();
  const entries=vm.runInContext('Object.entries(SITE_ZH)',c);
  for(const [source,translated] of entries){
    assert.deepEqual([...(source.match(/\{\d+\}/g)||[])].sort(),[...(translated.match(/\{\d+\}/g)||[])].sort(),source);
  }
});
