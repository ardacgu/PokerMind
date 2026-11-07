"""Explicit local QA server; NEVER imported by the production app.

Run: PYTHONPATH=. .venv/bin/python scripts/stage7_browser_fixtures.py
Only this launcher registers /__qa/scenario/{name}. All fixture states and
payouts come from PokerKit, not fake JSON. Fixed cards are private test setup.
"""
from collections import deque
from random import Random
from pokerkit import Card, Deck, NoLimitTexasHoldem
from pokermind.game import AUTOMATIONS
from pokermind.agents import Decision
from pokermind import server
import uvicorn


def setup(stacks,holes,board):
    g=server.configured_game();g.stacks=list(stacks);g.seats=list(range(4));g.hand=1;g.dealer=3
    s=NoLimitTexasHoldem.create_state(AUTOMATIONS,True,0,(10,20),20,stacks,4)
    g.state=s
    for i,h in enumerate(holes):s.deal_hole(h,i)
    g.original={i:list(map(repr,h)) for i,h in enumerate(s.hole_cards)}
    board=list(Card.parse(board));used=set(board)|{c for h in s.hole_cards for c in h}
    burns=[c for c in Deck.STANDARD if c not in used][:3]
    s.deck_cards=deque([burns[0],*board[:3],burns[1],board[3],burns[2],board[4]])
    g._settle();return g


def scenario(name):
    if name=='side-pots':
        g=setup([4000,500,1500,2000],['AcAd','KcKd','QcQd','JcJd'],'2h3h7s8s9c')
        for move in [Decision('raise',1500),Decision('call'),Decision('call'),Decision('call')]:g.act(g.actor,move)
        assert g.actor==0 and len(tuple(g.state.pots))==2
    elif name=='side-winners':
        g=setup([50,100,200,7650],['AcAd','KcKd','QcQd','JcJd'],'2h3h7s8s9c')
        g.act(g.actor,Decision('raise',200))
        while g.actor is not None:g.act(g.actor,Decision('call'))
        assert len(g.result)==3
    elif name in ('split','champion','eliminated'):
        if name=='split':g=setup([2000]*4,['2c3c','4d5d','6s7s','8c9c'],'AhKhQhJhTh')
        elif name=='champion':g=setup([2000]*4,['AcAd','KcKd','QcQd','JcJd'],'2h3h7s8s9c')
        else:g=setup([5,2000,2000,3995],['2c3d','AcAd','KcKd','QcQd'],'4h7s9cTsJh')
        while g.actor is not None:
            move=Decision('raise',g.state.max_completion_betting_or_raising_to_amount) if name=='champion' and g.state.can_complete_bet_or_raise_to() else Decision('call')
            g.act(g.actor,move)
        assert sum(g.stacks)==8000
    elif name=='heads-up':
        g=server.configured_game();g._rng=Random(1);g.stacks=[4000,0,0,4000];g.start_hand();g.advance_bots()
    elif name in ('live','error'):
        g=server.configured_game();g._rng=Random(1)
        if name=='error':g.start_hand();g.halted=True
    else:raise ValueError('Unknown QA scenario')
    return g


@server.app.post('/__qa/scenario/{name}')
def select(name:str):
    with server.lock:
        server.game=scenario(name)
        return server.public_state()

if __name__=='__main__':uvicorn.run(server.app,host='127.0.0.1',port=8768)
