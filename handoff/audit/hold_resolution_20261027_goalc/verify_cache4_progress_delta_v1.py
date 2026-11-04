"""Check the actual consumer proof chain and distinguish sources from positions."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
BASE=ROOT/'data_cache/p106b_hold_resolution_v1_20261027_goalc'
pins={}


def read(path):
    raw=path.read_bytes();pins[str(path.relative_to(ROOT))]=hashlib.sha256(raw).hexdigest().upper()
    return json.loads(raw)


exit_path=AUDIT/'CACHE_REVIEWED_PARTIAL_V4_VERIFY_EXIT_V1.json'
actual=read(exit_path)
assert actual['process_exit_code']==0 and actual['observation_method']=='ACTUAL_SUBPROCESS_WAIT_RETURN_CODE'
proofs={}
for name,pin in actual['proofs'].items():
    path=ROOT/pin['path'];proofs[name]=read(path);assert pins[pin['path']]==pin['sha256']
assert len(proofs)==5
core=proofs['verified.json'];recovery=proofs['recovery_verified.json']
partial=proofs['partial_resolution_verified.json'];restricted=proofs['restricted_metadata_verified.json']
baseline=proofs['baseline_preservation_scope.json']
old_path=BASE/'cache_reviewed_partial_v3/built.json';new_path=BASE/'cache_reviewed_partial_v4/built.json'
old=read(old_path);new=read(new_path)
assert recovery['built_sha256']==pins[str(new_path.relative_to(ROOT))]
assert recovery['core_verified_sha256']==actual['proofs']['verified.json']['sha256']
assert partial['core_recovery_verified_sha256']==actual['proofs']['recovery_verified.json']['sha256']
roster_path=BASE/'roster_reviewed_partial_v4/complete.json';roster=read(roster_path)
assert partial['roster_sha256']==pins[str(roster_path.relative_to(ROOT))]
assert core['status']=='CPU_FULL_CACHE_VERIFIED' and core['every_adopted_document_regenerated'] is True
assert core['exact_train_val_text_overlap']==0 and core['files_under_20mb'] is True
assert core['decisions']=={name:new['counts'][name] for name in
    ['documents','input_ids','EXCLUDE','KEEP','EDIT','HOLD']}
assert partial['checked']=={'documents':460695,'input_ids':462874291}
assert partial['outcomes']=={k:new['recovery_outcomes'][k] for k in ['KEEP','EDIT','EXCLUDE','HOLD']}
assert old['counts']['HOLD']==110173 and new['counts']['HOLD']==partial['remaining_hold']==109931
assert partial['reviewed_hold']==38 and partial['unprocessed']==109893
assert restricted['restricted_sources']==8 and restricted['alias_positions']==13
assert restricted['original_parent_bodies_decoded'] is False
assert restricted['contract_sha256']=='7CF0AA8B46DDAED415851EE5F356B78EFBE12F33530B8217F028F86904594306'
assert baseline['baseline_parent']=='data_cache/p106b_hold_recovery_v1_20261026_goalc/cache_v5'
assert baseline['preserved_baseline_documents']==1145290
selection_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V12.json';selection=read(selection_path)
assert baseline['selected_body_approval']['sha256']==pins[str(selection_path.relative_to(ROOT))]
assert selection['new_approved_sources']==123 and selection['new_approved_positions']==242
previous_core=read(BASE/'cache_reviewed_partial_v3/verified.json')
added={split:core['summary'][split]['documents']-previous_core['summary'][split]['documents'] for split in ['train','val']}
assert added=={'train':121,'val':2}
assert new['counts']['EXCLUDE']-old['counts']['EXCLUDE']==119
assert new['counts']['EDIT']-old['counts']['EDIT']==123
assert new['counts']['KEEP']==old['counts']['KEEP']
assert all(not doc['training_authorized'] for doc in [actual,core,recovery,partial,restricted,baseline])
receipt=dict(status='ACTUAL_CACHE4_CONSUMER_PROOF_CHAIN_AND_PROGRESS_DELTA_VERIFIED',
    official_verified_cache='cache_reviewed_partial_v4',previous_hold_positions=110173,
    current_hold_positions=109931,resolved_positions=242,new_unique_accepted_documents=123,
    additional_duplicate_positions_excluded=119,added_accepted_documents_by_split=added,
    original_hold_positions=460695,total_positions_processed=460695-109931,
    reviewed_HOLD_positions=38,unprocessed_in_admitted_roster=109893,
    actual_build_seconds=read(AUDIT/'CACHE_REVIEWED_PARTIAL_V4_PROCESS_EXIT_V1.json')['seconds'],
    actual_consumer_seconds=actual['seconds'],exact_train_val_text_overlap=0,
    all_adopted_documents_regenerated=True,files_under_20mb=True,
    preserved_baseline_documents=1145290,
    preservation_scope='Frozen cache_v5 baseline; explicitly reviewed intermediate corrections are not claimed unchanged.',
    global_article_leakage='UNVERIFIED_NO_ORIGINAL_ARTICLE_IDS',
    source_body_opens_in_this_metadata_crosscheck=0,goal_complete=False,training_authorized=False,
    input_pins=dict(pins,**{str(Path(__file__).relative_to(ROOT)):hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper()}))
out=AUDIT/'CACHE4_PROGRESS_DELTA_INDEPENDENT_VERIFIED_V1.json'
with out.open('x',encoding='utf-8') as stream:
    json.dump(receipt,stream,ensure_ascii=False,indent=2);stream.write(chr(10))
print(json.dumps({k:receipt[k] for k in ['status','previous_hold_positions','current_hold_positions','resolved_positions','new_unique_accepted_documents']}))
