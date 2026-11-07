import json
from collections import deque
import pytest
from pokerkit import Card, Deck, NoLimitTexasHoldem, ChipsPushing
from pokermind.game import Game, AUTOMATIONS
from pokermind.views import observe
from pokermind.agents import Decision, RuleBot


def fixture(stacks, holes, board='2c3d7h8s9c', blinds=(10,20), ante=0):
    s = NoLimitTexasHoldem.create_state(AUTOMATIONS, True, ante, blinds, max(blinds), stacks, len(stacks))
    for i, cards in enumerate(holes):
        s.deal_hole(cards, i)
    remaining = list(Card.parse(board))
    used = set(c for hand in s.hole_cards for c in hand) | set(remaining)
    burns = [c for c in Deck.STANDARD if c not in used][:3]
    s.deck_cards = deque([burns[0], *remaining[:3], burns[1], remaining[3], burns[2], remaining[4]])
    return s


def finish(s):
    for _ in range(100):
        if not s.status:
            return
        if s.actor_index is not None:
            s.check_or_call()
        elif s.can_burn_card():
            s.burn_card()
        elif s.can_deal_board():
            s.deal_board()
        else:
            pytest.fail('stuck')
    pytest.fail('limit')


def test_unequal_allins_sidepots():
    s = fixture([50,100,200,200], ['AcAd','KcKd','QcQd','JcJd'])
    s.complete_bet_or_raise_to(200)  # UTG/index 2
    s.check_or_call(); s.check_or_call(); s.check_or_call()
    finish(s)
    assert s.stacks == [200,150,200,0]
    pots = [op for op in s.operations if isinstance(op, ChipsPushing)]
    assert [sum(op.amounts) for op in pots] == [200,150,200]
    assert sum(s.stacks) == 550


def test_split_and_odd_chip_left_of_button():
    s = fixture([101]*3, ['2c3c','4d5d','6s7s'], 'AhKhQhJhTh', (1,2), 1)
    s.fold()  # index 2 loses ante; 7-chip pot split between index 0 and 1
    finish(s)
    assert s.stacks == [102,101,100]


def test_short_allin_does_not_reopen_prior_raiser():
    s = fixture([200,200,200,50], ['AcAd','KcKd','QcQd','JcJd'])
    s.complete_bet_or_raise_to(40)  # index 2 full raise
    s.complete_bet_or_raise_to(50)  # index 3 short all-in
    s.check_or_call(); s.check_or_call()
    assert s.actor_index == 2
    assert not s.can_complete_bet_or_raise_to()
    assert s.checking_or_calling_amount == 10
    with pytest.raises(ValueError): s.complete_bet_or_raise_to(80)
    finish(s)


def test_cumulative_short_allins_reopen():
    s = fixture([60,200,200,50], ['AcAd','KcKd','QcQd','JcJd'])
    s.complete_bet_or_raise_to(40)
    s.complete_bet_or_raise_to(50)
    s.complete_bet_or_raise_to(60)
    s.check_or_call()
    assert s.actor_index == 2
    assert s.can_complete_bet_or_raise_to(80)


def test_invalid_actions_do_not_mutate():
    g=Game(1);g.start_hand(); before=observe(g)
    with pytest.raises(ValueError): g.act(0,Decision('call'))
    with pytest.raises(ValueError): g.act(g.actor,Decision('raise',21))
    with pytest.raises(ValueError): g.act(g.actor,Decision('raise',2001))
    with pytest.raises(ValueError): g.act(g.actor,Decision('raise',1.2))
    with pytest.raises(ValueError): g.start_hand()
    assert observe(g)==before


def test_hidden_information_and_detached_views():
    g=Game(5);g.start_hand()
    for viewer in range(4):
        v=observe(g,viewer)
        assert len(v['players'][viewer]['cards'])==2
        for p in v['players']:
            if p['seat']!=viewer: assert p['cards']==[None,None]
        assert not any(k in json.dumps(v) for k in ['deck','random','seed','hole_cards','operations'])
        v['players'][viewer]['cards'][0]='fake'
        assert 'fake' not in json.dumps(observe(g,viewer))
    while g.actor is not None: g.act(g.actor,Decision('fold') if g.state.can_fold() else Decision('call'))
    assert all(p['cards']==[None,None] for p in observe(g)['players'][1:])


def test_rotation_elimination_heads_up():
    g=Game(4);g.start_hand(); assert g.dealer==0 and g.actor==3
    while g.actor is not None: g.act(g.actor,Decision('call'))
    g.stacks=[3000,0,2500,2500];g.start_hand()
    assert g.dealer==2 and g.seats==[3,0,2] and g.actor==2
    while g.actor is not None: g.act(g.actor,Decision('call'))
    g.stacks=[4000,0,0,4000];g.start_hand()
    assert g.dealer==0 and g.seats==[3,0] and g.actor==0
    assert g.state.bets==[20,10]
    g.act(0,Decision('call'));g.act(3,Decision('call'))
    assert g.state.street_index==1 and g.actor==3
    while g.actor is not None: g.act(g.actor,Decision('call'))
    g.start_hand(); assert g.dealer==3 and g.actor==3
    g.reset();assert g.stacks==[2000]*4 and g.state is None


def test_results_persist_and_reveal_only_show_operations():
    from pokerkit import HoleCardsShowingOrMucking
    g=Game(1);g.start_hand()
    while g.actor is not None: g.act(g.actor,Decision('call'))
    v=observe(g);assert v['finished'] and v['result'] and v==observe(g)
    shown={g.seats[o.player_index]:list(map(repr,o.hole_cards)) for o in g.state.operations if isinstance(o,HoleCardsShowingOrMucking) and o.hole_cards}
    for p in v['players'][1:]: assert p['cards']==shown.get(p['seat'],[None,None])


@pytest.mark.parametrize('seed',range(12))
def test_reproducible_tournaments_conservation_unique_cards(seed):
    def run():
        g=Game(seed)
        for _ in range(600):
            g.start_hand()
            while g.actor is not None:
                s=g.state
                assert sum(s.stacks)+s.total_pot_amount==8000
                cards=[c for h in g.original.values() for c in h]+[repr(c) for b in s.board_cards for c in b]+[repr(c) for c in s.burn_cards]
                assert len(cards)==len(set(cards))
                v=observe(g,g.actor)
                # Aggressive legal test policy forces finite elimination.
                d=Decision(**v['legal']['all_in']) if v['legal']['all_in'] else Decision('call')
                g.act(g.actor,d)
            assert sum(g.stacks)==8000
            assert all(n>=0 for n in g.stacks)
            if observe(g)['champion'] is not None:
                return g.hand,g.stacks
        pytest.fail('Tournament did not finish')
    assert run()==run()


def test_baseline_policy_full_hands():
    g=Game(19)
    for _ in range(25):
        g.start_hand()
        for _ in range(300):
            if g.actor is None: break
            g.act(g.actor,RuleBot(g.actor).decide(observe(g,g.actor)))
        assert g.actor is None and sum(g.stacks)==8000
        if observe(g)['champion'] is not None: break


def test_uncalled_excess_returned():
    s=fixture([50,100,200,200],['AcAd','KcKd','QcQd','JcJd'])
    s.complete_bet_or_raise_to(200)
    s.fold();s.check_or_call();s.check_or_call()
    finish(s)
    assert s.stacks==[150,100,100,200]
    assert sum(s.stacks)==550


def test_short_blind_all_in_and_terminal_restart():
    g=Game(7);g.stacks=[5,7995,0,0];g.start_hand()
    while g.actor is not None: g.act(g.actor,Decision('call'))
    assert sum(g.stacks)==8000
    g.stacks=[0,8000,0,0]
    assert observe(g)['champion']==1
    with pytest.raises(ValueError): g.start_hand()
    g.reset();g.start_hand();assert len(g.seats)==4


def test_simulation_policy_seam():
    from pokermind.simulation import play
    class PushPolicy:
        def decide(self, observation):
            move=observation['legal']['all_in']
            return Decision(**move) if move else Decision('call')
    result=play(12,[PushPolicy() for _ in range(4)],200)
    assert result['completed'] and result['stacks'][result['champion']]==8000
    assert play(12,[PushPolicy() for _ in range(4)],1)['hands']==1
