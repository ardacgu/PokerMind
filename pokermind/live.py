"""Incremental local table: one real PokerKit operation (or decision) per step.

The frozen Game/simulator stays untouched. Only scheduling is different here.
No future snapshots, deck, burns, model features or queued decisions are exported.
"""
from collections import deque, Counter
from uuid import uuid4
from pokerkit import (NoLimitTexasHoldem, Deck, StandardHighHand, Label,
                      Folding, HoleCardsShowingOrMucking, ChipsPushing)
from .game import Game, NAMES, BotExecutionError
from .views import observe
from .presentation import table_details

LABELS = {Label.HIGH_CARD:'Höchste Karte', Label.ONE_PAIR:'Ein Paar',
          Label.TWO_PAIR:'Zwei Paare', Label.THREE_OF_A_KIND:'Drilling',
          Label.STRAIGHT:'Straße', Label.FLUSH:'Flush', Label.FULL_HOUSE:'Full House',
          Label.FOUR_OF_A_KIND:'Vierling', Label.STRAIGHT_FLUSH:'Straight Flush'}
RANKS = dict(zip('23456789TJQKA', ['Zwei','Drei','Vier','Fünf','Sechs','Sieben','Acht','Neun','Zehn','Bube','Dame','König','Ass']))


def describe_hand(hole, board):
    """Label PokerKit's best five, never decide a pot or rank an unfinished board."""
    if len(hole) != 2 or len(board) != 5 or any(c is None for c in hole):
        return None
    hand = StandardHighHand.from_game(''.join(hole), ''.join(board))
    ranks = [repr(c)[0] for c in hand.cards]
    label = LABELS[hand.entry.label]
    if hand.entry.label == Label.STRAIGHT_FLUSH and set(ranks) == set('TJQKA'):
        label = 'Royal Flush'
    ordered = sorted(Counter(ranks), key=lambda r: (ranks.count(r), '23456789TJQKA'.index(r)), reverse=True)
    high = '5' if set(ranks) == set('A2345') else ordered[0]
    plural=dict(zip('23456789TJQKA',['Zweien','Dreien','Vieren','Fünfen','Sechsen','Siebenen','Achten','Neunen','Zehnen','Buben','Damen','Könige','Asse']))
    if label=='Royal Flush':detail=label
    elif hand.entry.label in (Label.STRAIGHT,Label.STRAIGHT_FLUSH,Label.HIGH_CARD,Label.FLUSH):detail=f'{label} · {RANKS[high]} hoch'
    elif hand.entry.label==Label.TWO_PAIR:detail=f'{label} · {plural[ordered[0]]} und {plural[ordered[1]]}'
    elif hand.entry.label==Label.FULL_HOUSE:detail=f'{label} · {plural[ordered[0]]} über {plural[ordered[1]]}'
    else:detail=f'{label} · {plural[ordered[0]]}'
    return dict(category=label, description=detail, best_five=[repr(c) for c in hand.cards])


class LiveGame(Game):
    def __init__(self, *args, **kwargs):
        self.epoch = uuid4().hex  # process/table identity; not a seed
        super().__init__(*args, **kwargs)

    def reset(self):
        super().reset()
        self.event = dict(kind='ready', text='Dein Tisch ist bereit.')
        self.events = []
        self.starting_stacks = list(self.stacks)
        self.payouts = []
        self.pot_layers = []

    def _emit(self, kind, text, **fields):
        self.event = dict(id=f'{self.epoch}:{self.version}', kind=kind, text=text, **fields)
        self.events.append(dict(self.event))

    def start_hand(self):
        # Same moving-button/seating convention as the frozen Game. Differential
        # tests compare actions, cards, settlement and subsequent hands.
        if self.state and self.state.status:
            raise ValueError('Die laufende Hand ist noch nicht beendet.')
        active = [i for i, stack in enumerate(self.stacks) if stack > 0]
        if len(active) < 2:
            raise ValueError('Die Partie ist beendet. Bitte neu starten.')
        if len(active) == 2 and len(self.seats) > 2:
            previous_bb = self.seats[1]
            next_bb = next((previous_bb+d)%4 for d in range(1,5) if (previous_bb+d)%4 in active)
            self.dealer = next(seat for seat in active if seat != next_bb)
        else:
            self.dealer = next((self.dealer+d)%4 for d in range(1,5) if (self.dealer+d)%4 in active)
        self.seats = [(self.dealer+d)%4 for d in range(1,5) if (self.dealer+d)%4 in active]
        self.starting_stacks = list(self.stacks)
        self.state = NoLimitTexasHoldem.create_state((), True, 0, (10,20), 20,
                                                    [self.stacks[i] for i in self.seats], len(active))
        deck = list(Deck.STANDARD); self._rng.shuffle(deck); self.state.deck_cards = deque(deck)
        self.hand += 1; self.result = []; self.original = {}; self.history = []
        self.payouts = []; self.pot_layers = []; self.events = []
        self.version += 1
        self._emit('hand_start', f'Hand {self.hand} · die Blinds werden gesetzt.')

    def _settle(self):
        # No automatic run-ahead. The final reconciliation is identical to Game.
        if self.state and not self.state.status:
            super()._settle()

    def act(self, seat, decision):
        before = self.state.stacks[self.seats.index(seat)] if seat in self.seats else 0
        super().act(seat, decision)
        action = table_details(self)['actions'][-1]
        delta = before-self.state.stacks[self.seats.index(seat)]
        text=self.history[-1]
        if action['kind']=='bet':text=text.replace('erhöht auf','setzt').replace('erhöhst auf','setzt')
        all_in=self.state.stacks[self.seats.index(seat)]==0 and action['kind']!='fold'
        if all_in:text=text.rstrip('.')+' · All-in.'
        self._emit(action['kind'],text,seat=seat,amount=delta,total=action['amount'],all_in=all_in)

    def step(self):
        if self.halted:
            raise BotExecutionError(self.failure_message)
        s = self.state
        if not s or not s.status or self.actor == 0:
            raise ValueError('Kein automatischer Schritt ausstehend.')
        try:
            if self.actor is not None:
                seat, version = self.actor, self.version
                decision = self.policies[seat].decide(observe(self, seat))
                if version != self.version or seat != self.actor:
                    raise RuntimeError('Stale decision')
                self.act(seat, decision)
                return
            before_stacks = list(s.stacks)
            kind, text, fields = 'progress', 'Die Hand wird fortgesetzt.', {}
            if s.can_post_ante():
                op=s.post_ante(); kind='blind';text='Ante gesetzt.'
            elif s.can_collect_bets():
                op=s.collect_bets();kind='collect';text='Die Einsätze werden eingesammelt.'
                fields['transfers']=[dict(seat=self.seats[i], amount=n) for i,n in enumerate(op.bets) if n]
                # Uncalled excess is refunded by PokerKit, never called winnings.
                fields['refunds']=[dict(seat=self.seats[i],amount=n-before_stacks[i]) for i,n in enumerate(s.stacks) if n>before_stacks[i]]
                self.pot_layers=[dict(index=i,amount=p.amount,eligible=[self.seats[j] for j in p.player_indices]) for i,p in enumerate(s.pots) if p.amount]
            elif s.can_post_blind_or_straddle():
                op=s.post_blind_or_straddle();kind='blind'
                fields=dict(seat=self.seats[op.player_index],amount=op.amount)
                text=f'{NAMES[fields["seat"]]} setzt den Blind: {op.amount} Chips.'
            elif s.can_deal_hole():
                # Match frozen Game's actual deal order. One card per operation.
                op=s.deal_hole(1);self.original.setdefault(op.player_index,[]).extend(map(repr,op.cards))
                kind='deal';fields=dict(seat=self.seats[op.player_index],card_index=len(self.original[op.player_index])-1)
                text=f'{NAMES[fields["seat"]]} erhält eine Karte.'
            elif s.can_burn_card():
                s.burn_card();kind='prepare';text='Die nächste Gemeinschaftskarte wird vorbereitet.'
            elif s.can_deal_board():
                s.deal_board(1);kind='board';fields=dict(card_index=sum(map(len,s.board_cards))-1)
                text=['Flop','Flop','Flop','Turn','River'][fields['card_index']]+' wird aufgedeckt.'
            elif s.can_select_runout_count():
                s.select_runout_count();kind='prepare';text='Der Showdown wird vorbereitet.'
            elif s.can_show_or_muck_hole_cards():
                op=s.show_or_muck_hole_cards();kind='show';fields=dict(seat=self.seats[op.player_index])
                text=f'{NAMES[fields["seat"]]} '+(('zeigst die Karten.' if op.hole_cards else 'legst die Karten verdeckt ab.') if fields['seat']==0 else ('zeigt die Karten.' if op.hole_cards else 'legt die Karten verdeckt ab.'))
            elif s.can_kill_hand():
                s.kill_hand();kind='prepare';text='PokerKit prüft die Topfberechtigung.'
            elif s.can_push_chips():
                op=s.push_chips();kind='award'
                winners=[dict(seat=self.seats[i],name=NAMES[self.seats[i]],amount=n) for i,n in enumerate(op.amounts) if n]
                award=dict(index=len(self.payouts),engine_pot=op.pot_index,amount=sum(op.amounts),winners=winners)
                self.payouts.append(award);fields['award']=dict(award)
                text='Topfauszahlung: '+', '.join(f'{w["name"]} {w["amount"]} Chips' for w in winners)+'.'
            elif s.can_pull_chips():
                s.pull_chips();kind='credit';text='Auszahlung wird dem Chipstand gutgeschrieben.'
            else:
                raise RuntimeError('Unsupported live lifecycle')
            self._settle();self.version += 1
            if not s.status:
                kind='complete';text='Hand abgeschlossen · alle Chips sind ausgezahlt.'
            self._emit(kind,text,**fields)
        except Exception:
            self.halted=True;self.bot_errors+=1;self.version+=1
            raise BotExecutionError(self.failure_message) from None


def live_view(game, learning=True):
    # observe is unchanged for agents and old evaluation. Initial blind/dealing
    # phase has no PokerKit street; supply a separate explicit projection there.
    s=game.state
    if s and s.street_index is None and s.status:
        from copy import copy
        proxy=copy(game);proxy.state=None
        result=observe(proxy)
        result.update(hand=game.hand,can_start=False,stage='Auszahlung' if s.board_cards else 'Austeilen',pot=s.total_pot_amount,
                      board=[repr(c) for group in s.board_cards for c in group])
        for p in result['players']:
            if p['seat'] in game.seats:
                i=game.seats.index(p['seat']);p.update(stack=s.stacks[i],bet=s.bets[i],dealer=p['seat']==game.dealer)
    else:
        result=observe(game)
    shown={}
    if s:
        for op in s.operations:
            if isinstance(op,HoleCardsShowingOrMucking) and op.hole_cards:
                shown[op.player_index]=list(map(repr,op.hole_cards))
    finished=bool(s and not s.status)
    folded={op.player_index for op in s.operations if isinstance(op,Folding)} if s else set()
    for p in result['players']:
        seat=p['seat'];i=game.seats.index(seat) if seat in game.seats else None
        cards=game.original.get(i,[])
        p['cards']=list(cards) if seat==0 or (finished and learning) else list(shown.get(i,[None]*len(cards)))
        p['participated']=i is not None
        p['combination']=describe_hand(p['cards'],result['board']) if finished else None
        if s and i is not None and s.status:
            p['status']='gepasst' if i in folded else 'All-in' if s.stacks[i]==0 else 'im Spiel'
    result.update(epoch=game.epoch,opponents=dict(game.bot_info),halted=game.halted,
                  message=game.failure_message if game.halted else None,table=table_details(game),
                  event=dict(game.event),events=[dict(e) for e in game.events[-100:]],
                  advance=bool(s and s.status and game.actor!=0 and not game.halted),learning=learning)
    if game.halted:
        result['legal']=dict(fold=False,call=None,raise_min=None,raise_max=None,all_in=None);result['can_start']=False
    folded={op.player_index for op in s.operations if isinstance(op,Folding)} if s else set()
    result['outcome']=None
    if finished:
        fold_win=len(game.seats)-len(folded)==1
        result['outcome']=dict(reason='fold' if fold_win else 'showdown',
            explanation='Alle anderen Spieler sind ausgestiegen.' if fold_win else 'PokerKit hat die berechtigten Hände für jeden Topf verglichen.',
            incomplete_board=len(result['board'])<5,payouts=[dict(p) for p in game.payouts],
            pot_layers=[dict(p) for p in game.pot_layers],
            players=[dict(seat=p['seat'],name=p['name'],cards=list(p['cards']),combination=p['combination'],
                          folded=game.seats.index(p['seat']) in folded,net=p['stack']-game.starting_stacks[p['seat']],
                          awarded=sum(r['awarded'] for r in game.result if r['seat']==p['seat']))
                     for p in result['players'] if p['participated']])
    return result
