# CRISP-DM — complete PokerMind development record

This is the current account of all six phases. Earlier stage snapshots are retained under [history](history/README.md). The objective is an explainable, reproducible school project, not a claim of optimal poker.

## 1. Business Understanding

**Problem:** poker combines incomplete information, chance and sequential decisions. We want to build a playable local game and study whether a learned policy can imitate a self-developed decision maker and perform against controlled opponents.

**Scope and success criteria:** one human plus three computer opponents; correct No-Limit Hold'em through PokerKit; clear information boundaries; reproducible simulated data and experiments; a documented baseline/model comparison; separate imitation and playing-performance measures; an accessible local interface and a reproducible submission by 18 December 2026. Real money, production multiplayer, optimal-strategy proofs and unrestricted reinforcement learning are outside scope.

**Evidence:** [architecture](architecture.md), [Model Card](model-card.md), [UI report](ui-report.md).

## 2. Data Understanding

The self-developed TeacherAgent estimates eligible showdown pot shares using **128 Monte Carlo samples** and applies programmed decision thresholds. Samples use only permitted observations and an independent random stream, never the real future deck. Uniform unknown hands and no future betting are explicit approximations.

The natural main dataset contains **20,024 accepted decisions in 252 independent seeded sessions**. Even-index sessions have four Teachers; odd-index sessions have two rotating Teachers and two RuleBots. Each session keeps stacks across at most 12 completed hands or ends at a winner. All Teacher decisions are collected. Pilot data and six targeted rare-action scenarios are separate populations and do not enter the main train/test scores.

Raw records contain the protected observation, extracted features, legal candidates, Teacher label and executed action. IDs, seeds, provenance and Teacher sampling diagnostics support auditing; they are not predictive inputs. Labels mean the Teacher's decision, not an independently proven best action.

Quality analysis found no invalid accepted rows, duplicate IDs or cross-split session overlap. It distinguished 10 genuinely recurring snapshots in independent sessions from accidental copied exports. There were 32 additional repeated feature-vector rows, 15 feature patterns shared across splits and eight conflicting-label patterns; these are documented, not silently removed from test.

**Evidence:** [data quality and distributions](data-quality.md), `data/main-v1/manifest.json`, `data/pilot-v1/stability.json`.

## 3. Data Preparation

An explicit ordered allowlist contains **54 integer features**: own-card ranks/suits, public board slots, current hand category, street, position, public stack/bet/contribution information and legal action masks/bounds. Missing future board slots use a documented zero sentinel, not future-card information. Unknown raise bounds use −1. Hidden opponent cards, Monte Carlo estimates, labels, random seeds, winners and future stacks are excluded.

The shared extractor is used both offline and in live inference. The strict loader rejects unknown keys or malformed values. Every raw observation was reprocessed to verify its saved features, legal candidates, target/action mapping and chip accounting. No fitted imputer, scaler or feature selector is needed for these validated tree inputs.

Session-ID hash ordering assigns approximately 70/15/15 groups without labels/outcomes: **176/38/38 sessions**, containing **14,156/2,811/3,057 decisions**. Every hand and player from one session stays in the same group. `groups.json` freezes the assignment. Pilot and main seeds do not overlap; no oversampling or test balancing was performed. Legitimate recurrence from independent sessions remains visible.

Class imbalance is severe: check 7,686; call 4,448; small 3,411; fold 2,537; large 1,921; standalone all_in only 21. Duplicate concrete candidates retain the earlier canonical label: an all-in call is call, and a clipped raise can be small/large. Thus actual all-in behavior must also be counted from chip movement.

A boundary-enriched pilot rechecked 41 states with three seeds at 128 and 512 samples. At 128 samples, 11 states changed labels across repeats; this is evidence of sampling sensitivity, **not a population noise rate or accuracy ceiling**. Higher-sample results are not ground truth. The existing 128-sample Teacher was frozen, and no held-out data were used to tune it.

**Evidence:** [schema and splitting contract](data-schema.md), `data/main-v1/schema.json`, `groups.json`, [audit](stage3-audit.json).

## 4. Modeling

The predeclared search trained DummyClassifier(prior), six DecisionTreeClassifiers and six RandomForestClassifiers. Tree depth/minimum-leaf pairs were (6,20), (12,10), (20,3), each with no weighting or balanced class weights. Forests contain 200 trees and use a fixed seed, with two inference/training workers. Class weights derive only from training labels.

scikit-learn learns the internal splits and leaf probabilities from data; the project does not hand-author 200 trees. Each forest tree is trained on a bootstrap sample and considers random feature subsets at splits. Predicted class probabilities are aggregated across trees. Our contribution is the Teacher, generation/feature pipeline, legal action mapping, predeclared comparison, verification and integration.

Validation legal-filtered Macro-F1 averaged over five non-all_in classes chose the winner. All class metrics are computed on all rows; six-class Macro-F1 and rare-class support remain reported. The rare class was not removed from evaluation. Exact tie rules were predeclared. The selected forest has depth 20, minimum leaf size 3 and balanced class weights. Finalists and hashes were locked **before** test evaluation; there was no train+validation refit or post-test reselection.

**Evidence:** [training report](training-report.md), `experiments/imitation-v1.json`, `models/imitation-v1/selection.json` and `events.json`.

## 5. Evaluation

**Imitation:** on 3,057 held-out decisions, legal-filtered accuracy is 59.63% for the prior baseline, 76.55% for the selected tree and **78.70% for the selected forest**. Forest five-class Macro-F1 is 0.7360; six-class Macro-F1 is 0.6133. Four standalone all_in test targets were all missed by every finalist. The forest's train/validation five-class F1 gap (0.9485 versus 0.7294) indicates generalization loss; it does not identify its cause. An external legality adapter corrects illegal class proposals; this is not proof that the forest learned poker rules.

**Playing performance:** 12 seed blocks × four seat rotations for each main lineup A (Learned against rules), B (Teacher against rules), C (marked rule against rules); eight × four for mixed D. Each session stops at a real tournament winner or 100 settled hands. Deck seeds per hand and independent policy randomness prevent strategy sampling from consuming the deal stream. Shared seeds help pairing, but divergent survivors/actions mean identical complete counterfactual trajectories are not guaranteed.

Actually completed: **176 sessions, 12,601 hands**, 100 regular tournament finishes, 76 capped sessions, zero errors. Mean net chips: Learned A **+4,445.31**, Teacher B **+4,413.17**. Their paired difference is **+32.15 [−551.87, +631.24]**, an approximate 95% bootstrap interval over complete seed blocks. No difference was resolved; equality was not demonstrated. C's exact zero block means result from verified behavioral/rotation symmetry, not certainty for every rule-opponent experiment. Mixed D suggests a Teacher advantage, but has only eight blocks and is exploratory.

Hands, rotated sessions and players in a table are dependent. Uncertainty is not calculated as though 12,601 hands were independent trials. Hand limits are not wins; completed-tournament win fractions are duration-selected. Chip changes are bounded tournament outcomes, not ordinary cashgame winrates. Neither label agreement nor the measured bankroll results proves optimal strategy, general superiority or exploitability bounds.

**Evidence:** [results summary](results-summary.md), [full evaluation](evaluation-report.md), `evaluations/stage6-v1/summary.json`, manifest and session checkpoints.

## 6. Deployment

Three separate LearnedAgent instances share one validated, read-only saved model per server process. Each gets its own protected observation and counters. The same feature extractor and legal candidate mapping used offline remain active. No Teacher simulations or online fitting occur during normal learned-mode play.

FastAPI serializes commands with a lock and monotonic state version; PokerKit validates every action. The browser receives only a human-safe view and public presentation details. A stale command is rejected; uncertain requests refresh state rather than automatically repeating actions. Unexpected inference errors halt the table visibly. The active mode/version is server-provided.

Stage 7 added a responsive table, readable cards, public action/payout display, legal sizing controls, keyboard focus, reduced motion and clear end states. Stage 8 consolidates English documentation, publication hygiene, a fresh isolated installation, lightweight CI and the portable release. No model, Teacher, dataset, split, rule or scientific result changed during either finalization stage.

**Evidence:** [integration](integration-report.md), [UI acceptance](ui-report.md), [final report](final-report.md), [reproduction guide](reproducibility.md). Remaining limits include a single in-memory table, fixed blinds, no persistence, limited device/accessibility coverage and an open owner license decision.
