"""Bounded HTTP/engine integration evidence; not a strength comparison."""
import json
from pathlib import Path
from random import Random
from fastapi.testclient import TestClient
from pokerkit import HoleCardsShowingOrMucking
from pokermind import server

g=server.configured_game();g._rng=Random(1);server.game=g
client=TestClient(server.app);runs=[];responses=0
for stacks in ([2000]*4,[50,100,200,7650],[4000,0,0,4000]):
 g.reset();g.stacks=list(stacks);s=client.get('/api/state').json()
 for _ in range(3):
  r=client.post('/api/command',json=dict(action='start',version=s['version']));assert r.status_code==200;s=r.json();responses+=1
  while True:
   shown={g.seats[o.player_index]:list(map(repr,o.hole_cards)) for o in g.state.operations if isinstance(o,HoleCardsShowingOrMucking) and o.hole_cards}
   for p in s['players'][1:]:
    if p['seat'] in g.seats:assert p['cards']==shown.get(p['seat'],[None,None])
   assert not any(k in json.dumps(s) for k in ('probabilities','last_prediction','features','deck','seed'))
   if s['finished']:break
   r=client.post('/api/command',json=dict(action='call',version=s['version']));assert r.status_code==200;s=r.json();responses+=1
  assert sum(g.stacks)==8000
  if s['champion'] is not None:break
 runs.append(dict(start_stacks=stacks,hands=g.hand,end_stacks=g.stacks,champion=s['champion']))
result=dict(runs=runs,http_responses_checked=responses,decisions=sum(p.decisions for p in g.policies[1:]),fallbacks=sum(p.fallbacks for p in g.policies[1:]),errors=sum(p.errors for p in g.policies[1:]),engine_errors=g.bot_errors)
Path('docs/stage5-http.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
