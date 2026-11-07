"""Build and byte-verify the portable project archive (no environment/cache files)."""
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
EXCLUDE={'.venv','.git','__pycache__','.pytest_cache','work','.run.lock','.DS_Store'}

def build():
    paths=sorted(p for p in ROOT.rglob('*') if p.is_file() and not EXCLUDE.intersection(p.relative_to(ROOT).parts))
    dest=ROOT.parent/'PokerMind.zip'
    temporary=dest.with_suffix('.zip.tmp')
    with ZipFile(temporary,'w',ZIP_DEFLATED) as archive:
        for p in paths:archive.write(p,'PokerMind/'+str(p.relative_to(ROOT)))
    with ZipFile(temporary) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist())==len(set(archive.namelist()))==len(paths)
        for p in paths:assert archive.read('PokerMind/'+str(p.relative_to(ROOT)))==p.read_bytes()
    temporary.replace(dest)
    checksum=sha256(dest.read_bytes()).hexdigest()
    dest.with_suffix('.zip.sha256').write_text(f'{checksum}  {dest.name}\n')
    print(dict(archive=str(dest),files=len(paths),bytes=dest.stat().st_size,sha256=checksum,crc_and_member_bytes_verified=True))
    return dest
if __name__=='__main__':build()
