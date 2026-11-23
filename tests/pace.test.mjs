import {test} from 'node:test';
import assert from 'node:assert/strict';
import {TIMING,thinkingTime,duration,movementTime,settings,AutoLoop} from '../pokermind/static/experience.mjs';
import {controlMode,decisionKey} from '../pokermind/static/controls.mjs';
import {seatHand,victoryData} from '../pokermind/static/outcome.mjs';
const base={epoch:'table',hand:1,version:12,champion:null,can_start:false,actor:0,legal:{call:20}};
const result={...base,finished:true,outcome:{reason:'showdown',players:[{seat:0,name:'Du',cards:['As','Ks'],combination:{description:'Flush · Ass hoch'},awarded:200,net:150},{seat:1,name:'Ada',cards:[null,null],combination:null,awarded:0,net:-150}],payouts:[{winners:[{seat:0,name:'Du',amount:200}]}]}};
test('normal decision has a 1250ms think and 1750ms hold, even with reduced motion',()=>{
 const p=settings(null);assert.equal(thinkingTime(p)+duration({kind:'fold'},p),3000);
 assert.equal(thinkingTime(p),1250);assert.equal(duration({kind:'raise'},p,true),1750);
 assert.equal(movementTime({kind:'raise'},p,true),0);assert.equal(duration({kind:'complete'},p),4000);
 assert.ok(Object.isFrozen(TIMING.normal));
});
test('instant and skip remove every wait and movement while fast stays readable',()=>{
 const p={...settings(null),speed:'instant'};assert.equal(thinkingTime(p),0);
 for(const kind of ['call','deal','board','show','complete','award']){assert.equal(duration({kind},p),0);assert.equal(movementTime({kind},p),0);assert.equal(duration({kind},settings(null),false,true),0);}
 assert.equal(thinkingTime({...p,speed:'fast'}),300);assert.equal(duration({kind:'fold'},{...p,speed:'fast'}),600);
 assert.equal(settings({getItem:()=>'{"speed":"instant"}'}).speed,'instant');
});
test('foreign turns and pending settlement cannot expose active human controls',()=>{
 assert.equal(controlMode(base),'human');assert.equal(controlMode({...base,actor:1}),'waiting');
 assert.equal(controlMode(base,true),'waiting');assert.equal(controlMode({...base,finished:true,can_start:true},true),'waiting');
 assert.equal(controlMode({...base,can_start:true}),'ready');assert.equal(controlMode({...base,champion:2}),'champion');assert.equal(controlMode({...base,halted:true}),'halted');
});
test('display-only refresh keeps decision identity; new hand, process or version changes it',()=>{
 assert.equal(decisionKey(base),decisionKey({...base,learning:false,event:{kind:'show'}}));
 for(const diff of [{version:13},{epoch:'new'},{hand:2}])assert.notEqual(decisionKey(base),decisionKey({...base,...diff}));
});
test('seat badges are terminal only and cannot invent a hidden hand category',()=>{
 assert.equal(seatHand({...result,finished:false},0),null);assert.equal(seatHand(result,2),null);
 assert.deepEqual(seatHand(result,0),{text:'Flush · Ass hoch',won:true});
 assert.equal(seatHand(result,1).text,'Nicht aufgedeckt');
 const folded={...result,outcome:{...result.outcome,reason:'fold'}};
 assert.equal(seatHand(folded,0).text,'Gewonnen durch Fold');assert.equal(victoryData(folded).winners[0].hand,'Gewonnen durch Fold');
});
test('central result displays actual gross and net; not a sum claimed as one winner',()=>{
 assert.equal(victoryData({...result,finished:false}),null);
 const v=victoryData(result);assert.equal(v.title,'Du gewinnst!');assert.equal(v.winners[0].gross,200);assert.equal(v.winners[0].net,150);
 const mixed={...result,outcome:{...result.outcome,players:[...result.outcome.players,{seat:2,name:'Turing',awarded:100,net:0,combination:{description:'Ein Paar'}}],payouts:[...result.outcome.payouts,{winners:[{seat:2,name:'Turing',amount:100}]}]}};
 assert.equal(victoryData(mixed).title,'Mehrere Pot-Gewinner');assert.deepEqual(victoryData(mixed).winners.map(w=>w.gross),[200,100]);
 mixed.outcome.payouts=[{winners:[{seat:0,name:'Du',amount:200},{seat:2,name:'Turing',amount:100}]}];assert.equal(victoryData(mixed).title,'Geteilter Pot');
});
test('reset during a thinking pause cancels the pending decision without inference',async()=>{
 const loop=new AutoLoop();let calls=0;
 const p=loop.run(()=>({advance:true}),async()=>{calls++;return true;},()=>1250);
 loop.stop();await p;assert.equal(calls,0);
});
