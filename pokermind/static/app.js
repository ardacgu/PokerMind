import {fmt,escapeHTML as esc,cardMarkup,betOptions,validAmount,actionText,turnText,potName,CommandGate} from './ui.mjs';
import {settings,saveSettings,duration,Clock,AutoLoop,SoundBank,TableMotion} from './experience.mjs';
const $=id=>document.getElementById(id);
let state=null;
let actionFocus=false;
const reduced=window.matchMedia('(prefers-reduced-motion: reduce)');
let storage;try{storage=window.localStorage;}catch{storage=null;}
const prefs=settings(storage),clock=new Clock(),loop=new AutoLoop();
const motion=new TableMotion(document.querySelector('.arena'));
const sound=new SoundBank(()=>new (window.AudioContext||window.webkitAudioContext)());
let skipSequence=false,paused=false,animateNext=false,pendingEvent=null,activeCommand=Promise.resolve();
const transition=()=>{const event=pendingEvent;pendingEvent=null;if(!event)return Promise.resolve();
 const ms=duration(event,prefs,reduced.matches,skipSequence);sound.play(event.kind);
 motion.play(event,ms,prefs.motion&&!reduced.matches&&!skipSequence);return clock.wait(ms);};
const readState=()=>{animateNext=false;return jsonRequest('/api/live/state?learning='+prefs.learning);};
async function drive(){if(paused||gate.offline||gate.busy||!state?.advance)return;
 await loop.run(()=>paused||gate.offline?null:state,()=>execute('step',null,state.version),()=>skipSequence?0:state.actor!==null?(prefs.speed==='fast'?35:180):15);
 if(!state?.advance)skipSequence=false;busyChanged(gate.busy);
}
function execute(action,amount=null,version=state.version){activeCommand=gate.send(action,amount,version);return activeCommand;}
async function submit(action,amount=null,version=state.version){if(paused)return false;await execute(action,amount,version);drive();}
function cancelVisuals(){clock.cancel();motion.cancel();loop.clock.cancel();}

async function jsonRequest(url,options={}) {
  let response,data;
  try{response=await fetch(url,{...options,signal:AbortSignal.timeout(15000)});}
  catch{throw new Error('Der Server antwortet nicht. Der Spielstand wird erneut abgefragt.');}
  try{data=await response.json();}
  catch{throw new Error('Die Serverantwort konnte nicht gelesen werden. Bitte erneut verbinden.');}
  if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'Die Eingabe konnte nicht verarbeitet werden.');
  return data;
}
function showError(message) {$('error').textContent=message;$('error').hidden=!message;}
function busyChanged(busy) {
  if(busy && $('controls').contains(document.activeElement))actionFocus=true;
  document.querySelector('.arena').setAttribute('aria-busy',String(busy));
  $('controls').setAttribute('aria-busy',String(busy));
  document.querySelectorAll('[data-control]').forEach(el=>{el.disabled=busy||gate.offline||el.dataset.invalid==='true';});
  $('reset').disabled=gate.offline||!state;
  $('skip').disabled=!(busy||state?.advance);
  document.body.classList.toggle('motion-off',!prefs.motion||reduced.matches||skipSequence);
  $('busy-message').textContent=busy?(state?.event?.text||'Zug wird verarbeitet …'):'';
  $('retry').hidden=!gate.offline;
  if(!busy&&actionFocus){if(gate.offline)$('retry').focus({preventScroll:true});else if(document.activeElement===document.body||$('controls').contains(document.activeElement))$('controls').focus({preventScroll:true});actionFocus=false;}
}
const gate=new CommandGate({getState:()=>state,commit:render,refresh:readState,
  request:async body=>{const result=await jsonRequest('/api/live/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...body,epoch:state.epoch,learning:prefs.learning})});animateNext=true;return result;},
  onBusy:busyChanged,onError:showError,transition});
function control(label,id,handler,cls='') {
  const button=document.createElement('button');button.type='button';button.id=id;button.textContent=label;button.className=cls;button.dataset.control='';
  button.addEventListener('click',event=>{if(event.detail>1)return;handler();});return button;
}
function send(action,amount=null) {return submit(action,amount,state.version);}
function renderSeats(s,previous) {
  $('seats').innerHTML=[1,2,3,0].map(seat=>{
    const p=s.players[seat],last=s.table.last_actions[String(seat)];
    const won=s.finished&&s.result.some(r=>r.seat===seat);
    const folded=p.status==='gepasst'||(s.finished&&last?.kind==='fold');
    const eliminated=p.status==='ausgeschieden';
    const status=eliminated?'Ausgeschieden':folded?'Gepasst':p.status==='All-in'?'All-in':s.actor===seat?'Am Zug':!s.hand?'Bereit':s.finished?'Hand beendet':'Im Spiel';
    const fresh=!previous||previous.hand!==s.hand;
    const cardList=Array.from({length:2},(_,i)=>cardMarkup(p.cards[i],{empty:i>=p.cards.length,hole:true,fresh:animateNext&&i<p.cards.length&&(fresh||previous?.players[seat]?.cards[i]!==p.cards[i])})).join('');
    const changed=previous&&previous.players[seat].stack!==p.stack;
    return `<article class="seat seat-${seat} ${s.actor===seat?'active':''} ${folded?'folded':''} ${eliminated?'eliminated':''} ${won?'winner':''}" aria-label="${esc(p.name)}, ${fmt(p.stack)} Chips, ${status}${p.dealer?', Dealer':''}">
      <div class="cards hole-cards" aria-label="Karten von ${esc(p.name)}">${cardList}</div>
      <div class="seat-panel"><span class="avatar" aria-hidden="true">${seat===0?'♠':p.name[0]}</span><div class="player-main"><div class="player-name">${esc(p.name)}${seat===0?'<small>DEIN PLATZ</small>':''}${p.dealer?'<span class="dealer" title="Dealer" aria-label="Dealer">D</span>':''}</div><div class="bankroll ${changed?'chip-change':''}">${fmt(p.stack)} <small>Chips</small></div></div><span class="seat-status ${p.status==='All-in'?'all-in':''}">${status}</span></div>
      <div class="seat-caption"><span class="last-action">${s.hand&&last?esc(actionText(last)):'—'}</span>${p.bet?`<span class="bet ${previous?.players[seat]?.bet!==p.bet?'chip-change':''}"><span class="mini-chip" aria-hidden="true"></span>Einsatz ${fmt(p.bet)}</span>`:''}</div></article>`;
  }).join('');
}
function renderActions(s) {
  $('actions').replaceChildren();$('call-hint').textContent='';
  const captured=s.version, submit=(action,amount=null)=>{if(!paused)execute(action,amount,captured).then(drive);};
  if(s.halted){$('call-hint').textContent='Bitte starte eine neue Partie.';return;}
  if(s.champion!==null){$('call-hint').textContent='Alle 8.000 Chips sind vergeben.';$('actions').append(control('Neue Partie','new-tournament',openReset,'primary start'));return;}
  if(s.can_start){$('call-hint').textContent=!s.hand?'2.000 Chips für jeden. Die Blinds stehen bei 10 / 20.':s.players[0].stack===0?'Du kannst die verbleibenden Gegner bis zum Turnierende beobachten.':'Der Dealer wandert weiter. Bereit für die nächste Hand?';$('actions').append(control(s.hand?'Nächste Hand':'Erste Hand starten','start',()=>submit('start'),'primary start'));return;}
  const l=s.legal;
  if(l.call===null){$('call-hint').textContent=s.actor!==null?`${s.players[s.actor].name} entscheidet …`:'Karten und Chips werden nacheinander verarbeitet.';return;}
  $('call-hint').textContent=l.call?`${fmt(l.call)} Chips zum Mitgehen${l.call===s.players[0].stack?' · dein gesamter Reststack':''}.`:'Du kannst ohne weiteren Einsatz checken.';
  const basic=document.createElement('div');basic.className='basic-actions';
  if(l.fold)basic.append(control('Passen','fold',()=>submit('fold'),'fold-action'));
  basic.append(control(l.call?`Mitgehen · ${fmt(l.call)}`:'Check','call',()=>submit('call'),'primary'));
  if(l.all_in)basic.append(control('All-in','all-in',()=>submit(l.all_in.action,l.all_in.amount),'all-in-button'));
  $('actions').append(basic);
  if(l.raise_min!==null){
    const sizing=document.createElement('div');sizing.className='sizing';
    const label=s.table.bet_label==='Setzen'?'Setzen':'Erhöhen auf';
    sizing.innerHTML=`<div class="sizing-top"><label for="raise">${label} <span>· Gesamtbetrag dieser Setzrunde</span></label><span id="limits">${fmt(l.raise_min)}–${fmt(l.raise_max)}</span></div><div class="sizing-inputs"><input id="raise-range" type="range" min="${l.raise_min}" max="${l.raise_max}" step="1" value="${l.raise_min}" aria-label="Gesamten Einsatz wählen" data-control><div class="amount-wrap"><input id="raise" type="number" inputmode="numeric" min="${l.raise_min}" max="${l.raise_max}" step="1" value="${l.raise_min}" aria-label="Gesamtbetrag dieser Setzrunde" aria-describedby="limits amount-error" data-control><span aria-hidden="true">Chips</span></div></div><div class="sizing-bottom"><div class="presets"></div></div><span id="amount-error" class="amount-error" aria-live="polite"></span>`;
    $('actions').append(sizing);
    const amount=$('raise'),range=$('raise-range');
    const betButton=control(`${label} ${fmt(l.raise_min)}`,'bet',()=>{if(amount.reportValidity())submit('raise',Number(amount.value));},'bet-button');
    sizing.querySelector('.sizing-bottom').append(betButton);
    function update(value,fromRange=false){
      if(fromRange)amount.value=value;
      const valid=validAmount(amount.value,l);amount.setAttribute('aria-invalid',String(!valid));
      betButton.dataset.invalid=String(!valid);betButton.disabled=!valid||gate.busy||gate.offline;
      betButton.textContent=valid?`${label} ${fmt(Number(amount.value))}`:label;
      $('amount-error').textContent=valid?'':`Ganze Zahl von ${fmt(l.raise_min)} bis ${fmt(l.raise_max)} eingeben.`;
      if(valid)range.value=amount.value;
    }
    amount.addEventListener('input',()=>update(amount.value));range.addEventListener('input',()=>update(range.value,true));
    amount.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();if(!e.repeat&&!betButton.disabled)betButton.click();}});
    betOptions(s).forEach((p,i)=>sizing.querySelector('.presets').append(control(p.label,`preset-${i}`,()=>update(p.amount,true),'preset')));
  }
}
function renderPots(s) {
  $('pot').textContent=fmt(s.finished?s.result.reduce((sum,p)=>sum+p.awarded,0):s.pot);$('pot-label').textContent=s.finished?'AUSGEZAHLT':'GESAMTER POT';
  $('pots').replaceChildren();
  if(s.table.pots.length>1){
    s.table.pots.forEach(p=>{const el=document.createElement('span');el.textContent=`${potName(p.index)} ${fmt(p.amount)}`;el.title='Berechtigt: '+p.eligible.map(i=>s.players[i].name).join(', ');$('pots').append(el);});
    if(s.table.pending_bets){const el=document.createElement('span');el.textContent=`+ ${fmt(s.table.pending_bets)} laufende Einsätze`;$('pots').append(el);}
  }
  $('table-result').textContent='';
  if(s.finished&&s.result.length){const split=s.table.awards.some(p=>p.winners.length>1);$('table-result').textContent=s.champion!==null?`♛ ${s.champion===0?'Du gewinnst':s.players[s.champion].name+' gewinnt'} die Partie`:split?'Geteilter Pot · Ergebnis unten':`${s.result.length===1&&s.result[0].seat===0?'Du gewinnst':s.result.map(p=>p.name).join(' & ')+(s.result.length>1?' gewinnen':' gewinnt')} ${fmt(s.result.reduce((n,p)=>n+p.awarded,0))} Chips`;}
  $('result').hidden=!s.finished;
  $('result').replaceChildren();
  if(s.finished){
    const heading=document.createElement('h2');heading.textContent=s.champion!==null?'♛ Turnier entschieden':s.result.length===1?`♛ ${s.result[0].name==='Du'?'Du gewinnst':s.result[0].name+' gewinnt'}!`:'♛ Mehrere Pot-Gewinner';$('result').append(heading);
    const explanation=document.createElement('p');explanation.className='outcome-note';explanation.textContent=s.outcome?.explanation||'';$('result').append(explanation);
    if(s.outcome?.incomplete_board){const note=document.createElement('p');note.className='outcome-note';note.textContent='Die Hand endete vorzeitig. Es werden keine weiteren Gemeinschaftskarten oder vollständigen Pokerkombinationen ergänzt.';$('result').append(note);}

    if(s.outcome?.reason==='showdown'){const ranks=document.createElement('p');ranks.className='winning-hands';ranks.textContent=s.outcome.players.filter(p=>p.awarded&&p.combination).map(p=>`${p.name}: ${p.combination.description}`).join(' · ');$('result').append(ranks);}
    const totals=document.createElement('div');totals.className='result-totals';
    s.result.forEach(r=>{const el=document.createElement('p');el.innerHTML=`<strong>${esc(r.name)}</strong><span>${fmt(r.awarded)} aus dem Pot</span><b>${r.net>=0?'+':''}${fmt(r.net)} netto</b>`;totals.append(el);});$('result').append(totals);
    (s.outcome?.payouts||s.table.awards).forEach(p=>{const el=document.createElement('p');el.className='pot-award';el.textContent=`Topfauszahlung ${(p.index??p.pot)+1}${p.winners.length>1?' · geteilt':''}: ${p.winners.map(w=>`${w.name} ${fmt(w.amount)}`).join(' / ')} Chips`;$('result').append(el);});
    if(s.outcome){
      const mode=document.createElement('p');mode.className='learning-badge';mode.textContent=s.learning?'LERNMODUS · Alle beteiligten Hände nach vollständiger Auszahlung':'REALISTISCHE ANSICHT · Nur regulär aufgedeckte Karten';$('result').append(mode);
      const hands=document.createElement('div');hands.className='hand-grid';
      for(const p of s.outcome.players){const el=document.createElement('article');el.className='hand-result '+(p.awarded?'paid':'');
        el.innerHTML=`<div class="hand-result-name"><strong>${esc(p.name)}</strong><span>${p.folded?'Gepasst':p.awarded?'Pot-Empfänger':'Showdown'}</span></div><div class="cards">${p.cards.map(c=>cardMarkup(c)).join('')}</div><b>${esc(p.combination?.description||(s.outcome.incomplete_board?'Vorzeitig beendet':p.cards.includes(null)?'Nicht aufgedeckt':'Keine Wertung'))}</b><small>${fmt(p.awarded)} brutto · ${p.net>=0?'+':''}${fmt(p.net)} netto</small>`;hands.append(el);}
      $('result').append(hands);
      if(s.outcome.pot_layers.length>1){const p=document.createElement('p');p.className='pot-award';p.textContent='Berechtigung vor dem Showdown: '+s.outcome.pot_layers.map(x=>`${potName(x.index)} ${fmt(x.amount)}: ${x.eligible.map(i=>s.players[i].name).join(', ')}`).join(' · ');$('result').append(p);}
    }
  }
}
function renderActivity(s,previous) {
  const earlier=previous?.hand===s.hand?previous.table.actions.length:0;
  const count=s.table.actions.length-earlier;
  $('activity-note').textContent=s.hand?`${s.table.actions.length} Aktionen · Hand ${s.hand}`:'Deine Partie bleibt lokal.';
  $('recent').innerHTML=s.table.actions.length?s.table.actions.slice(-4).map(a=>`<span class="event ${a.index>=earlier&&count>0?'new-event':''}"><strong>${esc(a.name)}</strong> ${esc(actionText(a))}</span>`).join(''):'<span>Eine gute Entscheidung beginnt mit der ersten Hand.</span>';
  $('history').replaceChildren(...s.table.actions.map(a=>{const li=document.createElement('li');li.textContent=`${a.name}: ${actionText(a)}`;return li;}));
}
function render(s) {
  const previous=state,focused=document.activeElement?.id,wasInControls=$('controls').contains(document.activeElement);
  pendingEvent=animateNext&&s.event?.id!==previous?.event?.id?s.event:null;
  state=s;renderSeats(s,previous);renderActions(s);renderPots(s);renderActivity(s,previous);
  $('board').innerHTML=Array.from({length:5},(_,i)=>cardMarkup(s.board[i],{empty:true,fresh:animateNext&&!!s.board[i]&&(!previous||s.hand!==previous.hand||previous.board[i]!==s.board[i])})).join('');
  $('live-event').textContent=s.event?.text||'Dein Tisch ist bereit.';
  $('round').textContent=s.hand?`Hand ${s.hand} · ${s.stage}`:'Die erste Hand wartet';
  $('turn').textContent=s.advance?(s.actor!==null?`${s.players[s.actor].name} ist am Zug`:(s.stage==='Auszahlung'?'Die Pots werden ausgezahlt':s.stage==='Austeilen'?'Die Karten werden verteilt':s.event?.text||'Die Hand läuft')):turnText(s);$('turn-kicker').textContent=s.finished?'AM ENDE DER HAND':s.actor===0?'DEINE ENTSCHEIDUNG':'DEIN PLATZ AM TISCH';
  $('hand-indicator').textContent=s.hand?`HAND ${String(s.hand).padStart(2,'0')}`:'HAND —';
  const active=s.players.filter(p=>p.stack>0||(!s.finished&&s.hand&&p.participated)).length;
  $('players-count').innerHTML=`${active} Spieler<small>${active===2?'HEADS-UP':'AM TISCH'}</small>`;
  $('opponent-type').textContent=s.opponents.label;
  const descriptions={learned:'Die drei Gegner verwenden einen Random Forest mit 200 Bäumen, trainiert anhand von Teacher-Entscheidungen. Das Modell lernt während der Partie nicht weiter. Die gemessenen 78,70 % Label-Accuracy beschreiben Teacher-Nachahmung – keine Gewinnwahrscheinlichkeit deiner Hand.',teacher:'Die Gegner verwenden die selbst entwickelte Teacher-Heuristik mit Monte-Carlo-Schätzungen. Sie sind kein trainiertes Modell und lernen während der Partie nicht weiter.',baseline:'Die Gegner verwenden einfache feste Regeln für Karten und Einsätze. Sie sind kein trainiertes Modell und lernen während der Partie nicht weiter.'};
  $('ai-info').textContent=descriptions[s.opponents.mode]||'Die aktive Gegnerkonfiguration wird vom Server vorgegeben.';
  if(s.opponents.version){const version=document.createElement('small');version.textContent=`Version ${s.opponents.version}`;$('ai-info').append(version);}
  if(s.halted)showError(s.message);
  $('announcement').textContent=[turnText(s),s.hand?`Hand ${s.hand}, ${s.stage}. ${s.finished?'Ausgezahlt':'Pot'} ${fmt(s.finished?s.result.reduce((n,r)=>n+r.awarded,0):s.pot)} Chips.`:'',s.history.at(-1)||''].join(' ');
  busyChanged(gate.busy);animateNext=false;
  // Preserve keyboard orientation without stealing focus from history or the info panel.
  if(wasInControls){const next=$(focused);if(next&&!next.disabled)next.focus({preventScroll:true});else $('controls').focus({preventScroll:true});}
}
function openReset(){
 if(gate.offline)return;paused=true;loop.stop();cancelVisuals();
 $('reset-dialog').returnValue='';$('reset-dialog').showModal();
}
$('reset').addEventListener('click',e=>{if(e.detail<=1)openReset();});
$('reset-dialog').addEventListener('close',async()=>{
 await activeCommand;await loop.pending;
 if($('reset-dialog').returnValue==='confirm'&&!gate.offline){await execute('reset');skipSequence=false;}
 paused=false;drive();
});
document.addEventListener('keydown',e=>{if(e.repeat&&['Enter',' '].includes(e.key)&&e.target.matches('button'))e.preventDefault();});
async function connect(){
 paused=true;loop.stop();cancelVisuals();await activeCommand;await loop.pending;
 $('retry').disabled=true;
 try{const next=await readState();gate.offline=false;showError('');render(next);}
 catch{gate.offline=true;showError('Der lokale Server ist nicht erreichbar. Starte PokerMind und verbinde dich erneut.');busyChanged(false);}
 finally{$('retry').disabled=false;paused=false;drive();}
}
function updatePreferences(){
 saveSettings(storage,prefs);sound.enabled=prefs.sound;sound.volume=prefs.volume;
 $('speed').value=prefs.speed;$('motion').checked=prefs.motion;$('learning').checked=prefs.learning;
 $('volume').value=prefs.volume;$('sound').textContent=prefs.sound?'Ton an':'Ton aus';$('sound').setAttribute('aria-pressed',String(prefs.sound));
 $('motion-note').textContent=reduced.matches?'Reduzierte Bewegung ist systemseitig aktiv. Alle Aktionen bleiben als Text sichtbar.':'';
 document.body.classList.toggle('motion-off',!prefs.motion||reduced.matches||skipSequence);
}
$('speed').addEventListener('change',()=>{prefs.speed=$('speed').value;updatePreferences();cancelVisuals();});
$('motion').addEventListener('change',()=>{prefs.motion=$('motion').checked;updatePreferences();cancelVisuals();});
$('learning').addEventListener('change',async()=>{prefs.learning=$('learning').checked;updatePreferences();await connect();});
$('sound').addEventListener('click',async()=>{prefs.sound=!prefs.sound;updatePreferences();await sound.unlock();if(!sound.enabled){prefs.sound=false;updatePreferences();}sound.play('deal');});
$('volume').addEventListener('input',()=>{prefs.volume=Number($('volume').value);updatePreferences();});
$('skip').addEventListener('click',()=>{skipSequence=true;cancelVisuals();busyChanged(gate.busy);});
reduced.addEventListener('change',()=>{updatePreferences();cancelVisuals();});
// Audio starts only following a real user gesture, including after restored preferences.
document.addEventListener('pointerdown',()=>{if(prefs.sound)sound.unlock();},{once:true});
document.addEventListener('keydown',()=>{if(prefs.sound)sound.unlock();},{once:true});
$('retry').addEventListener('click',connect);updatePreferences();connect();
