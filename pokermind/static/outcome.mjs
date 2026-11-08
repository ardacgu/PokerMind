import {fmt,escapeHTML as esc} from './ui.mjs';

export function seatHand(s,seat){
 if(!s.finished||!s.outcome)return null;
 const p=s.outcome.players.find(p=>p.seat===seat);if(!p)return null;
 if(p.awarded&&s.outcome.reason==='fold')return {text:'Gewonnen durch Fold',won:true};
 return {text:p.combination?.description||(p.cards.includes(null)?'Nicht aufgedeckt':'Vorzeitig beendet'),won:p.awarded>0};
}
export function victoryData(s){
 if(!s.finished||!s.outcome)return null;
 const payouts=s.outcome.payouts;
 const split=payouts.some(p=>p.winners.length>1);
 const winners=s.outcome.players.filter(p=>p.awarded>0).map(p=>({name:p.name,seat:p.seat,gross:p.awarded,net:p.net,hand:s.outcome.reason==='fold'?'Gewonnen durch Fold':p.combination?.description||'Regulärer Showdown'}));
 const title=split?'Geteilter Pot':winners.length>1?'Mehrere Pot-Gewinner':winners[0]?.name==='Du'?'Du gewinnst!':`${winners[0]?.name||'Hand'} gewinnt!`;
 return {title,winners,payouts,total:winners.reduce((n,p)=>n+p.gross,0),split};
}
export function renderVictory(el,s,animate){
 const data=victoryData(s);el.hidden=!data;if(!data){el.replaceChildren();delete el.dataset.key;return;}
 const key=JSON.stringify([s.epoch,s.hand,s.version,s.learning,data]);if(el.dataset.key===key)return;
 el.dataset.key=key;el.dataset.winners=data.winners.length;
 el.innerHTML=`<p class="victory-kicker">♛ HAND ${s.hand} · VOLLSTÄNDIG AUSGEZAHLT</p><h2>${esc(data.title)}</h2><div class="victory-winners">${data.winners.map(p=>`<article><strong>${esc(p.name)}</strong><b>${fmt(p.gross)} Chips <small>brutto</small></b><span>${esc(p.hand)}</span><small>${p.net>=0?'+':''}${fmt(p.net)} netto</small></article>`).join('')}</div>${data.payouts.length>1||data.split?`<div class="victory-pots">${data.payouts.map((p,i)=>`<p>Auszahlung ${i+1}: ${p.winners.map(w=>`${esc(w.name)} ${fmt(w.amount)}`).join(' · ')}</p>`).join('')}</div>`:''}<p class="victory-stays">Ergebnis bleibt bis zur nächsten Hand</p>`;
 el.classList.toggle('celebrate',animate);
}
