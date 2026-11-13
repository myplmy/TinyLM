"""Reuse six-proof delta checks; pin failed-built history, guard6 and two companions."""
from pathlib import Path
import hashlib
import sys

AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(AUDIT))
from selection_metadata_store_v1 import bound_selection_loads

frozen=AUDIT/'verify_cache_progress_delta_v2.py'
raw=frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()=='D390F23A2BC7B396BA7BE1E68B1E0FFAF71CDC6E1ED2688E378E0554B5BB3ACD'
text=raw.decode('utf-8')
before='    assert not (directory/\'built.json\').exists() and not (directory/\'verified.json\').exists()'
assert text.count(before)==1
replacement="""    assert not (directory/'verified.json').exists()
    failed_path=AUDIT/f'CACHE_REVIEWED_PARTIAL_V{skipped}_PROCESS_EXIT_V1.json'
    failed=json.loads(failed_path.read_bytes())
    assert failed['process_exit_code']!=0 and failed['owned_worker_wait_completed'] is True
    assert failed['observation_method']=='ACTUAL_SUBPROCESS_WAIT_RETURN_CODE'
    if (directory/'built.json').exists():
        assert failed['built_receipt']['sha256']==hashlib.sha256((directory/'built.json').read_bytes()).hexdigest().upper()
""".rstrip()
text=text.replace(before,replacement.replace(chr(10),r'\n'))
anchor="exec(compile(code, str(scope['frozen']), 'exec'), dict(__name__='six_proof_delta_actual_check',"
assert text.count(anchor)==1
scope=dict(__name__='guard6_eight_proof_delta_transform',__file__=str(Path(__file__)))
exec(compile(text.split(anchor)[0],str(frozen),'exec'),scope)
code=scope['code']
before="assert restricted['restricted_sources']==9 and restricted['alias_positions']==15"
after="guard6=read(AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V6.json')"+chr(10)+\
    "assert restricted['restricted_sources']==len(guard6['restricted_ids']) and restricted['alias_positions']==len(guard6['trusted_metadata'])"
assert code.count(before)==1
code=code.replace(before,after)
before='59CA9419990CD1D6968EA9B1E7EF4416D418C8C460EDD8074E98DA9BF5FCEF7D'
assert code.count(before)==1
code=code.replace(before,'5AAFF02F7B2709C06843221FBE39C700909685809FA845253B6A749553721C0E')
before='receipt=dict(status='
assert code.count(before)==1
extra="""out_directory=BASE/f"cache_reviewed_partial_v{CONFIG['cache_version']}"
safe=read(out_directory/'prior_safe_derivative_reuse_verified.json')
assert safe['status']=='EXACT_PRIOR_THREE_APPROVED_DERIVATIVES_REUSED_WITHOUT_SOURCE_VIEW_REOPEN'
assert safe['source_view_payload_opens']==safe['source_view_hashes_recomputed']==0
assert safe['fresh_source_code_unicode_comparison_performed'] is False
assert safe['past_source_preservation_proof_reused'] and safe['current_exact_approved_body_identity_checked']
assert not safe['global_code_guard_waiver'] and len(safe['bodies'])==3
assert safe['authority']['sha256']=='A4B4A347C5E42C02DEAC11B68A71DC325EECCC0771E224CC440EADC7ACCCD1EB'
exact=read(out_directory/'exact_unicode_annotation_12122_verified.json')
assert exact['status']=='EXACT_UNICODE_ANNOTATION_PAIR_COVERED_BY_FULL_SOURCE_CONSUMER'
assert exact['authority']['sha256']=='B15D224709457FA51579546BB2BEC5FA1EBDDED34D6404C2F80D64C3007E9749'
assert set(exact['parent_alias_ids'])=={'expanded_train:12122','historical_train:12122'}
assert exact['original']['sha256']=='CD3FD71905B88EB510417DBF8A41A6E746577AF76440039E437FDFB1FB9A57EB'
assert exact['body']['sha256']=='5676C31B690068B8367D41DB1FA0DA622B6FA31C7A65B3BCFFD7B743565825DF'
assert exact['codepoint_labels_preserved']==32 and exact['actual_special_scalars_preserved']==5
assert exact['global_code_or_unicode_guard_waiver'] is False
assert not safe['goal_complete'] and not exact['goal_complete']
for skipped in CONFIG['skipped_unverified_cache_versions']:
    failed=read(AUDIT/f'CACHE_REVIEWED_PARTIAL_V{skipped}_PROCESS_EXIT_V1.json')
    assert failed['process_exit_code']!=0
pins[str(ADAPTER_V2_PATH.relative_to(ROOT))]=hashlib.sha256(ADAPTER_V2_PATH.read_bytes()).hexdigest().upper()
pins[str((AUDIT/'selection_metadata_store_v1.py').relative_to(ROOT))]=hashlib.sha256((AUDIT/'selection_metadata_store_v1.py').read_bytes()).hexdigest().upper()
"""
code=code.replace(before,extra+before)
before='proof_count=6,'
assert code.count(before)==1
code=code.replace(before,'proof_count=6,companion_proof_count=2,')
ROOT=AUDIT.parents[2]
c=scope['scope']['c']
bindings=[(AUDIT/('ROOT_AUTHORED_SELECTIONS_V'+str(version)+'.json'),
    hashlib.sha256((AUDIT/('ROOT_AUTHORED_SELECTIONS_V'+str(version)+'.json')).read_bytes()).hexdigest().upper())
    for version in [c['selection_version'],c['prior_selection_version']]]
with bound_selection_loads(bindings,directory=AUDIT):
    exec(compile(code,str(scope['scope']['frozen']),'exec'),dict(__name__='guard6_eight_proof_delta_actual_check',
        __file__=str(Path(__file__)),CONFIG=c,CONFIG_PATH=scope['scope']['config_path'],
        FROZEN_PATH=scope['scope']['frozen'],ADAPTER_V1_PATH=scope['frozen'],ADAPTER_V2_PATH=frozen))
