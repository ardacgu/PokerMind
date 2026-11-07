"""Inspect the exact Git index before publishing; never print credential values."""
import json
from pathlib import Path
import re
import subprocess
from zipfile import ZipFile
from fnmatch import fnmatch
from stage8_package import PRIVATE_NAMES, EXCLUDED

ROOT = Path(__file__).resolve().parents[1]


def audit():
    assert Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],cwd=ROOT,text=True).strip()).resolve() == ROOT
    names = subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')[:-1]
    assert subprocess.run(['git','diff','--quiet'],cwd=ROOT).returncode == 0, 'Stage reviewed changes before auditing'
    forbidden = EXCLUDED
    patterns = {'personal_path': rb'/(?:Users|home)/[A-Za-z0-9_.-]+/',
                'credential': rb'gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{24,}|-----BEGIN [A-Z ]*PRIVATE KEY-----'}
    problems=[]; sizes=[]
    for name in names:
        p=ROOT/name; data=p.read_bytes();sizes.append((len(data),name))
        if forbidden.intersection(Path(name).parts) or name.endswith(('.log','.tmp','.pem','.key')) or Path(name).name.startswith('.env'):
            problems.append((name,'excluded file type'))
        if len(data)>=100*1024*1024:problems.append((name,'GitHub file size limit'))
        if name.endswith('.zip') and name!='evaluations/stage6-runtime.zip':problems.append((name,'redundant archive'))
        if any(fnmatch(Path(name).name.casefold(), pattern) for pattern in PRIVATE_NAMES):
            problems.append((name,'private study material'))
        for label,pattern in patterns.items():
            if re.search(pattern,data):problems.append((name,label))
        if name.endswith('.zip'):
            with ZipFile(p) as archive:
                for member in archive.namelist():
                    for label,pattern in patterns.items():
                        if re.search(pattern,archive.read(member)):problems.append((name+':'+member,label))
    assert not problems, problems
    print(json.dumps({'repository_isolated':True,'indexed_files':len(names),
                      'uncompressed_bytes':sum(n for n,_ in sizes),
                      'largest_files':[{'file':p,'bytes':n} for n,p in sorted(sizes,reverse=True)[:6]],
                      'secret_and_personal_path_matches':0,
                      'scope':'Exact Git index paths, source bytes and contents of the frozen runtime archive. Pattern scan plus manual review; not a universal secret-detection proof.'},indent=2))

if __name__=='__main__':audit()
