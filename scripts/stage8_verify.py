"""Read-only release checks: immutable artifacts, scientific claims and document links."""
from hashlib import sha256
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def verify():
    frozen = json.loads((ROOT/'docs/stage8/frozen-artifacts.json').read_text())
    for name, digest in frozen['files'].items():
        assert sha256((ROOT/name).read_bytes()).hexdigest() == digest, name
    manifest = json.loads((ROOT/'data/main-v1/manifest.json').read_text())
    metadata = json.loads((ROOT/'models/imitation-v1/metadata.json').read_text())
    results = json.loads((ROOT/'models/imitation-v1/results.json').read_text())
    evaluation = json.loads((ROOT/'evaluations/stage6-v1/manifest.json').read_text())
    assert manifest['accepted'] == 20024
    assert len(metadata['features']) == 54
    assert evaluation['recorded_sessions'] == 176 and evaluation['completed_hands'] == 12601
    score = results['forest-d20-l3-balanced']['test']['filtered']
    assert round(score['accuracy'] * 100, 2) == 78.70
    assert score['classes']['all_in']['support'] == 4
    # Current submission documents; historical reports describe their original stage.
    docs = ['README.md', 'docs/crisp-dm.md', 'docs/results-summary.md',
            'docs/reproducibility.md',
            'docs/final-report.md', 'docs/abschlussbericht.md', 'docs/third-party-notices.md']
    for name in docs:
        path = ROOT/name
        assert path.is_file(), name
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text()):
            if target.startswith(('https://', 'http://', '#')): continue
            target = target.split('#')[0]
            assert (path.parent/target).exists(), (name, target)
    print(json.dumps({'frozen_files_verified': len(frozen['files']),
                      'teacher_decisions': 20024, 'features': 54,
                      'evaluation_sessions': 176, 'evaluation_hands': 12601,
                      'current_document_links': 'passed'}, indent=2))


if __name__ == '__main__': verify()
