"""Independently parse framed inputs and test role/opaque-source boundaries."""
from collections import Counter
from pathlib import Path
import difflib
import importlib.util
import json
import re
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv
import guarded_scan_metadata_v1 as opaque
from scoped_packet_reader_v1 import read_piece

BASE=inv.BASE;GROUP='root12_independent_admission_counter_v1'
guard_path=AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V3.json'
assert inv.file_sha(guard_path)=='7CF0AA8B46DDAED415851EE5F356B78EFBE12F33530B8217F028F86904594306'
guard=inv.cache.read(guard_path)
assert len(guard['restricted_ids'])==8 and len(guard['restricted_hashes'])==9
assert len(guard['trusted_metadata'])==13
projected=[]
for key in ['expanded_train:28876','historical_train:28876']:
    record=dict(guard['trusted_metadata'][key]);record.pop('parent_decision')
    record.update(ordinal=28876,complete_eos=True,valid_utf8=True,
                  original_signals={},language_proxy={})
    raw=json.dumps(record).encode('ascii')[:-1]+b',"text":"'+bytes([255])+b'"}'
    result=opaque.guarded_row(raw,restricted_ids=set(guard['restricted_ids']),
        restricted_hashes=set(guard['restricted_hashes']),trusted_metadata=guard['trusted_metadata'])
    assert result['restricted_parent_body_not_decoded'] is True and result['text']==''
    projected.append(key)
unknown=raw.replace(b'historical_train:28876',b'historical_train:99999999')
try:
    opaque.guarded_row(unknown,restricted_ids=set(guard['restricted_ids']),
        restricted_hashes=set(guard['restricted_hashes']),trusted_metadata=guard['trusted_metadata'])
except ValueError as exc:
    assert 'frozen metadata' in str(exc)
else:raise AssertionError('unknown protected alias did not fail closed')
manifest_path=BASE/GROUP/'manifest.json'
assert inv.file_sha(manifest_path)=='A71B3109889F32F5969298287C7ADA9B1C223130A8603D87B80D2D910A57527D'
manifest=inv.cache.read(manifest_path)
for name,sha in {**manifest['input_pins'],**manifest['source_code_pins']}.items():
    assert inv.file_sha(ROOT/name)==sha
rows=manifest['rows'];by_id={row['id']:row for row in rows};assert len(rows)==len(by_id)==3688
all_ids=[key for ids in manifest['assignments'].values() for key in ids]
assert len(all_ids)==len(set(all_ids))==3688 and set(all_ids)==set(by_id)
counts=Counter()
for row in rows:
    key=row['id'];assert row['role']!=row['primary_author_role']
    assert key not in guard['restricted_ids']
    assert all(row[label]['sha256'] not in guard['restricted_hashes'] for label in ['original','candidate'])
    values={}
    for label in ['original','candidate']:
        pin=row[label];path=ROOT/pin['path'];assert inv.file_sha(path)==pin['sha256']
        raw=path.read_bytes();values[label]=raw.decode('utf-8')
        assert path.read_text(encoding='utf-8')==values[label],'unrecorded view newline normalization'
    joined=[];cursor=0
    for pin in row['reading_parts']:
        path=ROOT/pin['path'];assert inv.file_sha(path)==pin['sha256']
        fragment=path.read_bytes().decode('utf-8');assert len(fragment)<=2000
        assert pin['characters']==[cursor,cursor+len(fragment)]
        joined.append(fragment);cursor+=len(fragment);counts['packet_files']+=1
    text=''.join(joined);cursor=0;sections={}
    for label in ['original','candidate','full_diff']:
        match=re.match(r'=== BEGIN '+re.escape(key)+' '+label+r' characters=([0-9]+) ==='+chr(10),text[cursor:])
        assert match is not None
        cursor+=match.end();length=int(match[1]);sections[label]=text[cursor:cursor+length];cursor+=length
        end=chr(10)+'=== END '+key+' '+label+' ==='+chr(10)
        assert text[cursor:cursor+len(end)]==end;cursor+=len(end)
    assert cursor==len(text) and sections['original']==values['original']
    if row['byte_identical_body']:
        assert values['original'].encode('utf-8')==values['candidate'].encode('utf-8')
        assert row['original']['sha256']==row['candidate']['sha256']
        assert sections['candidate'].startswith('EXACT_BODY_BYTE_IDENTICAL_TO_FULL_ORIGINAL '+row['original']['sha256'])
        counts['identity_sources']+=1
    else:assert sections['candidate']==values['candidate']
    delta=''.join(difflib.unified_diff(values['original'].splitlines(keepends=True),
        values['candidate'].splitlines(keepends=True),fromfile='original',tofile='prior_selected_body'))
    assert sections['full_diff']==(delta or '비교한 원문과 선택본문의 바이트 및 줄 차이 없음')
    counts.update(sources=1,positions=row['occurrences'])
for role,ids in manifest['assignments'].items():
    registry=AUDIT/('SCOPED_ROOT12_'+role.upper()+'_INPUTS_V1.json');data=inv.cache.read(registry)
    assert set(data['sources'])==set(ids)
    directory=BASE/'agents'/role/GROUP;seen=[]
    for task in sorted(directory.glob('TASK_*.md')):
        declared=re.findall(r'^## ((?:expanded_train|historical_train|validation):[0-9]+)$',task.read_text(),re.M)
        assert 1<=len(declared)<=5;seen+=declared
    assert seen==ids
    other=next(key for key in all_ids if key not in set(ids))
    try:read_piece(registry,inv.file_sha(registry),ROOT,other,1,1)
    except ValueError as exc:assert 'outside this role' in str(exc)
    else:raise AssertionError('cross-role read was not denied')
    first=read_piece(registry,inv.file_sha(registry),ROOT,ids[0],1,1)
    assert first['text'].startswith('=== BEGIN '+ids[0]+' original')
assert counts['sources']==3688 and counts['positions']==6610 and counts['packet_files']==17756
report=dict(status='COUNTER_INPUTS_EXACT_RECONSTRUCTION_AND_ROLE_BOUNDARIES_VERIFIED_NOT_SEMANTIC_ADMISSION',
    counts=dict(counts),metadata_only_protected_alias_positive_tests=projected,
    invalid_UTF8_opaque_fixture_was_not_decoded=True,unknown_protected_alias_denied=True,
    cross_role_source_requests_denied=2,source_or_body_payload_changes=0,
    independent_semantic_admission='PENDING_DELEGATED_REVIEW',
    input_pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in [manifest_path,guard_path,Path(__file__),
        AUDIT/'guarded_scan_metadata_v1.py',AUDIT/'scoped_packet_reader_v1.py']},
    protected_actual_original_or_candidate_TXT_opens=0,new_first_review_credit=0,
    root_adopted=0,cache_admitted=0,goal_complete=False,training_authorized=False)
out=AUDIT/'ROOT12_INDEPENDENT_COUNTER_INPUTS_VERIFIED_V1.json'
assert not out.exists();inv.write_json(out,report)
print(json.dumps(dict(status=report['status'],counts=dict(counts),sha256=inv.file_sha(out))))
