"""Join a reviewed roster under guard4 without a redundant legacy census copy."""
from pathlib import Path
import hashlib
import json
import sys

AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIT))
from active_guard_v4_preflight_v1 import activate, assert_no_protected_opens
from guarded_reviewed_cache_v6 import checked_contract
activate()
contract = checked_contract()
frozen = AUDIT/'advance_reviewed_roster_v1.py'
raw = frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == 'F20E288A65638A3E6011244B5223AF78D46961838E2ABEDF4E91B6BFA879F868'
text = raw.decode('utf-8')
last = "exec(compile(code,str(frozen),'exec'),dict("
assert text.count(last) == 1
scope = dict(__name__='roster_guard4_transform', __file__=str(Path(__file__)))
exec(compile(text.split(last)[0], str(frozen), 'exec'), scope)
code = scope['code']
prior_pin = scope['selection']['prior_selection']
prior_raw = (scope['ROOT']/prior_pin['path']).read_bytes()
assert hashlib.sha256(prior_raw).hexdigest().upper() == prior_pin['sha256']
prior_rows = {row['id']: row for row in json.loads(prior_raw)['rows']}
safe_ids = {'expanded_train:1250821', 'expanded_train:15695', 'expanded_train:20624'}
for row in scope['selection']['rows']:
    if row['selected']['decision'] in {'KEEP', 'EDIT'}:
        if row['id'] in contract['restricted_ids']:
            # Preserve only the three already approved safe derivatives exactly.
            # No original payload access or new restricted-source admission.
            assert row['id'] in safe_ids and row == prior_rows[row['id']]
        else:
            assert row['original_text_sha256'] not in contract['restricted_hashes']
        assert row['selected']['clean_text_sha256'] not in contract['restricted_hashes']
anchor = 'with guarded.runtime(selection_path):'
assert code.count(anchor) == 1
# Roster creation does not need token runtime pins or its own 266MB parent copy.
# Current guard6 pins are made later, after the matching opaque contract exists.
code = code.split(anchor)[0]
code += """assert_no_protected_opens()
print(json.dumps(dict(status='WHOLE_SOURCE_ROSTER_READY_NOT_CACHE_BUILT',unique_counts=dict(unique),
    positions=dict(positions),hold_partition=dict(partition),legacy_census_created=False,
    active_guard_sha256=ACTIVE_GUARD_SHA,protected_payload_open_attempts=0,goal_complete=False)))
"""
anchor = 'approval=dict(status='
assert code.count(anchor) == 1
code = code.replace(anchor, 'assert_no_protected_opens()' + chr(10) + anchor)
anchor = '    input_pins={str(p.relative_to(ROOT)):inv.file_sha(p) for p in paths},goal_complete=False,training_authorized=False)'
assert code.count(anchor) == 1
code = code.replace(anchor,
    '    active_guard_sha256=ACTIVE_GUARD_SHA,protected_payload_open_attempts=0,legacy_census_created=False,' + chr(10) + anchor)
anchor = 'approval=dict(status='
code = code.replace(anchor,
    "paths.extend([ADAPTER_V1_PATH,AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V4.json',AUDIT/'active_guard_v4_preflight_v1.py'])" + chr(10) + anchor)
exec(compile(code, str(frozen), 'exec'), dict(__name__='actual_guard4_roster_without_census',
    __file__=str(Path(__file__)), CONFIG_PATH=scope['config_path'], FROZEN_PATH=scope['frozen'],
    PRIOR_PROOF_PATH=scope['proof_path'], ADAPTER_V1_PATH=frozen,
    ACTIVE_GUARD_SHA='59CA9419990CD1D6968EA9B1E7EF4416D418C8C460EDD8074E98DA9BF5FCEF7D',
    assert_no_protected_opens=assert_no_protected_opens))
assert_no_protected_opens()
