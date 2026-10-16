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
      assert.equal(c.combineLocalDateTime('2026-11-01','16:00').toISOString(),'2026-11-01T23:00:00.000Z',device);
      assert.equal(c.minuteOfDay(Date.parse('2026-11-01T23:00:00Z')/1000),960);
      assert.equal(c.gridTimestamp(c.weekStartFromParam(),6,960),Date.parse('2026-11-01T23:00:00Z')/1000);
      assert.equal(c.localDateValue(new Date('2026-11-02T01:00:00Z')),'2026-11-01');
      assert.equal(c.quarterTimeValue(new Date('2026-11-02T01:00:00Z')),'18:00');
    }
  }finally{if(oldTZ===undefined)delete process.env.TZ;else process.env.TZ=oldTZ;}
});

test('BOOK-02 DST gaps are disabled and repeated times choose the earlier occurrence',()=>{
  const c=scheduleContext();
  assert.equal(c.combineLocalDateTime('2027-03-14','02:30'),null);
  assert.equal(c.combineLocalDateTime('2026-11-01','01:30').toISOString(),'2026-11-01T07:30:00.000Z');
  assert.equal(c.combineLocalDateTime('2026-02-30','16:00'),null);
  c.location.search='?week='+Date.parse('2027-03-08T07:00:00Z')/1000;
  assert.equal(c.gridTimestamp(c.weekStartFromParam(),6,150),null);
  assert.doesNotThrow(()=>c.scheduleWeekHTML(c.weekStartFromParam(),{minutes:60,name:'Synthetic'}));
});

test('BOOK-02 booking cells submit the exact studio instant in every supported zone',()=>{
  for(const [zone,expected] of Object.entries({'America/Edmonton':'2026-11-01T23:00:00Z',
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
