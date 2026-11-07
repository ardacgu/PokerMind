# Stage 2: self-developed TeacherAgent

Status: implemented and tested. **No model has been trained and no large training dataset has been produced.** This teacher defines example imitation targets, not proven optimal poker decisions. Existing `RuleBot` policies remain unchanged and selectable.

## Modules and information boundary

`teacher/features.py` derives public features and counterfactual pot eligibility. `teacher/equity.py` samples cards and calls PokerKit's `StandardHighHand.from_game` for ranking. `teacher/__init__.py` owns the central immutable `TeacherConfig`, legal candidates, independent RNG and deterministic selection. `teacher/diagnostics.py` is a separate offline pilot command. All policies implement the existing `decide(observation) -> Decision` interface.

The observation adds `contribution` (public total net commitment for this hand, including outstanding bets, derived from negative PokerKit payoffs) and `in_hand` (still live, including all-in). Folded contributions remain dead money. Neither field exposes private cards. All other inputs are the existing protected view. The teacher receives no game object, actual deck, dealer RNG or seed. Its RNG is a private `random.Random`; system/dealer randomness is never read or advanced by estimation. Identical observations, configurations and teacher RNG states yield identical estimates and decisions; elapsed timings naturally differ.

Diagnostics are retained in the policy object and exported only by the offline runner. HTTP responses continue to use the explicit observation allowlist. They contain no teacher diagnostics or derived opponent strengths. JSONL pilot observations include the simulated teacher's own cards; these offline teaching examples must not be wired into browser responses during human games.

## Monte Carlo meaning and assumptions

The result is an **estimated showdown pot share under uniform unknown hands and no further betting**, not win probability and not full action EV. One joint `Random.sample` draws all unknown live hole cards and missing board cards without replacement. Known own, public board and any legitimately exposed cards are removed. All live opponents, including all-ins, are sampled. Hidden folded cards and burn cards are marginalized out: without conditioning on their hidden identities, sampling uniformly from the remaining unseen deck gives the correct marginal distribution. Opponent ranges are NOT adjusted for prior bets, folds or style.

PokerKit's [official API](https://pokerkit.readthedocs.io/en/stable/reference.html) documents the hand evaluator used here. We use a small explicit sampling loop to control RNG isolation and evaluate distinct eligible player sets for each pot; PokerKit remains the hand-ranking and actual game-settlement authority.

Each simulated pot gives a tying winner `1 / number_of_winners`. This estimates fractional pot share, not integer-chip settlement: actual odd chips remain PokerKit's responsibility. Samples default to **128**. Standard Monte Carlo noise remains material (a bounded proportion's worst-case standard error at 128 samples is about 4.4 percentage points); the margin is a heuristic, not a confidence bound.

## Public accounting and call valuation

For a decision, freeze everyone else's current contributions and add only the actor's actual capped call. Split these public contributions at each distinct commitment level. Each layer's amount is its width times the number of contributing players. Folded players contribute money but cannot win. A layer with only one contributor is refundable unmatched excess and is excluded. Only layers containing the actor among eligible live contributors enter its valuation. This accounting is a counterfactual feature calculation, never a replacement for PokerKit settlement.

For each sample, rank the live hands with PokerKit and compute the actor's share separately in each eligible layer. Let `R` be mean receipts summed across those layers, `P` their combined amount and `C` the actual call cost. Report:

- `estimated_showdown_pot_share = R / P` (amount-weighted across eligible pots).
- `call_ev = R - C`, relative to folding now; past contributions are sunk.
- `call_threshold = C / P`, a descriptive break-even threshold ONLY for this frozen-contribution, no-further-betting counterfactual.

A short stack cannot win higher layers. Unmatched opponent excess cannot inflate `P`. With multiple eligibility sets, a single all-opponent win probability is insufficient; use each pot's own ranks and eligible players. Players who have not yet matched a wager do not receive assumed future contributions or eligibility. Future calls, folds, new side pots, later streets, fold equity and responses to raises are NOT modeled. The preflop estimate can therefore differ substantially from eventual realized equity.

## Features and strategy parameters

Input features include own and public cards (in the observation), street, stack, actual call, own street bet, highest public bet, live opponent count, button status, public contribution layers and eligible amounts. `button` is the deliberately coarse positional feature; full positional history is not modeled. Public action history is available but does not reweight sampled ranges.

All defaults live in `TeacherConfig`:

| Parameter | Default | Purpose |
| --- | --- | --- |
| samples | 128 | Interactive latency vs Monte Carlo precision |
| small_fraction / large_fraction | 0.5 / 1.0 | Half-pot / pot-sized raise increments after calling |
| small_edge / large_edge | 0.12 / 0.28 | Share advantage over `1/(opponents+1)` for value raises |
| shove_share | 0.85 | High estimated share required for shove |
| shove_stack_pots | 1.5 | Shove only with low stack relative to eligible pot |
| call_margin | 0.02 | Avoid marginal estimated calls |
| early_street_margin | 0.02 | Additional caution preflop/flop |
| button_discount | 0.02 | Small positional relaxation of call margin |

These starting values are understandable design choices, not empirically optimized parameters. The policy is deterministic once the sampling RNG state is fixed. Order:

1. If a paid call fails `R - C >= margin * P`, fold when legal. Margin adds early-street caution and subtracts button discount, floored at zero.
2. Otherwise prefer a legal all-in at share >= 0.85 and stack <= 1.5P.
3. Otherwise choose a large raise for edge >= 0.28, then small for edge >= 0.12.
4. Otherwise check for free or call.

Raise-to target = own street bet + actual call + round(fraction × (current public pot + call)). Clamp to PokerKit-provided min/max. Bounds already encode reopening rights and short all-ins. Include the engine's legal all-in candidate; remove identical `(action, amount)` pairs. A duplicated all-in may retain its small/large label but the actual decision is the same. `call` represents both check and call in the existing API; zero call cost disambiguates them.

If calculation produces a recognized unusable input or nonfinite estimate, use legal check, otherwise fold, otherwise call (last resort: first legal candidate). Record `fallback=true` and the exception class. An observation with no legal actions is rejected instead of inventing a turn. Unanticipated programming exceptions are not silently swallowed.

## Try it

From the project directory with `.venv` activated:

```bash
# Three Teacher opponents at the existing local table; no frontend changes needed.
POKERMIND_BOTS=teacher POKERMIND_SAMPLES=128 POKERMIND_TEACHER_SEED=1 \
  python -m uvicorn pokermind.server:app --host 127.0.0.1 --port 8000
# Open http://127.0.0.1:8000

# One Teacher at seat 0; the other seats use the baseline.
python -m pokermind.simulation --seed 41 --teacher-seat 0 --samples 128 --max-hands 12

# Four small seat-rotated pilots and bounded offline diagnostic examples.
python -m pokermind.teacher.diagnostics --samples 128 --hands 12 --output docs/stage2

# Reproduce the previously unfinished baseline game, allowing enough hands.
python -m pokermind.simulation --seed 1 --max-hands 4000
python -m pytest -q
```

Without `POKERMIND_BOTS=teacher`, the table uses the original baseline. Teacher seeds control only teacher sampling; interactive dealing remains system-random. At the table, a new game resets chips but the policy's RNG stream continues; restart the server to reset that stream. All other parameters are configurable by supplying `TeacherConfig(...)` through Python. No new dependencies are required.

## Stage 3 handoff

The versioned diagnostic schema includes observation, derived features, estimate, samples, eligible pots, candidates, selected action/amount, reason, config, fallback and runtime, plus pilot provenance (game seed, teacher seed, seat and hand). Only the first eight teacher decisions per pilot are exported (32 records), intentionally not a training corpus. Replaying a sequential RNG stream requires the initial seed and preceding decisions; game seed alone is not a teacher seed. Later data generation should record episode/decision IDs, preserve this provenance and version the feature encoder, teacher and label policy. Split datasets by entire episode before training; monitor class imbalance, fallback and illegal-proposal rates. Decision Tree/Random Forest training remains future work.
