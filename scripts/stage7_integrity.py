"""Verify frozen development artifacts and retain Stage 6 provenance across UI changes."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]

def verify():
    before = json.loads((ROOT/'docs/stage7/before-hashes.json').read_text())
    changed = [name for name, digest in before.items()
               if not (ROOT/name).is_file() or sha256((ROOT/name).read_bytes()).hexdigest() != digest]
    allowed = {'pokermind/server.py', 'pokermind/static/index.html',
               'pokermind/static/app.js', 'pokermind/static/style.css'}
    assert set(changed) <= allowed, changed
    frozen = json.loads((ROOT/'evaluations/stage6-v1/provenance.json').read_text())['files']
    archived = []
    with ZipFile(ROOT/'evaluations/stage6-runtime.zip') as archive:
        assert archive.testzip() is None
        for name, digest in frozen.items():
            data = (ROOT/name).read_bytes()
            if sha256(data).hexdigest() != digest:
                data = archive.read(name); archived.append(name)
            assert sha256(data).hexdigest() == digest, name
    result = dict(preexisting_files_checked=len(before), unchanged=len(before)-len(changed),
                  authorized_changes=changed, categories=dict(Counter(n.split('/')[0] for n in before)),
                  stage6_provenance_files_verified=len(frozen), original_bytes_from_archive=archived,
                  model_teacher_rules_data_splits_evaluation_unchanged=True)
    (ROOT/'docs/stage7/integrity-check.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))

if __name__ == '__main__': verify()
