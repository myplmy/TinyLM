"""Install five fixed-role small-final readers; never replace another tool."""
from pathlib import Path
import hashlib

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
ENTRY=AUDIT/'small_final_review_task_batch_v1.py'
SHA='8A9377DEF62746FAC68762DCDB3EF1BC40756A00F114C94AF98C0BB31F029548'
assert not ENTRY.is_symlink() and hashlib.sha256(ENTRY.read_bytes()).hexdigest().upper()==SHA
for letter,role in dict(c='context_controls',l='context_latin',h='context_hangul',j='historical_review',g='legacy_review').items():
    text='''#!/bin/bash
set -eu
if [ "$#" -lt 4 ] || [ "$#" -gt 16 ]; then
  echo "usage: shortcut PAGE ID1 FINAL_BASENAME1 FINAL_SHA1 [... maximum 5 triples]" >&2
  exit 64
fi
exec /home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B -c 'from pathlib import Path
import hashlib,importlib.util
root=Path("/home/uranus/tinyLM")
path=root/"handoff/audit/hold_resolution_20261027_goalc/small_final_review_task_batch_v1.py"
if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest().upper()!="'''+SHA+'''":
    raise SystemExit("fixed small-final batch entry changed; no corpus read")
spec=importlib.util.spec_from_file_location("fixed_small_final_task_batch_v1",path)
entry=importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)
entry.cli(root,"'''+role+'''")' "$@"
'''
    target=ROOT/'tmp'/('hold-'+letter+'-field-final-task-batch-v1')
    if target.exists():
        assert not target.is_symlink() and target.read_text(encoding='utf-8')==text
    else:
        with target.open('x',encoding='utf-8') as stream:stream.write(text)
print('FIVE_FIXED_ROLE_SMALL_FINAL_BATCH_SHORTCUTS_READY')
