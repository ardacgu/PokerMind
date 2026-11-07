import copy
import json
from random import Random
from pathlib import Path
import pytest
from pokerkit import HoleCardsShowingOrMucking
from pokermind.agents import Decision, RuleBot
from pokermind.game import Game
from pokermind.evaluation.core import lineup, jobs, seed_for, play_session, semantic
from pokermind.evaluation.run import canonical, collect, write_json, run, provenance, validate_config

ROOT = Path(__file__).resolve().parents[1]
@pytest.fixture
def config():
    c=json.loads((ROOT/'experiments/evaluation-v1.json').read_text())
    c.update(max_hands=3,scenarios={'C':[6200001]})
    return c

def test_rotation_preserves_identities_and_styles(config):
    for scenario in 'ABCD':
        for r in range(4):
            roster=lineup(scenario,r)
            assert [p['seat'] for p in roster]==list(range(4))
            assert next(p['seat'] for p in roster if p['identity']=='target')==r
            assert sorted((p['identity'],p['strategy'],str(p['style'])) for p in roster)==sorted((p['identity'],p['strategy'],str(p['style'])) for p in lineup(scenario,0))
    assert len({j['id'] for j in jobs(config)})==4

@pytest.mark.parametrize('scenario',list('ABCD'))
def test_reproducible_real_agents(config,scenario):
    config['max_hands']=2
    job=dict(id='test',scenario=scenario,seed=6200002,rotation=2)
    a=play_session(job,config);b=play_session(job,config)
    assert a['status']!='error'
    assert semantic(a)==semantic(b)

def test_agent_randomness_does_not_change_deck_or_results(config):
    class NoisyRule(RuleBot):
        def __init__(self,style): super().__init__(style);self.rng=Random(style)
        def decide(self,o):
            for _ in range(1234):self.rng.random()
            return super().decide(o)
    job=jobs(config)[0]
    usual=play_session(job,config)
    noisy=play_session(job,config,[NoisyRule(p['style']) for p in lineup('C',0)])
    assert semantic(usual)==semantic(noisy)
    assert seed_for('deck',1,1)!=seed_for('agent',1,1)
    assert seed_for('deck',1,1)!=seed_for('deck',1,2)

def test_private_views_chip_conservation_and_attribution(config):
    g=Game(0);seen=set()
    class CheckedRule(RuleBot):
        def __init__(self,p):super().__init__(p['style']);self.seat=p['seat']
        def decide(self,o):
            assert o['viewer']==self.seat==g.actor;seen.add(self.seat)
            assert o['players'][self.seat]['cards']==g.original[g.seats.index(self.seat)]
            shown={op.player_index:list(map(repr,op.hole_cards)) for op in g.state.operations if isinstance(op,HoleCardsShowingOrMucking) and op.hole_cards}
            for p in o['players']:
                if p['seat']!=self.seat and p['seat'] in g.seats:
                    assert p['cards']==shown.get(g.seats.index(p['seat']),[None,None])
            assert not any(k in o for k in ('seed','deck','rng','state'))
            result=super().decide(o)
            o['players'][self.seat]['cards'].clear()
            assert len(g.original[g.seats.index(self.seat)])==2
            return result
    job=jobs(config)[0];a=play_session(job,config,[CheckedRule(p) for p in lineup('C',0)],g)
    assert a['status']=='hand_limit' and seen==set(range(4))
    assert all(sum(h['end_chips'])==8000 for h in a['hands'])
    assert sum(p['net_chips'] for p in a['players'])==0
    assert sum(sum(p['actions'].values()) for p in a['players'])==sum(h['actions'] for h in a['hands'])
    assert all(sum(p['actions'].values())==sum(p['labels'].values()) for p in a['players'])
    assert a['champion'] is None and not any(p['tournament_win'] for p in a['players'])

def test_regular_winner_elimination_and_all_ins(config):
    class Shove:
        def decide(self,o):return Decision(**o['legal']['all_in']) if o['legal']['all_in'] else Decision('call')
    config['max_hands']=10
    a=play_session(jobs(config)[0],config,[Shove() for _ in range(4)])
    assert a['status']=='tournament_complete'
    assert sum(p['tournament_win'] for p in a['players'])==1
    assert a['players'][a['champion']]['end_chips']==8000
    assert sum(p['eliminated'] for p in a['players'])==3
    assert all(p['elimination_hand'] is not None for p in a['players'] if p['eliminated'])
    assert sum(p['all_in_actions'] for p in a['players'])>=4
    assert all(p['all_in_hands']<=p['dealt_hands'] for p in a['players'])

def test_controlled_illegal_action_and_sanitized_error(config):
    class Broken:
        def decide(self,o):return Decision('raise',1)
    a=play_session(jobs(config)[0],config,[Broken() for _ in range(4)])
    assert a['status']=='error' and a['completed_hands']==0 and a['champion'] is None
    assert a['incomplete_hand']==1 and sum(p['errors'] for p in a['players'])==1
    assert all(p['end_chips']==2000 for p in a['players'])
    class Secret:
        def decide(self,o):raise ValueError('SECRET hidden cards')
    b=play_session(jobs(config)[0],config,[Secret() for _ in range(4)])
    assert 'SECRET' not in json.dumps(b)

def test_fallback_attribution(config):
    class Fallback(RuleBot):
        def decide(self,o):
            self.last_prediction=dict(label='call',fallback=True,raw_illegal=True)
            return Decision('call')
    a=play_session(jobs(config)[0],config,[Fallback() for _ in range(4)])
    assert a['status']=='hand_limit'
    assert all(p['adapter_fallbacks']==sum(p['actions'].values())==p['raw_illegal'] for p in a['players'])

def test_resume_merge_and_conflicting_duplicates(config,tmp_path):
    left=tmp_path/'left';right=tmp_path/'right';out=tmp_path/'out'
    expected={j['id']:j for j in jobs(config)}
    ch=canonical(config);ph=canonical(provenance())
    records=[]
    for j in jobs(config):
        r=play_session(j,config);r.update(config_hash=ch,provenance_hash=ph);records.append(r)
    for r in records[:2]:write_json(left/'sessions'/f"{r['id']}.json",r)
    for r in records[1:]:write_json(right/'sessions'/f"{r['id']}.json",r)
    assert len(collect([left,right],expected,ch,ph))==4
    merged=run(config,out,workers=1,merge=[left,right])
    before={p.name:p.read_bytes() for p in (out/'sessions').glob('*.json')}
    assert len(run(config,out,workers=1))==len(merged)==4
    assert before=={p.name:p.read_bytes() for p in (out/'sessions').glob('*.json')}
    assert json.loads((out/'manifest.json').read_text())['invocations'][-1]['scheduled']==0
    altered=copy.deepcopy(records[1]);altered['players'][0]['actions']['fold']=999
    write_json(right/'sessions'/f"{altered['id']}.json",altered)
    with pytest.raises(ValueError,match='Conflicting'):collect([left,right],expected,ch,ph)
    with pytest.raises(ValueError,match='configuration/source'):collect([left],expected,'wrong',ph)

def test_reject_changed_teacher_and_duplicate_seeds(config):
    config['teacher_config']['samples']=64
    with pytest.raises(ValueError,match='Frozen'):validate_config(config)
    config['scenarios']['C']*=2
    with pytest.raises(ValueError,match='duplicate'):validate_config(config)
