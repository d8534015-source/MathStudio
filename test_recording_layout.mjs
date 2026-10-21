import test from 'node:test';import assert from 'node:assert/strict';
import {initials,recordingLayout,receivedCamera} from './classroom_recorder.js';
test('safe deterministic initials without account identifiers',()=>{
  for(const [name,value] of [['Daniel Zhang','DZ'],[' 李 明 ','李明'],['王小明','王小'],['Alice','AL'],['  ','?'],[null,'?']])assert.equal(initials(name),value);
});
test('zero through many participants fit balanced bounded tiles',()=>{
  for(const main of [false,true])for(const count of [0,1,2,3,6,15,32]){
    const tiles=recordingLayout(count,main);assert.equal(tiles.length,count);
    for(const t of tiles){assert.ok(t.x>=0&&t.y>=0&&t.w>0&&t.h>0&&t.x+t.w<=1280&&t.y+t.h<=720);if(main)assert.ok(t.x>=1036);}
    for(let i=0;i<tiles.length;i++)for(let j=i+1;j<tiles.length;j++){const a=tiles[i],b=tiles[j];assert.ok(a.x+a.w<=b.x||b.x+b.w<=a.x||a.y+a.h<=b.y||b.y+b.h<=a.y);}
  }
  const [solo]=recordingLayout(1,false);assert.ok(solo.w>1200&&solo.h>650);
});
test('only actual enabled received camera is eligible; unavailable returns avatar',()=>{
  const track={enabled:true,readyState:'live',muted:false};const item={enabled:true,element:{readyState:2,srcObject:{getVideoTracks:()=>[track]}}};
  assert.equal(receivedCamera(item),true);item.enabled=false;assert.equal(receivedCamera(item),false);item.enabled=true;track.muted=true;assert.equal(receivedCamera(item),false);track.muted=false;track.readyState='ended';assert.equal(receivedCamera(item),false);assert.equal(receivedCamera({enabled:true}),false);
});
