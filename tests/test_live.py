"""Live scheduling is presentation; the original engine remains the oracle."""
import json
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from random import Random
import pytest
from fastapi.testclient import TestClient
from pokerkit import Card, Deck, NoLimitTexasHoldem, HoleCardsShowingOrMucking
from pokermind import server
from pokermind.agents import Decision
from pokermind.game import Game
from pokermind.live import LiveGame, live_view, describe_hand
from pokermind.views import observe

CASES=[('AcKd','8s6h2c9d3s','Höchste Karte'),('AcAd','KhQhJs2d3s','Ein Paar'),
 ('AcAd','KcKd2s8h9h','Zwei Paare'),('AcAd','AhKc2s8h9h','Drilling'),
 ('AcKd','QhJsTc2h3s','Straße'),('AcTc','8c6c2c3s4s','Flush'),
 ('AcAd','AhKcKd2s3s','Full House'),('AcAd','AhAs2c3s4s','Vierling'),
 ('9s8s','7s6s5s2c3d','Straight Flush'),('AsKs','QsJsTs2c3d','Royal Flush')]

@pytest.mark.parametrize('hole,board,category',CASES)
def test_all_ten_hand_names(hole,board,category):
 h=list(map(repr,Card.parse(hole)));b=list(map(repr,Card.parse(board)))
 result=describe_hand(h,b);assert result['category']==category and len(result['best_five'])==5
 assert set(result['best_five'])<=set(h+b)

def test_wheel_board_tie_and_incomplete_not_ranked():
 assert describe_hand(['Ac','2d'],['3h','4s','5c','Kd','Qh'])['description']=='Straße · Fünf hoch'
 a=describe_hand(['2c','3d'],['Ah','Kh','Qh','Jh','Th'])
 b=describe_hand(['4c','5d'],['Ah','Kh','Qh','Jh','Th'])
 assert a==b and a['category']=='Royal Flush'
 assert describe_hand(['Ac','Ad'],['Ah','As','2c']) is None
 assert describe_hand([None,None],['Ah','Kh','Qh','Jh','Th']) is None


def settle_to_actor(g):
 for _ in range(150):
  if not g.state.status or g.actor is not None:return
  g.step()
 pytest.fail('No actor/settlement after 150 steps')

@pytest.mark.parametrize('seed',range(6))
def test_differential_frozen_game_cards_decisions_payouts_rotation(seed):
 a=Game(seed);b=LiveGame(seed)
 for _ in range(6):
  a.start_hand();b.start_hand();settle_to_actor(b)
  assert a.seats==b.seats and a.dealer==b.dealer and a.original==b.original
  for _ in range(150):
   assert a.actor==b.actor
   if a.actor is None:break
   va=observe(a,a.actor);vb=observe(b,b.actor)
   for k in va:
    if k not in ('version','history'):assert va[k]==vb[k],k
   move=va['legal']['all_in'];d=Decision(**move) if move and seed%2 else Decision('call')
   a.act(a.actor,d);b.act(b.actor,d);settle_to_actor(b)
  assert a.stacks==b.stacks and a.result==b.result
  assert sum(b.stacks)==8000
  assert live_view(b)['finished']
  if sum(n>0 for n in a.stacks)==1:break


def test_incremental_deal_board_private_views_and_conservation():
 g=LiveGame(7);g.start_hand();deal=[];board=[];previous=live_view(g);shown=set()
 for _ in range(200):
  v=live_view(g,True)
  assert sum(g.state.stacks)+g.state.total_pot_amount==8000
  assert not any(('\"'+k+'\"') in json.dumps(v) for k in ('deck','seed','probabilities','features','hole_cards'))
  if not v['finished']:
   assert v['outcome'] is None
   for p in v['players'][1:]:
    i=g.seats.index(p['seat'])
    allowed=any(isinstance(o,HoleCardsShowingOrMucking) and o.player_index==i and o.hole_cards for o in g.state.operations)
    if not allowed:assert all(c is None for c in p['cards'])
  if g.event['kind']=='deal':deal.append((g.event['seat'],g.event['card_index']))
  if g.event['kind']=='board':board.append(len(v['board']))
  assert len(v['board'])-len(previous['board']) in (0,1)
  previous=v
  if v['finished']:break
  if g.actor==0:g.act(0,Decision('call'))
  else:g.step()
 assert len(deal)==8 and len(set(deal))==8 and board==[1,2,3,4,5]
 assert sum(r['amount'] for r in v['outcome']['payouts'])==sum(r['awarded'] for r in g.result)
 assert all(len(p['cards'])==2 for p in v['players'])


def test_fold_learning_only_after_final_credit_and_realistic_masks():
 g=LiveGame(2);g.start_hand();settle_to_actor(g)
 while g.actor is not None:
  g.act(g.actor,Decision('fold'));settle_to_actor(g)
 learning=live_view(g,True);real=live_view(g,False)
 assert learning['finished'] and learning['outcome']['reason']=='fold'
 assert learning['board']==[] and learning['outcome']['incomplete_board']
 assert all(p['combination'] is None for p in learning['players'])
 assert all(len(p['cards'])==2 and None not in p['cards'] for p in learning['players'])
 assert all(p['cards']==[None,None] for p in real['players'][1:])
 assert all(p['cards']==[None,None] for p in observe(g)['players'][1:])
 assert sum(p['net'] for p in learning['outcome']['players'])==0
 assert live_view(g,False)==real  # presentation mode never changes the game


def fixed_live(stacks,holes,board,blinds=(10,20),ante=0):
 g=LiveGame(1);g.stacks=list(stacks)+[0]*(4-len(stacks));g.starting_stacks=list(g.stacks)
 s=NoLimitTexasHoldem.create_state((),True,ante,blinds,max(blinds),stacks,len(stacks));g.state=s;g.seats=list(range(len(stacks)));g.hand=1
 while s.can_post_ante():s.post_ante()
 if s.can_collect_bets():s.collect_bets()
 while s.can_post_blind_or_straddle():s.post_blind_or_straddle()
 for i,h in enumerate(holes):s.deal_hole(h,i);g.original[i]=list(map(repr,Card.parse(h)))
 cards=list(Card.parse(board));used=set(cards)|set(c for h in s.hole_cards for c in h)
 burns=[c for c in Deck.STANDARD if c not in used][:3]
 s.deck_cards=deque([burns[0],*cards[:3],burns[1],cards[3],burns[2],cards[4],*[c for c in Deck.STANDARD if c not in used and c not in burns]])
 return g


def finish_calls(g):
 for _ in range(200):
  if not g.state.status:return
  if g.actor is not None:g.act(g.actor,Decision('call'))
  else:g.step()
 pytest.fail('stuck')


def test_side_pot_eligibility_and_single_award_per_engine_push():
 g=fixed_live([50,100,200,200],['AcAd','KcKd','QcQd','JcJd'],'2c3d7h8s9c')
 g.act(g.actor,Decision('raise',200));finish_calls(g)
 v=live_view(g)
 assert g.stacks==[200,150,200,0]
 assert [p['amount'] for p in v['outcome']['payouts']]==[200,150,200]
 assert [p['winners'][0]['seat'] for p in v['outcome']['payouts']]==[0,1,2]
 assert [p['eligible'] for p in v['outcome']['pot_layers']]==[[0,1,2,3],[1,2,3],[2,3]]
 assert len([e for e in v['events'] if e['kind']=='award'])==3
 assert all(p['combination']['category']=='Ein Paar' for p in v['outcome']['players'])


def test_split_odd_chip_and_uncalled_return_not_award():
 g=fixed_live([101]*3,['2c3c','4d5d','6s7s'],'AhKhQhJhTh',(1,2),1)
 g.act(g.actor,Decision('fold'));finish_calls(g)
 assert g.stacks==[102,101,100,0]
 winners=live_view(g)['outcome']['payouts'][0]['winners']
 assert sorted(w['amount'] for w in winners)==[3,4]
 g=fixed_live([50,100,200,200],['AcAd','KcKd','QcQd','JcJd'],'2c3d7h8s9c')
 g.act(g.actor,Decision('raise',200));g.act(g.actor,Decision('fold'));finish_calls(g)
 assert g.stacks==[150,100,100,200]
 assert any(e.get('refunds') for e in g.events)
 assert sum(r['awarded'] for r in g.result)==250


def test_heads_up_elimination_no_phantom_cards():
 g=LiveGame(8);g.stacks=[4000,0,0,4000];g.start_hand();settle_to_actor(g)
 assert g.seats==[3,0] and g.actor==0 and g.state.bets==[20,10]
 finish_calls(g);v=live_view(g)
 assert v['players'][1]['cards']==[] and v['players'][2]['cards']==[]
 assert len(v['outcome']['players'])==2 and sum(g.stacks)==8000
 g.start_hand();settle_to_actor(g);assert g.dealer==3 and g.actor==3

@pytest.fixture
def live_api(monkeypatch):
 monkeypatch.setenv('POKERMIND_BOTS','learned')
 g=server.configured_game(LiveGame);g._rng=Random(1);monkeypatch.setattr(server,'live_game',g)
 return g,TestClient(server.app)


def test_api_duplicate_epoch_resume_real_model_and_learning_boundary(live_api):
 g,c=live_api
 def get():return c.get('/api/live/state').json()
 def post(a,v=None,**kw):
  s=v or get();return c.post('/api/live/command',json=dict(version=s['version'],epoch=s['epoch'],action=a,**kw))
 first=get();assert post('start',first).status_code==200
 assert post('start',first).status_code==409
 for _ in range(200):
  s=get();assert get()==s
  if s['finished']:break
  assert s['outcome'] is None
  a='call' if s['actor']==0 else 'step'
  before=sum(p.decisions for p in g.policies[1:]);response=post(a,s);assert response.status_code==200
  after=sum(p.decisions for p in g.policies[1:]);assert after-before==(1 if s['actor'] not in (None,0) else 0)
  assert post(a,s).status_code==409
 assert all(p.decisions>0 for p in g.policies[1:])
 assert all(p.errors==0 and p.fallbacks==0 for p in g.policies[1:])
 assert s['opponents']['version']=='imitation-v1' and s['outcome']
 s=get();assert post('reset',s).status_code==200
 assert post('step',s).status_code==409
 current=get();assert current['event']['kind']=='ready' and current['events']==[]
 wrong={**current,'epoch':'old-process'};assert post('start',wrong).status_code==409


def test_api_concurrent_steps_origin_illegal_and_halt(live_api,monkeypatch):
 g,c=live_api;g.start_hand();settle_to_actor(g)
 body=dict(version=g.version,epoch=g.epoch,action='step')
 with ThreadPoolExecutor(2) as pool:
  responses=list(pool.map(lambda _:c.post('/api/live/command',json=body).status_code,range(2)))
 assert sorted(responses)==[200,409]
 s=c.get('/api/live/state').json()
 assert c.post('/api/live/command',json={**body,'version':s['version']},headers={'origin':'https://evil.example'}).status_code==403
 assert c.post('/api/live/command',json={**body,'version':s['version'],'action':'raise','amount':0}).status_code==400
 assert c.post('/api/live/command',json={**body,'version':s['version'],'hidden':True}).status_code==422
 g.reset();g.start_hand();settle_to_actor(g)
 def fail(_):raise RuntimeError('PRIVATE hidden cards')
 monkeypatch.setattr(g.policies[g.actor],'decide',fail)
 r=c.post('/api/live/command',json=dict(version=g.version,epoch=g.epoch,action='step'))
 assert r.status_code==503 and 'PRIVATE' not in r.text
 view=c.get('/api/live/state').json();assert view['halted'] and not view['advance'] and view['legal']['call'] is None


def test_post_and_get_learning_mode_never_changes_agent_inputs(live_api):
 g,c=live_api;g.start_hand()
 for _ in range(200):
  a=c.get('/api/live/state?learning=true').json();b=c.get('/api/live/state?learning=false').json()
  if not a['finished']:
   a.pop('learning');b.pop('learning');assert a==b
  else:break
  if g.actor==0:g.act(0,Decision('call'))
  else:g.step()
 assert c.get('/api/live/state?learning=false').json()['finished']
 assert all(p['combination'] is None for p in c.get('/api/live/state?learning=false').json()['players'] if None in p['cards'])


def test_short_blind_no_cards_for_busted_and_tournament_restart():
 g=LiveGame(7);g.stacks=[5,7995,0,0];g.start_hand();finish_calls(g)
 assert sum(g.stacks)==8000 and live_view(g)['players'][2]['cards']==[]
 g.stacks=[0,8000,0,0]
 assert live_view(g)['champion']==1
 with pytest.raises(ValueError):g.start_hand()
 old=g.version;g.reset();assert g.version>old and live_view(g)['outcome'] is None
 g.start_hand();settle_to_actor(g);assert len(g.seats)==4
