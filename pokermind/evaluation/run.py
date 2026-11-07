"""Run/resume/merge immutable evaluation checkpoints; no training code."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
import json
import multiprocessing
import os
from pathlib import Path
import platform
from time import perf_counter
from .core import jobs, play_session, semantic
from ..learning.learned import PROJECT_ROOT


def digest(path): return sha256(path.read_bytes()).hexdigest()
def canonical(value): return sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
    temp.replace(path)


def provenance():
    paths = [p for folder in ('pokermind', 'models/imitation-v1', 'data/main-v1', 'data/scenarios-v1')
             for p in (PROJECT_ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    return dict(files={str(p.relative_to(PROJECT_ROOT)):digest(p) for p in sorted(paths)},
                python=platform.python_version(), versions={k:version(k) for k in
                ('pokerkit','numpy','scikit-learn','joblib','scipy')})


def validate_config(config):
    if type(config['max_hands']) is not int or config['max_hands'] < 1: raise ValueError('Invalid hand limit')
    if not config['scenarios'] or not set(config['scenarios']) <= set('ABCD'): raise ValueError('Invalid scenarios')
    for seeds in config['scenarios'].values():
        if not seeds or len(set(seeds)) != len(seeds) or any(type(s) is not int for s in seeds):
            raise ValueError('Invalid or duplicate seeds')
    from dataclasses import asdict
    from ..teacher import TeacherConfig
    if config['teacher_config'] != asdict(TeacherConfig()): raise ValueError('Frozen Teacher configuration required')
    if config['model'] != 'models/imitation-v1': raise ValueError('Frozen selected model required')


@contextmanager
def lock_output(output):
    output.mkdir(parents=True, exist_ok=True)
    # Kernel-released lock also survives interruption; no stale PID lock removal.
    import fcntl
    with (output/'.run.lock').open('a') as lock:
        try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: raise RuntimeError('Evaluation directory is already being written') from None
        try: yield
        finally: fcntl.flock(lock, fcntl.LOCK_UN)


def accept(record, expected, config_hash, provenance_hash):
    if record['id'] not in expected: raise ValueError('Unknown checkpoint session')
    if any(record[k] != v for k,v in expected[record['id']].items()): raise ValueError('Session identity mismatch')
    if record.get('config_hash') != config_hash or record.get('provenance_hash') != provenance_hash:
        raise ValueError('Checkpoint configuration/source mismatch')
    if record['status'] not in ('error','hand_limit','tournament_complete'): raise ValueError('Invalid status')
    if record['status'] != 'error':
        assert sum(p['end_chips'] for p in record['players']) == 8000
        assert len(record['hands']) == record['completed_hands']
        assert sum(p['tournament_win'] for p in record['players']) == int(record['status']=='tournament_complete')


def collect(directories, expected, config_hash, provenance_hash):
    records = {}
    for directory in directories:
        for path in sorted((Path(directory)/'sessions').glob('*.json')):
            record = json.loads(path.read_text()); accept(record, expected, config_hash, provenance_hash)
            key = record['id']
            if key in records and semantic(records[key]) != semantic(record):
                raise ValueError('Conflicting duplicate session: '+key)
            records.setdefault(key, record)
    return records


def run(config, output, workers=4, merge=()):
    validate_config(config)
    output = Path(output)
    with lock_output(output):
        start = perf_counter(); started = datetime.now(timezone.utc).isoformat()
        source = provenance(); ch = canonical(config); ph = canonical(source)
        if (output/'config.json').exists() and json.loads((output/'config.json').read_text()) != config:
            raise ValueError('Existing configuration differs')
        if (output/'provenance.json').exists() and json.loads((output/'provenance.json').read_text()) != source:
            raise ValueError('Source/model/data changed; use a separate output directory')
        write_json(output/'config.json', config); write_json(output/'provenance.json', source)
        expected = {j['id']:j for j in jobs(config)}
        records = collect([output, *merge], expected, ch, ph)
        for key, record in records.items():
            if not (output/'sessions'/f'{key}.json').exists(): write_json(output/'sessions'/f'{key}.json', record)
        pending = [j for key,j in expected.items() if key not in records]
        previous = json.loads((output/'manifest.json').read_text()) if (output/'manifest.json').exists() else {}
        attempts = previous.get('invocations', [])
        invocation = dict(started_utc=started, workers=workers, scheduled=len(pending), finished=0, wall_seconds=0)
        attempts.append(invocation)
        def manifest():
            write_json(output/'manifest.json', dict(config_hash=ch, provenance_hash=ph,
                platform=platform.platform(), processor=platform.processor(), cpu_count=os.cpu_count(),
                expected_sessions=len(expected), recorded_sessions=len(records),
                status_counts={s:sum(r['status']==s for r in records.values()) for s in ('tournament_complete','hand_limit','error')},
                completed_hands=sum(r['completed_hands'] for r in records.values()),
                missing_sessions=sorted(set(expected)-set(records)), invocations=attempts,
                sessions={key:digest(output/'sessions'/f'{key}.json') for key in sorted(records)}))
        manifest()
        try:
            with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context('spawn')) as pool:
                futures = {pool.submit(play_session,j,config):j for j in pending}
                for future in as_completed(futures):
                    record = future.result()
                    record.update(config_hash=ch, provenance_hash=ph)
                    accept(record, expected, ch, ph)
                    write_json(output/'sessions'/f"{record['id']}.json", record)
                    records[record['id']] = record
                    invocation['finished'] += 1; invocation['wall_seconds'] = perf_counter()-start
                    manifest()
                    print(f"{len(records)}/{len(expected)} {record['id']} {record['status']} {record['completed_hands']} hands {record['elapsed_seconds']:.1f}s", flush=True)
        finally:
            invocation['wall_seconds'] = perf_counter()-start
            invocation['ended_utc'] = datetime.now(timezone.utc).isoformat()
            manifest()
        return records


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True); parser.add_argument('--output', required=True)
    parser.add_argument('--workers', type=int, default=4); parser.add_argument('--merge', nargs='*', default=[])
    args=parser.parse_args()
    if not 1 <= args.workers <= 4: parser.error('Use 1..4 bounded worker processes')
    records=run(json.loads(Path(args.config).read_text()), args.output, args.workers, args.merge)
    if any(r['status']=='error' for r in records.values()): raise SystemExit(2)
if __name__ == '__main__': main()
