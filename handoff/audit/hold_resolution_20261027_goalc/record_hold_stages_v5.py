"""Keep guard5 stage arithmetic and bind the exact sharded selection."""
from pathlib import Path
import hashlib
import json
import sys

AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIT))
from selection_metadata_store_v1 import bound_selection_loads

frozen = AUDIT/'record_hold_stages_v4.py'
raw = frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == 'F8A03C7B2EC6E20442DDC6B2B317CF483134133DA9B97A72195A3F2586960A88'
assert hashlib.sha256((AUDIT/'selection_metadata_store_v1.py').read_bytes()).hexdigest().upper() == 'A5DE169B5493EDB1AD4FF456145BA0BF729754670FF258BADD2AFC67CC89E461'
ROOT = AUDIT.parents[2]
config = json.loads((ROOT/sys.argv[sys.argv.index('--config') + 1]).read_bytes())
with bound_selection_loads([(ROOT/config['selection'], config['selection_sha256'])], directory=AUDIT):
    exec(compile(raw, str(frozen), 'exec'), dict(__name__='sharded_guard5_stage_recorder',
        __file__=str(Path(__file__))))
