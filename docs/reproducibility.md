# Reproduction and preservation guide

Use Python 3.11 with `requirements.txt`; recorded scientific runtime: Python 3.11.9, PokerKit 0.7.7, scikit-learn 1.7.2, NumPy 2.4.6, SciPy 1.17.1, joblib 1.5.2. Install the optional `requirements-report.txt` only for plotting. Normal play does not need Node; UI tests use Node 24.15.0.

Run commands from the project root with the virtual environment activated. Never overwrite delivered `main-v1`, `imitation-v1` or `stage6-v1` artifacts. No training or full playing evaluation is needed to start the application.

## Read-only delivered-artifact checks

```bash
python -m pip check
python -m pytest -q
node --test tests/ui.test.mjs
python scripts/stage8_verify.py
python -m pokermind.data.pipeline validate --output data/main-v1
python -m pokermind.learning.evaluate_saved --model models/imitation-v1 --data data/main-v1
python -m pokermind.learning.inference --model models/imitation-v1 \
  --observation models/imitation-v1/example-observation.json
```

`evaluate_saved` loads the locked finalists and compares held-out labels; it does not fit or reselect. Its stdout can be redirected to a new file under `work/`. The validation command checks data, not the strength of the Teacher.

## Independent data reproduction

The main generator uses separate card/Teacher seeds, 12-hand sessions, 128 samples and batches of four completed sessions. Retain four workers to reproduce the original target overshoot. Data/Teacher/schema sources are unchanged.

```bash
python -m pokermind.data.pipeline generate --output work/main-reproduction \
  --target 20000 --base 100000 --hands 12 --samples 128 --workers 4
python -m pokermind.data.pipeline export --output work/main-reproduction
python -m pokermind.data.pipeline validate --output work/main-reproduction
```

Re-running the same command resumes that new directory when its configuration/runtime fingerprint matches. The original pilot used base 900000, target 500 and eight complete sessions; its stability study is separate from the main split. Preserve all decisions of each session together. Do not mix targeted scenarios with natural test data.

## Independent training reproduction

This is optional, computational work and creates **new artifacts**, not a replacement for the delivered forest. It was not executed during finalization.

```bash
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 VECLIB_MAXIMUM_THREADS=2 \
python -m pokermind.learning.experiment --data data/main-v1 \
  --config experiments/imitation-v1.json --output work/imitation-reproduction
```

The experiment refuses a nonempty model output. It performs the predeclared train/validation procedure, locks finalists and then tests. The original experiment/selection/results remain authoritative; cross-platform bitwise floating-point identity is not promised.

## Playing evaluation with the original Stage 6 runtime

Stage 6 provenance hashes included its then-current server/static files. Those files changed in Stage 7, while rules, strategies, data and model stayed unchanged. Do not bypass the guard or rewrite the old fingerprint. Reconstruct the original source in a fresh directory:

```bash
mkdir -p work/stage6-replay
python -m zipfile -e evaluations/stage6-runtime.zip work/stage6-replay
cp -R models data experiments work/stage6-replay/
cd work/stage6-replay
# Keep using the activated Python environment from the main project.
python -m pokermind.evaluation.run --config experiments/evaluation-v1.json \
  --output evaluations/reproduction --workers 4
```

Re-run the same command to resume without duplicate sessions. Output remains inside the reconstructed directory. The original main plan has 176 sessions and a 100-hand cap; an evaluation pilot configuration is also supplied. For a new experiment on the current runtime, use a new output directory and report the changed fingerprint explicitly.

## Figures and historical evidence

Delivered PNG/SVG figures are already available. Stage-specific report scripts regenerate summaries/figures and can write outputs, so use a **scratch copy** for regeneration. Install `requirements-report.txt` there. Do not regenerate over the original scientific evidence during submission preparation.

Historical stage reports are dated development evidence. Earlier statements such as “no model trained” describe that stage, not the current release. [History index](history/README.md) identifies current replacements. Some test transcripts contained a machine-specific project prefix; public copies use `<PROJECT_ROOT>`, with original/published SHA-256 values in [redactions.json](stage8/redactions.json). Local originals remain outside the published tree. Old evidence manifests still refer to original bytes and must not be silently described as hashes of edited documents. Scientific artifact hashes remain unchanged.

## Packaging

```bash
python scripts/stage8_verify.py
# For maintainers: stage the reviewed release files before this index audit.
python scripts/publication_audit.py
python scripts/stage8_package.py
```

The portable archive includes application sources, the selected model, data, scientific evidence, docs and tests. It excludes virtual environments, Git internals, scratch files, local logs and other project ZIPs. The only embedded archive is the original Stage 6 runtime needed for provenance. CRC, unique paths, every member's bytes and a separate SHA-256 file are checked. Recreate `.venv` after extraction; never copy a virtual environment between machines.
