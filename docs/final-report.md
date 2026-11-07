# PokerMind final project report — Stage 8

## Scope and preserved results

The submission combines a playable local poker application, self-developed rule/Teacher strategies, simulated supervised learning, an independent playing evaluation and a responsive interface. The deadline is 18 December 2026. Stage 8 finalizes reproducibility, documentation and publication; it does not change the scientific development outcome.

The frozen model still has 200 learned trees and 54 inputs. Dataset: 20,024 decisions / 252 sessions. Held-out legal-filtered Teacher agreement: 78.70%. Playing evaluation: 176 sessions / 12,601 hands, 100 regular finishes / 76 caps, no errors. Learned/Teacher mean chip gains against rules are +4,445.31/+4,413.17, with an unresolved paired difference. [Results summary](results-summary.md) explains conditions, uncertainty and rare-class weaknesses.

A complete SHA-256 manifest protects the Stage 7 runtime, model files, Teacher, data/splits and evaluation artifacts. Current checks are read-only. The original source archive supports Stage 6 historical fingerprints. No unused scientific checkpoint or finalist was deleted merely because another export duplicates its content.

## Documentation and publication preparation

The English README follows the complete project/AI/data/training/evaluation/install/play/test/reproduction/limitations/CRISP-DM structure. All six CRISP-DM phases now describe actual implementation and results. Detailed stage reports remain historical evidence. The technical completion report is also available in German; the game interface remains German.

The Git root was confirmed to be exactly PokerMind, with no existing remote or commits. Parent repositories and remotes were not modified. The authenticated GitHub account is `ardacgu`; a public repository named PokerMind is the publication target. Commit identity uses the account's GitHub no-reply address. No account email, token or machine-specific configuration is published.

Ten historical verification files had personal project prefixes replaced with `<PROJECT_ROOT>`. [Redaction ledger](stage8/redactions.json) retains original and public hashes; originals stay in ignored local scratch storage. Raw local server logs, virtual environments, caches and scratch files are excluded. Public acceptance counters, states, transcripts and reports remain available. Historical evidence-manifest hashes still refer to original stage bytes, and are not silently changed.

All required model/data files fit ordinary Git storage. The largest file is 43,309,369 bytes; the selected model is 19,672,230 bytes. Selected/finalist duplicates remain because frozen selection hashes reference both. Release ZIPs are separate assets. The one embedded Stage 6 runtime ZIP is necessary historical source, not a redundant project archive. GitHub documents the per-file limit in its [file documentation](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository).

The workflow uses one standard Ubuntu 24.04 job, Python 3.11.9, Node 24.15.0, exact package pins and official action commit pins. It runs dependency consistency, Python/JavaScript tests and artifact/document checks. It does not train or run the large evaluation on every push. See [workflow](../.github/workflows/tests.yml).

## Acceptance status

The independent fresh installation passed **68 Python tests and seven JavaScript tests, zero failures**. `pip check`, full-data validation, frozen-artifact/document checks and saved-model reevaluation passed. Saved raw/filtered test metrics exactly matched the original recorded results. All inspected dependency modules came from the new environment with system-site-packages disabled; no previous environment was reused. See [fresh tests](stage8/fresh-tests.txt), [environment check](stage8/environment-check.json) and [saved-model check](stage8/saved-model-check.json).

The copied server completed a real browser hand: start → Call 45 → legal All-in to 2,000 → five-card showdown. All three trained opponents acted; Ada received 6,020 chips, final stacks [0, 6020, 1980, 0]. Opponent cards were hidden preflop, and folded Turing stayed concealed at showdown. Confirmed reset restored all four stacks to 2,000. There were **6 model decisions, 0 fallbacks, 0 errors** and no captured browser warnings/errors. [Browser evidence](stage8/fresh-browser-check.json) and [screenshot](stage8/fresh-browser-showdown.png). Initial navigation occurred before cold startup finished; retry after readiness succeeded.

The main checkout independently repeated all 75 tests with zero failures. The public Ubuntu GitHub Actions run also passed 68 Python and seven JavaScript tests, dependency consistency and the frozen-artifact/document verification. [Initial successful remote run](https://github.com/ardacgu/PokerMind/actions/runs/42422707979), [CI evidence](stage8/ci-check.json).

## Public repository and release

**Public repository:** [ardacgu/PokerMind](https://github.com/ardacgu/PokerMind). The authenticated owner, successful push and public visibility were confirmed. An anonymous codeload download of the initial submission commit was CRC-checked and all **707 files** compared byte-for-byte, including the 19,672,230-byte selected model, all data and evaluation artifacts. [Public-source verification](stage8/public-source-check.json).

**Release entry:** [v1.0.0](https://github.com/ardacgu/PokerMind/releases/tag/v1.0.0). The release procedure requires another successful workflow for the final documentation/release commit, then an annotated tag and an attached portable ZIP plus SHA-256 file. The final tag, download URLs, asset digest and latest CI conclusion are independently checked when publishing; the release page and [workflow page](https://github.com/ardacgu/PokerMind/actions/workflows/tests.yml) expose the actual final state. No paid service or external deployment is used.

The ZIP builder checks CRC, unique member names and equality to every reviewed source file. Documentation-only changes after the fresh-copy test do not alter the frozen runtime. The release inventory excludes private prefixes, local logs, environments and scratch copies. The project's license decision remains explicitly open.

The independent acceptance copy is created from the reviewed release file set and uses a newly created virtual environment with dependencies installed from `requirements.txt`. It does not borrow the previous `.venv`. Normal pip download/wheel caches are allowed, but installed module origins are checked to belong to the new environment.

## Limits and ownership

One local in-memory table; no persistence, multiplayer, real money or production hosting. Physics of touch devices and screen-reader speech were not tested; Stage 7 covered requested responsive viewports and actual 200% zoom. Teacher approximations, class imbalance, four standalone all_in test targets, small evaluation-block counts and opponent dependence remain. One existing Starlette/httpx test-client warning remains with pinned dependencies.

The owner has not selected a project license. No fabricated copyright or license grant was added. [Dependency/asset notices](third-party-notices.md) document actual package metadata and original CSS/SVG visuals. Library licenses do not automatically license the entire school project.

[English README](../README.md) · [CRISP-DM](crisp-dm.md) · [Reproduction](reproducibility.md)
