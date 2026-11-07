"""Predeclared fit/validation selection, persisted lock, then final test only."""
import argparse,json,platform,time
from collections import Counter
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
from dataclasses import asdict
from importlib.metadata import version
import joblib
import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_recall_fscore_support,accuracy_score,confusion_matrix
from ..data.schema import FEATURE_NAMES,CLASSES,SCHEMA,VERSION,ACTION_VERSION,extract,model_row
from ..teacher import TeacherConfig
from .inference import adapt,ModelAgent

def save(path,x):Path(path).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def read(path):return json.loads(Path(path).read_text())
def hashfile(p):return sha256(Path(p).read_bytes()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()

def verify(root):
    root=Path(root);m=read(root/'manifest.json');schema=read(root/'schema.json')
    assert schema['features']==SCHEMA and schema['feature_order']==list(FEATURE_NAMES) and len(FEATURE_NAMES)==54
    assert schema['classes']==list(CLASSES) and schema['version']==VERSION and schema['action_version']==ACTION_VERSION
    for name,h in m['hashes'].items():assert hashfile(root/name)==h,name
    groups=read(root/'groups.json');splits={};seen=set();families=[]
    for s in ('train','validation','test'):
        rows=[json.loads(x) for x in (root/(s+'.jsonl')).read_text().splitlines()]
        for r in rows:
            model_row(r);assert groups[r['session']]==s and r['id'] not in seen;seen.add(r['id'])
        families.append({r['session'] for r in rows});splits[s]=rows
    assert all(not a&b for i,a in enumerate(families) for b in families[i+1:])
    assert sum(map(len,splits.values()))==m['accepted']==20024 and len(groups)==252
    obs={}
    cfg=TeacherConfig(**m['generation']['teacher_config'])
    for line in (root/'raw.jsonl').open():
        r=json.loads(line);assert extract(r['observation'],cfg)==r['features'];obs[r['id']]=r['observation']
    assert set(obs)==seen
    return splits,obs,m

def metrics(y,p):
    precision,recall,f1,support=precision_recall_fscore_support(y,p,labels=list(CLASSES),zero_division=0)
    cm=confusion_matrix(y,p,labels=list(CLASSES));s=cm.sum(axis=1,keepdims=True)
    return dict(accuracy=float(accuracy_score(y,p)),macro_f1_five=float(np.mean(f1[:5])),macro_f1_six=float(np.mean(f1)),
        classes={c:dict(precision=float(precision[i]),recall=float(recall[i]),f1=float(f1[i]),support=int(support[i])) for i,c in enumerate(CLASSES)},
        confusion=cm.tolist(),confusion_normalized=np.divide(cm,s,out=np.zeros_like(cm,dtype=float),where=s!=0).tolist())

def evaluate(model,rows,obs,cfg):
    start=time.perf_counter();x=[model_row(r)[0] for r in rows];y=[r['label'] for r in rows]
    probabilities=model.predict_proba(x);records=[]
    for r,p in zip(rows,probabilities):
        info,d=adapt(p,model.classes_,obs[r['id']],cfg)
        records.append(dict(id=r['id'],teacher=r['label'],street=obs[r['id']]['stage'],executed=asdict(d),**info))
    raw=[r['raw'] for r in records];filtered=[r['label'] for r in records]
    result=dict(n=len(y),raw=metrics(y,raw),filtered=metrics(y,filtered),
        raw_illegal_rate=sum(r['raw_illegal'] for r in records)/len(y),fallback_rate=sum(r['fallback'] for r in records)/len(y),
        missing_training_classes=[c for c in CLASSES if c not in model.classes_],seconds=time.perf_counter()-start,streets={})
    for street in ('Preflop','Flop','Turn','River'):
        rr=[r for r in records if r['street']==street]
        if rr:result['streets'][street]=dict(n=len(rr),raw=metrics([r['teacher'] for r in rr],[r['raw'] for r in rr]),filtered=metrics([r['teacher'] for r in rr],[r['label'] for r in rr]))
    return result,records

def run(data,output,configuration):
    out=Path(output)
    if out.exists():raise ValueError('Use a NEW model directory; do not overwrite a locked experiment')
    out.mkdir(parents=True);spec=read(configuration);save(out/'experiment.json',spec)
    save(out/'events.json',[dict(event='configuration_frozen',at=now(),sha256=hashfile(out/'experiment.json'))])
    splits,obs,manifest=verify(data)
    cfg=TeacherConfig(**manifest['generation']['teacher_config'])
    save(out/'data-audit.json',dict(counts={s:dict(Counter(r['label'] for r in rows)) for s,rows in splits.items()},rows={s:len(r) for s,r in splits.items()},sessions={s:len({r['session'] for r in rows}) for s,rows in splits.items()},features=len(FEATURE_NAMES),all_hashes_verified=True,disjoint=True))
    x=[model_row(r)[0] for r in splits['train']];y=[r['label'] for r in splits['train']]
    configs=[dict(id='dummy',family='dummy',params=dict(strategy='prior'))]
    for family in spec['families']:
        for depth,leaf in spec['pairs']:
            for weight in spec['class_weights']:
                params=dict(max_depth=depth,min_samples_leaf=leaf,class_weight=weight,random_state=spec['seed'])
                if family=='forest':params.update(n_estimators=spec['forest_estimators'],n_jobs=spec['forest_n_jobs'])
                configs.append(dict(id=f'{family}-d{depth}-l{leaf}-{weight or "none"}',family=family,params=params))
    results=[];models={}
    for c in configs:
        model={'dummy':DummyClassifier,'tree':DecisionTreeClassifier,'forest':RandomForestClassifier}[c['family']](**c['params'])
        start=time.perf_counter();model.fit(x,y);fit=time.perf_counter()-start
        score,_=evaluate(model,splits['validation'],obs,cfg)
        result=dict(**c,fit_seconds=fit,validation=score);results.append(result);models[c['id']]=model
        save(out/'validation.json',results)
        print(c['id'],round(score['filtered']['macro_f1_five'],4),f'fit={fit:.3f}s',flush=True)
    finalize(out,results,models,splits,obs,manifest,data,spec)

def finalize(out,results,models,splits,obs,manifest,data,spec):
    cfg=TeacherConfig(**manifest['generation']['teacher_config'])
    x=[model_row(r)[0] for r in splits['train']]
    def key(r):
        p=r['params'];return (-r['validation']['filtered']['macro_f1_five'],r['family']!='tree',p.get('max_depth',0),-p.get('min_samples_leaf',0),p.get('class_weight') is not None)
    finalists=[min([r for r in results if r['family']==f],key=key) for f in ('tree','forest')]
    winner=min(finalists,key=key);chosen=['dummy']+[r['id'] for r in finalists]
    artifacts={}
    for name in chosen+['selected']:
        model=models[winner['id'] if name=='selected' else name]
        joblib.dump(model,out/(name+'.joblib'),compress=3);artifacts[name+'.joblib']=hashfile(out/(name+'.joblib'))
        before=model.predict_proba(x[:32]);after=joblib.load(out/(name+'.joblib')).predict_proba(x[:32])
        np.testing.assert_allclose(before,after,rtol=1e-13,atol=1e-15)
        assert np.array_equal(before.argmax(axis=1),after.argmax(axis=1))
    meta=dict(package='imitation-v1',selected=winner,features=list(FEATURE_NAMES),schema_version=VERSION,action_version=ACTION_VERSION,classes=list(CLASSES),teacher_config=asdict(cfg),artifacts=artifacts,
        versions={k:version(k) for k in ('scikit-learn','numpy','scipy','joblib','pokerkit')},python=platform.python_version(),
        data_path=str(data),data_hashes={p:hashfile(Path(data)/p) for p in ('manifest.json','schema.json','groups.json','train.jsonl','validation.jsonl','test.jsonl')},
        source_hashes={str(p):hashfile(p) for p in sorted(Path('pokermind').rglob('*.py'))},preprocessing='none',selection_metric=spec['primary'])
    save(out/'metadata.json',meta)
    save(out/'selection.json',dict(locked_at=now(),winner=winner['id'],finalists=chosen,configuration_hash=hashfile(out/'experiment.json'),validation_hash=hashfile(out/'validation.json'),artifacts=artifacts))
    events=read(out/'events.json');events.append(dict(event='selection_and_artifacts_locked',at=now()));save(out/'events.json',events)
    # No test performance was computed above this line. No refit after selection.
    final={}
    for name in chosen:
        model=joblib.load(out/(name+'.joblib'));final[name]={}
        for split in ('train','validation','test'):
            result,records=evaluate(model,splits[split],obs,cfg);final[name][split]=result
            if split in ('validation','test'):(out/(name+'-'+split+'-predictions.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in records))
    save(out/'results.json',final);events.append(dict(event='test_evaluated',at=now()));save(out/'events.json',events)
    start=time.perf_counter();agent=ModelAgent(out);load=time.perf_counter()-start
    sample=[obs[r['id']] for r in splits['validation'][:200]]
    for o in sample[:10]:agent.decide(o)
    times=[]
    for o in sample:
        start=time.perf_counter();agent.decide(o);times.append(time.perf_counter()-start)
    save(out/'latency.json',dict(n=len(times),warmup=10,load_seconds=load,mean_seconds=float(np.mean(times)),p95_seconds=float(np.percentile(times,95)),measurement='Sequential calls to ModelAgent.decide including feature extraction, predict_proba, legal mapping; first 200 validation observations; ten warmup calls excluded',environment=platform.platform(),processor=platform.processor()))
    save(out/'example-observation.json',sample[0])
    print('LOCKED WINNER:',winner['id'],flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--data',default='data/main-v1');p.add_argument('--output',default='models/imitation-v1');p.add_argument('--config',default='experiments/imitation-v1.json');p.add_argument('--finalize-existing',action='store_true');a=p.parse_args()
    if a.finalize_existing:
        out=Path(a.output)
        if (out/'selection.json').exists():raise ValueError('Selection already locked; do not reselect')
        results=read(out/'validation.json');spec=read(out/'experiment.json')
        assert spec==read(a.config) and len(results)==13
        splits,obs,manifest=verify(a.data)
        models={p.stem:joblib.load(p) for p in out.glob('*.joblib')}
        finalize(out,results,models,splits,obs,manifest,a.data,spec)
    else:run(a.data,a.output,a.config)
if __name__=='__main__':main()
