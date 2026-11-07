import {test} from 'node:test';
import assert from 'node:assert/strict';
import {cardMarkup,betOptions,validAmount,turnText,actionText,CommandGate} from '../pokermind/static/ui.mjs';
const state=()=>({version:7,hand:1,actor:0,champion:null,finished:false,halted:false,players:[{name:'Du',bet:10,stack:990},{name:'Ada',stack:0}],pot:80,legal:{call:30,raise_min:70,raise_max:1000}});
test('cards have suit and rank names, masked cards contain no face',()=>{
 assert.match(cardMarkup('Ah'),/Herz Ass/);assert.match(cardMarkup('Ts'),/Pik 10/);
 assert.match(cardMarkup(null),/Verdeckte Karte/);assert.doesNotMatch(cardMarkup(null),/corner|Ass/);
 assert.equal(cardMarkup('<script>'),'');assert.match(cardMarkup(null,{empty:true,hole:true}),/Noch keine Karte ausgeteilt/);
});
test('quick sizes are integer legal raise-to totals including call',()=>{
 assert.deepEqual(betOptions(state()).map(x=>x.amount),[70,95,150]);
 const s=state();s.legal.raise_max=80;assert.deepEqual(betOptions(s).map(x=>x.amount),[70,80,80]);
 s.legal.raise_min=null;assert.deepEqual(betOptions(s),[]);
});
test('amount field rejects empty, fractional and out-of-range values',()=>{
 for(const value of ['',69,1001,70.5,'bad'])assert.equal(validAmount(value,state().legal),false);
 for(const value of [70,'1000',95])assert.equal(validAmount(value,state().legal),true);
});
test('terminal, halted, eliminated and active copy follows actual state',()=>{
 const s=state();assert.equal(turnText(s),'Du bist am Zug.');s.halted=true;assert.equal(turnText(s),'Partie angehalten');
 s.halted=false;s.champion=1;assert.match(turnText(s),/Ada gewinnt/);s.champion=null;s.finished=true;s.players[0].stack=0;assert.match(turnText(s),/Ausgeschieden/);
 assert.equal(actionText({kind:'raise',amount:70}),'Erhöht auf 70');
});
test('duplicate and stale commands blocked, transition remains locked',async()=>{
 let s=state(),count=0,release,finish;const pending=new Promise(r=>release=r),transition=new Promise(r=>finish=r);
 const gate=new CommandGate({getState:()=>s,commit:n=>{s=n},request:async()=>{count++;await pending;return {...s,version:8}},refresh:async()=>s,onBusy:()=>{},onError:()=>{},transition:()=>transition});
 const first=gate.send('call',null,7);assert.equal(await gate.send('call',null,7),false);release();await new Promise(r=>setImmediate(r));
 assert.equal(gate.busy,true);assert.equal(await gate.send('call',null,8),false);finish();await first;
 assert.equal(await gate.send('call',null,7),false);assert.equal(count,1);assert.equal(gate.busy,false);
});
test('failed POST refreshes without retrying action',async()=>{
 let s=state(),posts=0;const errors=[];
 const gate=new CommandGate({getState:()=>s,commit:n=>s=n,request:async()=>{posts++;throw Error('Veraltet')},refresh:async()=>({...s,version:8}),onBusy:()=>{},onError:e=>errors.push(e)});
 await gate.send('call',null,7);assert.equal(posts,1);assert.equal(s.version,8);assert.equal(gate.offline,false);assert.ok(errors.includes('Veraltet'));
});
test('unreachable refresh locks commands until explicitly reconnected',async()=>{
 const gate=new CommandGate({getState:state,commit:()=>{},request:async()=>{throw Error('network')},refresh:async()=>{throw Error('network')},onBusy:()=>{},onError:()=>{}});
 await gate.send('call',null,7);assert.equal(gate.offline,true);assert.equal(await gate.send('call',null,7),false);assert.equal(gate.busy,false);
});
