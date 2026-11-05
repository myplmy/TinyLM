"""Current guard5 before frozen disjoint checkpoint4; no corpus TXT staging."""
from pathlib import Path
import hashlib
import json
import sys

AUDIT=Path(__file__).resolve().parent;ROOT=AUDIT.parents[2]
sys.path.insert(0,str(AUDIT))
from active_guard_v5_preflight_v1 import activate,checked_contract,assert_no_protected_opens
activate();guard=checked_contract()
config=json.loads((ROOT/sys.argv[sys.argv.index('--config')+1]).read_bytes())
selection=json.loads((AUDIT/config['selection']).read_bytes())
prior_pin=selection['prior_selection'];p=ROOT/prior_pin['path']
assert hashlib.sha256(p.read_bytes()).hexdigest().upper()==prior_pin['sha256']
prior={r['id']:r for r in json.loads(p.read_bytes())['rows']}
safe={'expanded_train:1250821','expanded_train:15695','expanded_train:20624'}
for row in selection['rows']:
    if row['selected']['decision'] not in {'KEEP','EDIT'}:continue
    if row['id'] in guard['restricted_ids']:
        assert row['id'] in safe and row==prior[row['id']]
    else:assert row['original_text_sha256'] not in guard['restricted_hashes']
    assert row['selected']['clean_text_sha256'] not in guard['restricted_hashes']
frozen=AUDIT/'prepare_versioned_checkpoint_v4.py'
raw=frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()=='1BF6B748A7FF61EC9D83ED6910B7D11167516BBF9B7B0839C04EAB7F2038B96A'
exec(compile(raw,str(frozen),'exec'),dict(__name__='guard5_checkpoint_actual',__file__=str(Path(__file__))))
assert_no_protected_opens()
