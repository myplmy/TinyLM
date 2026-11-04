"""Verify exact header and path repairs without opening corpus text."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[3];A=Path(__file__).resolve().parent
B=ROOT/'data_cache/p106b_hold_resolution_v1_20261027_goalc';pins={}


def read(path,expected=None):
    assert not path.is_symlink()
    raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest().upper()
    if expected is not None:assert digest==expected,str(path)
    pins[str(path.relative_to(ROOT))]=digest
    return json.loads(raw)


def snapshot(version,expected):
    d=read(B/'root12_independent_admission_counter_v1_snapshots'/version/'complete.json',expected)
    rows=[]
    for pin in d['shards']:rows+=read(ROOT/pin['path'],pin['sha256'])
    by={row['id']:row for row in rows};assert len(by)==len(rows)==d['records']
    return d,by


old,before=snapshot('v14','CA4642E7AB2A77C0A2FF35DA8E093107B3A2B131092C133C93F2384C46619D6D')
mid,middle=snapshot('v15','D98F067EA09E9290B84A64F420465918E651CEF6D6EF9C3694B806DEA42FEF0F')
new,after=snapshot('v16','441444B92FDC7C59DDB82EBB1DB2ADF9EA1D89DD9BFBA4B6DF369C3CD6E2F648')
assert not new['errors'] and not new['invalid_task_rows'] and not new['unparsed_review_history']
assert new['unreviewed_payload_open_attempts']==0
assert all(row.get('read_scope','').strip() and row.get('reason','').strip() for row in after.values())
affected={key:row for key,row in before.items() if not row.get('read_scope') or not row.get('reason')}
assert len(affected)==115
assert len({row['review']['path'] for row in affected.values()})==23
header=b'| source_id | decision | actual read scope | exact output | evidence |'
seen=set();unchanged_bodies=0
for key,row in affected.items():
    current=after[key];assert current['read_scope'] and current['reason']
    review=ROOT/row['review']['path']
    if review not in seen:
        raw=review.read_bytes();assert hashlib.sha256(raw).hexdigest().upper()==row['review']['sha256']
        assert raw.splitlines()[0]==header;seen.add(review);pins[str(review.relative_to(ROOT))]=row['review']['sha256']
    if row.get('body'):
        assert row['body']==current['body'] and row['clean_text_sha256']==current['clean_text_sha256'];unchanged_bodies+=1
    if not row['review']['path'].endswith('/review_160.md'):
        assert row['review']==current['review']
assert unchanged_bodies==114
assert {row['id'] for row in old['errors']}=={'expanded_train:8561'}
assert {row['id'] for row in mid['errors']}=={'expanded_train:914931'}
manifest=read(B/'root12_independent_admission_counter_v1/manifest.json','A71B3109889F32F5969298287C7ADA9B1C223130A8603D87B80D2D910A57527D')
sources={row['id']:row for row in manifest['rows']}
for key in ['expanded_train:8561','expanded_train:914931']:
    row=after[key];source=sources[key]
    assert row['decision']=='ADOPT_CANDIDATE' and not row.get('error')
    assert row['clean_text_sha256']==source['candidate']['sha256']
    assert row['body']==source['candidate']['path']
    review=ROOT/row['review']['path'];raw=review.read_bytes()
    assert hashlib.sha256(raw).hexdigest().upper()==row['review']['sha256'];pins[str(review.relative_to(ROOT))]=row['review']['sha256']
    assert str(ROOT/source['candidate']['path']) in row['declared_output_cell']
for name in ['exact_review_header_alias_v1.py','exact_review_header_alias_v2.py','exact_review_header_alias_v3.py','collect_root12_counter_v4.py',Path(__file__).name]:
    path=A/name;pins[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest().upper()
result=dict(status='EXACT_REVIEW_HEADER_METADATA_AND_ASSIGNED_PATH_REBINDING_VERIFIED',snapshot='v16',saved_rows=1675,old_missing_scope_or_reason_rows=115,old_english_header_reviews=23,current_missing_scope_or_reason_rows=0,existing_valid_bodies_unchanged=114,corrected_assigned_output_paths=2,errors=0,invalid_task_rows=0,unreviewed_source_payload_opens=0,corpus_original_or_body_opens=0,content_guard_changes=0,root_or_cache_new_admissions=0,input_pins=pins,goal_complete=False,training_authorized=False)
raw=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8');assert len(raw)<20000000
with (A/'COUNTER_HEADER_AND_PATH_REBINDING_INDEPENDENT_VERIFIED_V1.json').open('xb') as handle:handle.write(raw)
print(json.dumps({'status':result['status'],'sha256':hashlib.sha256(raw).hexdigest().upper()}))
