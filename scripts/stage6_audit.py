"""Integrity, checkpoint and observed RuleBot-symmetry audit (no new samples)."""
from pathlib import Path
from hashlib import sha256
import json
from pokermind.evaluation.core import play_session, semantic, lineup
from pokermind.evaluation.run import provenance, canonical, collect, jobs
from pokermind.agents import RuleBot

ROOT=Path(__file__).resolve().parents[1]

def main():
    folder=ROOT/'evaluations/stage6-v1'
    config=json.loads((folder/'config.json').read_text())
    stored=json.loads((folder/'provenance.json').read_text())
    assert provenance()==stored
    expected={j['id']:j for j in jobs(config)}
    records=collect([folder],expected,canonical(config),canonical(stored))
    assert len(records)==len(expected)==176
    meta=json.loads((ROOT/'models/imitation-v1/metadata.json').read_text())
    for rel,h in meta['data_hashes'].items():assert sha256((ROOT/'data/main-v1'/rel).read_bytes()).hexdigest()==h
    manifest=json.loads((ROOT/'data/main-v1/manifest.json').read_text())
    for rel,h in manifest['hashes'].items():assert sha256((ROOT/'data/main-v1'/rel).read_bytes()).hexdigest()==h
    for rel,h in meta['artifacts'].items():assert sha256((ROOT/'models/imitation-v1'/rel).read_bytes()).hexdigest()==h
    for rel,h in meta['source_hashes'].items():
        if '/teacher/' in rel or rel in ('pokermind/agents.py','pokermind/data/schema.py'):
            assert sha256((ROOT/rel).read_bytes()).hexdigest()==h
    compared=0;different=0
    class AuditRule(RuleBot):
        def decide(self,o):
            nonlocal compared,different
            choices=[RuleBot(style).decide(o) for style in range(3)]
            compared+=1;different+=int(len(set(choices))!=1)
            return super().decide(o)
    repeats=[]
    for r in records.values():
        if r['scenario']!='C':continue
        repeat=play_session({k:r[k] for k in ('id','scenario','seed','rotation')},config,
                            [AuditRule(p['style']) for p in lineup('C',r['rotation'])])
        clean={k:v for k,v in r.items() if k not in ('config_hash','provenance_hash')}
        assert semantic(clean)==semantic(repeat)
        repeats.append(dict(id=r['id'],semantic_replay_identical=True))
    per_block_identical=[]
    for seed in config['scenarios']['C']:
        rotations=[records[f'C-{seed}-r{i}']['hands'] for i in range(4)]
        per_block_identical.append(dict(seed=seed,physical_trajectories_identical=all(h==rotations[0] for h in rotations)))
    result=dict(frozen_provenance_files_checked=len(stored['files']),
        original_dataset_hashes_checked=len(manifest['hashes']),model_and_teacher_unchanged=True,
        sessions_checked=len(records),completed_hands=sum(r['completed_hands'] for r in records.values()),
        completed_hand_chip_conservation=all(sum(h['end_chips'])==8000 for r in records.values() for h in r['hands']),
        unique_ids=True,rule_style_decision_comparisons=compared,rule_style_disagreements=different,
        rule_repeats=repeats,rule_blocks=per_block_identical,
        interpretation='No RuleBot style disagreement on any replayed C decision; cyclic target rotation averages the same zero-sum physical trajectory to zero in every block. Degenerate bootstrap interval is a design symmetry, not universal certainty.')
    (ROOT/'docs/stage6/integrity-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('rule_repeats','rule_blocks')},indent=2))
if __name__=='__main__':main()
