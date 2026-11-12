"""Recheck all admitted rule27 sources against a newly observed counterexample."""
from pathlib import Path
import hashlib
import json
import sys

AUDIT=Path(__file__).resolve().parent;ROOT=AUDIT.parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(AUDIT))
from active_guard_v5_preflight_v1 import activate,checked_contract,assert_no_protected_opens
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_disambiguation_v2 as structural

activate();guard=checked_contract()
census_path=AUDIT/'RULE27_DECLARED_NAME_LIST_CENSUS_V1.json'
assert inv.file_sha(census_path)=='0BBAF7B7B05B9F922ED780BA75A1529018934ADB0B899375E2C760F0194A40C6'
census=json.loads(census_path.read_bytes());findings=[];seen=0
for row in inv.cache.rows(ROOT/census['metadata_directory'],census['metadata_manifest']):
    if not row['eligible_rule_candidate']:continue
    pin=row['original'];assert pin['sha256'] not in guard['restricted_hashes']
    path=(ROOT/pin['path']).resolve();assert path.is_relative_to(inv.BASE) and not path.is_symlink()
    raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest().upper()==pin['sha256'];text=raw.decode('utf-8')
    unnamed=structural.unnamed_value_row(text);unbalanced=not structural.balanced_prose_parentheses(text)
    if unnamed or unbalanced:findings.append(dict(id=row['id'],original=pin,unnamed_value_row=unnamed,unbalanced_parentheses=unbalanced))
    seen+=1
assert seen==478 and len(findings)==1 and findings[0]['id']=='expanded_train:1045103'
review=inv.BASE/'agents/legacy_review/remaining_field_title_page_030_counter_v1/review_1045103_independent_context_20261112_v1.md'
review_text=review.read_text(encoding='utf-8')
assert '1045103' in review_text and '다음 사람' in review_text
findings[0].update(root_full_original_and_selected_body_read=True,
    independent_role='legacy_review',independent_review=dict(path=str(review.relative_to(ROOT)),sha256=inv.file_sha(review)),
    context_outcome='PRESERVE_EXPLICIT_SHARED_NAME_LIST_HIERARCHY_WITHOUT_INVENTING_A_NAME',
    explanation='원문 표제가 존 리처드슨이라는 같은 이름의 다음 사람들을 명시한다. 생몰연대와 직업이 적힌 두 번째 행은 그 목록 아래의 생략 이름 항목으로 해석 가능하며 새 정제본은 그 계층과 모든 값을 그대로 보존했다. 다른 비명시 이름목록을 같은 이유로 일반 해제하지 않는다.',
    source_name_or_value_invented=False,selected_body_changed=False)
assert_no_protected_opens()
inputs=[Path(__file__),census_path,review,ROOT/'scripts/p106b_hold_resolution_disambiguation_v2.py',
    AUDIT/'ROOT34_RULE27_SELECTION_INDEPENDENT_VERIFIED_V1.json',AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V5.json']
receipt=dict(status='ALL_RULE27_SOURCES_RESCANNED_AND_ONE_STRUCTURAL_FLAG_INDEPENDENTLY_CONTEXT_CLOSED',
    verified_sources=seen,structural_flags=len(findings),unresolved_flags=0,findings=findings,
    guard_rule_not_globally_waived=True,source_or_selected_body_modified=False,
    input_pins={str(p.relative_to(ROOT)):inv.file_sha(p) for p in inputs},
    goal_complete=False,training_authorized=False)
inv.write_json(AUDIT/'RULE27_NEW_UNNAMED_ROW_COUNTEREXAMPLE_RESCAN_V1.json',receipt)
print(json.dumps({k:receipt[k] for k in ['status','verified_sources','structural_flags','unresolved_flags']},ensure_ascii=False))
