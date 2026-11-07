from collections import deque
from fastapi.testclient import TestClient
from pokerkit import Card, ChipsPushing, HoleCardsShowingOrMucking
from pokermind import server
from pokermind.agents import Decision
from pokermind.game import Game
from pokermind.presentation import table_details
from pokermind.views import observe
from test_game import fixture, finish


def adapted(state):
    g=Game(1);g.state=state;g.seats=list(range(len(state.stacks)))
    g.original={i:list(map(repr,h)) for i,h in enumerate(state.hole_cards)}
    g.hand=1
    return g


def test_public_actions_and_detachment():
    g=Game(1);g.start_hand();before=observe(g,g.actor)
    g.act(g.actor,Decision('call'));details=table_details(g)
    assert [a['kind'] for a in details['actions']]==['blind','blind','call']
    assert details['last_actions']['3']['seat']==3
    assert details['pending_bets']==50
    assert all(set(a)=={'index','seat','name','kind','amount'} for a in details['actions'])
    details['actions'][0]['amount']=-100
    assert table_details(g)['actions'][0]['amount']==10
    assert 'table' not in before


def test_side_pots_and_split_awards_from_engine():
    s=fixture([50,100,200,200],['AcAd','KcKd','QcQd','JcJd'])
    g=adapted(s)
    s.complete_bet_or_raise_to(200);s.check_or_call();s.check_or_call();s.check_or_call()
    # All-in runout pending: engine owns the already collected layers.
    detail=table_details(g)
    assert [p['amount'] for p in detail['pots']]==[200,150,200]
    assert sum(p['amount'] for p in detail['pots'])+detail['pending_bets']==s.total_pot_amount
    finish(s);detail=table_details(g)
    assert [p['amount'] for p in detail['awards']]==[200,150,200]
    assert [p['winners'][0]['seat'] for p in detail['awards']]==[0,1,2]
    assert not detail['pots']
    split=fixture([101]*3,['2c3c','4d5d','6s7s'],'AhKhQhJhTh',(1,2),1)
    split.fold();finish(split)
    awards=table_details(adapted(split))['awards']
    assert len(awards[0]['winners'])==2
    assert sorted(w['amount'] for w in awards[0]['winners'])==[3,4]


def test_pending_bets_not_mislabeled_pots_and_bet_label():
    g=Game(1);g.start_hand();d=table_details(g)
    assert d['pots']==[] and d['pending_bets']==30 and d['bet_label']=='Erhöhen auf'
    while g.state.street_index==0:g.act(g.actor,Decision('call'))
    d=table_details(g);assert d['bet_label']=='Setzen' and sum(p['amount'] for p in d['pots'])==80
    g.act(g.actor,Decision('raise',20))
    assert table_details(g)['actions'][-1]['kind']=='bet'


def test_browser_api_addition_preserves_observation_privacy(monkeypatch):
    g=Game(1);monkeypatch.setattr(server,'game',g);c=TestClient(server.app)
    s=c.get('/api/state').json();assert s['table']['actions']==[]
    s=c.post('/api/command',json={'version':s['version'],'action':'start'}).json()
    assert all(p['cards']==[None,None] for p in s['players'][1:])
    assert set(s['table'])=={'actions','last_actions','pots','pending_bets','awards','bet_label'}
    assert observe(g).keys()==(set(s)-{'table','opponents','halted','message'})
    while not s['finished']:
        s=c.post('/api/command',json={'version':s['version'],'action':'call'}).json()
    assert sum(p['amount'] for p in s['table']['awards'])==sum(r['awarded'] for r in s['result'])
    shown={g.seats[o.player_index]:list(map(repr,o.hole_cards)) for o in g.state.operations if isinstance(o,HoleCardsShowingOrMucking) and o.hole_cards}
    for p in s['players'][1:]:assert p['cards']==shown.get(p['seat'],[None,None])


def test_frontend_modules_and_accessible_shell(monkeypatch):
    monkeypatch.setattr(server,'game',Game(1));c=TestClient(server.app)
    assert c.post('/__qa/scenario/live').status_code==404
    html=c.get('/').text
    assert 'type="module"' in html and 'aria-live="polite"' in html and '<dialog' in html
    for asset in ('app.js','ui.mjs','style.css','favicon.svg'):assert c.get('/static/'+asset).status_code==200
    css=c.get('/static/style.css').text
    assert 'prefers-reduced-motion:reduce' in css and ':focus-visible' in css
