"""Baseline policies. The only input is a detached, allowlisted observation."""
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class Decision:
    action: str
    amount: int | None = None

class Policy(Protocol):
    def decide(self, observation: dict) -> Decision: ...

class RuleBot:
    """Deterministic, deliberately simple teacher; no trained model or dealer RNG."""
    def __init__(self, style: int = 0):
        self.style = style

    def decide(self, observation: dict) -> Decision:
        legal = observation['legal']
        cards = observation['players'][observation['viewer']]['cards']
        ranks = ['23456789TJQKA'.index(c[0]) + 2 for c in cards if c]
        pair = len(ranks) == 2 and ranks[0] == ranks[1]
        strong = pair or (len(ranks) == 2 and min(ranks) >= 11)
        # One modest value raise per street; cheaper calls with a broad range.
        own_bet = observation['players'][observation['viewer']]['bet']
        if strong and legal['raise_min'] is not None and own_bet <= 20:
            return Decision('raise', legal['raise_min'])
        if legal['call'] == 0:
            return Decision('call')
        budget = (120, 220, 360)[self.style % 3]
        if strong or legal['call'] <= budget:
            return Decision('call')
        return Decision('fold')
