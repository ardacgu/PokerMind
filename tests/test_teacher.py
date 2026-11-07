from copy import deepcopy
from random import Random
import json
import pytest
from pokermind.game import Game
from pokermind.views import observe
from pokermind.teacher import TeacherAgent,TeacherConfig,candidates
from pokermind.teacher.features import features
from pokermind.teacher.equity import estimate,sample_deal
from pokermind.agents import Decision

def scenario(contributions=(100,100,100,100), me=0):
    g=Game(2);g.start_hand();o=observe(g,g.actor);o['viewer']=me
    o['board']=['Ah','Kh','Qh','Jh','Th'];o['stage']='River'
    for i,p in enumerate(o['players']):
        p.update(cards=['2c','3c'] if i==me else [None,None],in_hand=True,contribution=contributions[i],bet=0)
    o['legal']=dict(fold=False,call=0,raise_min=20,raise_max=2000,all_in=dict(action='raise',amount=2000))
    return o

def test_certain_win_and_tie():
    o=scenario();f=features(o);e=estimate(o,f,20,Random(1))
    assert e['estimated_showdown_pot_share']==.25 and e['expected_receipt']==100
    o['board']=['Qh','Jh','Th','4c','5d'];o['players'][0]['cards']=['Ah','Kh']
    assert estimate(o,features(o),20,Random(2))['estimated_showdown_pot_share']==1

def test_sidepots_short_call_and_excess():
    o=scenario((20,100,200,200));o['legal']['call']=30
    f=features(o)
    assert f['eligible_total']==200 and f['call_threshold']==.15
    assert [p['amount'] for p in f['pots']]==[200,150,200]
    assert estimate(o,f,8,Random(3))['expected_receipt']==50
    o['players'][3]['contribution']=2000
    assert features(o)['eligible_total']==200
    assert sum(p['amount'] for p in features(o)['pots'])==550
    o['players'][2]['in_hand']=False
    assert estimate(o,features(o),8,Random(3))['expected_receipt']==pytest.approx(200/3)

def test_samples_no_duplicates_and_allin_included():
    o=scenario();o['board']=[];o['players'][1]['status']='All-in';o['players'][1]['stack']=0
    for _ in range(100):
        h,b=sample_deal(o,features(o)['live'],Random(_))
        cards=b+[c for hand in h.values() for c in hand]
        assert len(cards)==13 and len(set(cards))==13

def test_hidden_independence_and_rng_isolation():
    g=Game(8);g.start_hand();o=observe(g,g.actor);rng=g._rng.getstate()
    a=TeacherAgent(99,TeacherConfig(samples=8));d=a.decide(o)
    # Change actual hidden cards without rebuilding the public view; actor's view remains identical.
    others=[i for i,seat in enumerate(g.seats) if seat!=g.actor]
    i,j=others[:2];g.state.hole_cards[i],g.state.hole_cards[j]=g.state.hole_cards[j],g.state.hole_cards[i]
    assert observe(g,g.actor)==o
    b=TeacherAgent(99,TeacherConfig(samples=8));assert b.decide(observe(g,g.actor))==d
    assert a.last_diagnostic['estimate']==b.last_diagnostic['estimate']
    assert rng==g._rng.getstate()

def test_candidates_and_fallback():
    o=scenario();o['legal'].update(raise_min=50,raise_max=50,all_in=dict(action='raise',amount=50))
    cs=candidates(o,TeacherConfig());assert len(cs.values())==len(set(cs.values()))
    assert [d.amount for d in cs.values() if d.action=='raise']==[50]
    o['players'][0]['cards']=['Ah','Ah']
    a=TeacherAgent();assert a.decide(o)==Decision('call') and a.last_diagnostic['fallback']
    o['legal'].update(raise_min=None,raise_max=None,all_in=None)
    assert all(d.action!='raise' for d in candidates(o,TeacherConfig()).values())

def test_real_short_call_observation():
    g=Game(2);g.stacks=[50,100,200,7650];g.start_hand()
    g.act(g.actor,Decision('raise',200))
    o=observe(g,g.actor);assert o['legal']['call']==50
    assert features(o)['eligible_total']==130  # 50+50+10+20; excess excluded
    a=TeacherAgent(1,TeacherConfig(samples=8));g.act(g.actor,a.decide(o))

@pytest.mark.parametrize('seed',range(3))
def test_legal_teacher_hands(seed):
    g=Game(seed);a=TeacherAgent(seed,TeacherConfig(samples=8))
    for _ in range(5):
        g.start_hand()
        while g.actor is not None:
            g.act(g.actor,a.decide(observe(g,g.actor)))
            assert not a.last_diagnostic['fallback']
        assert sum(g.stacks)==8000
        if observe(g)['champion'] is not None: break

def test_configured_table_no_diagnostics(monkeypatch):
    from fastapi.testclient import TestClient
    from pokermind import server
    monkeypatch.setenv('POKERMIND_BOTS','teacher');monkeypatch.setenv('POKERMIND_SAMPLES','8')
    monkeypatch.setattr(server,'game',server.configured_game())
    client=TestClient(server.app);s=client.get('/api/state').json()
    s=client.post('/api/command',json=dict(action='start',version=s['version'])).json()
    while not s['finished']:
        s=client.post('/api/command',json=dict(action='call',version=s['version'])).json()
    assert 'estimate' not in json.dumps(s) and 'diagnostic' not in json.dumps(s)
    assert any(p.last_diagnostic for p in server.game.policies)
