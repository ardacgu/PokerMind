# Stage 3 dataset contract

The learning target is the **discrete action class of our heuristic Teacher**, given permitted cards and public game state. The inputs never include Monte Carlo results, teacher scores, reasons, labels, seeds, session IDs, winners or future stacks. No model has been trained.

## Shared inference-time extractor

`pokermind.data.schema.extract(observation, config)` consumes only a detached protected observation and does not call `TeacherAgent.decide`. `FEATURE_NAMES` is the explicit ordered allowlist; `SCHEMA` defines every field's integer type, range and unit. The exported `schema.json` is the machine-readable contract. The same extractor can be used at the live table in stage 4. No feature encoder is fitted in stage 3.

- Two own cards sorted by rank/suit: ranks 2–14, suits clubs=1, diamonds=2, hearts=3, spades=4; pair and suited flags.
- Five public board slots in deal order. Rank/suit 0 means **not yet dealt**, not an unknown future card. Board count and street disambiguate absence.
- Current best five-card category evaluated by PokerKit when at least the flop exists: −1 preflop, then 0 high card through 8 straight flush.
- Street: Preflop=0, Flop=1, Turn=2, River=3.
- Clockwise fixed-seat distance from the dealer, 0–3. This is a seat distance, not a compressed rank among surviving players.
- Public stack, street bet, call, pot, highest street bet, eligible amount after own call, and eligible contribution-layer count. These are chip counts; layers follow the documented frozen-contribution convention and need not be final settled side pots.
- Relative seats 0–3 starting at the actor: public stack, street bet, total hand contribution and live-in-hand flag. Folded money remains visible. Hidden cards at other seats are never encoded.
- Legal raise bounds in chips; −1 means unavailable. Short-call and all-in-call flags.
- One binary mask per canonical action class.

The extractor intentionally omits public history text because this teacher does not condition ranges on it. It omits exposed opponent cards as predictive features as well; the current game produces no betting decisions after tournament all-in reveal. Absolute seat ID, human-readable names, hand counter and RNG metadata are also omitted.

## Shared action mapping

The existing `teacher.candidates` function is the single mapping authority for both teacher and future model. `schema.decode(label, observation, config)` delegates to it, and rejects a masked-out label. Teacher sizing configuration is pinned in the manifest. Canonical classes, in insertion/deduplication order:

| Class | Engine action | Amount |
| --- | --- | --- |
| fold | fold | none; pays 0 |
| check | call | no raise-to; call cost 0 |
| call | call | no raise-to; actual capped call cost, including a short all-in call |
| small | raise | own street bet + call + round(0.5 × (pot + call)), clamped to engine min/max |
| large | raise | own street bet + call + round(1.0 × (pot + call)), clamped to engine min/max |
| all_in | engine all-in action | remaining stack + own street bet for an all-in raise |

Duplicate `(action, amount)` pairs keep the **first** class. Thus an all-in call is canonical `call`, never an all-in raise. A clamped small/large raise can also use all remaining chips; it keeps the earlier label. The `all_in` class exists only when that candidate is distinct. Do not infer all-in frequency from that class alone; use paid amount, stack and call flags. `legal` records concrete pre-decision candidates, `label` is the target, `executed` records engine action/raise-to, and `paid` records additional chips actually committed.

## Artifact structure

Each directory is a separate dataset population:

- `data/pilot-v1/`: bounded development pilot and pilot-only stability study; excluded from main splits.
- `data/main-v1/sessions/`: one atomically committed JSON checkpoint per independent simulation session, containing immutable pre-decision snapshots, diagnostics, exclusions and session provenance.
- `raw.jsonl`: accepted records including full protected observations, extracted features, masks/candidates, target and executed amounts.
- `train.jsonl`, `validation.jsonl`, `test.jsonl`: `{id, session, features, label}`. IDs are metadata, not features.
- `diagnostics.jsonl`: separate teacher estimates, scores, reasons, configurations and decisions keyed by record ID. Nondeterministic per-decision elapsed timing is omitted for reproducible content; session runtimes are metadata.
- `excluded.jsonl`: explicit exclusion log. Empty if none.
- `examples.jsonl`: first eight accepted raw records for readable inspection; **not an additional training source**.
- `schema.json`, `generation.json`, `groups.json`, `manifest.json`: allowlist, configuration/source hashes, frozen assignment, provenance/file hashes/counts.
- `data/scenarios-v1/`: clearly separated targeted rule-valid short-call and all-in-raise states. These have no natural split membership; intended as separate regression checks, not synthetic test balancing.

`load_model(path)` explicitly validates and reads only `FEATURE_NAMES` and the target. Unknown feature keys cause an error rather than becoming columns. Future training must use this loader (or an equally strict allowlist), never flatten all raw/diagnostic fields. Any scaler, imputation learned from data, selection or resampling belongs in the training-only pipeline in stage 4.

## Generation and session families

Teacher version `teacher-2.0.0`, all main labels at 128 samples and unchanged thresholds. Each independent session has a unique card seed `base + index`. Each Teacher has a distinct local seed `base*10 + index*4 + seat`. RuleBots are deterministic and have no random stream. Card dealing, teacher sampling and comparison behavior are separate. Initial stacks and rules are unchanged. Sessions maintain stacks across hands and stop at a genuine winner or after 12 complete hands, below the requested maximum of 100. The main target is checked between batches of four complete sessions, so the final count exceeds 20,000 slightly.

Even-index sessions have four Teachers. Odd-index sessions have two Teachers at rotating adjacent seats and two RuleBots. Every teacher decision at those tables is captured. Natural busts are retained; no winner is required at a hand cutoff. The source seed is the family identifier: no seed repeats across pilot/main. Different random ranges are not manufactured as separate split groups from the same card game.

## Resume and release policy

Only a finished session is published, using temporary file + atomic rename. An interrupted in-progress session is recomputed from the same seeds; no partial session is appended. Existing checkpoints are skipped. Resume rejects configuration, Python-version or source-hash changes. Run **one coordinator per output directory**. Workers are separate processes, not separate agents. The original worker count should be retained for exact target overshoot reproduction.

Splits are formed after generation: deterministic SHA-256 ordering of session IDs, then rounded 70/15/15 group counts. Every hand and actor from one session stays together. `groups.json` freezes the assignment; exporting after adding sessions refuses to silently change it. Create a new dataset version to grow a released dataset. No labels or model results influence assignment. Raw data duplicates are distinguished from identical feature vectors arising in independent games; legitimate recurrence is measured and kept.

## Commands (from project root)

```bash
source .venv/bin/activate
# Pilot; use a fresh directory for a clean reproduction.
python -m pokermind.data.pipeline generate --output data/pilot-reproduction --target 500 --base 900000 --hands 12 --samples 128 --workers 4
python -m pokermind.data.pipeline export --output data/pilot-reproduction
python -m pokermind.data.stability data/pilot-reproduction

# Main generation AND exact resume command (same command).
python -m pokermind.data.pipeline generate --output data/main-v1 --target 20000 --base 100000 --hands 12 --samples 128 --workers 4
python -m pokermind.data.pipeline export --output data/main-v1
python -m pokermind.data.pipeline validate --output data/main-v1

PYTHONPATH=. python scripts/stage3_scenarios.py
python -m pytest -q
```

The main source hashes are pinned. If implementation changes, recover that version before resuming, or use a new output version; never bypass the source guard. The pilot was developed before the final source freeze, so its historical generation hashes differ from main while teacher, features and sampling configuration remain the same. Independent reproduction should use a new folder, never overwrite a delivered manifest.

For optional chart regeneration, install `requirements-report.txt` into a plotting environment and run `python scripts/stage3_report.py`. The delivered charts were rendered with Matplotlib 3.9.0 from the host's existing Python environment. Core generation and validation use only the existing pinned application requirements. Plotting/report scripts are not part of model inference.
