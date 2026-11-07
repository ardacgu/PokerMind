# PokerMind imitation-v1 Model Card

## Intended use

Local educational imitation of the self-developed `teacher-2.0.0`, not poker optimization or a real-money product. Stage 4 provides a reloadable model and observation-only inference. Stage 5 integrates this model at the three browser opponent seats. Stage 6 independently evaluates its bounded simulated playing performance; see the measured results below.

## Selected model

RandomForestClassifier: 200 trees, max_depth=20, min_samples_leaf=3, class_weight=balanced, random_state=20261107, n_jobs=2; other sklearn defaults are recorded by the estimator. Artifact: `models/imitation-v1/selected.joblib`, approximately 19 MB. No preprocessing. It is the exact train-only model selected on validation and subsequently tested; no train+validation refit.

The data comprise 20,024 simulated teacher decisions from 252 independent sessions. Fixed splits: train 14,156/176 sessions, validation 2,811/38, test 3,057/38. No additional observations or synthetic cases were used for training or model selection. All 54 `observation-features-1.0.0` integer features use the frozen order. The complete class mapping is fold, check, call, small, large, all_in. Action mapping is `teacher-candidates-2.0.0` with the original teacher sizing configuration. Monte Carlo outputs, labels, IDs, seeds and future outcomes are not inputs.

## Selection and measured performance

Predeclared bounded search: 12 candidates plus DummyClassifier(prior). Primary metric: validation Macro-F1 averaged over five non-all_in classes AFTER legal filtering, with class metrics computed on all rows. Zero-division metrics become zero. Selected RF validation score 0.7294; locked test score 0.7360; test accuracy 0.7870. Baseline legal test F1-5 0.2938; best tree 0.7222. Full raw and filtered class/street/confusion results are in the [training report](training-report.md) and package JSON.

The forest proposed two originally illegal actions out of 3,057 test decisions (0.0654%). The external legal adapter corrected these; fallback rate was zero. This does not mean the model itself guarantees poker legality. Full inference latency over 200 sequential validation states after ten warmups: mean 12.84 ms, p95 13.24 ms. Separate warm-process artifact loading: 93.44 ms. See latency.json for environment and scope; no directly comparable Teacher speedup is claimed.

## Limitations

Only 21 standalone all_in targets exist (15 train / 2 validation / 4 test). Scores for this class are unstable and cannot support robust conclusions. Short all-in calls use the call class; clipped small/large raises may also commit the entire stack. Do not equate the standalone class count with all-in coverage.

This teacher uses uniform unknown-hand assumptions, finite Monte Carlo sampling and a frozen-contribution approximation. Agreement measures imitation, not optimal poker or opponent strength. The boundary-enriched 41-state pilot cannot establish general dataset noise or an accuracy ceiling. Probabilities are uncalibrated class scores, not win probabilities. No confidence-based refusal threshold or probability calibration was fitted. Stage 6 tested bounded model-driven trajectories against the documented opponent lineups; broader distribution shift and generalization remain unestablished.

## Inference contract

`ModelAgent(directory).decide(protected_observation)` returns the existing Decision type. No Teacher or Monte Carlo evaluation occurs. It checks metadata schema/order, sklearn version, model hash and feature count, extracts the same allowlisted features, then aligns `classes_` probabilities. Missing classes receive zero. Illegal classes are removed; fixed order breaks ties. Zero probability across all legal classes triggers check → fold → call → small → large → all_in fallback priority. No legal candidates raises ValueError. Missing/incompatible observations fail explicitly. Runtime explanations are available as `last_prediction`, not automatically exposed to the browser.

Only load this trusted local joblib artifact. Pickle/joblib can execute code when loading untrusted files; checksums here detect accidental mismatch, not a maliciously replaced artifact plus metadata. Use the pinned requirements and recorded versions; cross-version sklearn persistence is unsupported.

## Reproduce

From the project directory:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
# Existing example observation; no teacher invocation:
python -m pokermind.learning.inference --model models/imitation-v1 \
  --observation models/imitation-v1/example-observation.json
# Evaluate the locked artifacts without refitting or reselection:
python -m pokermind.learning.evaluate_saved --model models/imitation-v1 --data data/main-v1
# Independent reproduction; requires a NEW output directory:
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 VECLIB_MAXIMUM_THREADS=2 \
  python -m pokermind.learning.experiment --data data/main-v1 \
  --config experiments/imitation-v1.json --output models/imitation-reproduction
python -m pytest -q
```

Use `--observation` with a JSON object produced by the existing protected `observe` interface, not a raw engine state. The original package is immutable with respect to selection and model bytes; report generation does not fit or select anything. Relevant versions, dataset and artifact hashes, seeds, features, configuration and selection evidence live in metadata.json, selection.json and events.json. The optional report chart can be regenerated with the host plotting environment via `python scripts/stage4_report.py`.

In the actual test, all three evaluated models had standalone all_in precision/recall/F1 of zero on four targets. None correctly predicted that class. This failure remains visible; the overall winner is not changed and the test distribution is not modified.

## Stage 5 deployment status

The frozen model now drives all three browser opponents by default, without retraining or changing its action mapping. LearnedAgent reuses this inference path with one cached model per process and per-seat mutable diagnostics/counters. Configuration: `POKERMIND_BOTS=learned`, `POKERMIND_MODEL=models/imitation-v1`. Relative model paths resolve against the project root. Startup checks recorded libraries, schema, classes and artifact/parameter integrity; runtime failures halt the table rather than substituting another policy. No learning occurs during play. Legal adapter fallbacks remain distinct from execution errors.

See the integration report for actual tests. A small functional browser/HTTP run was verified in stage 5. Stage 6 results below add bounded comparative strength evidence; broad generalization and reliability on the rare standalone all_in class remain unproven. The model, training splits and stage 4 selection results are unchanged.

## Stage 6 — independent playing-strength evidence

No retraining, reselection or parameter/data/split change. All artifacts and Teacher/rule/schema sources were integrity-checked. The frozen forest completed 48 sessions against three rule opponents (12 seed blocks, four seat rotations, 100-hand limit or actual tournament end). Mean net chips: **+4,445.31**, 95% block bootstrap **[3,697.00, 5,093.96]**. Teacher under matching blocks: **+4,413.17 [3,596.08, 5,150.56]**. Paired Learned−Teacher **+32.15 [−551.87, +631.24]**; no resolved difference and no proof of equivalence. The marked Rule control averaged zero by verified rotation symmetry, not universal certainty.

In 32 supplementary mixed sessions (eight blocks), Learned averaged **+395.63**, Teacher **+2,750.00**; paired Learned−Teacher **−2,354.38 [−4,604.38, −208.75]**. This exploratory lineup-specific result suggests a Teacher advantage; it does not establish general superiority. Capped sessions were not counted as wins. Learned used no standalone all_in labels but committed all remaining chips in 34 A actions and 50 D actions through call/clipped raise labels. Across the experiment, one raw illegal model label was legally filtered, zero zero-probability adapter fallbacks occurred and no session failed.

Full experiment: **176 sessions / 12,601 hands**, 100 completed tournaments / 76 capped, four fixed rosters. The unit for uncertainty is an independent seed block, not each hand/rotation. Opponent dependence, small 12/8-block samples, finite horizon, unequal survival, state-distribution shifts and rare-action coverage remain limitations. Label agreement (78.70%) measures imitation; bankroll change measures this particular playing task; neither measures optimal poker or exploitability. No model change follows from the evaluation. See [protocol, outcomes, uncertainty and figures](evaluation-report.md).
