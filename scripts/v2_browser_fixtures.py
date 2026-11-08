"""Opt-in localhost QA only: python -m uvicorn scripts.v2_browser_fixtures:app --port 8003.

These are real, deterministic PokerKit states, not model playing-strength results.
The production server never imports this module or registers its route.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
from test_live import fixed_live, finish_calls, settle_to_actor
from pokermind import server
from pokermind.agents import Decision
from pokermind.live import live_view,LiveGame
from fastapi import HTTPException
app=server.app

@app.post('/__qa/live/{name}')
def fixture(name:str):
 with server.lock:
  if name=='side-pots':
   g=fixed_live([50,100,200,7650],['AcAd','KcKd','QcQd','JcJd'],'2c3d7h8s9c')
   g.act(g.actor,Decision('raise',200));finish_calls(g)
  elif name=='split':
   g=fixed_live([2000]*4,['2c3c','4d5d','6s7s','8d9d'],'AhKhQhJhTh');finish_calls(g)
  elif name=='fold':
   g=fixed_live([2000]*4,['AcAd','KcKd','QcQd','JcJd'],'2c3d7h8s9c')
   while g.actor is not None:g.act(g.actor,Decision('fold'));settle_to_actor(g)
  elif name=='champion':
   g=fixed_live([4000,4000],['AcAd','KcKd'],'2c3d7h8s9c')
   g.act(g.actor,Decision('raise',4000));finish_calls(g)
  elif name=='heads-up':
   g=LiveGame(9);g.stacks=[4000,0,0,4000];g.start_hand();settle_to_actor(g)
  else:raise HTTPException(404,'Unknown QA scenario')
  g.bot_info=dict(mode='fixture',label='Deterministische Engine-Prüfszene',version=None)
  server.live_game=g
  return live_view(g)
