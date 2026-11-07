import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from pathlib import Path
from random import Random
import pytest
from fastapi.testclient import TestClient
from pokermind import server
from pokermind.learning.learned import LearnedAgent,load_resource,PROJECT_ROOT
from pokermind.teacher import TeacherAgent
from pokermind.views import observe
from pokermind.agents import Decision

@pytest.fixture
def table(monkeypatch):
 monkeypatch.setenv('POKERMIND_BOTS','learned');monkeypatch.delenv('POKERMIND_MODEL',raising=False)
 g=server.configured_game();g._rng=Random(1);monkeypatch.setattr(server,'game',g)
 return g,TestClient(server.app)

def test_shared_model_load_once_views_and_no_teacher(table,monkeypatch):
 g,client=table
 monkeypatch.setattr(TeacherAgent,'decide',lambda *_:pytest.fail('Teacher called'))
 from pokermind.teacher import equity
 monkeypatch.setattr(equity,'estimate',lambda *_:pytest.fail('Monte Carlo called'))
 import joblib
 monkeypatch.setattr(joblib,'load',lambda *_:pytest.fail('Reloaded on turn/reset'))
 assert all(isinstance(p,LearnedAgent) for p in g.policies[1:])
 assert len({id(p.model) for p in g.policies[1:]})==1
 assert len({id(p) for p in g.policies[1:]})==3
 original=LearnedAgent.decide;seen=set()
 def checked(self,o):
  seat=o['viewer'];seen.add(seat)
  idx=g.seats.index(seat);assert o['players'][seat]['cards']==g.original[idx]
  assert all(p['cards']==[None,None] for p in o['players'] if p['seat']!=seat and p['in_hand'])
  return original(self,o)
 monkeypatch.setattr(LearnedAgent,'decide',checked)
 for _ in range(3):
  g.start_hand();g.advance_bots()
  while g.actor is not None:g.act(0,Decision('call'));g.advance_bots()
 assert seen=={1,2,3}
 before=sum(p.decisions for p in g.policies[1:]);g.reset();assert sum(p.decisions for p in g.policies[1:])==before
 g.start_hand();g.advance_bots()
 s=client.get('/api/state').json();assert s['opponents']['mode']=='learned'
 assert not any(k in json.dumps(s) for k in ('probabilities','features','deck','seed','last_prediction'))
 assert all(p['cards']==[None,None] for p in s['players'][1:])

def test_resource_single_load_and_separate_games(monkeypatch):
 import joblib
 load_resource.cache_clear();original=joblib.load;count=[]
 def counted(*a,**kw):count.append(1);return original(*a,**kw)
 monkeypatch.setattr(joblib,'load',counted);monkeypatch.setenv('POKERMIND_BOTS','learned')
 a=server.configured_game();b=server.configured_game();assert len(count)==1
 assert a.policies[1].model is b.policies[1].model and a.policies[1] is not b.policies[1]
 a.start_hand();a.advance_bots();a.reset();assert len(count)==1 and b.state is None

def test_startup_errors_and_absolute_path(monkeypatch,tmp_path):
 monkeypatch.setenv('POKERMIND_BOTS','learned');monkeypatch.setenv('POKERMIND_MODEL',str(tmp_path))
 with pytest.raises(RuntimeError,match='nicht geladen'):server.configured_game()
 meta=json.loads((PROJECT_ROOT/'models/imitation-v1/metadata.json').read_text());meta['features']=meta['features'][::-1]
 (tmp_path/'metadata.json').write_text(json.dumps(meta))
 with pytest.raises(RuntimeError,match='nicht geladen'):server.configured_game()
 meta['features']=meta['features'][::-1];(tmp_path/'metadata.json').write_text(json.dumps(meta));(tmp_path/'selected.joblib').write_bytes(b'corrupted')
 with pytest.raises(RuntimeError,match='nicht geladen'):server.configured_game()
 monkeypatch.setenv('POKERMIND_MODEL',str(PROJECT_ROOT/'models/imitation-v1'));monkeypatch.chdir(tmp_path)
 assert server.configured_game().bot_info['mode']=='learned'

def test_concurrent_duplicate_reset_and_runtime_failure(table,monkeypatch):
 g,client=table;v=g.version;entered=Event();release=Event();original=g.policies[3].decide
 def pending(o):entered.set();assert release.wait(3);return original(o)
 monkeypatch.setattr(g.policies[3],'decide',pending)
 with ThreadPoolExecutor(2) as pool:
  first=pool.submit(client.post,'/api/command',json=dict(action='start',version=v))
  assert entered.wait(3)
  duplicate=pool.submit(client.post,'/api/command',json=dict(action='reset',version=v))
  release.set();assert first.result().status_code==200;assert duplicate.result().status_code==409
 current=client.get('/api/state').json();v=current['version']
 assert client.post('/api/command',json=dict(action='reset',version=v)).status_code==200
 after=client.get('/api/state').json()
 assert client.post('/api/command',json=dict(action='call',version=v)).status_code==409
 assert client.get('/api/state').json()==after
 def broken(o):raise ValueError('SECRET AcAd seed=123')
 monkeypatch.setattr(g.policies[3],'decide',broken)
 response=client.post('/api/command',json=dict(action='start',version=g.version))
 assert response.status_code==503 and 'SECRET' not in response.text
 s=client.get('/api/state').json();assert s['halted'] and s['hand']==1 and s['pot']==30
 assert s['legal']['call'] is None
 assert client.post('/api/command',json=dict(action='call',version=g.version)).status_code==503
 assert client.post('/api/command',json=dict(action='reset',version=g.version)).status_code==200
 assert not client.get('/api/state').json()['halted']

def test_short_stacks_and_heads_up(table):
 g,_=table
 for stacks in ([50,100,200,7650],[4000,0,0,4000]):
  g.reset();g.stacks=list(stacks);g.start_hand();g.advance_bots()
  while g.actor is not None:
   g.act(0,Decision('call'));g.advance_bots()
  assert sum(g.stacks)==8000 and not g.halted and g.result

def test_configured_modes(monkeypatch):
 for mode in ('baseline','teacher','learned'):
  monkeypatch.setenv('POKERMIND_BOTS',mode)
  assert server.configured_game().bot_info['mode']==mode
