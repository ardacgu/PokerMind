"""Tournament lifecycle adapter; PokerKit alone implements poker rules."""
from collections import deque
from random import Random, SystemRandom
from pokerkit import (Automation, NoLimitTexasHoldem, Deck, HoleDealing,
                      HoleCardsShowingOrMucking, ChipsPushing)
from .agents import Decision, RuleBot

AUTOMATIONS = tuple(a for a in Automation if a not in (
    Automation.HOLE_DEALING, Automation.BOARD_DEALING, Automation.CARD_BURNING))
NAMES = ['Du', 'Ada', 'Turing', 'Grace']

class BotExecutionError(RuntimeError):
    pass

class Game:
    def __init__(self, seed=None, policies=None):
        self.policies = policies or [RuleBot(i - 1) for i in range(4)]
        self._rng = SystemRandom() if seed is None else Random(seed)
        self.bot_info=dict(mode='baseline',label='Regelbasierte Vergleichsgegner',version=None)
        self.bot_errors=0
        self.version = 0
        self.reset()

    def reset(self):
        self.halted=False
        self.failure_message='Gegnerentscheidung fehlgeschlagen. Die Partie wurde angehalten. Der Spielstand bleibt sichtbar; bitte neu starten.'
        self.stacks = [2000] * 4
        self.dealer = 3
        self.hand = 0
        self.state = None
        self.seats = []
        self.result = []
        self.history = []
        self.original = {}
        self.version += 1

    @property
    def actor(self):
        return self.seats[self.state.actor_index] if self.state and self.state.actor_index is not None else None

    def start_hand(self):
        if self.state and self.state.status:
            raise ValueError('Die laufende Hand ist noch nicht beendet.')
        active = [i for i, stack in enumerate(self.stacks) if stack > 0]
        if len(active) < 2:
            raise ValueError('Die Partie ist beendet. Bitte neu starten.')
        if len(active) == 2 and len(self.seats) > 2:
            previous_bb = self.seats[1]
            next_bb = next((previous_bb + d) % 4 for d in range(1, 5) if (previous_bb + d) % 4 in active)
            self.dealer = next(seat for seat in active if seat != next_bb)
        else:
            self.dealer = next((self.dealer + d) % 4 for d in range(1, 5) if (self.dealer + d) % 4 in active)
        # PokerKit index 0 acts first postflop. In heads-up it is the BB,
        # index 1 is the button/SB; PokerKit reverses the supplied blinds.
        self.seats = [(self.dealer + d) % 4 for d in range(1, 5) if (self.dealer + d) % 4 in active]
        self.state = NoLimitTexasHoldem.create_state(AUTOMATIONS, True, 0, (10, 20), 20,
                          [self.stacks[i] for i in self.seats], len(active))
        deck = list(Deck.STANDARD)
        self._rng.shuffle(deck)
        self.state.deck_cards = deque(deck)
        self.hand += 1
        self.result = []
        self.history = ['Blinds 10 / 20 gesetzt.']
        self.original = {}
        self._settle()
        self.version += 1

    def _settle(self):
        s = self.state
        while s.status and s.actor_index is None:
            if s.can_deal_hole():
                op = s.deal_hole()
                self.original.setdefault(op.player_index, []).extend(map(repr, op.cards))
            elif s.can_burn_card():
                s.burn_card()
            elif s.can_deal_board():
                s.deal_board()
            else:
                raise RuntimeError('Unexpected PokerKit lifecycle state')
        if not s.status:
            for i, seat in enumerate(self.seats):
                self.stacks[seat] = s.stacks[i]
            awards = [0] * len(self.seats)
            for op in s.operations:
                if isinstance(op, ChipsPushing):
                    for i, amount in enumerate(op.amounts):
                        awards[i] += amount
            self.result = [dict(seat=seat, name=NAMES[seat], awarded=awards[i], net=s.payoffs[i])
                           for i, seat in enumerate(self.seats) if awards[i] > 0]

    def act(self, seat, decision: Decision):
        if seat != self.actor or self.actor is None:
            raise ValueError('Dieser Spieler ist nicht am Zug.')
        s = self.state
        if decision.action == 'fold':
            s.fold()
            label = 'passt'
        elif decision.action == 'call':
            op = s.check_or_call()
            label = f'geht {op.amount} mit' if op.amount else 'checkt'
        elif decision.action == 'raise':
            if type(decision.amount) is not int:
                raise ValueError('Der Einsatz muss eine ganze Chipzahl sein.')
            s.complete_bet_or_raise_to(decision.amount)
            label = f'erhöht auf {decision.amount}'
        else:
            raise ValueError('Unbekannte Aktion.')
        if seat == 0:
            label = label.replace('geht ', 'gehst ').replace('checkt', 'checkst').replace('passt', 'passt').replace('erhöht ', 'erhöhst ')
        self.history.append(f'{NAMES[seat]} {label}.')
        self._settle()
        self.version += 1

    def advance_bots(self):
        from .views import observe
        if self.halted:raise BotExecutionError(self.failure_message)
        for _ in range(500):
            if self.actor in (None, 0):
                return
            seat = self.actor
            expected_version=self.version
            try:
                decision=self.policies[seat].decide(observe(self, seat))
                if self.version!=expected_version or self.actor!=seat:
                    raise BotExecutionError('Stale bot decision')
                self.act(seat,decision)
            except Exception:
                self.halted=True
                self.bot_errors+=1
                self.version+=1
                raise BotExecutionError(self.failure_message) from None
        self.halted=True
        self.bot_errors+=1
        self.version+=1
        raise BotExecutionError(self.failure_message)
