import json
from pathlib import Path
import numpy as np
import pytest
from pokermind.learning.inference import align,adapt,ModelAgent
from pokermind.data.schema import CLASSES,FEATURE_NAMES,extract
from pokermind.game import Game
from pokermind.views import observe
from pokermind.agents import Decision

def observation():
 g=Game(3);g.start_hand();return observe(g,g.actor)

def test_class_order_missing_and_illegal():
 o=observation()
 assert align([.7,.3],['small','fold']).tolist()==[.3,0,0,.7,0,0]
 info,d=adapt([1],['check'],o)
 assert info['raw']=='check' and info['raw_illegal'] and info['fallback']
 assert d==Decision('fold')
 info,d=adapt([.5,.5],['small','fold'],o);assert info['label']=='fold'
 with pytest.raises(ValueError):align([1],['unknown'])

def test_no_legal_and_short_call():
 o=observation();o['legal']=dict(fold=False,call=None,raise_min=None,raise_max=None,all_in=None)
 with pytest.raises(ValueError,match='no available legal'):adapt([1],['fold'],o)
 g=Game(2);g.stacks=[50,100,200,7650];g.start_hand();g.act(g.actor,Decision('raise',200));o=observe(g,g.actor)
 info,d=adapt([1],['call'],o);assert d==Decision('call') and info['label']=='call'

def test_raise_mapping():
 o=observation();info,d=adapt([1],['small'],o)
 from pokermind.teacher import candidates,TeacherConfig
 assert d==candidates(o,TeacherConfig())['small']

def test_actual_reload_schema_and_teacher_isolation(monkeypatch,tmp_path):
 import shutil,joblib
 from pokermind.teacher import TeacherAgent
 root=Path('models/imitation-v1')
 if not root.exists():pytest.skip('Release artifact not built yet')
 monkeypatch.setattr(TeacherAgent,'decide',lambda *a:pytest.fail('Teacher called'))
 from pokermind.teacher import equity
 monkeypatch.setattr(equity,'estimate',lambda *a:pytest.fail('Monte Carlo called'))
 a=ModelAgent(root);b=ModelAgent(root);o=observation();assert a.decide(o)==b.decide(o)
 model=joblib.load(root/'selected.joblib');f=extract(o);x=[[f[k] for k in FEATURE_NAMES]]
 np.testing.assert_allclose(model.predict_proba(x),a.model.predict_proba(x))
 joblib.dump(model,tmp_path/'roundtrip.joblib');np.testing.assert_allclose(model.predict_proba(x),joblib.load(tmp_path/'roundtrip.joblib').predict_proba(x))
 meta=json.loads((root/'metadata.json').read_text());meta['features']=meta['features'][::-1]
 (tmp_path/'metadata.json').write_text(json.dumps(meta))
 with pytest.raises(ValueError,match='ordering'):ModelAgent(tmp_path)
 with pytest.raises(ValueError,match='observation'):a.decide({})

def test_primary_metric_includes_allin_rows():
 from pokermind.learning.experiment import metrics
 r=metrics(['fold','all_in'],['fold','fold'])
 assert r['classes']['fold']['precision']==.5
 assert r['macro_f1_five']==pytest.approx((2/3)/5)
 assert len(r['classes'])==6 and r['classes']['all_in']['support']==1
