"""Small actual-model API acceptance run; no UI or gameplay modifications."""
import json
from pathlib import Path
from random import Random
from fastapi.testclient import TestClient
from pokerkit import HoleCardsShowingOrMucking
from pokermind import server
from pokermind.learning.learned import LearnedAgent
from pokermind.teacher import TeacherAgent


def main():
    g=server.configured_game();g._rng=Random(1);server.game=g
    assert g.bot_info['mode']=='learned'
    assert all(isinstance(p,LearnedAgent) for p in g.policies[1:])
    original=TeacherAgent.decide
    def forbidden(*args):raise AssertionError('Teacher used in learned mode')
    TeacherAgent.decide=forbidden
    responses=0
    try:
        with TestClient(server.app) as c:
            for _ in range(3):
                state=c.get('/api/state').json()
                response=c.post('/api/command',json=dict(action='start',version=state['version']))
                while True:
                    assert response.status_code==200;responses+=1;state=response.json()
                    assert state['opponents']['mode']=='learned' and not state['halted']
                    assert not any(k in json.dumps(state) for k in ('probabilities','features','deck','seed'))
                    shown={op.player_index:list(map(repr,op.hole_cards)) for op in g.state.operations if isinstance(op,HoleCardsShowingOrMucking) and op.hole_cards}
                    for p in state['players'][1:]:
                        if p['seat'] in g.seats:assert p['cards']==shown.get(g.seats.index(p['seat']),[None,None])
                    if state['finished']:break
                    assert state['actor']==0
                    response=c.post('/api/command',json=dict(action='call',version=state['version']))
                assert sum(g.stacks)==8000
            result=dict(hands=g.hand,responses=responses,stacks=g.stacks,mode=g.bot_info,
                model_decisions=sum(p.decisions for p in g.policies[1:]),
                adapter_fallbacks=sum(p.fallbacks for p in g.policies[1:]),
                inference_errors=sum(p.errors for p in g.policies[1:]),bot_errors=g.bot_errors,
                privacy_checked=True,teacher_forbidden=True)
            response=c.post('/api/command',json=dict(action='reset',version=state['version']))
            assert response.status_code==200 and g.stacks==[2000]*4
            assert c.get('/').status_code==200 and c.get('/static/app.js').status_code==200
            result['reset_and_static_assets']=True
    finally:TeacherAgent.decide=original
    dest=Path(__file__).resolve().parents[1]/'docs/stage6/http-check.json'
    dest.parent.mkdir(exist_ok=True);dest.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
