"""Allowlisted inference-time features. Never invokes TeacherAgent.decide."""
from pokerkit import StandardHighHand
from ..teacher import TeacherConfig,candidates
from ..teacher.features import features as pot_features

VERSION='observation-features-1.0.0'
ACTION_VERSION='teacher-candidates-2.0.0'
CLASSES=('fold','check','call','small','large','all_in')
SCHEMA={}
def field(name,low,high,unit='count'):
    SCHEMA[name]=dict(type='integer',minimum=low,maximum=high,unit=unit)
for i in range(2):
    field(f'hole_rank_{i}',2,14,'rank');field(f'hole_suit_{i}',1,4,'suit')
for i in range(5):
    field(f'board_rank_{i}',0,14,'rank; 0=absent');field(f'board_suit_{i}',0,4,'suit; 0=absent')
for key in ('pair','suited','short_call','all_in_call'):
    field(key,0,1,'boolean')
field('street',0,3,'Preflop=0,Flop=1,Turn=2,River=3')
field('relative_button',0,3,'clockwise fixed-seat distance from dealer')
field('live_count',2,4);field('board_count',0,5)
field('made_hand',-1,8,'-1=preflop; 0 high card to 8 straight flush')
for key in ('stack','bet','call','pot','eligible_total','highest_bet','raise_min','raise_max'):
    field(key,-1 if key.startswith('raise_') else 0,8000,'chips; -1=unavailable' if key.startswith('raise_') else 'chips')
field('eligible_layers',0,4)
for i in range(4):
    for key in ('stack','bet','contribution'):field(f'rel_{i}_{key}',0,8000,'chips')
    field(f'rel_{i}_live',0,1,'boolean')
for c in CLASSES:field('legal_'+c,0,1,'boolean')
FEATURE_NAMES=tuple(SCHEMA)
LABELS=['High card','One pair','Two pair','Three of a kind','Straight','Flush','Full house','Four of a kind','Straight flush']

def encode_card(c):
    return ('23456789TJQKA'.index(c[0])+2,'cdhs'.index(c[1])+1) if c else (0,0)

def extract(o,config=None):
    config=config or TeacherConfig();me=o['viewer'];p=o['players'][me];out={}
    cards=sorted(p['cards'],key=encode_card,reverse=True)
    for i,c in enumerate(cards):out[f'hole_rank_{i}'],out[f'hole_suit_{i}']=encode_card(c)
    for i in range(5):out[f'board_rank_{i}'],out[f'board_suit_{i}']=encode_card(o['board'][i] if i<len(o['board']) else None)
    f=pot_features(o);cs=candidates(o,config);dealer=next(p['seat'] for p in o['players'] if p['dealer'])
    out.update(pair=int(cards[0][0]==cards[1][0]),suited=int(cards[0][1]==cards[1][1]),
        street=['Preflop','Flop','Turn','River'].index(o['stage']),relative_button=(me-dealer)%4,
        live_count=len(f['live']),board_count=len(o['board']),made_hand=-1,
        stack=p['stack'],bet=p['bet'],call=f['call'],pot=o['pot'],eligible_total=f['eligible_total'],
        highest_bet=f['highest_bet'],eligible_layers=len(f['eligible_pots']),
        short_call=int(f['call']<max(0,f['highest_bet']-p['bet'])),
        all_in_call=int(f['call']>0 and f['call']==p['stack']),
        raise_min=o['legal']['raise_min'] if o['legal']['raise_min'] is not None else -1,
        raise_max=o['legal']['raise_max'] if o['legal']['raise_max'] is not None else -1)
    if o['board']:
        label=StandardHighHand.from_game(''.join(cards),''.join(o['board'])).entry.label.value
        out['made_hand']=LABELS.index(label)
    for i in range(4):
        other=o['players'][(me+i)%4]
        for key in ('stack','bet','contribution'):out[f'rel_{i}_{key}']=other[key]
        out[f'rel_{i}_live']=int(other['in_hand'])
    for c in CLASSES:out['legal_'+c]=int(c in cs)
    validate_features(out)
    return out

def validate_features(x):
    if set(x)!=set(FEATURE_NAMES):raise ValueError('Feature allowlist mismatch')
    for k,v in x.items():
        s=SCHEMA[k]
        if type(v) is not int or not s['minimum']<=v<=s['maximum']:raise ValueError(f'Invalid feature: {k}')

def label_for(o,decision,config):
    return next(k for k,v in candidates(o,config).items() if v==decision)

def decode(label,o,config=None):
    """Shared legal mapping for a future classifier; illegal labels raise KeyError."""
    return candidates(o,config or TeacherConfig())[label]

def model_row(row):
    validate_features(row['features'])
    if row['label'] not in CLASSES or not row['features']['legal_'+row['label']]:raise ValueError('Illegal label')
    return [row['features'][k] for k in FEATURE_NAMES],row['label']
