"""Read released data, audit splits/duplicates and create static quality charts."""
import json,hashlib
from pathlib import Path
from collections import Counter,defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path('data/main-v1');m=json.loads((root/'manifest.json').read_text());pilot=json.loads(Path('data/pilot-v1/manifest.json').read_text());noise=json.loads(Path('data/pilot-v1/stability.json').read_text())
labels=defaultdict(set);split_ids={};copied=0;seen={}
for line in (root/'raw.jsonl').open():
 r=json.loads(line);h=json.dumps(r['features'],sort_keys=True);labels[h].add(r['label'])
 core=json.dumps({k:v for k,v in r.items() if k not in ('id','session')},sort_keys=True)
 if core in seen:
  copied+=1
  assert r['session'] not in seen[core], 'Same-session duplicate snapshot'
 seen.setdefault(core,set()).add(r['session'])
for split in ('train','validation','test'):
 split_ids[split]={json.loads(line)['session'] for line in (root/(split+'.jsonl')).open()}
assert all(not a&b for i,a in enumerate(split_ids.values()) for b in list(split_ids.values())[i+1:])
assert m['accepted']>=20000 and m['duplicate_ids']==0
start=(root/'generation.json').stat().st_mtime;end=max(p.stat().st_mtime for p in (root/'sessions').glob('*.json'))
audit=dict(accepted=m['accepted'],groups_disjoint=True,full_raw_copies_excluding_ids=copied,
           conflicting_feature_patterns=sum(len(v)>1 for v in labels.values()),wall_seconds=end-start,
           summed_session_seconds=m['seconds'],valid_schema_rows=m['accepted'])
Path('docs/stage3-audit.json').write_text(json.dumps(audit,indent=2))
fig,axs=plt.subplots(2,2,figsize=(12,8),layout='constrained')
for ax,key,title in zip(axs.flat,['label','street','live','stack_band'],['Teacher action classes','Betting streets','Live players','Acting stack (chips)']):
 order={'label':['fold','check','call','small','large','all_in'],'street':['Preflop','Flop','Turn','River'],'live':['2','3','4'],'stack_band':['<200','200-999','1000-2999','3000+']}[key]
 counts={k:m['counts'][key].get(k,0) for k in order};bars=ax.bar(list(counts),list(counts.values()),color='#287550');ax.bar_label(bars,fontsize=9);ax.set_title(title);ax.set_ylabel('Decisions');ax.spines[['top','right']].set_visible(False)
fig.suptitle('PokerMind · simulated main dataset v1',fontsize=17)
fig.savefig('docs/stage3-distributions.png',dpi=150);fig.savefig('docs/stage3-distributions.svg');plt.close(fig)

def table(key):
 counts=m['counts'][key]
 return '| Value | Decisions | Share |\n| --- | ---: | ---: |\n'+''.join(f'| {k} | {v:,} | {v/m["accepted"]:.2%} |\n' for k,v in counts.items())
summary=f'''# Stage 3 data quality report

All data are simulated. Labels are decisions of our self-developed heuristic Teacher, not proven optimal poker moves. The future model will imitate this teacher. **No model has been trained or shown to play well.**

## Actual release

Generated **{m['generated']:,}** Teacher decisions; accepted **{m['accepted']:,}** from **{m['sessions']} independent sessions**. Excluded **{m['excluded']}**; no fallback or invalid row was silently used as a target. All 8,000 chips remained conserved during generation. Every saved session ends at a completed hand, either a winner or the explicit 12-hand limit. Even sessions contain four Teachers; odd sessions contain two rotating Teachers and two deterministic RuleBots. All main labels use teacher-2.0.0, 128 samples and the configuration in the manifest.

Main generation wall duration from first generation config write to final atomic checkpoint: **{audit['wall_seconds']:.2f} seconds**. Summed worker session times: **{m['seconds']:.2f} seconds**, a different quantity from wall duration. Four worker processes were used. Checkpoint and final export overhead are not included in summed worker time.

The pilot accepted {pilot['accepted']} decisions from {pilot['sessions']} sessions (target approximately 500; completed sessions caused overshoot). Its summed worker runtime was {pilot['seconds']:.2f} seconds: {pilot['accepted']/pilot['seconds']:.1f} decisions per worker-second, or an ideal four-worker estimate of {20000*pilot['seconds']/pilot['accepted']/4:.0f} seconds for 20,000 rows before overhead/uneven batches. The initial user-facing estimate was three to four minutes; actual wall duration above is authoritative. Main generation began only after pilot schema checks and the label-stability study.

## Frozen splits

{table('split')}

Group counts: {', '.join(f'{k}={len(v)}' for k,v in split_ids.items())}. SHA-256 session-ID ordering determines approximately 70/15/15 groups without labels or outcomes. `groups.json` is frozen. All observations from all hands and actors of each session stay together. Card seeds are unique; pilot seeds 900000+ and main seeds 100000+ do not overlap. No variants of a source game family cross splits. No validation/test balancing was performed.

## Action and situation coverage

{table('label')}

{table('street')}

{table('live')}

{table('position')}

Position is clockwise fixed-seat distance from dealer, not compressed live-player position.

{table('seat')}

{table('stack_band')}

![Action and situation distributions](stage3-distributions.png)

`call` includes short all-in calls. `small`/`large` may become all-in raises after clipping, so class `all_in` alone understates all-in activity. Pre-decision all-in-call flags: {m['counts']['all_in_call']}; short-call flags: {m['counts']['short_call']}; executed all-in raises: {m['counts']['all_in_raise']}. Eligible-layer distribution: {m['counts']['eligible_layers']}. These are frozen public contribution layers, not necessarily final settled side pots. Six separate targeted legal scenarios cover short all-in calls and a certain quads shove; they were NOT merged into natural train/validation/test data. Rare classes remain rare.

## Pilot-only label stability

Selected **{noise['selected']}** pilot observations by street/action strata: one early example and one nearest heuristic boundary per populated stratum, deduplicated. Each was reevaluated with three independent seeds at both 128 and 512 samples. Selection and full per-row outcomes are in `data/pilot-v1/stability.json`. No held-out main test observations were used for configuration selection.

At 128 samples, {noise['summary']['128']['unstable']} / {noise['selected']} observations changed labels across the three reevaluations; {noise['summary']['128']['original_disagreements']} / 123 reevaluations disagreed with the original pilot label. At 512 samples, these figures were {noise['summary']['512']['unstable']} / {noise['selected']} and {noise['summary']['512']['original_disagreements']} / 123. Study runtime: {noise['seconds']:.2f} seconds. This boundary-enriched sample estimates sensitivity, NOT population-wide noise. Higher-sample labels are not ground truth either.

Decision: freeze 128 samples for this first dataset, preserving the existing teacher behavior and practical generation cost. The remaining sampling noise is intentional and documented; boundary cases are retained. No different sample configuration is mixed into the main targets. Classification accuracy against this stochastic teacher has a noise ceiling; stage 4 must not equate disagreement with bad poker play.

## Full-data audit and executed checks

The full released raw dataset was re-read and every feature recalculated from its observation. Candidate masks and concrete action mapping were reconstructed. Every label had to be legal and agree with the diagnostic decision; paid chips, actor identity, hand index and public chip totals were checked. Every accepted record had to have fallback=false. All three model files were re-read through the strict allowlisted loader. File hashes were verified with the validate command.

- Valid exported rows: {m['accepted']:,}; missing/invalid/inconsistent accepted feature values: **0**.
- Duplicate IDs: **0**; repeated card-seed families: **0**; cross-split session overlap: **0**.
- Exact repeated raw snapshots excluding IDs/session: **{copied}**. Independently recurring feature vectors: **{m['duplicate_feature_rows']}** extra rows; feature patterns shared across splits: **{m['cross_split_feature_patterns']}**. Conflicting-label feature patterns: **{audit['conflicting_feature_patterns']}**. All {copied} exact repeated snapshots were traced to distinct independently seeded sessions (see stage3-repeat-audit.json); accidental export copies: 0. These are recurring initial situations, not repeated exports. Legitimate recurrence is retained, not removed from test.
- Fallback exclusions: **{m['excluded']}**. Any fallback would be logged and omitted from accepted targets; unexpected engine errors abort the session instead of producing a label.
- Regression suite: **40 passed**, including all previous 36. New tests cover reproducibility, checkpoint resume without duplicate exports, observation snapshots, feature isolation, strict loading, legal decoding, short all-in-call mapping and disjoint groups. Existing Starlette/httpx deprecation warning remains.
- No training, fitted scaler, fitted feature selector, class balancing, model evaluation or new browser UI test was performed.

## Reproduction and stage 4 limits

See [schema and commands](data-schema.md). Main artifacts: `data/main-v1/manifest.json`, `schema.json`, `groups.json`, raw/diagnostic JSONL and the three model files. Manifest records configuration, independent seeds, source hashes, versions, groups, exact counts and artifact hashes. `examples.jsonl` is a documentation copy, never an extra training source. Original stage 1/2 evidence is preserved.

Uniform opponent ranges and a frozen-contribution/no-future-betting counterfactual limit teacher quality. The main data overrepresent heads-up situations as players bust; fixed blinds and 12-hand sessions constrain coverage. Sampling noise, rare all-in class, class imbalance and policy-dependent state distribution matter in stage 4. Fit transformations only on train; use validation for choices and preserve test for final evaluation. Do not claim strength from imitation accuracy. Keep targeted scenario scores separate from natural held-out scores.
'''
Path('docs/data-quality.md').write_text(summary)
print(json.dumps(audit,indent=2))
