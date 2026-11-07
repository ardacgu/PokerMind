> Historical snapshot at the end of Stage 7. Relative links refer to its original location; use the current README for navigation and commands.

# Architecture, rules and privacy

## Components and authority

`game.py` owns the table lifecycle: stacks between hands, seat mapping, dealer movement, shuffling, hand start, elimination, and tournament completion. PokerKit 0.7.7 is the **only poker rule authority**. The adapter calls its legality checks and actions; it does not independently rank hands, compute side pots, minimum raises, reopening rights, or split payouts.

`views.py` builds an explicit JSON-compatible observation. `agents.py` defines `Policy.decide(observation) -> Decision(action, amount)` and a deterministic baseline. `simulation.py` plugs four policies into the same game for seeded evaluation. `server.py` exposes only `GET /api/state` and `POST /api/command` for one table, with a static frontend. POST commands carry the last observed version; a lock serializes processing, and stale versions receive HTTP 409. Client controls are locked while a request is pending. The API independently checks the human seat, amount type and PokerKit legality.

The browser uses ordinary fetch requests. It receives the state after automatic bot actions have reached the human or the hand has ended. It intentionally does not animate every intermediate bot move. Public action history records what happened.

## PokerKit suitability review

The current official [simulation guide](https://pokerkit.readthedocs.io/en/stable/simulation.html) and [API reference](https://pokerkit.readthedocs.io/en/stable/reference.html) were consulted on 7 November 2026, and the installed 0.7.7 implementation was inspected for blind indexing, showdown and chip distribution. The library supports the requested No-Limit Hold'em actions and settlement operations. Focused integration tests exercise the edge cases rather than duplicating those rules.

PokerKit automates posting, collection, showing/mucking, hand killing, pushing and pulling chips. Hole dealing, burns and community cards are advanced explicitly by the adapter using PokerKit operations, so a private shuffled deck can be installed before the first deal. Only the private game core contains that deck. Tests may use fixed cards; the browser exposes no seed or fixed-deck endpoint.

## Table conventions

- Four permanent UI seats, 2,000 chips each; no antes or rake; blinds 10/20; one board and one runout.
- With three or four active players, use a **moving button**: the dealer advances clockwise to the next surviving seat. Small and big blinds follow clockwise. This is an explicit home-game convention, not the dead-button convention used by some tournaments.
- When entering heads-up, the big blind advances clockwise from the previous big blind to the next survivor; the other player becomes the button/small blind. Subsequently the button alternates.
- PokerKit index 0 is the first position after the button. With three or four players it posts the small blind. Heads-up it is the big blind, while index 1 is the button/small blind; PokerKit reverses its raw blind inputs in this case. The button acts first preflop and last postflop in heads-up.
- Busted players leave only after settlement. Fixed seats remain visible and are omitted from the next PokerKit state. The tournament ends with one positive stack.
- PokerKit returns uncalled excess, creates eligible side pots and awards tied pots. Its remainder goes to the first winning internal index, which corresponds to the tied player nearest left of the button in our mapping.
- Results show **gross chips awarded from pots** and **net change** separately. Refunded uncalled bets are not presented as won pots.
- Automatic showdown uses PokerKit's tournament rules: eligible all-in hands are exposed; other hands may be mucked when not needed to win. A fold win does not reveal the winner's concealed cards.

## Information boundary

An observation contains only public seat data, community cards, that viewer's own cards, legally exposed opponent cards, public action text, result data, and legal actions for that viewer when it is their turn. Opponent cards are represented as null values until exposed. Showdown visibility comes from `HoleCardsShowingOrMucking` operations; being at the end of a hand alone does not authorize exposure.

Observations are constructed afresh from primitive values and copied collections. Agents are passed no Game, PokerKit State, deck, dealer RNG, seed, or private operation list. Mutating an observation cannot mutate the game. Normal logs contain no dealt cards; Uvicorn access logs contain only routes and status codes. The browser never receives the full engine state. This is an application data boundary for trusted Python policies, not a security sandbox for malicious Python plugins.

## Baseline strategy

Each bot reads its own two ranks and the legal actions. Any pocket pair, or two cards each at least a jack, is considered strong. A strong holding makes a minimum legal raise when its current street contribution is at most 20 chips. Otherwise it checks for free, calls with strong cards, or calls a weak holding only if the additional cost is at most its style budget: Ada 120, Turing 220, Grace 360. It folds larger weak calls. The simple strategy ignores board strength and bluffing; no claim of poker skill is made. Its role is a documented, replaceable comparison policy.

## Scope limits

Only one local user/table/process is supported. There is no persistence, authentication, real money, network multiplayer, pause animation, or hand-history export in the live application. Offline training and data tools are documented separately. Bind to loopback. Runtime dependencies are installed once; normal play is offline. The frontend is German; project documentation is English. The API rejects foreign browser origins and extra command fields. Production hosting is outside this stage.

## Stage 2 extension

`teacher/` adds independent card sampling, public counterfactual pot-accounting features, versioned action selection and offline diagnostics. The game's actual rule decisions and payouts remain exclusively PokerKit's. `Game` accepts policy instances; the server's environment configuration can select Teacher opponents. The simulator can replace one chosen seat. Observations now also include public per-hand contributions and live-in-hand flags. See [Teacher specification](teacher.md) for all formulas, assumptions and privacy constraints. Baseline policies and the moving-button convention are unchanged.

## Stage 4 extension

`learning/experiment.py` verifies frozen artifacts, fits the predeclared train-only candidates, locks validation selection and then tests the finalists. `learning/inference.py` supplies the shared six-class probability alignment, legal adapter and checked `ModelAgent` loader. `learning/evaluate_saved.py` re-evaluates the locked artifacts without fitting or selecting. The browser server still uses its existing baseline/Teacher configuration; selecting learned browser opponents is deferred to stage 5. Data, feature and action schemas are unchanged.

## Stage 5 browser integration

The browser now defaults to learned mode. `learning/learned.py` caches a validated, frozen resource descriptor per resolved model path. Its estimator is treated as read-only; no fit or parameter updates occur. Each seat has a separate LearnedAgent with its own last prediction and counters, reusing ModelAgent's extractor, prediction and legal adapter. No agent receives another seat's view. A new Game has separate state/policies; only the estimator and frozen sizing configuration are shared.

`configured_game()` resolves relative model paths from the project root, checks Python major/minor and recorded library versions, then validates the existing schema, artifact hash, estimator type/classes and declared parameters. Missing/incompatible resources fail startup. Reset preserves loaded policies and increments the state version; it does not deserialize the model again. Core Game defaults, simulator and generator policies remain unchanged.

The existing request lock covers human action, synchronous bot decisions and their engine application. Each bot application also checks the version and acting seat against the decision snapshot. Reset cannot interleave with a pending decision. A stale reset request is rejected, requiring a refreshed version. Unexpected bot inference/engine failures halt the game and increment an internal error counter; public responses show a generic error, never the exception text or private observation. Prior legal actions remain in the state/history. Reset clears the halt. The public HTTP projection adds only actual mode/version and halt/message fields; inference features, probabilities and bot observations are never serialized. On normal shutdown, only aggregate decision/fallback/error counts are logged.

## Stage 6 evaluation extension

`evaluation/core.py` builds explicit identity/strategy/style rosters per seat and drives all four policies through the existing protected observation → Decision → Game.act seam. It reuses Game for every rule, button transition and payout. A fresh private deck RNG is installed before each hand using the block/hand-derived seed; Teacher receives a separate identity/rotation-derived stream. The original simulator/API/core/model/Teacher sources are unchanged.

The evaluator records settled-hand bankrolls, identity-specific action/label and all-in counters, eliminations, target outcomes and distinct complete/hand-limit/error statuses. Errors halt and retain the last settled bankroll; they are not substituted with a baseline policy. `evaluation/run.py` uses up to four spawned processes, atomic session writes, a kernel file lock and config/runtime/model/data fingerprints. Resume skips existing session IDs; merge accepts identical duplicates but rejects conflicts or differing fingerprints. `scripts/stage6_report.py` aggregates checkpointed records and bootstraps complete seed blocks, never treating hands or rotations as independent. See evaluation-report.md for exact pairing limitations, control symmetry and measurements.


## Stage 7 presentation extension

The browser now uses semantic HTML and two native ES modules. `ui.mjs` contains pure card/amount/state helpers and `CommandGate`; `app.js` renders seats, board, pots, controls, results, public action history and the server's opponent configuration. CSS provides responsive layouts and reduced motion. There is no frontend build step or downloaded asset dependency.

`presentation.table_details(game)` converts only public action and pot/payout operations to primitive dictionaries. The HTTP human view gains `table`; agent `observe()` and model inputs are untouched. Live pot eligibility maps internal indices back to permanent seats. Pending bets are reported separately. Settled payout indices are not claimed to preserve live side-pot indices, because PokerKit can consolidate pots after hand killing. This module does not determine winners, legality or chip transfers.

Every rendered command captures its state version. The gate locks during fetch and a short visual transition, rejects duplicate/stale local commands and never retries a POST. An uncertain request refreshes with GET; failed refresh enters an offline state until explicit reconnect. The server's original lock/version/legality enforcement remains authoritative. Rendering restores keyboard orientation without stealing focus from information disclosures. Reset uses a native dialog whose return value is cleared on each open.

The production app exposes no fixture route. `scripts/stage7_browser_fixtures.py` explicitly registers one only when launched for local QA. It constructs engine states for rare-case display checks; fixed cards never enter public JSON before legal exposure. See [Stage 7 report](ui-report.md) for browser evidence and limitations.

The Stage 6 runtime is archived separately because its provenance fingerprint included static UI files. Current UI changes must not be merged into old evaluation checkpoints under the original fingerprint. Frozen results, model bytes, data, Teacher and game rules remain unchanged.
