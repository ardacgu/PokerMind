"""Public counterfactual accounting for evaluation, never game settlement."""
def features(o):
    me=o['viewer']; players=o['players']; call=o['legal']['call']
    if call is None: raise ValueError('Teacher must act on its own turn')
    contributions=[p['contribution'] for p in players]
    contributions[me]+=call
    live=[p['seat'] for p in players if p['in_hand']]
    pots=[]; previous=0
    for level in sorted(set(contributions)-{0}):
        donors=[i for i,n in enumerate(contributions) if n>=level]
        eligible=[i for i in donors if i in live]
        amount=(level-previous)*len(donors); previous=level
        # A single contributor's excess is refundable, not contested money.
        if len(donors)>1:
            pots.append(dict(amount=amount,eligible=eligible))
    relevant=[p for p in pots if me in p['eligible']]
    eligible_total=sum(p['amount'] for p in relevant)
    own=players[me]
    return dict(viewer=me,stage=o['stage'],stack=own['stack'],call=call,
                own_bet=own['bet'],highest_bet=max(p['bet'] for p in players),
                opponents=len(live)-1,button=own['dealer'],live=live,
                pots=pots,eligible_pots=relevant,eligible_total=eligible_total,
                call_threshold=call/eligible_total if eligible_total else None)
