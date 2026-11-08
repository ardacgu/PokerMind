import {test} from 'node:test';
import assert from 'node:assert/strict';
import {settings,saveSettings,duration,Clock,AutoLoop,SoundBank} from '../pokermind/static/experience.mjs';
test('presentation defaults are local learning, normal speed and muted sound',()=>{
 const p=settings(null);assert.equal(p.sound,false);assert.equal(p.learning,true);assert.equal(p.speed,'normal');
 assert.doesNotThrow(()=>saveSettings(null,p));
 const store={getItem:()=>'{"volume":10,"speed":"bad","motion":false,"learning":false,"sound":true}'};
 assert.deepEqual(settings(store),{volume:1,speed:'normal',motion:false,learning:false,sound:true});
 assert.equal(settings({getItem:()=>'{broken'}).sound,false);
});
test('tempo, reduced movement and skip only change presentation duration',()=>{
 const p=settings(null),e={kind:'raise'};
 assert.equal(duration(e,p),1750);assert.ok(duration(e,{...p,speed:'fast'})<duration(e,p));
 assert.equal(duration(e,p,true),duration(e,p));assert.equal(duration(e,p,false,true),0);
 assert.ok(duration(e,{...p,motion:false})>0); // readable event text without movement
});
test('cancel finishes an active transition promptly and cannot fire it twice',async()=>{
 const c=new Clock();let count=0;const p=c.wait(5000).then(()=>count++);c.cancel();c.cancel();await p;assert.equal(count,1);
 await c.wait(0);assert.equal(c.finish,null);
});
test('automatic steps remain serial and a reset invalidates the pending loop',async()=>{
 const loop=new AutoLoop();let steps=0,active=0,max=0,advance=true,release;
 const step=async()=>{steps++;active++;max=Math.max(max,active);await new Promise(r=>release=r);active--;return true;};
 const p=loop.run(()=>({advance}),step,()=>0);await new Promise(r=>setImmediate(r));
 assert.equal(loop.run(()=>({advance}),step,()=>0),p);
 loop.stop();release();await p;assert.equal(steps,1);assert.equal(max,1);
 advance=false;await loop.run(()=>({advance}),step,()=>0);assert.equal(steps,1);
});
test('automatic playback stops at the human turn and never queues future actions',async()=>{
 const loop=new AutoLoop();let actions=0;await loop.run(()=>({advance:actions<3}),async()=>{actions++;return true;},()=>0);
 assert.equal(actions,3);
 await loop.run(()=>({advance:true}),async()=>false,()=>0);assert.equal(loop.pending,null);
});
test('sound stays silent until user unlocks, and respects mute and zero volume',async()=>{
 let made=0,played=0;
 const param={setValueAtTime(){},exponentialRampToValueAtTime(){}};
 const ctx={state:'running',currentTime:0,destination:{},resume:async()=>{},createOscillator(){return {frequency:param,connect(){},start(){played++;},stop(){},disconnect(){}};},createGain(){return {gain:param,connect(){},disconnect(){}};}};
 const s=new SoundBank(()=>{made++;return ctx;});s.play('deal');await s.unlock();assert.equal(made,0);
 s.enabled=true;await s.unlock();s.play('deal');assert.equal(played,1);
 s.volume=0;s.play('award');s.volume=.3;s.enabled=false;s.play('call');assert.equal(played,1);
});
