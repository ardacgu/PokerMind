"""Read-only browser details from public PokerKit actions and pot operations.

This module is never added to agent observations or the feature pipeline.
"""
from pokerkit import (BlindOrStraddlePosting, CheckingOrCalling,
                      CompletionBettingOrRaisingTo, Folding, ChipsPushing, BetCollection)
from .game import NAMES


def table_details(game):
    s = game.state
    result = dict(actions=[], last_actions={}, pots=[], pending_bets=0, awards=[], bet_label='Setzen')
    if not s:
        return result
    street_bets = [0] * len(game.seats)
    for op in s.operations:
        if isinstance(op, BetCollection):
            street_bets = [0] * len(game.seats)
        kind = None
        if isinstance(op, BlindOrStraddlePosting):
            kind, amount = 'blind', op.amount
            street_bets[op.player_index] += amount
        elif isinstance(op, CheckingOrCalling):
            kind, amount = ('call' if op.amount else 'check'), op.amount
            street_bets[op.player_index] += amount
        elif isinstance(op, CompletionBettingOrRaisingTo):
            kind, amount = ('raise' if max(street_bets) else 'bet'), op.amount
            street_bets[op.player_index] = amount
        elif isinstance(op, Folding):
            kind, amount = 'fold', 0
        if kind:
            seat = game.seats[op.player_index]
            action = dict(index=len(result['actions']), seat=seat, name=NAMES[seat], kind=kind, amount=amount)
            result['actions'].append(action)
            result['last_actions'][str(seat)] = action
        if isinstance(op, ChipsPushing):
            result['awards'].append(dict(pot=op.pot_index,
                amount=sum(op.amounts), winners=[dict(seat=game.seats[i], name=NAMES[game.seats[i]], amount=n)
                                               for i,n in enumerate(op.amounts) if n > 0]))
    if s.status:
        result['pots'] = [dict(index=i, amount=p.amount, eligible=[game.seats[j] for j in p.player_indices])
                          for i,p in enumerate(s.pots) if p.amount > 0]
        result['pending_bets'] = sum(s.bets)
        result['bet_label'] = 'Erhöhen auf' if max(s.bets, default=0) > 0 else 'Setzen'
    return result
