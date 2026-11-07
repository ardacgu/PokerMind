"""Headless evaluation seam, with no training or dataset generation in stage 1."""
import argparse
import json
from .agents import Policy, RuleBot
from .game import Game
from .views import observe


def play(seed: int, policies: list[Policy], max_hands: int = 2000) -> dict:
    if len(policies) != 4:
        raise ValueError('Exactly four policies are required')
    game = Game(seed)
    actions = 0
    for _ in range(max_hands):
        game.start_hand()
        while game.actor is not None:
            seat = game.actor
            game.act(seat, policies[seat].decide(observe(game, seat)))
            actions += 1
        champion = observe(game)['champion']
        if champion is not None:
            return dict(seed=seed, completed=True, hands=game.hand,
                        actions=actions, champion=champion, stacks=game.stacks)
    return dict(seed=seed, completed=False, hands=game.hand,
                actions=actions, champion=None, stacks=game.stacks)


def main():
    parser = argparse.ArgumentParser(description='Reproducible baseline evaluation')
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--max-hands', type=int, default=2000)
    parser.add_argument('--teacher-seat',type=int,choices=range(4))
    parser.add_argument('--samples',type=int,default=128)
    args = parser.parse_args()
    if args.max_hands < 1:
        parser.error('--max-hands must be positive')
    policies=[RuleBot(i) for i in range(4)]
    if args.teacher_seat is not None:
        from .teacher import TeacherAgent, TeacherConfig
        policies[args.teacher_seat]=TeacherAgent(args.seed,TeacherConfig(samples=args.samples))
    print(json.dumps(play(args.seed, policies, args.max_hands), indent=2))


if __name__ == '__main__':
    main()
