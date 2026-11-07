> Historical snapshot at the end of Stage 7. Relative links were adjusted for this archive location; use the current README for commands.

# CRISP-DM — development history and current evaluation

Project: PokerMind, AI Systems Development. GitHub submission target: 18 December 2026.

## 1. Business understanding

**Completed:** defined a four-seat local Hold'em game, fair observations, a reproducible simulation seam and baseline policies. Stage 1 success means legal play, conserved chips, correctly settled hands, hidden-card isolation and a usable browser workflow.

**Planned:** imitation learning of a documented teacher strategy, comparing a Decision Tree and a Random Forest. The immediate learning objective is to reproduce teacher decisions from legal observations, not to claim optimal poker play or superhuman performance.

## 2. Data understanding

**Completed:** observation schema and privacy boundary implemented. No training corpus has been generated. Test fixtures are regression evidence, not a representative training dataset. The baseline teacher's limitations are documented in architecture.md.

**Planned:** record decision-time observations, teacher labels and chosen raise targets through a separate collector. Proposed features: own-card ranks/pair/suitedness, public board features, street, position, active-player count, stack-to-pot ratio, call cost, public bets and legal action mask. Private deck state and opponents' hidden cards must never become features. Hand/episode IDs and reproducibility seeds belong in evaluation metadata, not predictive inputs.

## 3. Data preparation

**Completed:** detached views and typed decisions provide a narrow integration seam. No feature encoder, sampling policy or cleaning pipeline exists yet.

**Planned:** version the teacher, schema and feature encoder; verify uniqueness, ranges, missing values, action legality, class balance and duplicated examples. Split by complete episodes, never individual decisions from the same hand across train and test. Reserve unseen seeds and rotate seats to detect positional bias. Document exclusions and class weighting. Keep a data-quality report with counts before and after cleaning.

## 4. Modeling

**Completed:** rule-based baseline only. No Decision Tree or Random Forest has been fitted.

**Planned:** compare identical feature sets and train/test splits for both models. Predict action class (fold, check/call, raise); define raise sizing explicitly, e.g. a separate head or documented discretized legal targets. Mask illegal predictions and report every fallback separately. Choose hyperparameters on training/validation data only. Freeze teacher and encoding before the final held-out evaluation.

## 5. Evaluation

**Completed:** game/API regression tests and browser acceptance checks; these validate the platform, not learned-model performance. A seeded headless runner reports completion, hands, actions, winner and final stacks.

**Planned:** report teacher agreement, macro-F1, confusion matrices, class frequencies, raise-size error, illegal-proposal rate, fallback rate and latency. Add seat-balanced tournaments against the baseline across held-out seeds. Compare net chips or tournament win rates with sample counts and uncertainty intervals. Separate imitation accuracy from playing strength. Use the same budgets, opponents and evaluation seeds for both models; discuss that imitation is limited by teacher quality.

## 6. Deployment

**Completed:** local Python service, browser interface, pinned dependencies, macOS instructions, tests, and repository structure.

**Planned:** wrap the selected model behind the existing `Policy` protocol, load a versioned artifact and encoder, preserve the same private observation boundary, and run game and model regression checks before use. Publish the reviewed project and English documentation on GitHub by the deadline. No cloud deployment or publication was performed in stage 1.

## Stage 2 update — 7 November 2026

The previous stage 1 entries above are retained as historical milestones. Stage 2 now implements a separate, versioned `TeacherAgent`, public contribution/eligibility features, independent uniform Monte Carlo sampling, legal candidate construction and offline diagnostics. Game rules and baseline opponents remain intact. See [teacher specification](../teacher.md) and [stage 2 verification](../stage2-report.md).

Business understanding: imitation targets are explicitly example decisions, not optimal play. Data understanding: 32 bounded diagnostic records expose schema and assumptions; this is not a representative dataset. Preparation: tested privacy, pot accounting, reproducibility and legal action mapping establish the collector seam. Modeling: no model trained. Evaluation: 36 passing tests and four seat-rotated pilots, with measured latency and zero observed fallbacks; strength superiority is unproven. Deployment: Teacher is selectable at the local table via environment configuration and in the simulator via CLI.

Stage 3 is training-data generation: version schemas and seeds, generate diverse complete episodes, audit duplicates/leakage/class balance, preserve cutoff/fallback labels, split by episode and retain held-out seeds. Decision Tree and Random Forest fitting and comparison follow in subsequent stages, not this implementation.

## Stage 3 update — simulated training data

Stage 3 implements and executes a session-checkpointed data pipeline and an inference-time feature allowlist. Pilot-only label-stability analysis precedes the frozen main configuration. Public card/game features are separated from teacher Monte Carlo diagnostics, target labels, seeds and future outcomes. Natural sessions preserve stacks and end cleanly at a winner or 12-hand cutoff. Session-level train/validation/test assignment is frozen without label balancing; targeted rare cases remain a separate scenario set.

Data understanding/preparation now include complete schema validation, legal-target checks, duplicate/family overlap auditing, sample-noise investigation, class/street/position/stack distributions and hashed provenance. See [actual data quality results](../data-quality.md) and [feature/action contract](../data-schema.md). Original stage 1/2 reports are historical evidence, not descriptions of the newest dataset state.

No Decision Tree or Random Forest has been fitted. Stage 4 must load only the allowlisted features, fit learned preprocessing on train only, select settings on validation and reserve test for final comparisons. Interpret agreement as imitation of a noisy heuristic teacher, not evidence of optimal poker or improved playing strength.

## Stage 4 update — Modeling and Evaluation completed for the first comparison

Modeling: trained DummyClassifier(prior), six Decision Trees and six Random Forests under a predeclared 12-candidate budget plus baseline. All fits and balanced class weights use train only; no fitted preprocessing is necessary. The common allowlisted observation extractor and legal probability adapter are reused in inference. No datasets or split assignments were modified.

Evaluation: selected each family finalist and overall winner by validation filtered five-class Macro-F1, then saved artifacts, hashes and selection before evaluating the locked test set. All six classes, raw and filtered metrics, support, confusion matrices, street performance, illegal proposals, fallbacks and latency are reported. The selected weighted Random Forest is the exact train-only tested artifact, not refitted on train+validation. See [training report](../training-report.md) and [Model Card](../model-card.md).

The earlier pilot cannot estimate general label-noise rates or an accuracy ceiling. Sparse standalone all_in support and simulation/teacher assumptions constrain conclusions. No model playing-strength claim follows. Deployment preparation includes checked local model loading and observation-only inference; browser integration and opponent-play evaluation remain stage 5 work.

## Stage 5 — Deployment integration

Completed local browser integration of the frozen imitation-v1 Random Forest at all three opponent seats. Shared process-local model loading, per-player observations, existing legal decoding, request/version synchronization, public status and controlled runtime-error handling are integrated. Baseline and Teacher remain explicit configuration options; simulator/data-generator defaults remain unchanged.

Deployment validation includes the regression suite, counted HTTP/engine runs, visual browser start/call/check/showdown/next-hand/reset checks, observed control locking/release, and portable-copy loading. See the integration report for measured counts and limits. No training data, splits, selected model bytes or selection metrics were changed. Evaluation of comparative playing strength is deferred to stage 6.

## Stage 6 — Evaluation completed

Independently evaluated the frozen deployed model, unchanged Teacher and rule baselines. Predeclared 12 shared seed blocks × four rotations for A/B/C plus eight × four for mixed D; 100 settled-hand horizon. Separate deck-per-hand and decision RNGs, protected observations, atomic fingerprinted checkpoints and explicit winner/hand-limit/error statuses make evaluation reproducible and auditable.

Executed **176 sessions / 12,601 hands** in **199.16 seconds**: 100 actual tournament finishes, 76 hand limits, zero errors. Main Learned and Teacher means were +4,445.31 and +4,413.17 chips. The paired difference interval crosses zero, so no difference is resolved against rule opponents. The supplementary mixed table suggests a Teacher advantage, with only eight independent blocks. The control's exact zero block means were traced to behavioral/rotation symmetry. Bootstrap resamples complete seed blocks; hands and rotated sessions are not treated as independent trials.

[Evaluation report](../evaluation-report.md) separates observations, plausible explanations and unsupported claims, covers actions/all-ins, conditional tournament wins, positional variation and uncertainty. Label accuracy remains an imitation metric; simulated bankroll performance is opponent/horizon dependent; optimal poker is not demonstrated. Model and Teacher weaknesses are recorded without changing the selected artifact or development splits. Integrity audits, 63 passing tests, API acceptance and a small actual browser flow verify preservation of deployment behavior. Stage 7 is reserved for browser UI/function improvements; none were introduced here.


## Stage 7 — Deployment usability and technical acceptance

Completed a responsive local poker interface with clear legal actions, raise-to sizing, public table/payout details, keyboard focus, reduced motion and controlled reconnect behavior. The deployed frozen Random Forest still drives all three opponents; no modeling, fitting, data changes or revised playing-strength claims occurred.

Acceptance evidence consists of 68 passing Python tests (all 63 earlier tests retained), seven JavaScript tests, actual desktop/mobile-viewport/200%-zoom browser flows, separately labeled engine fixtures, and a tested portable extraction. These checks evaluate usability and integration correctness, not statistical poker strength. All Stage 6 measurements and their uncertainty remain unchanged. See [UI verification report](../ui-report.md). Stage 8 remains final QA and repository publication; no GitHub publication occurred in Stage 7.
