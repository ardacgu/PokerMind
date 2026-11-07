# Stage 7 — Poker interface and usability verification

Stage 7 upgrades the local browser experience while retaining the frozen `imitation-v1` model and the evaluated poker implementation. The interface is German; this report and the operating documentation are English. No model training, strategy adjustment or new strength evaluation was performed.

## Delivered interface

The table uses a dark room, green felt, a layered rim, warm gold accents, original CSS chip stacks and rank/suit cards. The human sits below the community cards; Ada, Turing and Grace sit around the upper edge. Each seat displays its actual bankroll, current street contribution, dealer marker, last public action and active/folded/all-in/eliminated state. Numeric amounts are authoritative; chip illustrations are decorative, not denomination counts.

A large central pot changes to **AUSGEZAHLT** after settlement. Live side-pot layers come directly from PokerKit and are labeled **Hauptpot**, **Seitenpot 1**, etc.; uncollected current bets are separately identified when relevant. Result rows separate gross pot receipts from net hand profit. Split payouts and individual recipients are explicit. PokerKit can consolidate pot layers when losing hands are killed, so completed payout operations are honestly labeled **Topfauszahlung 1**, etc., rather than pretending that their indices always preserve the earlier live side-pot layers.

The action panel displays legal commands only. Check and Call share the existing server action; Bet and Raise share the existing raise-to API. A number field, keyboard-operable range slider, legal bounds and minimum/half-pot/pot presets provide sizing. Raise-to always means the total contribution on the current street, including an existing bet. Presets include the call cost and clamp to the server's legal limits. The server still validates every command.

New games require a native modal confirmation once a hand exists. Escape and Weiterspielen cancel it; confirmation resets all seats. A completed hand stays visible until Nächste Hand. Busted humans can watch subsequent bot hands; an actual tournament champion replaces next-hand controls with a new-game action.

Cards, changed chip amounts, public action events, active seats and winners have short visual transitions. `prefers-reduced-motion` disables animations and transition delays. The server still runs bot decisions synchronously: the UI shows the returned final snapshot, the last four actual public actions and an expandable ordered history. It does not fabricate intermediate bot turns or delay play for a cinematic sequence.

## Implementation and preservation

- `static/index.html`: semantic regions, dialog, status/error announcements and disclosures.
- `static/style.css`: original responsive table/card/chip design and reduced-motion styles.
- `static/ui.mjs`: pure display/amount helpers and a tested command gate.
- `static/app.js`: rendering, focus management, form interactions and HTTP orchestration.
- `presentation.py`: read-only public PokerKit action/pot/payout projection for the browser.
- `server.py`: adds this projection to the human HTTP state. Existing command locking, version validation, error handling, legality checks and mode selection are retained.

The presentation projection is **not** added to agent observations. Neither private cards, future cards, deck order, seeds, features nor model probabilities are sent to the UI. Cards are drawn exclusively from the existing allowlisted human view. Folded/mucked hands remain masked unless PokerKit has legally shown them.

The footer's active mode/version comes from the running server. Default text is Trainierte KI · Random Forest; its information disclosure explains 200 trees, Teacher imitation, no online learning and why 78.70% label accuracy is not a hand's chance of winning. Baseline and Teacher modes retain their own descriptions.

The integrity audit checked **558 preexisting files**: 554 unchanged and only the four authorized existing server/UI files changed. All 20 model files, 288 data files and 225 preexisting evaluation files are byte-identical. Rule engine, moving-button convention, protected observations, Teacher, learning modules and evaluation code are unchanged. All **312 Stage 6 provenance files** remain verifiable against either the current file or its archived original. See [integrity-check.json](stage7/integrity-check.json).

Stage 6 fingerprints intentionally covered the old browser runtime. `evaluations/stage6-runtime.zip` preserves that original source and documentation. Replaying historical checkpoints requires that frozen runtime; current UI files must not be passed off as the old provenance. No evaluation manifest or result was rewritten to hide this distinction. See README for a clean replay command.

## Actual browser checks

The application was started locally and operated using a real Chromium in-app browser and native Google Chrome. Browser actions used the real API and PokerKit. Screenshots are full-page images unless explicitly labeled as a native window capture. Full-page height may exceed viewport height.

| Check | Actual observation |
|---|---|
| 1440 × 900 | Four-seat live play, clear hidden opponent cards, flop, bet sizing, keyboard focus, live side pots, three separate payout recipients; no horizontal overflow or card overlap |
| 1280 × 800 | Live turn and four-way split payout; dealer, player captions and phase remain separate |
| 768 × 1024 | Live turn/showdown, two side-pot layers, heads-up with eliminated seats, controlled failure; vertical scrolling remains usable |
| 390 × 844 | Real all-in/showdown, live flop/actions, side pots, champion, disconnect/reconnect; numeric field and action buttons remain reachable by scrolling |
| Chrome at 200% | Actual Chrome zoom menu reported 200%, not CSS scaling; preset → Tab → raise action executed with real model responses; controls readable without overlap. Zoom reset to 100% afterward |
| Reduced motion | Actual macOS reduced-motion preference temporarily enabled; browser media query true, card animation `none`, seat transition `0s`, a real keyboard fold completed. Original off setting restored |
| Keyboard | Enter activates actions; slider arrow key synchronizes the number field; invalid amount blocks submission; visible focus; focus returns to action region after rendering; reset confirmation/Enter and Escape cancellation tested, including cancel after a previous confirmation |
| Request protection | Actual double-click result exactly matched an independent replay with **one** human call and real subsequent model decisions; stale second-browser command returned 409 and refreshed; busy controls locked |
| Connection loss | Server stopped before a call: visible error, actions disabled, retry offered. Server restarted and retry only fetched state; no automatic repeat POST |

The initial production-server browser flow completed **three hands** across two games: a raised/all-in hand ending in Grace receiving 6,020 chips, a subsequent heads-up hand with the human eliminated, then a restarted game with a keyboard fold. Shutdown counters recorded **22 real model decisions, zero fallbacks, zero errors** ([public acceptance counters](stage7/browser-acceptance.json)). These are functional smoke checks, not a new playing-strength sample. All three opponent identities made genuine learned decisions.

A further deterministic real-deal flow on the QA launcher used the unchanged learned policies: start, double-click Call 20, three keyboard Checks through flop/turn/river, Ada's 60-chip payout, next hand, confirmed reset, and Escape cancellation after that reset. The double-click check stores the exact public state and equality to a one-command replay in [double-click-check.json](stage7/double-click-check.json).

Rare states were deliberately constructed with PokerKit using `scripts/stage7_browser_fixtures.py`: live side pots and all-in opponents; three separate payout winners (200/150/200); a four-way royal-flush split (20 each); human elimination; heads-up; champion (8,000); a halted state. The live side-pot fixture was also continued through Bet 20/Check/Check with three actual Grace model decisions. These are **controlled functional fixtures**, not randomly encountered model-performance observations. Forced setup actions and private test decks never enter production HTTP responses. Only this explicit QA launcher registers its test route; a production-app test confirms that route returns 404.

Browser console checks before intentional connection interruption recorded no JavaScript errors. The deliberate network failure produces expected network errors and is not described as an error-free connection test.

## Visual and accessibility review

Screenshots were inspected for overlap, clipped content and readability. Early tablet card overlap and middle-seat/phase crowding were fixed by increasing table height and separating the center seat. Stale focus after re-rendering was fixed. Obsolete screenshots showing the identified overlap were removed from the release evidence gallery.

The controls use native buttons, labels, number/range inputs and a modal dialog. Rank and suit names are provided to assistive technology; suit shape accompanies red/black colors. A skip link leads to the action region, visible gold focus outlines are supplied, status is announced politely and errors use an alert. Mobile action controls and the sizing field/slider have at least 44px height; small preset buttons also have at least 44px width. Cards are larger at the human seat. Text contrast was spot-checked numerically for main/muted/button/card/error combinations; see [contrast-check.json](stage7/contrast-check.json). This is not a formal WCAG certification.

Not tested: physical touch hardware, VoiceOver/NVDA speech output, every browser/OS combination, or arbitrary zoom levels beyond the requested 200%. Viewport tests do not claim to be physical-device testing. Mobile and zoomed views deliberately scroll vertically; the whole table and all controls need not fit simultaneously in one viewport. The local service remains a single in-memory table without accounts, persistence or multiplayer.

## Automated verification and portable delivery

**75 distinct tests pass: 68 Python tests and 7 JavaScript tests.** This includes all 63 preexisting Python tests, five public-presentation/API tests, and seven Node built-in tests for card masking, amount validity, sizing, state messages, duplicate/stale/transition locking and error recovery. Python tests retain one preexisting Starlette/httpx deprecation warning. See [Python output](stage7/python-tests.txt) and [JavaScript output](stage7/ui-tests.txt).

The portable ZIP includes the frozen model, datasets, prior reports and evaluation evidence, UI sources, fixture launcher and new tests. Environments, caches and scratch work are excluded. Packaging checks ZIP CRC, unique member paths and equality of every member to the source file. A fresh extraction is tested with the pinned installed Python runtime, reruns both suites, and is started as an actual server for a browser smoke check. The extracted server completed one additional real hand (start, Call 20, All-in): all three bot seats acted; Ada received 4,020 chips, final stacks were [0, 4020, 1980, 2000]. Shutdown recorded six model decisions, zero fallbacks and zero errors. This validates copied paths/model/static assets; it does not claim a clean-machine dependency installation. See [package-check.json](stage7/package-check.json) and [extracted-tests.txt](stage7/extracted-tests.txt).

```bash
# In the project root, after installing requirements.txt:
python -m pytest -q
node --test tests/ui.test.mjs  # Node 18+; optional for running the game
python scripts/stage7_integrity.py
python scripts/stage7_package.py
# Explicit local fixture server for manual acceptance checks only:
PYTHONPATH=. python scripts/stage7_browser_fixtures.py
# Select a fixture, then reload http://127.0.0.1:8768:
curl -X POST http://127.0.0.1:8768/__qa/scenario/side-pots
```

[Open the screenshot gallery](stage7/screenshots.html). All visual assets are original CSS, inline SVG and Unicode suit symbols created within this project. Fonts use the system stack; there are no downloaded fonts, stock images, external asset licenses, paid services or frontend libraries. Prior scientific figures and project evidence remain unchanged.
