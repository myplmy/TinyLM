"""Verify one roster delta across a pinned, unchanged selection-prefix chain."""
from pathlib import Path
import hashlib
import json
import sys

AUDIT=Path(__file__).resolve().parent; ROOT=AUDIT.parents[2]
sys.path.insert(0,str(AUDIT))
from selection_metadata_store_v1 import SelectionStore,bound_selection_loads

frozen=AUDIT/'verify_reviewed_roster_batch_v1.py';raw=frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()=='3E4D87B4FE7692048780995EDA8BC4364411C0DE37A05D6EB50929E5CD51E375'
assert hashlib.sha256((AUDIT/'selection_metadata_store_v1.py').read_bytes()).hexdigest().upper()=='A5DE169B5493EDB1AD4FF456145BA0BF729754670FF258BADD2AFC67CC89E461'
config_path=Path(sys.argv[sys.argv.index('--config')+1]).resolve()
assert config_path.is_relative_to(AUDIT) and not config_path.is_symlink()
config=json.loads(config_path.read_bytes()); store=SelectionStore(AUDIT)
path=AUDIT/('ROOT_AUTHORED_SELECTIONS_V'+str(config['next_selection'])+'.json')
selection=store.read(path,config['selection_sha256'])
target=AUDIT/('ROOT_AUTHORED_SELECTIONS_V'+str(config['prior_selection'])+'.json')
bindings=[(path,config['selection_sha256'])]; chain=[]; seen={path}
current=selection
while path!=target:
    pin=current['prior_selection']; prior_path=(ROOT/pin['path']).resolve()
    assert prior_path.parent==AUDIT and prior_path not in seen and len(seen)<1000
    prior=store.read(prior_path,pin['sha256'])
    assert current['rows'][:len(prior['rows'])]==prior['rows']
    assert len(current['rows'])>len(prior['rows'])
    bindings.append((prior_path,pin['sha256'])); chain.append(dict(path=pin['path'],sha256=pin['sha256'],rows=len(prior['rows'])))
    seen.add(prior_path); current=prior; path=prior_path
assert selection['rows'][:len(current['rows'])]==current['rows']
with bound_selection_loads(bindings,directory=AUDIT):
    exec(compile(raw,str(frozen),'exec'),dict(__name__='independent_full_roster_pinned_selection_chain',
        __file__=str(Path(__file__))))
receipt=dict(status='UNCHANGED_SELECTION_PREFIX_CHAIN_AND_FULL_ROSTER_VERIFIED',
    selection_sha256=config['selection_sha256'],selection_chain=chain,
    skipped_intermediate_roster_builds=max(0,len(chain)-1),canonical_roster_rows_verified=297539,
    goal_complete=False,training_authorized=False)
out=AUDIT/('ROOT'+str(config['next_selection'])+'_ROSTER_SELECTION_LINEAGE_V1.json')
with out.open('xb') as stream:stream.write((json.dumps(receipt,ensure_ascii=False,indent=2)+chr(10)).encode())
