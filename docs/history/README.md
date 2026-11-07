# Historical evidence index

The top-level README, current CRISP-DM report, results summary and reproduction guide describe the final release. Earlier reports are retained as **stage-specific evidence**, not claims that their future plans are still outstanding.

| Stage | Original subject | Evidence |
| --- | --- | --- |
| 1 | Poker engine and initial browser | [Test report](../test-report.md) |
| 2 | Monte Carlo Teacher | [Teacher](../teacher.md), [pilot report](../stage2-report.md) |
| 3 | Simulated dataset and quality | [Data quality](../data-quality.md), [schema](../data-schema.md) |
| 4 | Locked supervised comparison | [Training report](../training-report.md), model selection/results files |
| 5 | Three learned browser opponents | [Integration report](../integration-report.md) |
| 6 | Independent playing evaluation | [Evaluation report](../evaluation-report.md), original checkpoints and figures |
| 7 | Responsive interface | [UI report](../ui-report.md), screenshots and verification evidence |
| 8 | Submission, fresh installation and publication | [Final report](../final-report.md) |

Stage 7 README, architecture and CRISP-DM snapshots are retained here for development history; relative links were adjusted to their archive location. The original Stage 6 source and documentation are preserved in `evaluations/stage6-runtime.zip`. Its runtime fingerprint remains distinct from the current interface.

Historical scripts are intentionally retained: they reconstruct experiments, audits and figures. They are not unused application dependencies. No model/data/pilot/session evidence was removed merely because an export duplicates checkpoint information.

Ten historical verification files had personal machine prefixes replaced by `<PROJECT_ROOT>`. The public redaction ledger records original and released hashes. Raw local server `.log` files and scratch environments remain excluded; corresponding counters, API states and reports provide public acceptance evidence. Historical manifests retain their original hashes rather than being rewritten to imply unchanged documentation.
