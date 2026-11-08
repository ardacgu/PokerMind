# PokerMind 2.0 — local development version

This branch improves live presentation and completed-hand analysis. It does not retrain the AI, change PokerKit rules, update the Teacher, or replace the published v1.0.0 release. Historical reports and the Stage 6 runtime remain evidence of their original versions.

## Run and play

Use Python 3.11 and the pinned `requirements.txt` from the project root:

```sh
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn pokermind.server:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. Start a hand, then use the highlighted legal actions. Raises are **total street contributions**, not additional chip amounts. Each actual opponent decision appears separately; the next player is highlighted before its decision. Amounts in flying chips are the actual newly committed chips, while raise captions show the total. There are no optimistic local bankroll updates.

**Spielgefühl & Ansicht** contains Normal (default), Schnell and Sofort speed, animation enablement, sound (off initially), volume and completed-hand learning mode. Settings are stored locally where storage is available. System reduced-motion overrides movement. Disabling movement preserves the selected readable text timings; **Animationen überspringen** immediately finishes the current visual transition and accelerates automatic processing until the next human decision or hand end. It never chooses a human action.

Sounds are original short Web Audio oscillator envelopes, activated only after a user gesture. No downloaded audio or external assets are used. Sound may be unavailable under a browser's audio restrictions; gameplay remains usable.

## Incremental authority, not a precomputed replay

`pokermind/live.py` adds `LiveGame`, a scheduling adapter using PokerKit with automations disabled. Each `step` performs exactly one legal engine operation or exactly one model decision/application. The frozen `Game` and simulator stay unchanged. The live adapter uses the same four seats, 2,000 starting chips, 10/20 blinds, moving-button and heads-up convention, shuffled deck and legal-action adapter. Differential tests compare observable decision states, actual cards, payouts and subsequent rotations against the original implementation.

The browser uses `/api/live/state` and `/api/live/command`. The original `/api/state` and `/api/command` remain an isolated compatibility table for the original integration contract and regression suite; the browser never mixes those tables. Both use the same read-only cached model resource, but have separate policies and game state. Only the live table is played by the new UI.

A live POST contains `epoch`, `version`, `action`, optional integer `amount`, and the requested `learning` display mode. The epoch is an opaque server-instance/table identifier, unrelated to shuffle randomness. The shared server lock checks epoch/version before mutation. Duplicate or stale commands receive 409 and cannot execute another decision. Foreign browser origins and unknown command fields are rejected. GET only projects current state and never advances the game. Model inference happens only for a real bot turn, not for frames, reads or settings changes.

One response contains only the state reached by that operation, its public event and past public event captions. It never contains queued future boards, future decisions, burn cards, deck order, model features or private policy observations. Cards are actually dealt one at a time, including all three flop cards. Each subsequent board card requires another versioned server step. Blind posting, collection, showdown/mucking, pot allocation and credit are also separate real engine operations.

Unexpected bot/lifecycle errors halt automatic processing with a generic message. The UI can reconnect or reset; it never displays private exception details. Regularly illegal human actions are rejected by the original PokerKit legality checks.

## Playback and recovery

`experience.mjs` provides a serial automatic-step loop, cancellable visual clock, chip/card motion, local settings and sound. `app.js` retains the versioned command gate: controls lock while a POST or its visual transition is pending. No POST is blindly retried. After an uncertain response the UI GETs current state; if that fails, it locks and offers explicit reconnect. A successful refresh may continue with the *next* current step, never replay the previous version's command. Reload resumes from the current server state, without replaying old visual events.

The central `TIMING` configuration in `experience.mjs` gives Normal 1,250 ms of thinking and 1,750 ms of action reading time; Schnell uses 300 + 600 ms; Sofort inserts no waits. Normal card dealing takes 280 ms per card and board reveal 650 ms per card. The completed-hand celebration takes 4,000 ms in Normal and 1,200 ms in Schnell; the result remains afterward. Fetch/model latency can add time. Reduced movement keeps readable static captions. The skip control resolves active waits and removes motion overlays. Reset pauses the loop, invalidates its generation and cancels visual waits; any already accepted server operation completes before a versioned reset is sent. An old loop cannot apply events to the reset table. Cancelling the reset dialog resumes the current hand.

A bet animates its actual incremental amount. Collection moves committed bets into the central pot, with PokerKit refunds explicitly distinguished. Each `ChipsPushing` operation creates exactly one payout event; `ChipsPulling` credits stacks without showing another win animation. The numbers always come from the server. Topf allocations can be consolidated by PokerKit after hand killing; displayed payout sequence numbers are not claimed to be persistent side-pot IDs. Pre-showdown pot layers separately list eligible seats.

## Stable action controls and player-side results

`controls.mjs` constructs action buttons, number input, slider and presets once. Updating the presentation locks these existing nodes instead of replacing them. Only a new human decision identity (epoch, hand, version) refreshes legal bounds and the draft amount. Display-only refreshes preserve the draft and focus. The action area reserves space across human, bot, settlement and ready states; its short heading avoids mobile wrapping shifts. `app.js` holds a presentation actor during the just-executed action, then highlights the next actual server actor before requesting its decision. This does not alter server state.

`outcome.mjs` projects terminal server outcomes into badges immediately above each participating seat and a central gold result panel. Gross receipts and net change are separate. All actual recipients are listed, including split and side-pot recipients; per-payout allocations remain visible. Fold winners explicitly say **Gewonnen durch Fold**. No result disappears on a timer: **Nächste Hand** clears it after user input. Reduced motion removes movement but keeps readable Normal timing.

## Learning mode and hand descriptions

**Alle Hände nach Spielende anzeigen** is enabled initially and explicitly labelled a local learning mode. Additional original hole cards are projected only when PokerKit's state is terminal, all payouts are complete and the browser requests learning mode. This is independent of agent `observe()`, which is unchanged. A nonparticipant has no invented cards. During a live hand, opponents reveal only what PokerKit legally exposes (including ordinary all-in showdown exposure).

Turning learning mode off requests the realistic projection: only the human's own cards and regular `HoleCardsShowingOrMucking` disclosures. Mucked/folded opponents remain masked. Switching modes never advances the game or changes policies. Like any single-machine application, it is not a security sandbox against someone modifying local Python code or deliberately selecting learning mode after settlement.

`StandardHighHand.from_game` supplies the best five-card category; there is no second hand-ranking engine. German labels cover high card, pair, two pair, trips, straight, flush, full house, quads and straight flush. Royal Flush is a display name for PokerKit's ace-high straight flush, not a new ranking rule. A wheel is five-high. Detailed descriptions and actual best-five cards are computed only on completed five-card boards. If a hand ends early, only dealt cards appear and the explanation explicitly says no complete combination is shown. No hypothetical runout is generated.

The outcome lists every participant, their permitted cards, category where available, gross pot receipts and net hand change. PokerKit's `ChipsPushing` recipients determine all winners. A high category does not grant eligibility for a side pot, and a folded player's learning-mode combination cannot win. Fold wins explicitly identify the fold reason rather than claiming a showdown category caused the win. Ties list every actual recipient, including odd-chip allocations.

## Tests and protected evidence

```sh
python -m pytest -q
node --test tests/*.test.mjs
python scripts/v2_verify.py
```

The original 68 Python and seven JS tests remain. Added tests cover all ten display categories, wheel/ties, side pots, uncalled refunds, early folds, sequential cards, chip conservation, heads-up/elimination, model calls, privacy, strict API commands, concurrency, stale epochs, controlled failure, presentation preferences, sound and cancelled loops.

The original Stage 8 manifest and verifier remain unchanged as historical evidence. `v2_verify.py` checks **558** original files byte-for-byte, allowing exactly four deliberate integration/UI edits: `server.py`, `app.js`, `index.html`, `style.css`. The original rules adapter, observations, Teacher, trained resources, dataset, splits and evaluation files remain protected. The original Stage 8 all-runtime verifier is intended for v1.0.0 and will correctly report differences on this development branch. CI uses the version-appropriate v2 verifier and all JS suites; no full training or evaluation runs on commits.

[Current tempo/control acceptance evidence](v2/pace/acceptance.md) (114 tests) and [initial browser evidence](v2/acceptance.md) distinguishes actual model-driven browser hands from deterministic rare-state fixtures. The fixture script is a separate opt-in local QA app; production exposes no scenario/debug endpoint.

## Limits

Single local user, one process, no persistence, multiplayer, real-money support or cloud service. Two browser tabs share the live table: versions prevent duplicate commands, but simultaneous tabs can advance the same hand at a different perceived pace. Use one playing tab. A server restart loses the table and changes the epoch. Reconnection shows current state rather than reconstructing an interrupted old animation. Individual hand descriptions do not estimate win probability; 78.70% remains the frozen Teacher-label test accuracy, not poker optimality. Rare-state fixtures verify display/engine integration and are not new scientific playing-strength results.
