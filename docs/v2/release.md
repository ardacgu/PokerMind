# PokerMind v2.0.0 release verification

Release preparation date: **23 November 2026**. Version 2.0 promotes the tested experience branch, including commits `561ea86` and `c849ba8`. It preserves the existing v1.0.0 tag/release and scientific evidence. No history rewrite or force-push is part of publication.

## Scope

The release adds sequential authoritative live steps, readable Normal/Schnell/Sofort speeds, stable action controls, player-side PokerKit descriptions, persistent central winner results, optional local synthesized sound and privacy-safe completed-hand learning views. The original simulator and compatibility API remain available. The new live adapter still uses PokerKit as the sole rule/payout authority; differential tests cover compatibility with the original rules.

This release preparation changes documentation, the package version and publication checks only. It does not modify runtime game/UI behavior from the accepted `c849ba8` version. No model training, data generation or new playing-strength experiment is performed.

## Reproduction

Use Python 3.11 (verified with 3.11.9) and Node 24.15.0 for JavaScript tests. The frontend needs no build. Install all pinned requirements into a new virtual environment with system site packages disabled:

```sh
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
python -m pytest -q
node --test tests/*.test.mjs
python scripts/v2_verify.py
python -m pokermind.learning.inference --model models/imitation-v1 \
  --observation models/imitation-v1/example-observation.json
python -m uvicorn pokermind.server:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. Use one playing tab and one server process. For the repeatable browser regression, start a separate disposable instance on port 8002 and run `python scripts/pace_browser_check.py --url http://127.0.0.1:8002`. This optional script requires Node/npm and Chrome and resets that QA table. It does not alter the model or frozen experiments.

The suite comprises **94 Python and 20 JavaScript tests**, including the original 75 tests. The artifact verifier checks **558 protected original files** against historical hashes. A preexisting Starlette/httpx deprecation warning is documented; dependencies are preserved rather than upgraded during release.

## Packaging and provenance

Build from the reviewed release checkout:

```sh
python scripts/stage8_package.py --output ../PokerMind-v2.0.0-cleaned.zip
# From the directory containing the archive and checksum:
shasum -a 256 -c PokerMind-v2.0.0-cleaned.zip.sha256
```

The allowlisted archive includes application source, the saved Random Forest and selection artifacts, all frozen datasets/splits, evaluation results and original runtime provenance, tests, scripts, technical reports, CRISP-DM documentation, screenshots and browser recordings. It excludes environments, credentials, caches, private study materials, local working files and Git metadata. No personal machine paths belong in public source or evidence.

The packager validates every ZIP CRC and compares each archived byte with source. Acceptance then extracts the archive separately, installs the pinned dependencies in an isolated environment, runs Python/JavaScript tests, dependency/artifact checks, saved-model inference and an actual server/browser check. The existing November 8 development ZIP is checked separately and retained.

The final release attaches the cleaned ZIP, its SHA-256 file and `PokerMind-v2.0.0-verification.json`. That manifest records the exact merged commit, archive hash, executed tests, CI links and preserved v1.0.0 identifiers. It is separate from the ZIP to avoid a self-referential hash. GitHub-generated source archives are additional tag snapshots; use the checked cleaned ZIP for the documented package.

## Publication gates

1. Keep a complete private local backup, including Git and untracked/ignored local files.
2. Compare the feature branch with current remote main without overwriting foreign changes.
3. Check the exact publication file list and scan both current files and newly published history for private paths or credential patterns. Review large files; do not remove scientific artifacts to reduce size.
4. Pass local and extracted-package checks. Push the feature branch normally and open a pull request.
5. Merge only after required checks pass; use the reviewed head SHA. Wait for the merged main workflow too.
6. Create a new annotated `v2.0.0` tag on that tested main commit. Never move `v1.0.0`.
7. Publish the release only with verified assets. Confirm public access, downloaded archive/checksum, and the previous release's unchanged tag and assets.

The single GitHub Actions job runs pinned-dependency installation, dependency checks, both test suites, protected-artifact/document checks and publication-file checks. It does not retrain models or run the expensive full evaluation.

## Publication-session checks

The 23 November local checkout, the retained November 8 ZIP, and the new cleaned ZIP each passed all **94 Python + 20 JavaScript tests**. Both ZIPs were extracted separately and tested using a newly created Python 3.11.9 environment with no system site packages; pinned dependencies were downloaded and installed anew. Dependency checks, protected-artifact verification and saved-model inference also passed.

The first additional browser regression reported 11 scroll-change samples during a bot thinking phase in one fast-mode hand, despite unchanged control geometry and no enabled foreign actions. A focused repeat and a further instrumented three-mode run did not reproduce the scroll change. The initial failure is retained in the release verification evidence; its cause was not established, and no application change or relaxed assertion was used to dismiss it. Publication requires the original, unmodified full browser regression to pass again. This intermittent observation remains a disclosed limitation rather than a claim that every environment is scroll-stable.

## Scientific results and limits

Unchanged evidence: **20,024 Teacher decisions**, **252 independent data sessions**, **54 allowed features**, **200 Random Forest trees**, **78.70% legal-filtered Teacher-label test accuracy**, and **176 evaluation sessions / 12,601 hands**. Learned vs rule bots averaged **+4,445.31 chips/session**, Teacher **+4,413.17**; the paired interval did not resolve a difference. These results measure imitation and bounded tournament performance, not optimal poker or a hand-winning probability.

[November 8 browser evidence](pace/acceptance.md) documents actual-model hands separately from deterministic rare-state fixtures. Its statement that publication had not occurred describes that historical date. The final release manifest and GitHub release show publication status. Small/short windows may require vertical scrolling. Smartphones were emulated rather than physically tested. One local in-memory table is supported; server restart loses it. The owner's project-license decision remains open; no license or copyright owner is invented here.
