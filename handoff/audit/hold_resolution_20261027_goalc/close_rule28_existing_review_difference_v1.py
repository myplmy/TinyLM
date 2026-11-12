"""Close one observed prose-layout difference without a global whitespace waiver."""
from pathlib import Path
import json
import hashlib
import sys

AUDIT=Path(__file__).resolve().parent;ROOT=AUDIT.parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(AUDIT))
from active_guard_v5_preflight_v1 import activate,checked_contract,assert_no_protected_opens
from scripts import p106b_hold_resolution_policy_v28 as policy
from scripts import p106b_hold_resolution_inventory as inv

activate();guard=checked_contract()
path=AUDIT/'RULE28_SAVED_CONTEXT_REVIEW_COMPARISON_V1.json'
assert inv.file_sha(path)=='9F59A2CFDFE2A7F66273A1859A5416876B268D2088F0CFFFA57E81FBD9787F95'
comparison=json.loads(path.read_bytes());different=[r for r in comparison['rows']
    if r['outcome']=='DIFFERENT_BODY_REQUIRES_ROOT_CONTEXT_REVIEW']
assert len(different)==1 and different[0]['id']=='expanded_train:346999'
row=different[0];pin=row['original'];assert pin['sha256'] not in guard['restricted_hashes']
raw=(ROOT/pin['path']).read_bytes();assert hashlib.sha256(raw).hexdigest().upper()==pin['sha256']
source=raw.decode('utf-8');value=policy.propose(dict(id=row['id'],text=source,complete_eos=True,valid_utf8=True))
rule=value.get('candidate',value['text']);assert inv.sha(rule)==row['rule_body_sha256']
manual_path=ROOT/row['saved_body'];manual_raw=manual_path.read_bytes()
assert hashlib.sha256(manual_raw).hexdigest().upper()==row['saved_body_sha256']
manual=manual_raw.decode('utf-8')
assert [line.strip() for line in rule.splitlines() if line.strip()]==[line.strip() for line in manual.splitlines() if line.strip()]
assert not any(mark in source for mark in [chr(96),'|','<','>'])
assert source.startswith('연산동()의 다른 뜻은 다음과 같다.')
assert len([line for line in rule.splitlines() if line.strip()])==4
assert inv.file_sha(ROOT/row['saved_review']['path'])==row['saved_review']['sha256']
assert_no_protected_opens()
receipt=dict(status='RULE28_EXACT_OBSERVED_PROSE_LAYOUT_DIFFERENCE_CONTEXT_CLOSED',
    comparison=dict(path=str(path.relative_to(ROOT)),sha256=inv.file_sha(path)),
    closed_exact_ids=[row['id']],unresolved_differences=0,
    closures=[dict(id=row['id'],original=pin,rule_body_sha256=row['rule_body_sha256'],
        saved_body_sha256=row['saved_body_sha256'],saved_review=row['saved_review'],
        context='동음이의 목록의 세 연산동 지명 항목에서 선행 공백1개와 끝 빈줄만 다르다. 모든 한자·행정구분·동 번호·문장·항목 순서가 같으며 코드/중첩목록/표가 아니다.',
        root_full_source_and_both_bodies_and_diff_read=True)],
    generic_whitespace_or_code_guard_waiver=False,body_modified=False,
    input_pins={str(p.relative_to(ROOT)):inv.file_sha(p) for p in [Path(__file__),path,
        ROOT/row['saved_review']['path'],ROOT/'scripts/p106b_hold_resolution_policy_v28.py']},
    goal_complete=False,training_authorized=False)
inv.write_json(AUDIT/'RULE28_SAVED_CONTEXT_REVIEW_DIFFERENCE_CLOSURE_V1.json',receipt)
print(json.dumps(dict(closed_exact_ids=receipt['closed_exact_ids'],unresolved_differences=0,
    closure_sha256=inv.file_sha(AUDIT/'RULE28_SAVED_CONTEXT_REVIEW_DIFFERENCE_CLOSURE_V1.json'))))
