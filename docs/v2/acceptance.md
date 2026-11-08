# PokerMind 2.0 — local acceptance report

Verified on 8 November 2026, on local branch `feature/pokermind-2-experience`, based on cleaned commit `18cf31149374d8584358a609cc3c7fa52ae56b0f`. This is a development delivery, version `2.0.0.dev0`. No push, public release, tag movement or history rewrite was performed. The published v1.0.0 remains unchanged.

## Result and protected scope

The browser now advances one real PokerKit operation or one real model decision at a time. Cards, betting, collection and payouts are visible separately. Local learning mode reveals all participants only after final settlement; realistic mode preserves normal disclosure. Completed-board descriptions use PokerKit's best five-card evaluation. The interface distinguishes gross receipts, net changes and eligible side-pot recipients.

The original game, observations, Teacher, 200-tree Random Forest, 54-feature schema, training data, splits and evaluation are unchanged. `scripts/v2_verify.py` verifies **558 original files by SHA-256**, explicitly allowing four integration/UI source changes. No scientific result was recomputed or replaced. The Stage 6 measurements are still historical playing-strength evidence, not a measurement of animation quality.

## Automated checks

| Suite | Passed | Failed |
| --- | ---: | ---: |
| Python / pytest | 94 | 0 |
| JavaScript / Node test runner | 13 | 0 |
| Total distinct tests | **107** | **0** |

All 75 original tests are included. The 32 additions cover ten hand categories, wheel and ties, 36 scheduled differential hand attempts across six seeds (tournaments may finish sooner), chip conservation, single-card dealing, all-in/side-pot eligibility, uncalled refunds, eliminated seats, heads-up and restart, learning-mode boundaries, model invocation counts, duplicates/concurrency, old epochs, illegal actions, failure control, settings, sound gating and cancellation. The differential test compares live observations and settlement against the frozen original Game, including later seat rotations.

[Python transcript](pytest-final.txt) · [JavaScript transcript](node-final.txt). Python 3.11.9 and Node 24.15.0 were used. `pip check` found no broken requirements. One preexisting Starlette/httpx deprecation warning remains; dependencies were not changed to hide it. The workflow is updated for both JS suites and the v2 verifier, but **no new GitHub Actions run was triggered**, because this branch was not published.

## Actual browser gameplay

Six full model-driven hands were completed during development/acceptance in a real headed Chrome browser, including a touch-emulated hand and the final recorded hand. These used the actual `imitation-v1` opponents, not scripted bot actions. Calls/checks, a legal minimum raise, folds, all-ins, elimination, showdown, next hand and reset were exercised. Additional starts were intentionally interrupted to test reset and recovery; they are not counted as full hands.

The final [17.08-second silent video](complete-hand-final.webm), recorded at **1440 × 900 / 25 fps**, shows an entire real-model hand. Its [HTTP event timeline](browser-timeline.json) contains 40 successful commands over 13.136 seconds from hand start through final settlement; recorder lead-in and the result pause account for the longer video. It records event text, amounts, versions and visibility counts, without deck data or future cards. The final browser page-error list is empty.

In that hand Grace raised to 45; the human called, Ada folded and Turing called. Three separate flop events then preceded checks/bets. Turn and river each arrived separately. The human received 3,915 chips from the pot; the final result separates this gross receipt from net profit. Time between successive opening bot actions, with a human call between, was about 0.62 seconds after the human response, matching the intended short readable cadence. Human response time in this demonstration is automated, not a claim about typical playing time.

The following recovery/settings checks were performed through the UI:

- Reset during card dealing, then wait for stale callbacks: the new table stayed at hand zero.
- Skip automatic transitions to the next human decision; no human choice was generated.
- Go offline before a human POST, display reconnect feedback, restore networking and recover current state without retrying that POST.
- Set fast speed, disable movement, enable sound and change volume; reload and verify persistence, then mute.
- Focus Call and use Enter to make the real legal action; keyboard focus remains visible.
- On a touch-emulated phone, reject a zero raise, select the legal minimum preset, tap Raise and complete the hand.
- Toggle realistic versus learning view after settlement. Additional folded cards disappear in realistic view.

Sound preference, unlock/mute/volume behavior and oscillator creation were tested; **audible quality was not independently listened to** and the recording contains no audio. Physical phones/tablets and screen-reader speech were not tested.

## Layout and visual review

| Environment | Checks and evidence |
| --- | --- |
| Desktop 1440 × 900, 100% | [Live hand](desktop-live-final.png), [final hand result](desktop-result-final.png), video; no horizontal overflow |
| Laptop 1280 × 800, 100% | [Completed-hand layout](laptop-final.png); legal controls remain reachable by scrolling |
| Tablet 768 × 1024, 100% | [Completed-hand layout](tablet-final.png); two-column result cards |
| Smartphone 390 × 844, 100% | [Touch preflop](phone-touch-preflop.png), [touch showdown](phone-touch-showdown.png); legal raise and full hand via taps |
| Native desktop Chrome, actual 200% browser zoom | [Table](chrome-200-table.png), [actions](chrome-200-actions.png), [next hand / human turn](chrome-200-playing.png); next-hand control exercised at 200% |
| System reduced motion | [Reduced-motion fixture](reduced-motion.png); CSS animation disabled and system note visible |

Full-page screenshots extend vertically beyond the viewport; this does not imply all content fits without scrolling. The native zoom test used a roughly 1200-pixel-wide desktop browser window (Retina screenshot 2400 pixels wide), with browser zoom set through Chrome's native menu, not CSS scaling. The zoom test used a deterministic engine fixture. Controls were read and operated, then zoom restored to 100%.

[Machine-readable layout checks](layout-checks.json) report no horizontal overflow and no collisions between the upper-seat caption, round label, board, winner line and human cards in all four requested viewport sizes. Visual inspection initially found a desktop caption/round collision; the final arena spacing was corrected and all four checks rerun. Final screenshots were visually reviewed. Small screens deliberately use vertical scrolling rather than tiny action targets. Supported controls are at least 44 pixels high in the mobile layout.

## Rare-state fixtures — separate from model gameplay

The opt-in QA app uses actual PokerKit operations with fixed cards/stacks. Its footer explicitly says “Deterministische Engine-Prüfszene”. These are display/integration checks, **not LearnedAgent strength measurements**.

| Fixture | Actual check |
| --- | --- |
| [Three pot recipients](fixture-side-pots.png) | Main pot 200 to human, side pot 150 to Ada, side pot 200 to Turing; eligible seat lists shown. The strongest hand cannot claim ineligible pots. |
| [Four-way split](fixture-split.png) | Royal Flush on board; all four share the pot and each shows the same category. Odd-chip handling additionally covered in Python. |
| [Early fold](fixture-fold.png) | Fold reason, no imaginary future board or five-card category; learning-mode cards available only after settlement. |
| [Tournament winner](fixture-champion.png) | All chips awarded, tournament end and restart control. |
| [Heads-up](fixture-heads-up.png) | Two active participants; eliminated seats receive no cards. |

Normal `pokermind.server:app` returned **404** for the QA scenario route. Start fixture mode only explicitly, on a separate port:

```sh
python -m uvicorn scripts.v2_browser_fixtures:app --host 127.0.0.1 --port 8003
curl -X POST http://127.0.0.1:8003/__qa/live/side-pots
```

Other names: `split`, `fold`, `champion`, `heads-up`. Open `http://127.0.0.1:8003` after selecting a fixture. Do not use fixture mode for ordinary play.

## Reproduce acceptance

From the project directory, install the pinned requirements into a Python 3.11 environment, then run:

```sh
python -m pip check
python -m pytest -q
node --test tests/*.test.mjs
python scripts/v2_verify.py
python -m uvicorn pokermind.server:app --host 127.0.0.1 --port 8000
```

Open the application in Chrome, reset, select normal speed and muted sound, start a hand and call/check until settlement. Repeat in fast mode and with reduced motion; use the fixture app for rare states. DevTools viewport emulation can reproduce the four dimensions. For offline recovery, disconnect before a human action and reconnect through the displayed button. Chrome's menu provides genuine 200% zoom. The final video and JSON timeline document the actual normal-speed run; random games need not produce the same cards.

Build a separate local archive without replacing the old release:

```sh
python scripts/stage8_package.py --output ../PokerMind-2.0-dev.zip
```

The packaging allowlist includes the model, data, scientific provenance, tests, source, documentation and these acceptance files. It excludes environments, Git history, private material, development work directories and redundant archives. ZIP CRCs and every included byte are checked against source. The archive was extracted to a separate directory and installed in a new Python 3.11.9 environment with system site packages disabled. Both suites passed again: **94 Python + 13 JavaScript tests**, zero failures. An additional complete browser hand used the extracted `imitation-v1` model, reached a five-card showdown, retained 8,000 chips and reset to four stacks of 2,000. Opponent cards stayed hidden at the initial human turn; no page errors occurred. See [portable-copy results](portable-check.json), [Python transcript](portable-pytest.txt) and [JS transcript](portable-node.txt). This is a seventh full browser hand in addition to the six development hands. The final archive adds this acceptance evidence; its executed runtime/model/data/test files are checked byte-for-byte against the tested copy.

## Remaining boundaries

This remains a single local, in-memory table with one server process. Use one playing browser tab. No multiplayer, persistence or external hosting is provided. A reload recovers current state rather than replaying missed visual history. Browser/OS combinations beyond the tested macOS Chrome environment were not independently verified. Animation timing depends on device and request latency. Hand labels are explanations of actual cards, not equity estimates or a new proof of AI strength. The cleaned public repository and its existing release remain untouched.
