"""Verify frozen science and rules while explicitly allowing four UI/integration edits.

The original Stage 8 manifest and verifier remain historical evidence, unchanged.
"""
import json
from pathlib import Path
from hashlib import sha256
import re
ROOT=Path(__file__).resolve().parents[1]
ALLOWED={'pokermind/server.py','pokermind/static/app.js','pokermind/static/style.css','pokermind/static/index.html'}

def verify():
 frozen=json.loads((ROOT/'docs/stage8/frozen-artifacts.json').read_text())['files']
 checked=0;changed=[]
 for name,digest in frozen.items():
  actual=sha256((ROOT/name).read_bytes()).hexdigest()
  if name in ALLOWED:
   if actual!=digest:changed.append(name)
  else:
   assert actual==digest,name
   checked+=1
 for name in ['README.md','docs/architecture.md','docs/pokermind-2.md']:
  p=ROOT/name
  for link in re.findall(r'\]\(([^)]+)\)',p.read_text()):
   if link.startswith(('http://','https://','#')):continue
   assert (p.parent/link.split('#')[0]).exists(),(name,link)
 assert not (ROOT/'docs/muendliche-pruefung.md').exists()
 print(json.dumps({'protected_original_files_verified':checked,'explicit_runtime_updates':changed,
                   'original_game_teacher_model_data_evaluation_unchanged':True,'document_links':'passed'},indent=2))
if __name__=='__main__':verify()
