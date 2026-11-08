// Local presentation only. No decisions, hidden cards or poker rules.
export const defaults={speed:'normal',motion:true,learning:true,sound:false,volume:0.25};
export function settings(storage) {
  try {const p=JSON.parse(storage.getItem('pokermind.presentation.v2')||'{}');
    return {speed:p.speed==='fast'?'fast':'normal',motion:p.motion!==false,learning:p.learning!==false,sound:p.sound===true,volume:typeof p.volume==='number'?Math.max(0,Math.min(1,p.volume)):0.25};
  } catch {return {...defaults};}
}
export function saveSettings(storage,p) {try{storage.setItem('pokermind.presentation.v2',JSON.stringify(p));}catch{/* Private/blocked storage is optional. */}}
export function duration(event,p,reduced=false,skip=false) {
  if(skip)return 0;
  const ms={deal:140,board:260,blind:260,call:420,raise:420,bet:420,fold:420,check:350,show:380,award:540,complete:350,collect:260,credit:70,prepare:25,hand_start:120};
  const base=ms[event?.kind]??80;
  return Math.round(base*(p.speed==='fast'?0.24:1)*(reduced||!p.motion?0.7:1));
}
export class Clock {
  constructor(){this.finish=null;}
  wait(ms){this.cancel();if(!ms)return Promise.resolve();return new Promise(resolve=>{const id=setTimeout(()=>this.cancel(),ms);this.finish=()=>{clearTimeout(id);this.finish=null;resolve();};});}
  cancel(){this.finish?.();}
}
export class AutoLoop {
  constructor(){this.generation=0;this.pending=null;this.clock=new Clock();}
  stop(){this.generation++;this.clock.cancel();}
  run(getState,step,delay){
    if(this.pending)return this.pending;
    const token=this.generation;
    const work=async()=>{while(token===this.generation&&getState()?.advance){await this.clock.wait(delay());if(token!==this.generation)break;const ok=await step();if(!ok)break;}};
    this.pending=work().finally(()=>{this.pending=null;});return this.pending;
  }
}
export class SoundBank {
  constructor(factory){this.factory=factory;this.context=null;this.enabled=false;this.volume=.25;}
  async unlock(){if(!this.enabled)return;try{this.context??=this.factory();await this.context.resume();}catch{this.enabled=false;}}
  play(kind){
    if(!this.enabled||!this.context||this.context.state!=='running'||!this.volume)return;
    const tones={deal:[700,0.035],board:[900,.05],blind:[520,.06],call:[520,.06],raise:[640,.07],bet:[600,.06],collect:[380,.09],fold:[180,.055],show:[860,.09],award:[1050,.14],complete:[1320,.14]};
    const tone=tones[kind];if(!tone)return;
    const c=this.context,o=c.createOscillator(),g=c.createGain(),now=c.currentTime;
    o.type='sine';o.frequency.setValueAtTime(tone[0],now);o.frequency.exponentialRampToValueAtTime(tone[0]*.65,now+tone[1]);
    g.gain.setValueAtTime(Math.max(.0001,this.volume*.07),now);g.gain.exponentialRampToValueAtTime(.0001,now+tone[1]);
    o.connect(g);g.connect(c.destination);o.start(now);o.stop(now+tone[1]);o.onended=()=>{o.disconnect();g.disconnect();};
  }
}
export class TableMotion {
  constructor(arena){this.arena=arena;this.active=[];}
  cancel(){for(const a of this.active)a.cancel();this.active=[];this.arena.querySelectorAll('.flying-token').forEach(el=>el.remove());}
  play(event,ms,enabled){
    this.cancel();if(!enabled||!event||!ms)return;
    const rect=el=>el?.getBoundingClientRect();
    const arena=rect(this.arena),pot=rect(this.arena.querySelector('.pot'));
    const seat=i=>rect(this.arena.querySelector(`.seat-${i} .seat-panel`));
    const fly=(from,to,label,card=false)=>{
      if(!from||!to)return;
      const el=document.createElement('span');el.className='flying-token '+(card?'flying-card':'flying-chips');el.setAttribute('aria-hidden','true');el.textContent=label;
      this.arena.append(el);const x=from.x+from.width/2-arena.x,y=from.y+from.height/2-arena.y;
      el.style.left=`${x}px`;el.style.top=`${y}px`;
      const a=el.animate([{transform:'translate(-50%,-50%) scale(.85)',opacity:0},{offset:.15,opacity:1},{transform:`translate(calc(-50% + ${to.x+to.width/2-from.x-from.width/2}px),calc(-50% + ${to.y+to.height/2-from.y-from.height/2}px)) scale(1)`,opacity:0}],{duration:ms,easing:'cubic-bezier(.2,.7,.3,1)'});
      this.active.push(a);a.finished.then(()=>el.remove()).catch(()=>el.remove());
    };
    if(['blind','call','raise','bet'].includes(event.kind)&&event.amount>0)fly(seat(event.seat),pot,`+${event.amount}`);
    if(event.kind==='collect'){
      // Bets have already travelled in; collection is a distinct smaller tray pulse.
      for(const t of event.transfers||[])fly(rect(this.arena.querySelector(`.seat-${t.seat} .seat-caption`)),pot,String(t.amount));
      for(const r of event.refunds||[])fly(pot,seat(r.seat),`Retour ${r.amount}`);
    }
    if(event.kind==='award')for(const w of event.award.winners)fly(pot,seat(w.seat),`+${w.amount}`);
    if(event.kind==='deal')fly(rect(this.arena.querySelector('.dealer-pack')),rect(this.arena.querySelector(`.seat-${event.seat} .hole-cards`)),'♠',true);
  }
}
