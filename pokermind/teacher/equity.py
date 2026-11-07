"""Independent uniform sampling; PokerKit alone ranks sampled hands."""
from pokerkit import Card, Deck, StandardHighHand

def sample_deal(o, live, rng):
    board=list(Card.parse(''.join(o['board'])))
    known={p['seat']:list(Card.parse(''.join(c for c in p['cards'] if c))) for p in o['players']}
    used=board+[c for h in known.values() for c in h]
    if len(used)!=len(set(used)): raise ValueError('Duplicate known cards')
    remaining=[c for c in Deck.STANDARD if c not in used]
    needed=5-len(board)+sum(2-len(known[i]) for i in live)
    draw=iter(rng.sample(remaining,needed))
    hands={i:known[i]+[next(draw) for _ in range(2-len(known[i]))] for i in live}
    board += [next(draw) for _ in range(5-len(board))]
    return hands,board

def estimate(o, f, samples, rng):
    receipts=0.; shares=[0.]*len(f['eligible_pots'])
    for _ in range(samples):
        hands,board=sample_deal(o,f['live'],rng)
        ranks={i:StandardHighHand.from_game(h,board) for i,h in hands.items()}
        for j,pot in enumerate(f['eligible_pots']):
            best=max(ranks[i] for i in pot['eligible'])
            winners=[i for i in pot['eligible'] if ranks[i]==best]
            share=1/len(winners) if f['viewer'] in winners else 0.
            shares[j]+=share
            receipts+=share*pot['amount']
    expected=receipts/samples
    return dict(samples=samples,estimated_showdown_pot_share=expected/f['eligible_total'] if f['eligible_total'] else 0.,
                expected_receipt=expected,call_ev=expected-f['call'],
                per_pot_shares=[v/samples for v in shares])
