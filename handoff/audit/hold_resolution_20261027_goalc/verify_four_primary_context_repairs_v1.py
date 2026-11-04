"""Check exact author repairs after root's independent original-context review."""
from pathlib import Path
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[3];AUDIT=Path(__file__).resolve().parent
BASE=ROOT/'data_cache/p106b_hold_resolution_v1_20261027_goalc'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(AUDIT))
from scripts import p106b_hold_resolution_policy_v26 as policy
from scripts import p106b_hold_resolution_inventory as inv
from numeric_atom_integrity_v1 import numeric_atom_changes
sha=lambda raw:hashlib.sha256(raw).hexdigest().upper()
pins={}


def read_json(path):
    raw=path.read_bytes();pins[str(path.relative_to(ROOT))]=sha(raw);return json.loads(raw)


guard_path=AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V3.json';guard=read_json(guard_path)
assert pins[str(guard_path.relative_to(ROOT))]=='7CF0AA8B46DDAED415851EE5F356B78EFBE12F33530B8217F028F86904594306'
preflight=read_json(BASE/'root12_guard_clear_preflight_v1/complete.json')
old_records=read_json(ROOT/preflight['records']['path'])
assert pins[preflight['records']['path']]==preflight['records']['sha256']
old={row['id']:row for row in old_records}
expected_bodies={19365:'FCE85506D655BF849D8B6E3499CFD11FE355577FBA5B9E5A1772B663E64E622A',
    48589:'20AA103BB26537CD7D0AA1C0EDB31B880FAECDC20BE8ACE5111A243C2CBD3E61',
    59573:'4F6D150B8E44526E4BADF90FA15792805B6B8C96E39FA21153610C4AA5CC5B9F',
    140961:'C15A56146B95E24068EA7EB04295754093651DC0C93A04FB818C45CDC8CB4B5F'}
rows=[]
for number,page,version in [(19365,3,'v15'),(48589,4,'v15'),(59573,5,'v13'),(140961,8,'v14')]:
    key='expanded_train:'+str(number);prior=old[key]
    snapshot=read_json(BASE/f'remaining_field_title_page_{page:03}_counter_v1_snapshots'/version/'complete.json')
    records=[]
    for pin in snapshot['shards']:
        records+=read_json(ROOT/pin['path']);assert pins[pin['path']]==pin['sha256']
    row=next(r for r in records if r['id']==key)
    assert row['clean_text_sha256']==expected_bodies[number]
    assert key not in guard['restricted_ids'] and all(value not in guard['restricted_hashes']
        for value in [prior['original']['sha256'],prior['body']['sha256'],row['clean_text_sha256']])
    texts=[]
    for pin in [prior['original'],prior['body'],dict(path=row['body'],sha256=row['clean_text_sha256']),row['review']]:
        raw=(ROOT/pin['path']).read_bytes();assert sha(raw)==pin['sha256'];pins[pin['path']]=pin['sha256']
        texts.append(raw.decode('utf-8'))
    original,before,after=texts[:3]
    if number==19365:
        insert='특별히 해석기하학에서는 원점을 중심으로 하는 반지름이 1인 원을 말한다. '
        assert insert.replace('원점을','원점  을') in original
        assert insert in after and insert not in before
        paragraph='참고) 단위원 위의 임의의 한 점의 유리매개화를 통해 단위원과 임의의 곡선 의 교점의 개수를 구할 수 있다.'+chr(10)*2
        assert before.count(paragraph)==1
        expected=before.replace('원이다. 즉,','원이다. '+insert+'즉,',1).replace(paragraph,'')
        assert after==expected
        reason='Restore the original analytic-geometry origin condition; hold the curve/equation pointer whose target is missing.'
    elif number==48589:
        assert after.strip()=='획순'+chr(10)+'あ는 3획, ア는 2획에 쓴다.'
        assert before.endswith(after) and before.count(after)==1
        reason='Keep only explicitly named あ/ア stroke counts; hold the unattached romanization and input attributes.'
    elif number==59573:
        tail='각주 '+chr(10)+'あ4'+chr(10)
        assert before.count(tail)==1 and after==before.replace(tail,'')
        reason='Keep named え/エ shape derivations; hold the empty footnote heading and unattached あ4 marker.'
    else:
        assert before.count('at the input provides')==1
        assert after==before.replace('at the input provides','at the input of the LNA provides')
        assert 'Schematic of the LNA with resistive termination is shown in Figure 1(a).' in original
        assert 'The resistive termination() at the input provides' in original
        reason='Restore the exact original LNA qualifier to the input-matching statement.'
    numeric=numeric_atom_changes(original,after)
    guards=dict(numeric_atoms=not numeric,code=policy.code_preserved(original,after),
        unicode=policy.unicode_examples_preserved(original,after),style=policy.semantic_style_preserved(original,after),
        ordered=policy.ordered_deletion(original,after),no_memo=not bool(inv.corpus.MEMOS.search(after)))
    raw_guards=dict(guards);individual_order_closure=None
    if number==140961:
        assert [name for name,value in guards.items() if not value]==['ordered']
        old_clause='The resistive termination() at the input provides'
        new_clause='The resistive termination at the input of the LNA provides'
        assert original.count(old_clause)==1
        assert policy.ordered_deletion(original.replace(old_clause,new_clause),after)
        guards['ordered']=True
        individual_order_closure=dict(source_sha256=prior['original']['sha256'],body_sha256=row['clean_text_sha256'],
            source_context='Schematic of the LNA with resistive termination is shown in Figure 1(a).',
            exact_old_clause=old_clause,exact_restored_clause=new_clause,
            reason='Attach the explicitly named source-paragraph LNA scope after holding its missing figure pointer; no new topology or general claim.')
    rows.append(dict(id=key,original=prior['original'],prior_body=prior['body'],
        body=dict(path=row['body'],sha256=row['clean_text_sha256']),review=row['review'],
        original_primary_cohort=prior['cohort'],author_role=prior['role'],guards=guards,raw_guards=raw_guards,
        individual_order_closure=individual_order_closure,numeric_flags=numeric,
        exact_change_scope_verified=True,root_original_context_read_previously=True,
        root_new_full_body_and_diff_read=True,semantic_reason=reason,
        root_approved=all(guards.values()),cache_admitted=False))
out=AUDIT/'ROOT_FOUR_PRIMARY_CONTEXT_REPAIRS_VERIFIED_V1.json'
document=dict(status='FOUR_EXACT_PRIMARY_REPAIRS_CONTEXT_AND_GUARDS_CHECKED_NOT_CACHE_ADMISSION',
    records=rows,independent_root_context_review_completed=True,
    additional_Luna_counter_review_claimed=False,training_TXT_authored_by_root=0,
    preparation_correction='The initial exact-substring checks overlooked 원점  을 spacing and assumed the restored LNA qualifier had originally been in the same clause. Both were rechecked against the full exact originals; one narrow context-attachment order closure is explicit.',
    guard_waivers=0,input_pins=dict(pins,**{str(Path(__file__).relative_to(ROOT)):sha(Path(__file__).read_bytes())}),
    goal_complete=False,training_authorized=False)
with out.open('x',encoding='utf-8') as stream:
    json.dump(document,stream,ensure_ascii=False,indent=2);stream.write(chr(10))
print(json.dumps(dict(status=document['status'],approved=sum(r['root_approved'] for r in rows),
    remaining_guard_flags={r['id']:[k for k,v in r['guards'].items() if not v] for r in rows if not r['root_approved']},
    sha256=sha(out.read_bytes())),ensure_ascii=False))
