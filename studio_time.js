// IANA studio-time conversion. No device-local Date arithmetic.
const formatters=new Map(),offsetCache=new Map();
const rulesByZone=new Map();
export function setTimezoneRules(rules){
  if(!rules)return;
  const previous=rulesByZone.get(rules.zone);
  if(JSON.stringify(previous)!==JSON.stringify(rules)){
    rulesByZone.set(rules.zone,rules);offsetCache.clear();
  }
}
function ruleOffset(value,zone){
  const rules=rulesByZone.get(zone),stamp=new Date(value).getTime()/1000;
  if(!rules||stamp<rules.start||stamp>=rules.end)return null;
  let offset=rules.transitions[0].offset;
  for(const item of rules.transitions){if(item.at>stamp)break;offset=item.offset;}
  return offset;
}
export function partsAt(value,zone){
  const offset=ruleOffset(value,zone);
  if(offset!==null){value=new Date(new Date(value).getTime()+offset*1000);zone='UTC';}
  if(!formatters.has(zone))formatters.set(zone,new Intl.DateTimeFormat('en-CA',{
    timeZone:zone,calendar:'gregory',numberingSystem:'latn',hourCycle:'h23',
    year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit'}));
  return Object.fromEntries(formatters.get(zone).formatToParts(new Date(value))
    .filter(p=>p.type!=='literal').map(p=>[p.type,Number(p.value)]));
}
export function formatAt(value,zone,locale,options={}){
  const offset=ruleOffset(value,zone);
  if(offset!==null){value=new Date(new Date(value).getTime()+offset*1000);zone='UTC';}
  return new Intl.DateTimeFormat(locale,{...options,timeZone:zone}).format(new Date(value));
}
const utc=p=>Date.UTC(p.year,p.month-1,p.day,p.hour||0,p.minute||0,p.second||0);
const equal=(a,b)=>['year','month','day','hour','minute','second'].every(k=>a[k]===(b[k]||0));
export function fromWall(value,zone){
  const p={hour:0,minute:0,second:0,...value},nominal=utc(p),check=new Date(nominal);
  if(!Number.isFinite(nominal)||check.getUTCFullYear()!==p.year||check.getUTCMonth()+1!==p.month||
    check.getUTCDate()!==p.day||check.getUTCHours()!==p.hour||check.getUTCMinutes()!==p.minute||check.getUTCSeconds()!==p.second)return null;
  const key=`${zone}:${p.year}-${p.month}-${p.day}`;
  if(!offsetCache.has(key)){
    const noon=Date.UTC(p.year,p.month-1,p.day,12);
    const offsets=new Set([-36,0,36].map(h=>{const t=noon+h*3600000;return utc(partsAt(t,zone))-t;}));
    if(offsetCache.size>=512)offsetCache.delete(offsetCache.keys().next().value);
    offsetCache.set(key,[...offsets]);
  }
  const candidates=offsetCache.get(key).map(offset=>nominal-offset).filter(t=>equal(partsAt(t,zone),p));
  // DST gaps have no candidate; repeated times consistently use the earlier one.
  return candidates.length?new Date(Math.min(...candidates)):null;
}
export function shiftLocalDays(value,days,zone){
  const p=partsAt(value,zone),day=new Date(Date.UTC(p.year,p.month-1,p.day+days));
  return fromWall({...p,year:day.getUTCFullYear(),month:day.getUTCMonth()+1,day:day.getUTCDate()},zone);
}
