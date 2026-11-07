"""Portable public release, restricted to reviewed project roots and verified bytewise."""
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = {'pokermind','models','data','evaluations','experiments','tests','scripts','docs','.github'}
ROOT_FILES = {'README.md','.gitignore','requirements.txt','requirements-report.txt','pyproject.toml'}
EXCLUDED = {'.git','.venv','work','__pycache__','.pytest_cache','node_modules','.DS_Store','.run.lock'}


def release_files(root=ROOT):
    for p in sorted(root.rglob('*')):
        rel=p.relative_to(root)
        if not p.is_file() or EXCLUDED.intersection(rel.parts):continue
        if rel.parts[0] not in DIRECTORIES and str(rel) not in ROOT_FILES:continue
        if p.suffix in {'.log','.tmp','.pyc','.pyo'}:continue
        if p.suffix=='.zip' and str(rel)!='evaluations/stage6-runtime.zip':continue
        yield p


def build():
    files=list(release_files());dest=ROOT.parent/'PokerMind-v1.0.0.zip'
    temp=dest.with_suffix('.zip.tmp')
    with ZipFile(temp,'w',ZIP_DEFLATED) as z:
        for p in files:z.write(p,'PokerMind/'+str(p.relative_to(ROOT)))
    with ZipFile(temp) as z:
        assert z.testzip() is None
        assert len(z.namelist())==len(set(z.namelist()))==len(files)
        for p in files:assert z.read('PokerMind/'+str(p.relative_to(ROOT)))==p.read_bytes()
    temp.replace(dest)
    digest=sha256(dest.read_bytes()).hexdigest()
    dest.with_suffix('.zip.sha256').write_text(f'{digest}  {dest.name}\n')
    print({'archive':dest.name,'files':len(files),'bytes':dest.stat().st_size,'sha256':digest,'crc_and_bytes':'verified'})

if __name__=='__main__':build()
