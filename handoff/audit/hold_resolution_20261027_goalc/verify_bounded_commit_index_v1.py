"""Check exact index membership and blob equality, without changing Git."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
post = '--post' in sys.argv
pathspec = Path('/tmp/tinylm_hold_01a17740_checkpoint_20261101_post.paths' if post else
                '/tmp/tinylm_hold_01a17740_checkpoint_20261101_v1.paths')
paths = [v.decode('utf-8') for v in pathspec.read_bytes().split(bytes([0])) if v]
assert len(paths) == len(set(paths))
manifest = json.loads((AUDIT/'BOUNDED_LOCAL_COMMIT_ALLOWLIST_V1.json').read_text(encoding='utf-8'))
if not post:
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip() == manifest['expected_head']
    for row in manifest['rows']:
        assert hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest().upper() == row['sha256'],row['path']
actual = {v.decode('utf-8') for v in subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=ROOT).split(bytes([0])) if v}
assert actual == set(paths),dict(missing=sorted(set(paths)-actual),extra=sorted(actual-set(paths)))
entries = subprocess.check_output(['git','ls-files','--stage','-z','--',*paths],cwd=ROOT)
index = {}
for value in entries.split(bytes([0])):
    if not value:
        continue
    header,name = value.split(bytes([9]),1)
    mode,object_id,stage = header.split()
    assert mode == b'100644' and stage == b'0'
    index[name.decode('utf-8')] = object_id.decode('ascii')
working = subprocess.check_output(['git','hash-object','--no-filters','--stdin-paths'],cwd=ROOT,
    input=(chr(10).join(paths)+chr(10)).encode('utf-8')).decode('ascii').splitlines()
assert len(working) == len(paths)
assert all(index[name] == value for name,value in zip(paths,working))
print(json.dumps(dict(status='EXACT_INDEX_AND_WORKING_BYTES_MATCH',paths=len(paths),post=post),ensure_ascii=False))
