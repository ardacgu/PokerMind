"""Separate targeted legal-state checks, never merged into natural splits."""
from dataclasses import asdict
from pathlib import Path
import json
from pokerkit import NoLimitTexasHoldem
from pokermind.game import Game,AUTOMATIONS
from pokermind.views import observe
from pokermind.agents import Decision
from pokermind.teacher import TeacherAgent,TeacherConfig,candidates
from pokermind.data.schema import extract,label_for

def record(g,name):
 o=observe(g,g.actor);cfg=TeacherConfig();teacher=TeacherAgent(87,cfg);d=teacher.decide(o)
 row=dict(scenario=name,observation=o,features=extract(o),legal={k:asdict(v) for k,v in candidates(o,cfg).items()},label=label_for(o,d,cfg),executed=asdict(d),diagnostic=teacher.last_diagnostic)
 g.act(g.actor,d) # Actual PokerKit legality check.
 return row
rows=[]
for seed in range(5):
 g=Game(seed);g.stacks=[50,100,200,7650];g.start_hand();g.act(g.actor,Decision('raise',200))
 rows.append(record(g,f'short-all-in-call-{seed}'))
# Valid heads-up deal with quads on the river and a distinct shove candidate.
g=Game(1);g.stacks=[700,7300,0,0];g.seats=[0,1];g.dealer=1;g.hand=1
s=NoLimitTexasHoldem.create_state(AUTOMATIONS,True,0,(10,20),20,[700,7300],2)
s.deal_hole('AhAd',0);s.deal_hole('KcKd',1);g.state=s;g.original={0:['Ah','Ad'],1:['Kc','Kd']}
s.complete_bet_or_raise_to(200);s.check_or_call()
for burn,board in [('2c','AsAc2d'),('3c','3d'),('4c','4h')]:
 s.burn_card(burn);s.deal_board(board)
 if len([c for b in s.board_cards for c in b])<5:s.check_or_call();s.check_or_call()
rows.append(record(g,'certain-quads-distinct-all-in-raise'))
p=Path('data/scenarios-v1');p.mkdir(exist_ok=True)
(p/'scenarios.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
(p/'README.md').write_text('# Targeted scenarios\n\nSix legal PokerKit states: five short all-in-call situations and one certain river quads shove. Separate regression/evaluation supplement only; no train/validation/test membership. Not a natural-frequency sample. Generation: `PYTHONPATH=. .venv/bin/python scripts/stage3_scenarios.py`.\n')
print([(r['scenario'],r['label']) for r in rows])
