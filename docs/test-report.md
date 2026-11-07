# Stage 1 verification report

Date: 7 November 2026. Environment: macOS / Apple Silicon, Python 3.11.9, PokerKit 0.7.7. Exact installed packages are recorded in `requirements.txt`.

## Executed checks

`python -m pytest -q`: **26 passed in 0.43 seconds**, with one dependency deprecation warning. Full output: [pytest-output.txt](pytest-output.txt).

| Risk | Executed evidence | Result |
| --- | --- | --- |
| Chip conservation | 12 seeded aggressive tournaments, each run twice; total stacks plus outstanding pot checked at every decision, final stacks checked after each hand | Passed; 8,000 chips conserved |
| Unique cards | Original dealt hole cards, board and burns checked for duplicates throughout those runs | Passed |
| Unequal all-ins / side pots | Fixed stacks 50/100/200/200 with AA/KK/QQ/JJ; three pots of 200/150/200 | Passed; final stacks 200/150/200/0 |
| Uncalled excess | One 200-chip bettor against 50/100-chip callers with the fourth seat folding | Passed; excess returned, total conserved |
| Ties and odd chips | Royal-flush board, two live players, folded ante creates a seven-chip pot | Passed; split 4/3, remainder to first winner left of button |
| Short all-in raises | Raise to 40, short all-in to 50, callers, original raiser | Passed; original raiser cannot raise again |
| Cumulative short raises | Raise to 40, short all-ins to 50 and 60, caller | Passed; original raiser may raise to 80 |
| Invalid commands | Below-minimum, over-stack, fractional raise, wrong seat, hand start during active hand | Passed; rejected without changing state |
| Stale/duplicate commands | Replay previous version after an accepted raise | Passed; HTTP 409 |
| HTTP validation | Extra seat field, fractional input, action before a hand, foreign Origin | Passed; rejected |
| Elimination / position | Four-seat start, three-seat and heads-up mapping; next big blind on heads-up transition; preflop and postflop order | Passed |
| Short blind and game end | Stack smaller than blind; champion detection, refusal to start after game end, four-seat reset | Passed |
| Privacy | All viewers checked, opponent cards masked, no deck/RNG fields, detached observations, fold-win concealment, showdown operation allowlist | Passed |
| Persistent result | Repeated observations after settlement, API state read, no automatic new hand | Passed |
| Policy integration | 25 baseline hands; headless Policy interface with aggressive policies | Passed |
| Seed reproducibility | 12 fixed seeds, identical hand count and final stacks on repeated complete tournaments | Passed |

`python -m pip check`: **No broken requirements found.**

`python -m compileall -q pokermind`: **Passed.**

Additional real baseline simulation:

```text
python -m pokermind.simulation --seed 1 --max-hands 2000
completed: false
hands: 2000
actions: 21933
champion: null
stacks: [4380, 0, 0, 3620]
```

This is an explicitly reported evaluation cutoff, not a completed tournament. Conservative strategies and fixed blinds can produce long games. The completed aggressive-policy tournament tests separately establish that elimination and winner detection work through the end.

## Executed browser acceptance check

Started the local Uvicorn server at `http://127.0.0.1:8000` and used the real in-app browser:

1. Started hand 1 from the ready screen; confirmed four seats and masked opponent cards.
2. Changed the raise input from 40 to **60**; observed the button become **Erhöhen auf 60**; submitted it.
3. Confirmed a 240-chip flop pot. Checked through flop, turn and river to showdown.
4. Confirmed the human received **240 chips from the pot, +180 net**, with stack **2,180**. Other stacks were **1,940** each. Only PokerKit-exposed opponent cards appeared.
5. Reloaded the page; the same completed-hand result remained visible.
6. Clicked **Nächste Hand**; hand 2 began and the dealer moved to Ada.
7. Clicked **Neustart**; all four stacks returned to **2,000**, with hand count reset and the first-hand start button visible.
8. Inspected the full page at **1366 × 900** and confirmed its document width matched the viewport. Fixed a last-action label that overlapped the bottom seat by moving it into the control panel. Saved [the showdown screenshot](browser-showdown.png). The temporary viewport override was reset afterwards.
9. Browser error logs were empty.

The screenshot was captured during the acceptance run before a later German grammar correction to the human action text; it is evidence of the actual run. The subsequent heads-up transition adjustment and simulator were covered by the final 26-test run. The full browser hand was not repeated after those Python-only changes.

## Not executed

- No GitHub remote CI run, publication or deployment.
- No independent Safari/Firefox/Chrome browser matrix; the browser acceptance run used the in-app browser.
- No exhaustive proof over every possible poker state, prolonged concurrency stress, accessibility audit, or statistical security audit.
- No training, model comparison or predictive performance evaluation: these belong to stage 2.
- The baseline-only 2,000-hand run did not reach a winner; no claim is made that every strategy completes within a fixed number of hands.

## Known limitations and remaining issues

No known failing core regression. One warning comes from Starlette's test-client integration deprecating `httpx` in favor of `httpx2`; it does not affect gameplay or passing tests. Keep dependencies pinned until deliberately reviewing that migration.

The application intentionally supports one local in-memory table; server restart loses the table. The bots are simplistic and may make games long. A moving button is used for three/four players, with special big-blind rotation entering heads-up; this is documented as the selected home-game convention. This is not a dead-button tournament implementation. Mobile layout was not comprehensively validated; the target is a normal laptop browser.

**Stage 1 status: complete for the documented local game foundation**, supported by the tests and browser acceptance run above. Stage 2 modeling and GitHub publication remain future work.
