// Pure presentation helpers; no poker rules or model inference live here.
export const fmt = n => Number(n).toLocaleString('de-DE');
export const escapeHTML = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function cardMarkup(value, {empty=false, fresh=false, hole=false}={}) {
  if (!value) return `<span class="card ${empty?'empty':'back'} ${fresh?'deal':''}" role="img" aria-label="${empty?(hole?'Noch keine Karte ausgeteilt':'Noch keine Gemeinschaftskarte'):'Verdeckte Karte'}"><span aria-hidden="true">${empty?'·':'♠'}</span></span>`;
  if (!/^[2-9TJQKA][shdc]$/.test(value)) return '';
  const suits={s:['♠','Pik'],h:['♥','Herz'],d:['♦','Karo'],c:['♣','Kreuz']};
  const [symbol,name]=suits[value[1]], rank=value[0]==='T'?'10':value[0];
  const rankName={A:'Ass',K:'König',Q:'Dame',J:'Bube'}[rank]||rank;
  return `<span class="card ${'hd'.includes(value[1])?'red':'black'} ${fresh?'deal':''}" role="img" aria-label="${name} ${rankName}"><span class="corner" aria-hidden="true">${rank}<small>${symbol}</small></span><span class="suit" aria-hidden="true">${symbol}</span><span class="corner reverse" aria-hidden="true">${rank}<small>${symbol}</small></span></span>`;
}
export function betOptions(state) {
  const l=state.legal;
  if (l.raise_min===null) return [];
  const base=state.players[0].bet+(l.call||0);
  const clamp=v=>Math.max(l.raise_min,Math.min(l.raise_max,Math.round(v)));
  return [{label:'Minimum',amount:l.raise_min},{label:'½ Pot',amount:clamp(base+(state.pot+(l.call||0))*.5)}, {label:'Pot',amount:clamp(base+state.pot+(l.call||0))}];
}
export function validAmount(value, legal) {
  return String(value).trim()!=='' && Number.isSafeInteger(Number(value)) && Number(value)>=legal.raise_min && Number(value)<=legal.raise_max && legal.raise_min!==null;
}
export function actionText(a) {
  if (!a) return 'Bereit';
  return {fold:'Passt',check:'Check',blind:`Blind ${fmt(a.amount)}`,call:`Call ${fmt(a.amount)}`,raise:`Erhöht auf ${fmt(a.amount)}`,bet:`Setzt ${fmt(a.amount)}`}[a.kind]||'';
}
export function turnText(s) {
  if(s.halted)return 'Partie angehalten';
  if(s.champion!==null)return s.champion===0?'Du gewinnst die Partie':`${s.players[s.champion].name} gewinnt die Partie`;
  if(!s.hand)return 'Bereit, wenn du es bist.';
  if(s.finished)return s.players[0].stack===0?'Ausgeschieden · nächste Hand ansehen':'Hand abgeschlossen';
  if(s.actor===0)return 'Du bist am Zug.';
  return s.players[0].stack===0?'Du schaust zu · ausgeschieden':'Die Gegner sind am Zug.';
}
export const potName = index => index===0?'Hauptpot':`Seitenpot ${index}`;

// The caller supplies the version captured by the clicked control. No automatic retry of a POST.
export class CommandGate {
  constructor({getState,commit,request,refresh,onBusy,onError,transition=()=>Promise.resolve()}) {
    Object.assign(this,{getState,commit,request,refresh,onBusy,onError,transition});this.busy=false;this.offline=false;
  }
  async send(action,amount,version) {
    if(this.busy||this.offline||version!==this.getState()?.version)return false;
    this.busy=true;this.onBusy(true);this.onError('');
    try {
      const next=await this.request({action,amount,version});this.commit(next);await this.transition();
    } catch(error) {
      this.onError(error.message||'Aktion fehlgeschlagen.');
      try {this.commit(await this.refresh());} catch {this.offline=true;this.onError('Verbindung unterbrochen. Bitte erneut verbinden. Die Aktion wird nicht automatisch wiederholt.');}
    } finally {this.busy=false;this.onBusy(false);}
    return true;
  }
}
