"""Self-developed imitation teacher, not an optimal or trained policy."""
from dataclasses import dataclass, asdict
from random import Random
from time import perf_counter
from math import isfinite
from ..agents import Decision
from .features import features
from .equity import estimate

@dataclass(frozen=True)
class TeacherConfig:
    samples: int = 128
    small_fraction: float = .5
    large_fraction: float = 1.
    small_edge: float = .12
    large_edge: float = .28
    shove_share: float = .85
    shove_stack_pots: float = 1.5
    call_margin: float = .02
    button_discount: float = .02
    early_street_margin: float = .02

    def __post_init__(self):
        if type(self.samples) is not int or self.samples<1: raise ValueError('samples must be positive')
        if any(not isfinite(v) or v<0 for k,v in asdict(self).items() if k!='samples'):
            raise ValueError('parameters must be finite and nonnegative')

def candidates(o,config):
    legal=o['legal']; me=o['players'][o['viewer']]
    options={}
    def add(label,d):
        if d not in options.values(): options[label]=d
    if legal['fold']: add('fold',Decision('fold'))
    if legal['call'] is not None: add('check' if legal['call']==0 else 'call',Decision('call'))
    if legal['raise_min'] is not None:
        base=me['bet']+legal['call']
        for label,fraction in [('small',config.small_fraction),('large',config.large_fraction)]:
            target=base+round((o['pot']+legal['call'])*fraction)
            target=max(legal['raise_min'],min(legal['raise_max'],target))
            add(label,Decision('raise',target))
    if legal['all_in']: add('all_in',Decision(**legal['all_in']))
    return options

class TeacherAgent:
    version='teacher-2.0.0'
    def __init__(self,seed=1,config=None):
        self.config=config or TeacherConfig(); self.rng=Random(seed); self.last_diagnostic=None

    def decide(self,o):
        start=perf_counter(); options=candidates(o,self.config)
        if not options: raise ValueError('No legal decision on this observation')
        fallback=False; f=None; e=None
        try:
            f=features(o); e=estimate(o,f,self.config.samples,self.rng)
            share=e['estimated_showdown_pot_share']
            if not isfinite(share): raise ValueError('Nonfinite equity')
            edge=share-1/(f['opponents']+1)
            margin=self.config.call_margin+(self.config.early_street_margin if f['stage'] in ('Preflop','Flop') else 0)
            if f['button']: margin=max(0,margin-self.config.button_discount)
            if f['call'] and e['call_ev'] < margin*f['eligible_total'] and 'fold' in options:
                choice='fold'; reason='Expected eligible receipt does not cover call plus uncertainty margin'
            elif share>=self.config.shove_share and f['stack']<=self.config.shove_stack_pots*max(1,f['eligible_total']) and 'all_in' in options:
                choice='all_in'; reason='High estimated share and low stack-to-eligible-pot ratio'
            elif edge>=self.config.large_edge and 'large' in options:
                choice='large'; reason='Large estimated share advantage over equal-share baseline'
            elif edge>=self.config.small_edge and 'small' in options:
                choice='small'; reason='Moderate estimated share advantage over equal-share baseline'
            else:
                choice='check' if 'check' in options else 'call'; reason='Free check or acceptable estimated call receipt'
            decision=options[choice]
        except (ValueError,KeyError,TypeError,ZeroDivisionError) as exc:
            fallback=True; reason=f'Calculation fallback: {type(exc).__name__}'
            decision=options.get('check',options.get('fold',options.get('call',next(iter(options.values())))))
        self.last_diagnostic=dict(strategy_version=self.version,config=asdict(self.config),
            features=f,estimate=e,candidates={k:asdict(v) for k,v in options.items()},
            decision=asdict(decision),reason=reason,fallback=fallback,elapsed_seconds=perf_counter()-start)
        return decision
