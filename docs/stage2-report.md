# Stage 2 executed verification — 7 November 2026

The original stage 1 report and screenshot are preserved. Stage 2 adds 10 tests: **36 total tests pass**, including all 26 existing tests. See [raw pytest output](stage2/pytest-output.txt). `pip check` reports no broken requirements. The existing Starlette/httpx deprecation warning remains.

New executed coverage: certain royal-flush wins, four-way ties, pot-specific eligibility with folded money, short calls, unmatched excess exclusion, unique jointly sampled cards, all-in participation, same observation with swapped actual hidden cards, dealer RNG unchanged, candidate deduplication and bounds, calculation fallback, actual short-call observation, three seeded multi-hand teacher legality runs, and configured Teacher table through the existing HTTP API. The table test plays a complete hand and asserts no estimates/diagnostics appear in the response. A separate simulator CLI smoke run also passed. No browser UI was changed; a new visual browser run was not performed in this stage. Stage 1 browser evidence remains available.

## Seat-rotated pilot

Four pilots, seeds 41–44, Teacher seeds 100–103, one Teacher at each of seats 0–3, three unchanged RuleBots. Each ran 12 hands, **48 total**, with **694 actions**, **136 Teacher decisions**, zero illegal actions, zero fallbacks and conserved 8,000 chips. All four runs hit the explicit 12-hand cutoff without a tournament winner. The fourth Teacher busted; the remaining baseline players continued legally.

| Teacher seat | Teacher decisions | Folds | Raises | Check/calls | Final stacks (seat order) |
| --- | ---: | ---: | ---: | ---: | --- |
| 0 | 43 | 5 | 12 | 26 | 5516, 0, 1072, 1412 |
| 1 | 42 | 4 | 12 | 26 | 0, 5900, 2100, 0 |
| 2 | 35 | 4 | 6 | 25 | 1810, 1840, 2260, 2090 |
| 3 | 16 | 2 | 4 | 10 | 2315, 1910, 3775, 0 |

Aggregate: 15 folds, 34 raises and 87 check/calls. Check/call is the existing combined API action; the diagnostic call cost distinguishes the two. No claim of superior playing strength follows from these small runs.

Measured on this Mac with **128 samples**: mean **47.1 ms**, empirical p95 **55.9 ms**, max **89.2 ms** per Teacher decision. Pilot runtimes summed to about **6.53 seconds**. These are observed end-to-end policy timings, not guaranteed latency; concurrent work and platform affect measurements. Three consecutive bot actions can accumulate latency. This default is practical for the local interface while remaining a coarse estimate.

Raw evidence: [pilot summary](stage2/pilot.json), [32 offline decisions](stage2/decisions.jsonl).

Two actual examples from seed 41 / Teacher seed 100 / seat 0:

- Hand 1, preflop **9h 3d**: call 20, eligible frozen pot 70, estimated share **18.56%**, expected receipts **12.99**, call EV **−7.01**. Teacher **folds** because expected receipts do not cover the call and margin.
- Hand 2, preflop **Tc Jc**: call 20, eligible frozen pot 50, estimated share **49.53%**, expected receipts **24.77**, call EV **+4.77**. Teacher **raises to 45** (small candidate; minimum 40, maximum 2000). The sampled share exceeds the equal-share baseline by more than 0.12. This is a heuristic raise, not a computed optimal raise EV.

## Investigation of the 2,000-hand baseline cutoff

Replayed original seed 1 with exactly the original policies, fixed blinds and moving-button rules. At hand 2,000 the result matched precisely: **21,933 actions**, stacks **[4380, 0, 0, 3620]**, no winner. Continuing the SAME game produced stacks [6940, 0, 0, 1060] after hand 3,000 and a legitimate winner at **hand 3,289**, **33,045 actions**, stacks **[8000, 0, 0, 0]**.

Every hand terminated with fewer than 500 actions and chip conservation held at each decision. Stack distribution changed in 3,188 hands. The 5.81-second investigation therefore found a long valid game, not a stalled progression bug. The original 2,000-hand result remains correctly recorded as a cutoff; no winner is retroactively invented at that limit. [Investigation checkpoints](stage2/baseline-investigation.json).

## Limits / not executed

No trained model, large dataset, range inference, exhaustive state-space verification, independent tournament-strength benchmark, cross-browser retest, or GitHub publication. Monte Carlo sampling noise, frozen-contribution assumptions, fractional rather than integer odd-chip estimation and heuristic raise selection remain intentional limitations. No known failing new regression; no fallbacks in the pilots. More samples and calibrated thresholds should be evaluated in later work, without silently changing the strategy version of generated data.
