"""Reuse the independent delta verifier across failed versions and six proofs."""
from pathlib import Path
import hashlib

AUDIT = Path(__file__).resolve().parent
frozen = AUDIT/'verify_cache_progress_delta_v1.py'
raw = frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == '261FBF0CFBD27391919C0A87CABE0E503A900E9FC995B7340E5D14037F6E80F4'
text = raw.decode('utf-8')
anchor = 'assert isinstance(n,int) and n==old_n+1 and n>=6'
assert text.count(anchor) == 1
text = text.replace(anchor,
    'assert isinstance(n,int) and n>old_n and n>=6' + chr(10) +
    "assert c['skipped_unverified_cache_versions']==list(range(old_n+1,n))" + chr(10) +
    "for skipped in c['skipped_unverified_cache_versions']:" + chr(10) +
    "    directory=ROOT/'data_cache/p106b_hold_resolution_v1_20261027_goalc'/f'cache_reviewed_partial_v{skipped}'" + chr(10) +
    "    assert not (directory/'built.json').exists() and not (directory/'verified.json').exists()")
last = "exec(compile(code,str(frozen),'exec'),{'__name__':'versioned_cache_progress_actual_proof_check'"
assert text.count(last) == 1
scope = dict(__name__='six_proof_delta_transform',__file__=str(Path(__file__)))
exec(compile(text.split(last)[0], str(frozen), 'exec'), scope)
code = scope['code']
changes = [
    ('assert len(proofs)==5', "assert set(proofs)=={'verified.json','recovery_verified.json','partial_resolution_verified.json','restricted_metadata_verified.json','baseline_preservation_scope.json','opaque_hold_verified.json'}"),
    ("assert restricted['restricted_sources']==8 and restricted['alias_positions']==13",
     "assert restricted['restricted_sources']==9 and restricted['alias_positions']==15"),
    ('7CF0AA8B46DDAED415851EE5F356B78EFBE12F33530B8217F028F86904594306',
     '59CA9419990CD1D6968EA9B1E7EF4416D418C8C460EDD8074E98DA9BF5FCEF7D')]
for old, new in changes:
    assert code.count(old) == 1
    code = code.replace(old, new)
anchor = 'receipt=dict(status='
assert code.count(anchor) == 1
extra = """build_exit=read(AUDIT/f"CACHE_REVIEWED_PARTIAL_V{CONFIG['cache_version']}_PROCESS_EXIT_V1.json")
assert build_exit['process_exit_code']==0 and build_exit['owned_worker_wait_completed'] is True
assert actual['owned_worker_wait_completed'] is True and not actual['interrupted']
assert build_exit['built_receipt']['sha256']==pins[str(new_path.relative_to(ROOT))]
opaque=proofs['opaque_hold_verified.json']
assert opaque['status']=='FULL_UNADOPTED_HOLD_METADATA_CONSUMER_VERIFIED'
assert opaque['counts']=={'positions':CONFIG['HOLD_positions'],'input_ids':new['counts']['HOLD_input_ids']}
assert opaque['unique_sources']==roster['unique_counts']['HOLD']
assert opaque['ordinary_HOLD_is_not_reclassified_as_sensitive'] is True
assert opaque['active_restricted_contract_sha256']==restricted['contract_sha256']
contract_path=AUDIT/CONFIG['opaque_contract'];contract=read(contract_path)
assert opaque['contract_sha256']==pins[str(contract_path.relative_to(ROOT))]
assert contract['counts']==opaque['counts'] and contract['unique_sources']==opaque['unique_sources']
assert not opaque['training_authorized'] and not opaque['goal_complete']
pins[str(ADAPTER_V1_PATH.relative_to(ROOT))]=hashlib.sha256(ADAPTER_V1_PATH.read_bytes()).hexdigest().upper()
"""
code = code.replace(anchor, extra + anchor)
anchor = "    source_body_opens_in_this_metadata_crosscheck=0,goal_complete=False,training_authorized=False,"
assert code.count(anchor) == 1
code = code.replace(anchor,
    "    source_body_opens_in_this_metadata_crosscheck=0,goal_complete=False,training_authorized=False," + chr(10) +
    "    proof_count=6,skipped_unverified_cache_versions=CONFIG['skipped_unverified_cache_versions'],opaque_hold_counts=opaque['counts'],")
exec(compile(code, str(scope['frozen']), 'exec'), dict(__name__='six_proof_delta_actual_check',
    __file__=str(Path(__file__)),CONFIG=scope['c'],CONFIG_PATH=scope['config_path'],
    FROZEN_PATH=scope['frozen'],ADAPTER_V1_PATH=frozen))
