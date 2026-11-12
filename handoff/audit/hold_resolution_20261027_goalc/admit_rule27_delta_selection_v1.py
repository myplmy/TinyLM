"""Admit only source-linked, independently checked policy27 deltas.

Creates program-derived text, never attributes it to a human author, and reuses
identical existing review bodies. Previous selection rows remain unchanged.
"""
from collections import Counter
from pathlib import Path
import hashlib
import json
import sys

AUDIT=Path(__file__).resolve().parent; ROOT=AUDIT.parents[2]
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(AUDIT))
from active_guard_v5_preflight_v1 import activate,checked_contract,assert_no_protected_opens
from selection_metadata_store_v1 import SelectionStore,encode
from verify_rule27_literal_delta_v1 import evaluate
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v27 as policy

activate(); guard=checked_contract(); pins={}


def read(path,expected=None):
    raw=path.read_bytes(); actual=hashlib.sha256(raw).hexdigest().upper()
    assert expected is None or actual==expected,str(path)
    pins[str(path.relative_to(ROOT))]=actual
    return json.loads(raw)


prior_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V33.json'
prior_sha='9F99AA65B6D42EE78DE4D1C09A13C57BF7E15B3EECAE724BC948B69A33A05DE0'
previous=SelectionStore(AUDIT).read(prior_path,prior_sha)
prior_verified=read(AUDIT/'ROOT33_SHARDED_SELECTION_INDEPENDENT_VERIFIED_V1.json')
assert prior_verified['selection']['sha256']==prior_sha
prior_ids={r['id'] for r in previous['rows']}; prior_hashes={r['original_text_sha256'] for r in previous['rows']}
census=read(AUDIT/'RULE27_DECLARED_NAME_LIST_CENSUS_V1.json',
    '0BBAF7B7B05B9F922ED780BA75A1529018934ADB0B899375E2C760F0194A40C6')
for name,expected in census['input_pins'].items():assert inv.file_sha(ROOT/name)==expected,name
literal=read(AUDIT/'RULE27_LITERAL_DELTA_INDEPENDENT_VERIFIED_V1.json',
    '67CBD366AEE45E82A32495173507F43512259367B381154E0DC659490635F2A6')
literal_rows={r['id']:r for r in literal['rows']}
comparison=read(AUDIT/'RULE27_SAVED_CONTEXT_REVIEW_COMPARISON_V2.json',
    '66310BEB5DB859D884CDB1059AB659468E3860D13757AE3D7B08F40EA3E2E75E')
assert comparison['candidates_with_saved_review']==24 and not any(
    key not in {'EXACT_BYTES_AGREE_WITH_SAVED_FULL_CONTEXT_REVIEW',
                'ONLY_TERMINAL_LINE_ENDINGS_DIFFER_FROM_SAVED_REVIEW'} for key in comparison['counts'])
scope_path=AUDIT/'RULE27_BATCH_ADMISSION_F3_F4_V1.md'
assert inv.file_sha(scope_path)=='C5D68659B1CF8E404769D4115E15E6F6F05A9FDF48A30A087C48E6A40B9FAFAC'
scope_pin=dict(path=str(scope_path.relative_to(ROOT)),sha256=inv.file_sha(scope_path))
stage=read(AUDIT/'HOLD_110173_STAGNATION_DIAGNOSIS_V13.json',
    '6413F2B3D328A0032637C4437259987EFC860D7CD0435584F8CD71B155B0BA30')
blocked_ids=set(guard['restricted_ids']); blocked_hashes=set(guard['restricted_hashes'])
body_reuse={}; saved_reviews={}
specs=stage['coverage']+[dict(cohort='root12_independent_admission_counter_v1',version='v39')]
for spec in specs:
    summary=read(inv.BASE/(spec['cohort']+'_snapshots')/spec['version']/'complete.json')
    assert not summary['errors']
    for shard in summary['shards']:
        for row in read(ROOT/shard['path'],shard['sha256']):
            if row.get('decision')=='NEEDS_ROOT':
                blocked_ids.add(row['id'])
                original=row.get('original')
                if original:blocked_hashes.add(original['sha256'])
            if row.get('body') and row.get('clean_text_sha256') not in guard['restricted_hashes']:
                body_reuse.setdefault(row['clean_text_sha256'],row['body'])
            if row.get('review'):
                saved_reviews.setdefault(row['id'],[]).append(row['review'])

directory=ROOT/census['metadata_directory']; inv.verify(directory,census['metadata_manifest'])
out=AUDIT/'ROOT_AUTHORED_SELECTIONS_V34.json'
closure_path=AUDIT/'ROOT34_RULE27_DELTA_CLOSURE_V1.json'
storage_path=AUDIT/'ROOT34_SELECTION_STORAGE_V1.json'
for path in [out,closure_path,storage_path]:assert not path.exists(),str(path)
selected=[]; checks=[]; deferred=[]; body_counts=Counter(); new_positions=0
for row in inv.cache.rows(directory,census['metadata_manifest']):
    if not row['eligible_rule_candidate']:continue
    key=row['id']; original=row['original']; proof=literal_rows[key]
    assert proof['eligible_narrow_literal_delta'] and all(proof['guards'].values())
    assert proof['original']==original and proof['proposed_body_sha256']==row['proposed_body_sha256']
    if key in prior_ids or original['sha256'] in prior_hashes:
        deferred.append(dict(id=key,reason='ALREADY_APPROVED_PRIOR_ROW_PRESERVED_UNCHANGED'));continue
    if (key in blocked_ids or original['sha256'] in blocked_hashes
            or row['prior_candidate']['sha256'] in blocked_hashes):
        deferred.append(dict(id=key,reason='INDIVIDUAL_OR_PROTECTED_HOLD_NOT_AUTOMATICALLY_RELEASED'));continue
    original_path=(ROOT/original['path']).resolve()
    assert original_path.is_relative_to(inv.BASE) and not original_path.is_symlink()
    raw=original_path.read_bytes(); assert hashlib.sha256(raw).hexdigest().upper()==original['sha256']
    source=raw.decode('utf-8')
    proposal=policy.propose(dict(id=key,text=source,complete_eos=True,valid_utf8=True))
    assert proposal['decision']==row['proposed_decision']=='EDIT'
    text=proposal.get('candidate',proposal['text']); body_raw=text.encode('utf-8')
    digest=hashlib.sha256(body_raw).hexdigest().upper()
    assert digest==row['proposed_body_sha256'] and digest not in guard['restricted_hashes']
    recheck=evaluate(source,text)
    assert recheck=={k:proof[k] for k in recheck} and all(recheck['guards'].values())
    assert 0<len(body_raw)<20_000_000
    if digest in body_reuse:
        body_path=(ROOT/body_reuse[digest]).resolve()
        assert body_path.is_relative_to(inv.BASE) and not body_path.is_symlink()
        assert body_path.read_bytes()==body_raw
        body_counts['existing_identical_author_or_rendered_body_reused']+=1
    else:
        body_path=inv.BASE/'rule27_approved_bodies_v1'/digest[:2]/(digest+'.txt')
        assert not body_path.is_symlink()
        if body_path.exists():
            assert body_path.read_bytes()==body_raw
            body_counts['identical_program_body_reused']+=1
        else:
            body_path.parent.mkdir(parents=True,exist_ok=True)
            with body_path.open('xb') as stream:stream.write(body_raw)
            body_counts['new_program_derived_bodies']+=1
            body_counts['new_program_derived_body_bytes']+=len(body_raw)
        body_reuse[digest]=str(body_path.relative_to(ROOT))
    choice=dict(cohort='source_class_rule27_declared_name_lists_v1',decision='EDIT',
        body=str(body_path.relative_to(ROOT)),clean_text_sha256=digest,original=original,
        review=scope_pin,reason='원문이 선언한 목록에서 비어 있는 별칭 구분기호와 실제 빈 EOF 표제만 정리하고 차 있는 문자·이름·숫자·설명·순서를 보존했다.',
        author_output=None,compare_source=None,root_approved=True,
        approval_mode='SOURCE_CLASS_RULE_WITH_ALL_ROW_LITERAL_PROOFS',
        individual_human_full_text_read_claimed=False,program_derived_policy=policy.RULES,
        independent_saved_context_reviews=saved_reviews.get(key,[]))
    selected.append(dict(id=key,original_text_sha256=original['sha256'],selected=choice,
        original_paths=[original],root_approved=True,cache_admitted=False,
        status='ROOT_APPROVED_NARROW_POLICY_DELTA_WITH_SOURCE_CLASS_CONTEXT_AUDIT',
        guard_closure_id='ROOT34_RULE27_DELTA_CLOSURE_V1'))
    checks.append(dict(id=key,original=original,body=dict(path=choice['body'],sha256=digest),
        occurrences=row['occurrences'],guards=recheck['guards'],
        source_populated_stream_sha256=recheck['source_populated_stream_sha256'],
        candidate_populated_stream_sha256=recheck['candidate_populated_stream_sha256'],
        source_empty_eof_appendix_headings=recheck['source_empty_eof_appendix_headings'],
        census_source_proof_count=row['source_proof_count'],census_source_proofs_sha256=row['source_proofs_sha256'],
        approval_mode=choice['approval_mode'],individual_human_full_text_read_claimed=False))
    new_positions+=row['occurrences']
assert len(selected)+len(deferred)==478 and selected
assert_no_protected_opens()
for path in [Path(__file__),scope_path,AUDIT/'verify_rule27_literal_delta_v1.py',
        AUDIT/'RULE27_LITERAL_DELTA_TESTS_V1.log',AUDIT/'selection_metadata_store_v1.py',
        AUDIT/'active_guard_v5_preflight_v1.py',AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V5.json',
        ROOT/'scripts/p106b_hold_resolution_disambiguation_v1.py',
        ROOT/'scripts/p106b_hold_resolution_policy_v27.py']:
    pins[str(path.relative_to(ROOT))]=inv.file_sha(path)
pins[str(prior_path.relative_to(ROOT))]=prior_sha
closure=dict(status='ROOT_RULE27_SOURCE_CLASS_AND_EVERY_LITERAL_DELTA_APPROVED',
    root_approved=True,root_approved_new_sources=len(selected),root_approved_new_positions=new_positions,
    automatic_guard_waivers=0,protected_payload_open_attempts=0,
    active_guard_sha256='01642506DFC284C3097F9E591CA297924A24D5043BF675A7A474FF6B86515338',
    full_individual_human_read_claimed_for_rule_batch=False,independent_saved_full_context_reviews=24,
    additional_root_read_risk_strata=6,root_manual_training_TXT_authored=0,
    program_derived_body_counts=dict(body_counts),checks=checks,deferred=deferred,
    input_pins=pins,cache_admitted=False,goal_complete=False,training_authorized=False)
inv.write_json(closure_path,closure)
all_rows=previous['rows']+selected
document=dict(previous,status='ROOT_APPROVED_COUNTER_AND_NARROW_POLICY_DELTAS_GOAL_INCOMPLETE',
    rows=all_rows,source_ids=len(all_rows),selected_sources=len(all_rows),
    counts=dict(Counter(r['selected']['decision'] for r in all_rows)),
    new_approved_sources=len(selected),new_approved_positions=new_positions,
    closure=dict(path=str(closure_path.relative_to(ROOT)),sha256=inv.file_sha(closure_path)),
    prior_selection=dict(path=str(prior_path.relative_to(ROOT)),sha256=prior_sha),
    prior_selected_rows_preserved_exactly=True,input_pins=dict(pins),
    expected_roster_HOLD_unique=previous['expected_roster_HOLD_unique']-len(selected),
    expected_roster_HOLD_positions=previous['expected_roster_HOLD_positions']-new_positions,
    additional_rule_approved_sources=len(selected),rule_approval_mode='SOURCE_CLASS_RULE_WITH_ALL_ROW_LITERAL_PROOFS',
    whole_corpus_semantic_completion=False,cache_admitted=False,goal_complete=False,training_authorized=False)
storage=SelectionStore(AUDIT).write(out,document,force_sharded=True)
with storage_path.open('xb') as stream:stream.write(encode(storage))
assert_no_protected_opens()
print(json.dumps(dict(selection_sha256=inv.file_sha(out),new_sources=len(selected),
    new_positions=new_positions,deferred=len(deferred),program_body_counts=dict(body_counts),
    expected_HOLD_unique=document['expected_roster_HOLD_unique'],
    expected_HOLD_positions=document['expected_roster_HOLD_positions'],cache_admitted=False),ensure_ascii=False))
