"""Append one source-scoped mixed-snippet nonadmission with exact raw copy."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv
from exact_manifest_review_row_binding_v1 import exact_entry, load_parser, FROZEN

prior_path = AUDIT / 'CURRENT_FIELD_WHOLE_HOLD_ADJUDICATIONS_V2.json'
manifest_path = inv.BASE / 'remaining_field_title_page_008_counter_v1/manifest.json'
contract_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
assert inv.file_sha(contract_path) == 'CE929E1C714E5419A78FF22481A6F990F0B27C813204F4B3B94CC8D58E73D6EF'
prior, manifest, contract = map(inv.cache.read, (prior_path, manifest_path, contract_path))
sources = {row['id']: row for row in manifest['rows']}
source = sources['expanded_train:125306']
assert source['role'] == 'context_hangul'
assert source['id'] not in contract['restricted_ids']
assert source['original']['sha256'] not in contract['restricted_hashes']
assert source['original']['sha256'] == 'FB6351C129C09C2CA2FD4712DE116320D23BC56865F2B9A266DFAE7CB58FD900'
for label in ('original', 'candidate'):
    path = ROOT / source[label]['path']
    assert not path.is_symlink() and path.resolve().is_relative_to(inv.BASE)
    assert inv.file_sha(path) == source[label]['sha256']
assert source['original']['sha256'] == source['candidate']['sha256']
raw = (ROOT / source['original']['path']).read_bytes()
assert len(raw.decode('utf-8')) == 2806
directory = inv.BASE / 'agents/context_hangul/remaining_field_title_page_008_counter_v1'
review_path = directory / 'review_009.md'
sidecar_path = directory / 'hold_125306_task009.md'
copy_path = directory / 'hold_125306_task009_original.txt'
assert copy_path.read_bytes() == raw
resolve, parse, parser_sha = load_parser()
entry = exact_entry(review_path.read_bytes(), source['id'], set(sources), resolve, parse)
assert entry['cells'][1] == 'NEEDS_ROOT' and entry['cells'][3] == '—'
assert copy_path.name in entry['raw'] and sidecar_path.name in entry['raw']
note = sidecar_path.read_text(encoding='utf-8')
assert copy_path.name in note and '# 125306 전체 원문 보류' in note
row = dict(id=source['id'], source=source['source'], source_ids=source['source_ids'],
           source_ids_sha256=source['source_ids_sha256'], input_ids=source['input_ids'],
           occurrences=source['occurrences'], original=source['original'], candidate=source['candidate'],
           decision='HOLD', root_approved_hold_decision=True,
           reason_code='MIXED_SNIPPETS_AND_AUTHOR_BOUNDARIES_NOT_RECOVERABLE_FROM_THIS_INPUT',
           reason='화해 도입과 세계화 환경설명·Essay/토론/검색 스니펫·평점·가정점검·Hypothesis가 이어지고 반복 도중 끼어듦과 미완 목적어가 남아 문장별 출처·귀속을 닫지 못한다. 일부 문장을 새로운 단일 본문으로 재조립하지 않고 이 한 원문을 분리한다.',
           author_first_review=dict(path=str(review_path.relative_to(ROOT)), sha256=inv.file_sha(review_path)),
           author_exact_review_row=entry['raw'], author_declared_full_original_read=True,
           sidecar=dict(path=str(sidecar_path.relative_to(ROOT)), sha256=inv.file_sha(sidecar_path)),
           exact_original_copy=dict(path=str(copy_path.relative_to(ROOT)), sha256=inv.file_sha(copy_path)),
           second_review=dict(reviewer='root', full_original_read=True,
                              actual_read_scope='원문2806자 전문·정확review행·보류사유MD와 원형사본 바이트',
                              chunks=['e60953', '06501b', '9a056b']),
           clean_text_path=None, clean_text_sha256=None, cache_admitted=False,
           raw_source_preserved=True, permanent_recovery_impossible_claim=False,
           all_web_or_original_dumps_exhausted=False,
           status='INDIVIDUALLY_REVIEWED_WHOLE_HOLD_PENDING_NEW_ROSTER_JOIN')
rows = [*prior['rows'], row]
assert len(rows) == len({item['id'] for item in rows}) == 4
paths = [prior_path, manifest_path, contract_path, review_path, sidecar_path, copy_path,
         Path(__file__).resolve(), AUDIT / 'exact_manifest_review_row_binding_v1.py']
result = dict(status='FOUR_CURRENT_FIELD_WHOLE_NONADMISSIONS_ADJUDICATED', rows=rows,
              unique_sources=4, source_positions=sum(item['occurrences'] for item in rows),
              raw_input_ids=sum(item['input_ids'] * item['occurrences'] for item in rows),
              input_pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in paths},
              canonical_parser_pin=dict(path=str(FROZEN.relative_to(ROOT)), sha256=parser_sha),
              new_roster_joined=False, root_authored_training_bodies=0, protected_body_reads=0,
              official_verified_cache_hold_positions_unchanged=110173,
              goal_complete=False, training_authorized=False)
with (AUDIT / 'CURRENT_FIELD_WHOLE_HOLD_ADJUDICATIONS_V3.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps(dict(status=result['status'], sources=4, positions=result['source_positions'],
                     root_or_cache_adoptions=0), ensure_ascii=False))
