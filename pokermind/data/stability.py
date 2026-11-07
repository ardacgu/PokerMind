"""Pilot-only, fixed stratified and boundary-focused label-noise study."""
import json,time
from collections import defaultdict,Counter
from pathlib import Path
from ..teacher import TeacherAgent,TeacherConfig
from .schema import label_for
from .pipeline import atomic

def run(root):
    root=Path(root);rows=[json.loads(x) for x in (root/'raw.jsonl').read_text().splitlines()]
    diag={d['id']:d for d in map(json.loads,(root/'diagnostics.jsonl').read_text().splitlines())}
    def distance(r):
        d=diag[r['id']];f=d['features'];e=d['estimate'];share=e['estimated_showdown_pot_share'];edge=share-1/(f['opponents']+1)
        margin=.02+(.02 if f['stage'] in ('Preflop','Flop') else 0)-(.02 if f['button'] else 0)
        return min(abs(edge-.12),abs(edge-.28),abs(share-.85),abs(e['call_ev']/max(1,f['eligible_total'])-max(0,margin)))
    buckets=defaultdict(list)
    for r in rows:buckets[(r['observation']['stage'],r['label'])].append(r)
    selected=[]
    for key,rs in sorted(buckets.items()):
        chosen=sorted(rs,key=distance)[:1]+rs[:1]
        for r in chosen:
            if r not in selected:selected.append(r)
    results=[];start=time.perf_counter()
    for r in selected:
        tests={}
        for samples in (128,512):
            labels=[]
            for seed in (771,772,773):
                c=TeacherConfig(samples=samples);a=TeacherAgent(seed,c)
                labels.append(label_for(r['observation'],a.decide(r['observation']),c))
            tests[str(samples)]=dict(labels=labels,disagreement=len(set(labels))>1,original_disagreements=sum(x!=r['label'] for x in labels))
        results.append(dict(id=r['id'],street=r['observation']['stage'],original=r['label'],boundary_distance=distance(r),tests=tests))
    summary=dict(selected=len(results),seconds=time.perf_counter()-start,
        results=results,summary={str(n):dict(unstable=sum(r['tests'][str(n)]['disagreement'] for r in results),comparisons=3*len(results),original_disagreements=sum(r['tests'][str(n)]['original_disagreements'] for r in results)) for n in (128,512)},
        decision='Freeze teacher-2.0.0 with 128 samples. Preserve noisy boundary cases; this first dataset imitates the stochastic 128-sample teacher, not a noise-free oracle. Higher-sample study is diagnostic only.')
    atomic(root/'stability.json',summary);print(json.dumps({k:v for k,v in summary.items() if k!='results'},indent=2))
if __name__=='__main__':
    import sys
    run(sys.argv[1])
