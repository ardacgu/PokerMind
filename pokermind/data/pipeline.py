"""Atomic session checkpoints, deterministic seeds, group splits and strict validation."""
import argparse
from collections import Counter,defaultdict
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
import json,os,platform,time
from pathlib import Path
from ..game import Game
from ..agents import RuleBot,Decision
from ..teacher import TeacherAgent,TeacherConfig,candidates
from ..views import observe
from .schema import *

def dumps(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(x):return sha256(dumps(x).encode()).hexdigest()
def atomic(path,value):
    path=Path(path);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(dumps(value)+'\n');os.replace(tmp,path)
def source_hashes():
    root=Path(__file__).resolve().parents[1]
    return {str(p.relative_to(root)):sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*.py'))}

def session(job):
    index,base,hands,samples=job;start=time.perf_counter()
    sid=f's{base+index:09d}';card_seed=base+index;teacher_seeds=[base*10+index*4+i for i in range(4)]
    seats=list(range(4)) if index%2==0 else [index%4,(index+1)%4]
    config=TeacherConfig(samples=samples)
    policies=[TeacherAgent(teacher_seeds[i],config) if i in seats else RuleBot(i) for i in range(4)]
    g=Game(card_seed);rows=[];diagnostics=[];excluded=[];action_index=0
    for _ in range(hands):
        g.start_hand()
        while g.actor is not None:
            seat=g.actor;o=deepcopy(observe(g,seat));policy=policies[seat];decision=policy.decide(o)
            action_index+=1
            if isinstance(policy,TeacherAgent):
                diag=deepcopy(policy.last_diagnostic);rid=f'{sid}:a{action_index:06d}'
                diag.pop('elapsed_seconds');diagnostics.append(dict(id=rid,**diag))
                row=dict(id=rid,session=sid,hand=g.hand,seat=seat,observation=o,
                         features=extract(o,config),legal={k:asdict(v) for k,v in candidates(o,config).items()},
                         label=label_for(o,decision,config),executed=asdict(decision),
                         paid=(decision.amount-o['players'][seat]['bet'] if decision.action=='raise' else o['legal']['call'] if decision.action=='call' else 0))
                if diag['fallback']:excluded.append(dict(id=rid,reason='teacher_fallback'))
                else:rows.append(row)
            g.act(seat,decision)
            assert sum(g.state.stacks)+g.state.total_pot_amount==8000
        if observe(g)['champion'] is not None:break
    return dict(session=sid,card_seed=card_seed,teacher_seeds=teacher_seeds,teacher_seats=seats,
        opponent_randomness='none: deterministic RuleBot',hands=g.hand,actions=action_index,
        end='winner' if observe(g)['champion'] is not None else 'hand_limit',final_stacks=g.stacks,
        seconds=time.perf_counter()-start,rows=rows,diagnostics=diagnostics,excluded=excluded)

def generate(root,target=20000,base=100000,hands=12,samples=128,workers=4):
    root=Path(root);root.mkdir(parents=True,exist_ok=True);(root/'sessions').mkdir(exist_ok=True)
    spec=dict(base=base,hands=hands,teacher_version=TeacherAgent.version,teacher_config=asdict(TeacherConfig(samples=samples)),
              schema=VERSION,action_schema=ACTION_VERSION,source_hashes=source_hashes(),python=platform.python_version(),pokerkit='0.7.7')
    cfg=root/'generation.json'
    if cfg.exists() and json.loads(cfg.read_text())!=spec:raise ValueError('Resume configuration/source mismatch; use a new dataset directory')
    atomic(cfg,spec)
    saved=sorted((root/'sessions').glob('*.json'));total=sum(len(json.loads(p.read_text())['rows']) for p in saved)
    index=0
    with ProcessPoolExecutor(max_workers=workers) as pool:
        while total<target:
            jobs=[]
            while len(jobs)<workers:
                if not (root/'sessions'/f's{base+index:09d}.json').exists():jobs.append((index,base,hands,samples))
                index+=1
            for result in pool.map(session,jobs):
                atomic(root/'sessions'/(result['session']+'.json'),result);total+=len(result['rows'])
                atomic(root/'progress.json',dict(accepted=total,last_session=result['session'],target=target))
                print(f"{result['session']} accepted={total}/{target}",flush=True)
    return total

def load_model(path):
    rows=[json.loads(line) for line in Path(path).read_text().splitlines()]
    pairs=[model_row(r) for r in rows]
    return [p[0] for p in pairs],[p[1] for p in pairs]

def export(root):
    root=Path(root);spec=json.loads((root/'generation.json').read_text());config=TeacherConfig(**spec['teacher_config'])
    sessions=[json.loads(p.read_text()) for p in sorted((root/'sessions').glob('*.json'))]
    assert len({s['card_seed'] for s in sessions})==len(sessions), 'Repeated source game family'
    ids=sorted(s['session'] for s in sessions);ranked=sorted(ids,key=lambda s:digest(['split-v1',s]))
    n=len(ids);a=round(.70*n);b=round(.85*n);groups={s:'train' if i<a else 'validation' if i<b else 'test' for i,s in enumerate(ranked)}
    gp=root/'groups.json'
    if gp.exists() and json.loads(gp.read_text())!=groups:raise ValueError('Frozen groups differ: do not append to a released dataset')
    atomic(gp,groups)
    counts=defaultdict(Counter);seen=set();signatures=defaultdict(set);raws=[];ds=[];outs=defaultdict(list);excluded=[]
    for s in sessions:
        ds.extend(s['diagnostics']);excluded.extend(s['excluded'])
        diag={d['id']:d for d in s['diagnostics']}
        for r in s['rows']:
            if r['id'] in seen:raise ValueError('Duplicate ID')
            seen.add(r['id']);o=r['observation'];f=extract(o,config)
            assert r['session']==s['session'] and r['id'].startswith(s['session']+':')
            assert o['viewer']==o['actor']==r['seat'] and o['hand']==r['hand'] and 1<=r['hand']<=s['hands']
            assert sum(p['stack'] for p in o['players'])+o['pot']==8000
            assert r['features']==f and r['legal']=={k:asdict(v) for k,v in candidates(o,config).items()}
            assert asdict(decode(r['label'],o,config))==r['executed']==diag[r['id']]['decision']
            assert not diag[r['id']]['fallback']
            expected_paid=r['executed']['amount']-o['players'][r['seat']]['bet'] if r['executed']['action']=='raise' else o['legal']['call'] if r['executed']['action']=='call' else 0
            assert r['paid']==expected_paid and 0<=r['paid']<=o['players'][r['seat']]['stack']
            model_row(r);split=groups[s['session']]
            for key,val in [('label',r['label']),('street',o['stage']),('live',f['live_count']),('seat',r['seat']),('position',f['relative_button']),('split',split),('all_in_call',f['all_in_call']),('short_call',f['short_call']),('eligible_layers',f['eligible_layers']),('stack_band','<200' if f['stack']<200 else '200-999' if f['stack']<1000 else '1000-2999' if f['stack']<3000 else '3000+')]:counts[key][str(val)]+=1
            counts['all_in_raise'][str(int(r['executed']['action']=='raise' and r['paid']==f['stack']))]+=1
            signatures[digest(f)].add(split)
            raws.append(r);outs[split].append(dict(id=r['id'],session=r['session'],features=f,label=r['label']))
    files={'raw.jsonl':raws,'diagnostics.jsonl':ds,'excluded.jsonl':excluded,'examples.jsonl':raws[:8],**{k+'.jsonl':v for k,v in outs.items()}}
    for name,rows in files.items():(root/name).write_text(''.join(dumps(r)+'\n' for r in rows))
    atomic(root/'schema.json',dict(version=VERSION,features=SCHEMA,feature_order=FEATURE_NAMES,classes=CLASSES,action_version=ACTION_VERSION))
    for split in outs:assert len(load_model(root/(split+'.jsonl'))[1])==len(outs[split])
    stats=dict(accepted=len(raws),generated=len(ds),excluded=len(excluded),sessions=len(sessions),counts={k:dict(v) for k,v in counts.items()},
        duplicate_ids=0,duplicate_feature_rows=len(raws)-len(signatures),cross_split_feature_patterns=sum(len(v)>1 for v in signatures.values()),
        seconds=sum(s['seconds'] for s in sessions),groups=groups,
        session_metadata=[{k:v for k,v in s.items() if k not in ('rows','diagnostics','excluded')} for s in sessions])
    hashes={str(p.relative_to(root)):sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file() and p.name not in ('manifest.json','progress.json') and not p.name.endswith('.tmp')}
    atomic(root/'manifest.json',dict(**stats,generation=spec,hashes=hashes))
    print(dumps({k:v for k,v in stats.items() if k not in ('groups','session_metadata')}),flush=True)
    return stats

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['generate','export','validate']);p.add_argument('--output',required=True);p.add_argument('--target',type=int,default=20000);p.add_argument('--base',type=int,default=100000);p.add_argument('--hands',type=int,default=12);p.add_argument('--samples',type=int,default=128);p.add_argument('--workers',type=int,default=4);a=p.parse_args()
    if min(a.target,a.hands,a.samples,a.workers)<1: p.error('positive limits required')
    if a.command=='generate':generate(a.output,a.target,a.base,a.hands,a.samples,a.workers)
    elif a.command=='export':export(a.output)
    else:
        root=Path(a.output);m=json.loads((root/'manifest.json').read_text())
        for name,h in m['hashes'].items():assert sha256((root/name).read_bytes()).hexdigest()==h,name
        export(root)

if __name__=='__main__':main()
