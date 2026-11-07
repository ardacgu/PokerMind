"""Explicit public projection. Never serialize PokerKit State or operations."""
from pokerkit import HoleCardsShowingOrMucking
from .game import NAMES

def observe(game, viewer=0):
    s = game.state
    shown = {}
    if s:
        for op in s.operations:
            if isinstance(op, HoleCardsShowingOrMucking) and op.hole_cards:
                shown[op.player_index] = list(map(repr, op.hole_cards))
    players = []
    for seat, name in enumerate(NAMES):
        idx = game.seats.index(seat) if seat in game.seats else None
        stack = s.stacks[idx] if s and idx is not None else game.stacks[seat]
        cards = []
        if s and idx is not None:
            cards = game.original.get(idx, []) if seat == viewer else shown.get(idx, [None, None])
        status = 'bereit'
        if idx is None and not stack or (s and not s.status and not stack):
            status = 'ausgeschieden'
        elif s and idx is not None and s.status:
            status = 'gepasst' if not s.statuses[idx] else ('All-in' if stack == 0 else 'im Spiel')
        players.append(dict(seat=seat, name=name, stack=stack,
                            bet=s.bets[idx] if s and idx is not None else 0,
                            contribution=max(0, -s.payoffs[idx]) if s and idx is not None and s.status else 0,
                            in_hand=bool(s and s.status and idx is not None and s.statuses[idx]),
                            cards=list(cards), status=status, dealer=seat == game.dealer and bool(s)))
    legal = dict(fold=False, call=None, raise_min=None, raise_max=None, all_in=None)
    if s and game.actor == viewer:
        legal['fold'] = s.can_fold()
        if s.can_check_or_call():
            legal['call'] = s.checking_or_calling_amount
        if s.can_complete_bet_or_raise_to():
            legal['raise_min'] = s.min_completion_betting_or_raising_to_amount
            legal['raise_max'] = s.max_completion_betting_or_raising_to_amount
        idx = s.actor_index
        total = s.stacks[idx] + s.bets[idx]
        if s.can_complete_bet_or_raise_to(total):
            legal['all_in'] = dict(action='raise', amount=total)
        elif legal['call'] == s.stacks[idx]:
            legal['all_in'] = dict(action='call', amount=None)
    finished = bool(s and not s.status)
    champion = next((i for i, n in enumerate(game.stacks) if n > 0), None) if finished and sum(n > 0 for n in game.stacks) == 1 else None
    return dict(version=game.version, viewer=viewer, hand=game.hand, players=players,
                board=[repr(c) for group in s.board_cards for c in group] if s else [],
                pot=s.total_pot_amount if s else 0, actor=game.actor, legal=legal,
                stage=('Ergebnis' if finished else ['Preflop', 'Flop', 'Turn', 'River'][s.street_index]) if s else 'Bereit',
                finished=finished, champion=champion, result=[dict(r) for r in game.result],
                history=list(game.history[-30:]), can_start=(not s or finished) and champion is None)
