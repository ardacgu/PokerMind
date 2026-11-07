from copy import deepcopy
import json
import pytest
from pokermind.data.schema import extract,FEATURE_NAMES,decode,label_for,model_row
from pokermind.data.pipeline import session,generate,export,load_model
from pokermind.game import Game
from pokermind.views import observe
from pokermind.teacher import TeacherConfig,TeacherAgent,candidates

def test_features_no_teacher_or_hidden_future(monkeypatch):
    g=Game(4);g.start_hand();o=observe(g,g.actor)
    monkeypatch.setattr(TeacherAgent,'decide',lambda *a:pytest.fail('Feature extractor called teacher'))
    f=extract(o);changed=deepcopy(o);changed.update(seed=33,winner=2,estimate=.99,label='fold')
    for p in changed['players']:
        if p['seat']!=o['viewer']:p['cards']=['Ac','Ad']
    assert extract(changed)==f and set(f)==set(FEATURE_NAMES)

def test_reproducible_session_and_snapshot():
    a=session((0,400,2,8));b=session((0,400,2,8));a.pop('seconds');b.pop('seconds');assert a==b
    assert a['rows'][0]['observation']['hand']==1
    assert len({r['id'] for r in a['rows']})==len(a['rows'])
    for r in a['rows']:
        assert r['features']==extract(r['observation'],TeacherConfig(samples=8))
        assert decode(r['label'],r['observation'],TeacherConfig(samples=8)).action==r['executed']['action']

def test_resume_export_and_loader(tmp_path):
    generate(tmp_path,1,base=500,hands=1,samples=8,workers=1)
    before={p.name:p.read_bytes() for p in (tmp_path/'sessions').glob('*.json')}
    generate(tmp_path,1,base=500,hands=1,samples=8,workers=1)
    assert before=={p.name:p.read_bytes() for p in (tmp_path/'sessions').glob('*.json')}
    generate(tmp_path,50,base=500,hands=1,samples=8,workers=1)
    m=export(tmp_path);assert len(m['groups'])==m['sessions']
    groups=[]
    for split in ('train','validation','test'):
        p=tmp_path/(split+'.jsonl')
        if p.exists():
            rows=[json.loads(x) for x in p.read_text().splitlines()];groups.append({r['session'] for r in rows})
            assert len(load_model(p)[1])==len(rows)
    assert all(not a&b for i,a in enumerate(groups) for b in groups[i+1:])
    r=json.loads((tmp_path/'raw.jsonl').read_text().splitlines()[0]);r['features']['equity']=.5
    with pytest.raises(ValueError):model_row(r)

def test_short_allin_call_mapping():
    g=Game(2);g.stacks=[50,100,200,7650];g.start_hand()
    from pokermind.agents import Decision
    g.act(g.actor,Decision('raise',200));o=observe(g,g.actor)
    assert extract(o)['all_in_call']==1 and extract(o)['short_call']==1
    assert 'all_in' not in candidates(o,TeacherConfig()) # duplicate call removed
    assert decode('call',o)==Decision('call')
