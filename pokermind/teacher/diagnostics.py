"""Small offline pilot only. Never imported by HTTP request handling."""
import argparse
from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path
from statistics import mean
from time import perf_counter
from ..agents import RuleBot
from ..game import Game
from ..views import observe
from . import TeacherAgent,TeacherConfig

def run(output, samples=128, hands=12):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    records=[];runs=[];times=[];counts=Counter();fallbacks=0
    for seat in range(4):
        seed=41+seat; teacher=TeacherAgent(100+seat,TeacherConfig(samples=samples))
        policies=[RuleBot(i) for i in range(4)];policies[seat]=teacher
        g=Game(seed);start=perf_counter();actions=0;local=Counter();fs=0;decisions=0
        for _ in range(hands):
            g.start_hand()
            while g.actor is not None:
                actor=g.actor;o=observe(g,actor);d=policies[actor].decide(o)
                if actor==seat:
                    diag=teacher.last_diagnostic
                    times.append(diag['elapsed_seconds']);counts[d.action]+=1;local[d.action]+=1
                    fallbacks+=int(diag['fallback']);fs+=int(diag['fallback']);decisions+=1
                    if decisions<=8:
                        records.append(dict(game_seed=seed,teacher_seed=100+seat,seat=seat,hand=g.hand,
                                            observation=o,**diag))
                g.act(actor,d);actions+=1
                assert sum(g.state.stacks)+g.state.total_pot_amount==8000
            if observe(g)['champion'] is not None: break
        runs.append(dict(seed=seed,teacher_seat=seat,hands=g.hand,actions=actions,teacher_decisions=decisions,
                         distribution=dict(local),fallbacks=fs,completed=observe(g)['champion'] is not None,
                         champion=observe(g)['champion'],stacks=g.stacks,seconds=perf_counter()-start))
    result=dict(config=asdict(TeacherConfig(samples=samples)),runs=runs,distribution=dict(counts),fallbacks=fallbacks,
                teacher_decisions=len(times),mean_seconds=mean(times),max_seconds=max(times),
                p95_seconds=sorted(times)[int(.95*(len(times)-1))])
    (output/'decisions.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
    (output/'pilot.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',default='docs/stage2');p.add_argument('--samples',type=int,default=128);p.add_argument('--hands',type=int,default=12)
    a=p.parse_args()
    if a.hands<1: p.error('hands must be positive')
    print(json.dumps(run(a.output,a.samples,a.hands),indent=2))

if __name__=='__main__': main()
