# Stage 5 integration report

## Implemented behavior

The browser's default mode is now `learned`. All three computer seats use the frozen selected RandomForestClassifier from `models/imitation-v1`: 200 trees, depth 20, minimum leaf 3, balanced class weights. Separate LearnedAgent instances share one read-only estimator loaded once per process. No fit or model mutation occurs during play. Decision flow remains protected observation → existing 54-feature extractor → model → existing class/legal adapter → PokerKit action.

The loader resolves project-relative or explicit absolute paths and validates Python major/minor, recorded library versions, schema/feature order, class mapping, selected artifact hash, estimator family and declared parameters. No model load occurs on a move, next hand or reset. Load/schema errors stop startup. Unexpected runtime errors halt processing with a generic HTTP 503 message; previous valid actions remain visible. No hidden exception data is sent to the browser and no replacement bot is chosen. Adapter zero-probability fallback remains separately counted.

The existing request lock serializes a human command and subsequent bot moves; monotonic versions reject duplicated/stale requests including pre-reset commands. Bot application additionally checks its observed version and actor. The test suite exercises a pending decision with a competing stale reset. No asynchronous job service or production delay was introduced.

## Automated regression and integration tests

**51 tests passed**, including all previous 45. Raw output: [stage5-tests.txt](stage5-tests.txt). The existing Starlette/httpx test-client deprecation warning remains; no new application deprecation warnings remain.

Six new integration tests cover shared loading and per-seat isolation; all three actual LearnedAgents with Teacher/Monte-Carlo methods forbidden; correct own-card and masked opponent views; cache reuse across moves/resets; independent Game state; missing, incompatible and corrupt model failures; absolute path loading from another working directory; concurrent command/stale-reset rejection; sanitized injected inference failure; short-stack and heads-up completion; and correct configuration labels in all modes.

The intentionally injected inference exception verifies controlled failure rather than successful play. It is not counted as an observed model defect in the clean acceptance runs below. Test-only dependency fault injection is restored afterwards. Existing adapter and side-pot rule tests remain in the suite and were not duplicated merely to repeat their implementation.

## Counted HTTP / engine acceptance run

Executed `PYTHONPATH=. .venv/bin/python scripts/stage5_http_check.py` against the actual FastAPI app and actual loaded model via TestClient. Seed 1, human checks/calls; three starting-stack settings:

| Starting stacks | Completed hands | Final stacks |
| --- | ---: | --- |
| 2000, 2000, 2000, 2000 | 3 | 1980, 2040, 2020, 1960 |
| 50, 100, 200, 7650 | 1 | 0, 0, 0, 8000 |
| 4000, 0, 0, 4000 | 3 | 4060, 0, 0, 3940 |

**33 command responses inspected; 43 model decisions; 0 adapter fallbacks; 0 inference errors; 0 bot-engine errors.** Every public opponent-card projection was compared with PokerKit's actual show/muck operations. No feature/probability/deck/seed fields appeared. Chip conservation held. Evidence: [stage5-http.json](stage5-http.json). These artificial short-stack/heads-up starts are functional checks, not strength samples. The six historical all-in scenarios remain separate functional fixtures and are not claimed as classification-strength evidence.

## Actual visual browser run

Used the real local server and in-app browser, with laptop viewport 1366 × 900. A private test launcher set dealer RNG to seed 1 (never exposed over HTTP) and held ONLY the first bot decision behind a manually released test gate. The gate was outside production code; it allowed inspection of transient busy controls. After release, all decisions came from the unmodified selected model and the normal server/action path.

Executed and visually confirmed:

1. Actual footer: **Trainierte KI · Random Forest · imitation-v1**, one human and three computer seats.
2. First-hand start; while the first decision was held, **Erste Hand starten** and **Neustart** were disabled, and **Aktion wird verarbeitet …** was visible. Screenshot: [stage5-busy.png](stage5-busy.png).
3. After release, Grace folded automatically, opponent cards remained face-down, and the human's buttons became enabled.
4. Human called 20 preflop, then checked flop, turn and river; model opponents automatically acted between human decisions. Public last-action text and active seat were visible.
5. Showdown: board 3d 9d As 5s Kh; Ada exposed Ad 2h and won **60 chips, +40 net**, ending at 2040. Human/Turing stacks 1980, Grace 2000. Other opponents' cards remained masked according to engine rules. [Showdown screenshot](stage5-showdown.png).
6. Next hand started, dealer moved to Ada, legal human actions returned.
7. Neustart restored all four stacks to 2000 and the first-hand start button. The active model label remained correct.
8. Browser error console was empty; temporary viewport override was reset.

**9 model decisions; 0 adapter fallbacks; 0 inference errors; 0 bot-engine errors** during this browser session. Shutdown counters are in [stage5-browser-counters.json](stage5-browser-counters.json). Separate real HTTP GETs from this same session checked preflop masking and the showdown projection; snapshots: [stage5-browser-http.json](stage5-browser-http.json).

The normal production command (without the test gate or fixed RNG) was also started successfully and returned HTTP 200 with learned/imitation-v1 status. Both servers were stopped after verification. The final added estimator-parameter startup validation was covered by the full test rerun; the UI and decision logic did not change after the visual test.

## Portable copy and integrity

The portable ZIP includes the frozen selected model and pinned requirements, excluding virtual environments, Git internals and scratch files. The extracted-copy check uses its own source tree and copied artifact, with the default project-relative model path and no original absolute model path. Executed outcome: fresh virtual environment installed from the copied requirements; copied source/model loaded successfully even after changing the working directory to docs; one genuine model decision, zero fallbacks/errors; extracted server returned HTTP 200 on port 8001. Evidence: `stage5-portability.json`. The extracted check server was then stopped. Across the separately counted clean HTTP, browser and portable acceptance runs: 53 model decisions, zero fallbacks, zero unexpected inference/engine errors. Dataset manifest hashes and stage 4 model/selection artifact hashes are checked unchanged.

## Start and limitations

```bash
source .venv/bin/activate
POKERMIND_BOTS=learned POKERMIND_MODEL=models/imitation-v1 \
  python -m uvicorn pokermind.server:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. Learned is also the default without these variables. Explicit alternatives: `POKERMIND_BOTS=baseline` or `POKERMIND_BOTS=teacher`. Do not run multiple workers for this one in-memory table. Stopping the server loses the current game. The displayed scores never claim a win probability or online learning. The sparse standalone all-in class remains unreliable; this integration does not establish comparative strength. Stage 6 will address opponent evaluation.

Not executed: multi-browser compatibility matrix, multi-user/network deployment, thousands-hand tournament stress test or comparative strength experiment. No outstanding test server is intended to remain running after delivery. The test suite's injected error is a controlled negative test; clean browser and HTTP acceptance runs had no unexpected errors. Unit-test-internal model calls are not included in the separately measured acceptance counters.
