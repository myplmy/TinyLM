"""Reuse the guard5 roster join with exact sharded-selection bindings."""
from pathlib import Path
import hashlib
import json
import sys

AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIT))
from selection_metadata_store_v1 import SelectionStore, bound_selection_loads

frozen = AUDIT/'advance_reviewed_roster_v3.py'
raw = frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == 'D5439BA25E896A2843F54B3732DDFBDA1B86FB1F4FD76B537D6D3FF4E2398B17'
assert hashlib.sha256((AUDIT/'selection_metadata_store_v1.py').read_bytes()).hexdigest().upper() == 'A5DE169B5493EDB1AD4FF456145BA0BF729754670FF258BADD2AFC67CC89E461'
config_path = Path(sys.argv[sys.argv.index('--config') + 1]).resolve()
assert config_path.is_relative_to(AUDIT) and not config_path.is_symlink()
config = json.loads(config_path.read_bytes())
selection_path = AUDIT/('ROOT_AUTHORED_SELECTIONS_V' + str(config['next_selection']) + '.json')
selection = SelectionStore(AUDIT).read(selection_path, config['selection_sha256'])
ROOT = AUDIT.parents[2]
prior = selection['prior_selection']
bindings = [(selection_path, config['selection_sha256']), (ROOT/prior['path'], prior['sha256'])]
with bound_selection_loads(bindings, directory=AUDIT):
    exec(compile(raw, str(frozen), 'exec'), dict(__name__='sharded_guard5_roster_join',
        __file__=str(Path(__file__))))
