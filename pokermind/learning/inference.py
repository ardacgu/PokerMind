"""One probability adapter for every estimator, including the baseline."""
from pathlib import Path
from hashlib import sha256
import json
import joblib
import numpy as np
import sklearn
from ..data.schema import FEATURE_NAMES,CLASSES,VERSION,ACTION_VERSION,extract,decode
from ..teacher import TeacherConfig,candidates

FALLBACK=('check','fold','call','small','large','all_in')

def align(probabilities,classes):
    values=np.asarray(probabilities,dtype=float)
    if values.shape!=(len(classes),) or len(set(classes))!=len(classes) or not set(classes)<=set(CLASSES):
        raise ValueError('Incompatible probability/class mapping')
    if not np.isfinite(values).all() or (values<0).any():raise ValueError('Invalid probabilities')
    return np.array([values[list(classes).index(c)] if c in classes else 0. for c in CLASSES])

def adapt(probabilities,classes,observation,config=None):
    config=config or TeacherConfig();legal=candidates(observation,config)
    if not legal:raise ValueError('Observation has no available legal action')
    probs=align(probabilities,classes);raw=CLASSES[int(probs.argmax())]
    allowed=[i for i,c in enumerate(CLASSES) if c in legal]
    best=max(allowed,key=lambda i:probs[i]);fallback=probs[best]==0
    chosen=next(c for c in FALLBACK if c in legal) if fallback else CLASSES[best]
    return dict(raw=raw,label=chosen,raw_illegal=raw not in legal,fallback=bool(fallback),
                probabilities=dict(zip(CLASSES,probs.tolist()))),decode(chosen,observation,config)

class ModelAgent:
    def __init__(self,directory,artifact='selected'):
        root=Path(directory);meta=json.loads((root/'metadata.json').read_text())
        if meta['features']!=list(FEATURE_NAMES) or meta['schema_version']!=VERSION or meta['action_version']!=ACTION_VERSION or meta['classes']!=list(CLASSES):
            raise ValueError('Incompatible model feature/action schema or ordering')
        if meta['versions']['scikit-learn']!=sklearn.__version__:raise ValueError('Incompatible scikit-learn version')
        file=root/(artifact+'.joblib')
        if sha256(file.read_bytes()).hexdigest()!=meta['artifacts'][file.name]:raise ValueError('Model artifact hash mismatch')
        # Only load our trusted local artifacts; joblib/pickle is not safe for untrusted files.
        self.model=joblib.load(file)
        if self.model.n_features_in_!=len(FEATURE_NAMES):raise ValueError('Incompatible model feature count')
        self.config=TeacherConfig(**meta['teacher_config']);self.last_prediction=None
    def decide(self,observation):
        try:
            if observation['actor']!=observation['viewer']:raise ValueError('Observation is not on the player turn')
            if not candidates(observation,self.config):raise ValueError('Observation has no available legal action')
            f=extract(observation,self.config)
        except (KeyError,IndexError,TypeError,StopIteration) as exc:
            raise ValueError('Incomplete or incompatible observation') from exc
        x=[[f[k] for k in FEATURE_NAMES]]
        self.last_prediction,d=adapt(self.model.predict_proba(x)[0],self.model.classes_,observation,self.config)
        return d

def main():
    import argparse
    from dataclasses import asdict
    p=argparse.ArgumentParser();p.add_argument('--model',default='models/imitation-v1');p.add_argument('--observation',default='models/imitation-v1/example-observation.json');a=p.parse_args()
    agent=ModelAgent(a.model);d=agent.decide(json.loads(Path(a.observation).read_text()))
    print(json.dumps(dict(decision=asdict(d),prediction=agent.last_prediction),indent=2))
if __name__=='__main__':main()
