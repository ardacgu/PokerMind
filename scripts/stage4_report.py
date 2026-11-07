"""Render measured experiment artifacts; never trains or selects a model."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
root=Path('models/imitation-v1')
def read(name):return json.loads((root/name).read_text())
selection=read('selection.json');results=read('results.json');validation=read('validation.json');latency=read('latency.json');audit=read('data-audit.json');meta=read('metadata.json');classes=meta['classes'];winner=selection['winner']
text=['# Stage 4 training and evaluation report\n',
'''This experiment measures imitation of the heuristic teacher on simulated data. It does not establish optimal poker decisions or playing strength. Browser integration is deliberately deferred to stage 5. Game rules, the moving button, existing opponents, data and fixed splits are unchanged.

## Predeclared procedure

`experiments/imitation-v1.json` was written before evaluation and copied into the package. Train-only fit: DummyClassifier(prior), six DecisionTreeClassifier configurations and six RandomForestClassifier configurations. Depth/leaf pairs (6,20), (12,10), (20,3), each unweighted and balanced; forests use 200 trees, two workers. Seed 20261107 throughout. Balanced weights derive only from training labels. No preprocessing, imputation, resampling, feature selection or new data. All 54 integer features are validated and loaded in the frozen order using the shared extractor/allowlist; no teacher estimates or future information enter X.

Primary selection: validation legal-filtered Macro-F1 over fold/check/call/small/large. Compute per-class metrics on ALL rows (including all_in targets), then average those five F1 values. Six-class Macro-F1 and accuracy remain reported. Fixed labels are always present; undefined precision/recall/F1 use zero. Exact score ties prefer tree, shallower depth, larger leaves, then no weighting. No search expansion and no train+validation refit.

The selected family finalists, validation results, model hashes and overall winner were saved in `selection.json` BEFORE test performance was computed. `events.json` records phase timestamps. Only the baseline and locked finalists were tested. No post-test parameter, fallback or winner change.

## Data audit and class support

All manifest file hashes and schema/order were verified; session assignments and disjointness checked. Raw protected observations were used to recalculate and verify the feature vectors. No split changed.

| Class | Train | Validation | Test |
| --- | ---: | ---: | ---: |''']
for c in classes:text.append('| '+c+' | '+' | '.join(str(audit['counts'][s].get(c,0)) for s in ('train','validation','test'))+' |')
text.append(f"\nRows: {audit['rows']}; sessions: {audit['sessions']}. All six classes occur in training; the missing-class zero-fill path is nevertheless tested.\n")
text.append('''## Probability adapter

The same adapter is used by all three families. `classes_` maps probabilities into the fixed six-class order; absent classes receive zero. Record raw argmax first; then remove illegal candidates using the existing candidate function and choose maximum remaining probability. Exact ties use fixed class order. If every legal probability is zero, choose check, fold, call, small, large, all_in in that priority among legal candidates; count it as a fallback. No Teacher or Monte Carlo call is involved. No-legal-action observations raise ValueError.

Candidate deduplication and raise-to mapping are unchanged. Short all-in calls are call; clipped raises may retain small/large labels. Adapter legality is externally enforced, not evidence of learned poker rules. Probabilities are neither poker win probabilities nor calibrated confidence estimates.

## All validation candidates

| Candidate | Fit s | Raw F1-5 | Legal F1-5 | Raw F1-6 | Legal F1-6 | Raw acc | Legal acc | Illegal % | Fallback % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |''')
for r in validation:
 v=r['validation'];text.append(f"| {r['id']} | {r['fit_seconds']:.3f} | {v['raw']['macro_f1_five']:.4f} | {v['filtered']['macro_f1_five']:.4f} | {v['raw']['macro_f1_six']:.4f} | {v['filtered']['macro_f1_six']:.4f} | {v['raw']['accuracy']:.4f} | {v['filtered']['accuracy']:.4f} | {100*v['raw_illegal_rate']:.2f} | {100*v['fallback_rate']:.2f} |")
text.append(f"\n**Validation-selected winner: {winner}.** Total measured fit time across 13 estimators: {sum(r['fit_seconds'] for r in validation):.3f} seconds. These are fit times; validation, integrity checks, serialization and reporting add overhead.\n")
text.append('## Finalists: training, validation and locked test\n\n| Model | Split | N | Raw F1-5 | Legal F1-5 | Raw F1-6 | Legal F1-6 | Raw acc | Legal acc | Illegal % | Fallback % |\n| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |')
for name,splits in results.items():
 for split,r in splits.items():
  text.append(f"| {name} | {split} | {r['n']} | {r['raw']['macro_f1_five']:.4f} | {r['filtered']['macro_f1_five']:.4f} | {r['raw']['macro_f1_six']:.4f} | {r['filtered']['macro_f1_six']:.4f} | {r['raw']['accuracy']:.4f} | {r['filtered']['accuracy']:.4f} | {100*r['raw_illegal_rate']:.2f} | {100*r['fallback_rate']:.2f} |")
text.append('## Test class metrics (every class retained)\n')
for name,splits in results.items():
 text.append(f'### {name}\n\n| Class | N | Raw precision | Raw recall | Raw F1 | Legal precision | Legal recall | Legal F1 |\n| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |')
 for c in classes:
  a=splits['test']['raw']['classes'][c];b=splits['test']['filtered']['classes'][c]
  text.append(f"| {c} | {a['support']} | {a['precision']:.4f} | {a['recall']:.4f} | {a['f1']:.4f} | {b['precision']:.4f} | {b['recall']:.4f} | {b['f1']:.4f} |")
text.append('## Test by street\n\n| Model | Street | N | Raw F1-5 | Legal F1-5 | Raw acc | Legal acc |\n| --- | --- | ---: | ---: | ---: | ---: | ---: |')
for name,splits in results.items():
 for street,r in splits['test']['streets'].items():
  text.append(f"| {name} | {street} | {r['n']} | {r['raw']['macro_f1_five']:.4f} | {r['filtered']['macro_f1_five']:.4f} | {r['raw']['accuracy']:.4f} | {r['filtered']['accuracy']:.4f} |")
fig,axs=plt.subplots(3,4,figsize=(23,15),layout='constrained')
for i,(name,splits) in enumerate(results.items()):
 for j,(mode,norm) in enumerate([('raw',False),('raw',True),('filtered',False),('filtered',True)]):
  matrix=np.array(splits['test'][mode]['confusion_normalized' if norm else 'confusion']);ax=axs[i,j]
  ax.imshow(matrix,cmap='Blues',vmin=0,vmax=1 if norm else None);ax.set_xticks(range(6),classes,rotation=45);ax.set_yticks(range(6),classes);ax.set_xlabel('Predicted');ax.set_ylabel('Teacher');ax.set_title(name+'\n'+mode+(' row-normalized' if norm else ' counts'))
  for (y,x),v in np.ndenumerate(matrix):ax.text(x,y,f'{v:.2f}' if norm else str(int(v)),ha='center',va='center',fontsize=8,color='white' if v>matrix.max()*.6 else 'black')
fig.savefig('docs/stage4-confusions.png',dpi=130);plt.close(fig)
text.append('\n![Locked test confusion matrices](stage4-confusions.png)\n\nRows are teacher labels, columns predictions. Zero-support rows normalize to zero. Full precision/recall/support and raw/filtered confusion matrices for train, validation and test, plus all candidate validation metrics and street breakdowns, are in the package JSON files.\n')
records=[json.loads(l) for l in (root/(winner+'-validation-predictions.jsonl')).open()]
obs={r['id']:r['observation'] for r in map(json.loads,Path('data/main-v1/raw.jsonl').open())}
examples=[]
for agreement in (True,False):
 examples.extend([r for r in records if (r['label']==r['teacher'])==agreement][:2])
(root/'validation-examples.json').write_text(json.dumps([dict(prediction=r,observation=obs[r['id']]) for r in examples],indent=2))
text.append('## Actual validation examples\n\n| Record | Street | Own cards | Teacher | Raw | Legal | Concrete action |\n| --- | --- | --- | --- | --- | --- | --- |')
for r in examples:text.append(f"| {r['id']} | {r['street']} | {' '.join(obs[r['id']]['players'][obs[r['id']]['viewer']]['cards'])} | {r['teacher']} | {r['raw']} | {r['label']} | {r['executed']} |")
a=results[winner]['train']['filtered'];b=results[winner]['validation']['filtered'];t=results[winner]['test']['filtered'];base=results['dummy']['test']['filtered']
text.append(f'''\n## Timing, interpretation and limits

Winner train vs validation F1-5: {a['macro_f1_five']:.4f} vs {b['macro_f1_five']:.4f}; gap {a['macro_f1_five']-b['macro_f1_five']:.4f}. This is a measured indication of generalization loss/possible overfitting, not a causal diagnosis. Locked test F1-5: {t['macro_f1_five']:.4f}, compared with prior baseline {base['macro_f1_five']:.4f}. The winner was NOT switched after seeing test.

Inference: {latency['n']} sequential validation observations, {latency['warmup']} warmup calls excluded, mean **{1000*latency['mean_seconds']:.3f} ms**, p95 **{1000*latency['p95_seconds']:.3f} ms**. Includes feature extraction, predict_proba and legal adapter. Model loading separately measured at **{1000*latency['load_seconds']:.3f} ms**, in an already initialized Python process (not cold application startup). Environment: {latency['environment']}, {latency['processor']}, Python {meta['python']}; libraries {meta['versions']}. No direct speedup claim against earlier Teacher times: workloads and conditions differ.

Only 21 independent all_in-class targets exist: 15 train, 2 validation, 4 test. Per-class test results are descriptive, not statistically robust. The six separate all-in scenarios are functional fixtures, not representative performance evidence, and were not used for model selection or measured imitation scores. Label noise and policy-dependent simulated states limit interpretation. The 41 boundary-enriched pilot states cannot estimate population error or an accuracy ceiling. Class probabilities are uncalibrated imitation scores, not poker equities. No opponent-play evaluation or browser integration was performed.

## Reproduction and evidence

See Model Card and README for exact commands. Packages use trusted-local joblib serialization; do not load untrusted pickle/joblib files. Loading checks artifact hash, sklearn version, feature order/schema and class/action mapping. Stored models are the exact train-only finalists, never refitted on train+validation. Reload equality and teacher-free inference are tested. `events.json`, `selection.json`, `metadata.json`, `validation.json`, `results.json`, prediction JSONL, `latency.json` and `data-audit.json` preserve machine-readable evidence. The original dataset hashes remain unchanged.

scikit-learn documentation: [RandomForestClassifier](https://scikit-learn.org/1.7/modules/generated/sklearn.ensemble.RandomForestClassifier.html), [model persistence](https://scikit-learn.org/1.7/model_persistence.html). No learned preprocessing is needed for these validated integer tree inputs.
''')
Path('docs/training-report.md').write_text('\n'.join(text))
print(json.dumps(dict(winner=winner,test={n:dict(f1=r['test']['filtered']['macro_f1_five'],accuracy=r['test']['filtered']['accuracy'],illegal=r['test']['raw_illegal_rate'],fallback=r['test']['fallback_rate']) for n,r in results.items()},latency=latency,total_fit_seconds=sum(r['fit_seconds'] for r in validation)),indent=2))
