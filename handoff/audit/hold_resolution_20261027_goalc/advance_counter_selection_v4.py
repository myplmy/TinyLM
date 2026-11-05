"""Use guard5 and defer its exact two metadata HOLDs before any payload hash."""
from pathlib import Path
import hashlib
import json
import sys

AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(AUDIT))
from active_guard_v5_preflight_v1 import (activate,assert_no_protected_opens,
    validate_new_hold,NEW_IDS,EXPECTED)
activate()
frozen=AUDIT/'advance_counter_selection_v3.py'
raw=frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()=='1C1E905582E922CE19C77C973D112CB560617C4A6E04EADF83222E98EF390566'
text=raw.decode();last="exec(compile(code, str(frozen), 'exec'), environment)"
assert text.count(last)==1
scope=dict(__name__='guard5_counter_selection_transform',__file__=str(Path(__file__)))
exec(compile(text.split(last)[0],str(frozen),'exec'),scope)
code=scope['code'];environment=scope['environment']
config=scope['config'];ROOT=scope['ROOT']
pending_ids=set();supersession_pins=[];superseded=None
if config.get('supersession_proof'):
    proof_path=(ROOT/config['supersession_proof']).resolve()
    assert proof_path.is_relative_to(AUDIT) and not proof_path.is_symlink()
    proof_raw=proof_path.read_bytes()
    assert hashlib.sha256(proof_raw).hexdigest().upper()==config['supersession_proof_sha256']
    proof=json.loads(proof_raw);superseded=proof['superseded_proposal'];prior=proof['effective_canonical_prior']
    assert config['prior_selection']==30 and config['next_selection']==31
    assert proof['pending_context_ids']==['expanded_train:77055']
    assert proof['root30_references_in_actual_cache_or_roster_receipts']==0
    for pin in [superseded,prior,*proof['all_existing_cache_and_roster_metadata_reference_checks']]:
        p=ROOT/pin['path'];assert hashlib.sha256(p.read_bytes()).hexdigest().upper()==pin['sha256']
        if pin in proof['all_existing_cache_and_roster_metadata_reference_checks']:
            assert b'ROOT_AUTHORED_SELECTIONS_V30.json' not in p.read_bytes()
    assert not (ROOT/'data_cache/p106b_hold_resolution_v1_20261027_goalc/roster_reviewed_partial_v22/complete.json').exists()
    assert not (ROOT/'data_cache/p106b_hold_resolution_v1_20261027_goalc/cache_reviewed_partial_v16/built.json').exists()
    before="previous_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V30.json'"
    assert code.count(before)==1
    code=code.replace(before,"previous_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V29.json'")
    assert code.count(config['prior_selection_sha256'])==1
    code=code.replace(config['prior_selection_sha256'],prior['sha256'])
    before='PRIOR_ROOT30_UNCHANGED_PLUS_PINNED_COUNTER_AND_CONTEXT_REPAIRS'
    assert code.count(before)==1
    code=code.replace(before,'PRIOR_VERIFIED_ROOT29_UNCHANGED_AND_UNADMITTED_ROOT30_SUPERSEDED')
    pending_ids=set(proof['pending_context_ids']);supersession_pins=[proof_path,ROOT/superseded['path']]
for before,after in [
    ('GUARDED_SOURCE_METADATA_CONTRACT_V4.json','GUARDED_SOURCE_METADATA_CONTRACT_V5.json'),
    ('59CA9419990CD1D6968EA9B1E7EF4416D418C8C460EDD8074E98DA9BF5FCEF7D',EXPECTED)]:
    assert before in code;code=code.replace(before,after)
anchor="    assert key not in guard['restricted_ids']"
assert code.count(anchor)==1
branch="""    if key in NEW_QUARANTINE_IDS:
        validate_new_hold(row,source)
        assert row.get('metadata_only') is True and row['active_quarantine_contract_sha256']==ACTIVE_GUARD5_SHA
        deferred.append(dict(id=key,reason='EXACT_METADATA_ONLY_HOLD_NO_PAYLOAD_ADMISSION'))
        continue
"""
branch="""    if key in PENDING_CONTEXT_IDS:
        deferred.append(dict(id=key,reason='ROOT_CONTEXT_FOLLOWUP_PENDING_UNADMITTED_PROPOSAL_SUPERSEDED'))
        continue
"""+branch
code=code.replace(anchor,branch+anchor)
anchor='pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in input_paths}'
assert code.count(anchor)==1
code=code.replace(anchor,"input_paths.extend([ADAPTER_V3_PATH,AUDIT/'active_guard_v5_preflight_v1.py']+SUPERSESSION_PINS)"+chr(10)+anchor)
anchor="document['additional_root_independent_context_sources']=extra_selected_count"
assert code.count(anchor)==1
code=code.replace(anchor,anchor+chr(10)+"document['superseded_unadmitted_proposal']=SUPERSEDED_PROPOSAL")
environment.update(NEW_QUARANTINE_IDS=NEW_IDS,validate_new_hold=validate_new_hold,
    ACTIVE_GUARD5_SHA=EXPECTED,ADAPTER_V3_PATH=frozen,assert_no_protected_opens=assert_no_protected_opens,
    PENDING_CONTEXT_IDS=pending_ids,SUPERSESSION_PINS=supersession_pins,SUPERSEDED_PROPOSAL=superseded)
exec(compile(code,str(frozen),'exec'),environment)
assert_no_protected_opens()
