import {fmt,betOptions,validAmount,turnText} from './ui.mjs';

export function controlMode(s,locked=false){
 if(!s||s.halted)return 'halted';
 if(locked)return 'waiting';
 if(s.champion!==null)return 'champion';
 if(s.can_start)return 'ready';
 return s.actor===0&&s.legal.call!==null?'human':'waiting';
}
export const decisionKey=s=>`${s.epoch}:${s.hand}:${s.version}`;
const text=(el,value)=>{if(el.textContent!==value)el.textContent=value;};
const disabled=(el,value)=>{if(el.disabled!==value)el.disabled=value;};

// Created once. Animation frames and foreign turns never recreate input nodes.
export class ActionPanel {
 constructor(root,{send,reset}){
  this.root=root;this.send=send;this.reset=reset;this.state=null;this.key=null;this.locked=true;
  root.querySelector('#actions').innerHTML=`
   <div class="control-fields">
    <div class="basic-actions"><button id="fold" class="fold-action" disabled>Passen</button><button id="call" class="primary" disabled>Check / Mitgehen</button><button id="all-in" class="all-in-button" disabled>All-in</button></div>
    <div class="sizing"><div class="sizing-top"><label for="raise"><span id="raise-label">Erhöhen auf</span><small> · Gesamtbetrag dieser Setzrunde</small></label><span id="limits">—</span></div>
     <div class="sizing-inputs"><input id="raise-range" type="range" min="20" max="2000" step="1" value="20" aria-label="Gesamten Einsatz wählen" disabled><div class="amount-wrap"><input id="raise" type="number" inputmode="numeric" min="20" max="2000" step="1" value="20" aria-label="Gesamtbetrag dieser Setzrunde" aria-describedby="limits amount-error" disabled><span aria-hidden="true">Chips</span></div></div>
     <div class="sizing-bottom"><div class="presets"><button id="preset-0" class="preset" disabled>Minimum</button><button id="preset-1" class="preset" disabled>½ Pot</button><button id="preset-2" class="preset" disabled>Pot</button></div><button id="bet" class="bet-button" disabled>Erhöhen</button></div>
     <span id="amount-error" class="amount-error" aria-live="polite"></span>
    </div>
   </div>
   <div class="ready-actions"><button id="start" class="primary" disabled>Erste Hand starten</button><button id="new-tournament" class="primary" disabled>Neue Partie</button></div>`;
  this.el=Object.fromEntries([...root.querySelectorAll('[id]')].map(el=>[el.id,el]));
  this.buttons=[...root.querySelectorAll('#actions button,#actions input')];
  this.el.fold.onclick=e=>{if(e.detail<=1)this.act('fold');};
  this.el.call.onclick=e=>{if(e.detail<=1)this.act('call');};
  this.el['all-in'].onclick=e=>{if(e.detail<=1&&this.snapshot?.legal.all_in){const a=this.snapshot.legal.all_in;this.act(a.action,a.amount);}};
  this.el.bet.onclick=e=>{if(e.detail<=1&&this.el.raise.reportValidity())this.act('raise',Number(this.el.raise.value));};
  this.el.start.onclick=e=>{if(e.detail<=1&&this.mode==='ready'&&!this.locked)this.send('start',null,this.state.version);};
  this.el['new-tournament'].onclick=e=>{if(e.detail<=1&&this.mode==='champion'&&!this.locked)this.reset();};
  this.el.raise.oninput=()=>this.validate();
  this.el['raise-range'].oninput=()=>{this.el.raise.value=this.el['raise-range'].value;this.validate();};
  this.el.raise.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();if(!e.repeat&&!this.el.bet.disabled)this.el.bet.click();}};
  for(let i=0;i<3;i++)this.el[`preset-${i}`].onclick=()=>{if(this.mode==='human'&&!this.locked){this.el.raise.value=betOptions(this.snapshot)[i].amount;this.validate();}};
 }
 act(action,amount=null){
  if(this.locked||this.mode!=='human'||!this.snapshot||decisionKey(this.snapshot)!==decisionKey(this.state))return;
  this.send(action,amount,this.snapshot.version);
 }
 update(s,locked){
  this.state=s;this.locked=locked;this.mode=controlMode(s,locked);
  this.root.dataset.mode=this.mode;
  const ready=this.mode==='ready',champion=this.mode==='champion',human=this.mode==='human';
  text(this.el.turn,human?'Du bist am Zug.':ready?(s.hand?'Hand abgeschlossen':'Bereit, wenn du es bist.'):champion?turnText(s):s?.halted?'Partie angehalten':s?.finished?'Hand abgeschlossen':'KI ist am Zug …');
  text(this.el['turn-kicker'],human?'DEINE ENTSCHEIDUNG':ready||champion?'BEREIT FÜR DEN NÄCHSTEN SCHRITT':'DEIN PLATZ AM TISCH');
  text(this.el['call-hint'],human?(s.legal.call?`${fmt(s.legal.call)} Chips zum Mitgehen.`:'Du kannst ohne weiteren Einsatz checken.'):ready?(s.hand?(s.players[0].stack===0?'Du bist ausgeschieden. Du kannst die nächste Hand beobachten.':'Das Ergebnis bleibt stehen, bis du die nächste Hand startest.'):'2.000 Chips für jeden. Die Blinds stehen bei 10 / 20.'):champion?'Alle 8.000 Chips sind vergeben.':s?.halted?'Bitte starte eine neue Partie.':'Die Bedienfelder bleiben gesperrt, bis du wieder am Zug bist.');
  text(this.el['hand-indicator'],s?.hand?`HAND ${String(s.hand).padStart(2,'0')}`:'HAND —');
  this.el.start.hidden=!ready;this.el['new-tournament'].hidden=!champion;
  if(!human)for(const el of this.buttons)disabled(el,true);
  else {disabled(this.el.start,true);disabled(this.el['new-tournament'],true);}
  if(ready){text(this.el.start,s.hand?'Nächste Hand':'Erste Hand starten');disabled(this.el.start,false);}
  if(champion)disabled(this.el['new-tournament'],false);
  if(!human)return;
  // Same decision after a display-only refresh keeps the user's amount and focus.
  if(this.key!==decisionKey(s)){
   this.key=decisionKey(s);this.snapshot=s;
   text(this.el.call,s.legal.call?`Mitgehen · ${fmt(s.legal.call)}`:'Check');
   text(this.el['raise-label'],s.table.bet_label==='Setzen'?'Setzen':'Erhöhen auf');
   text(this.el.limits,s.legal.raise_min===null?'Keine Erhöhung möglich':`${fmt(s.legal.raise_min)}–${fmt(s.legal.raise_max)}`);
   if(s.legal.raise_min!==null)for(const el of [this.el.raise,this.el['raise-range']]){el.min=s.legal.raise_min;el.max=s.legal.raise_max;el.value=s.legal.raise_min;}
  }
  disabled(this.el.fold,!s.legal.fold);disabled(this.el.call,false);disabled(this.el['all-in'],!s.legal.all_in);
  for(const id of ['raise','raise-range','preset-0','preset-1','preset-2'])disabled(this.el[id],s.legal.raise_min===null);
  this.validate();
 }
 validate(){
  const legal=this.snapshot?.legal;if(!legal)return;
  const valid=validAmount(this.el.raise.value,legal);
  this.el.raise.setAttribute('aria-invalid',String(!valid&&legal.raise_min!==null));
  disabled(this.el.bet,this.locked||this.mode!=='human'||!valid);
  text(this.el.bet,valid?`${this.el['raise-label'].textContent} ${fmt(Number(this.el.raise.value))}`:'Erhöhung nicht möglich');
  text(this.el['amount-error'],valid||legal.raise_min===null?'':`Ganze Zahl von ${fmt(legal.raise_min)} bis ${fmt(legal.raise_max)} eingeben.`);
  if(valid)this.el['raise-range'].value=this.el.raise.value;
 }
}
