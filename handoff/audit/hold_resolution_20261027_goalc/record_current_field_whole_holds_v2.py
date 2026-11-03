"""Append one fully read, individually adjudicated glyph-loss nonadmission."""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv
from exact_manifest_review_row_binding_v1 import exact_entry, load_parser, FROZEN

prior_path = AUDIT / 'CURRENT_FIELD_WHOLE_HOLD_ADJUDICATIONS_V1.json'
manifest_path = inv.BASE / 'remaining_field_title_page_005_counter_v1/manifest.json'
contract_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
prior, manifest, contract = map(inv.cache.read, (prior_path, manifest_path, contract_path))
sources = {row['id']: row for row in manifest['rows']}
source = sources['expanded_train:56714']
assert source['role'] == 'historical_review'
assert source['id'] not in contract['restricted_ids']
assert source['original']['sha256'] not in contract['restricted_hashes']
for label in ('original', 'candidate'):
    path = ROOT / source[label]['path']
    assert not path.is_symlink() and path.resolve().is_relative_to(inv.BASE)
    assert inv.file_sha(path) == source[label]['sha256']
raw = (ROOT / source['original']['path']).read_text(encoding='utf-8')
assert len(raw) == 752 and source['original']['sha256'] == source['candidate']['sha256']
directory = inv.BASE / 'agents/historical_review/remaining_field_title_page_005_counter_v1'
review_path = directory / 'review_007.md'
sidecar_path = directory / 'hold_56714_full_source_unattributed_glyph_20261104_v3.md'
resolve, parse, parser_sha = load_parser()
entry = exact_entry(review_path.read_bytes(), source['id'], set(sources), resolve, parse)
assert entry['cells'][1] == 'NEEDS_ROOT' and entry['cells'][3] == sidecar_path.name
note = sidecar_path.read_text(encoding='utf-8')
block = re.findall(r'=== BEGIN expanded_train:56714 original characters=752 ===\n(.*?)\n=== END expanded_train:56714 original ===', note, re.S)
assert len(block) == 1 and block[0] == raw.rstrip(chr(10))
row = dict(id=source['id'], source=source['source'], source_ids=source['source_ids'],
           source_ids_sha256=source['source_ids_sha256'], input_ids=source['input_ids'],
           occurrences=source['occurrences'], original=source['original'], candidate=source['candidate'],
           decision='HOLD', root_approved_hold_decision=True,
           reason_code='MAIN_GLYPHS_AND_REFERENCED_PRONUNCIATION_TARGETS_LOST',
           reason='첫 주제 글리프와 행·단/발음·자형 대상이 소실되어 e/we·순위·모스부호·惠/衛 유래를 독립 주체에 귀속하지 못한다. 남은 유래 구성요소로 원래 글리프를 추정하지 않고 전체 원형을 분리한다.',
           author_first_review=dict(path=str(review_path.relative_to(ROOT)), sha256=inv.file_sha(review_path)),
           author_exact_review_row=entry['raw'], author_declared_full_original_read=True,
           sidecar=dict(path=str(sidecar_path.relative_to(ROOT)), sha256=inv.file_sha(sidecar_path)),
           source_quote_character_ranges=[[0, len(raw.rstrip(chr(10)))]],
           second_review=dict(reviewer='root', full_original_read=True,
                              actual_read_scope='원문752자 전체와 정확 원형을 옮긴sidecar v3 전체',
                              chunks=['42dedc', '088dfe']),
           raw_sidecar_history='v1/v2 contained manual-copy errors and are preserved but not selected',
           clean_text_path=None, clean_text_sha256=None, cache_admitted=False,
           raw_source_preserved=True, permanent_recovery_impossible_claim=False,
           all_web_or_original_dumps_exhausted=False,
           status='INDIVIDUALLY_REVIEWED_WHOLE_HOLD_PENDING_NEW_ROSTER_JOIN')
rows = [*prior['rows'], row]
assert len(rows) == len({item['id'] for item in rows}) == 3
paths = [prior_path, manifest_path, contract_path, review_path, sidecar_path, Path(__file__).resolve(),
         AUDIT / 'exact_manifest_review_row_binding_v1.py']
result = dict(status='THREE_CURRENT_FIELD_WHOLE_NONADMISSIONS_ADJUDICATED', rows=rows,
              unique_sources=3, source_positions=sum(item['occurrences'] for item in rows),
              raw_input_ids=sum(item['input_ids'] * item['occurrences'] for item in rows),
              input_pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in paths},
              canonical_parser_pin=dict(path=str(FROZEN.relative_to(ROOT)), sha256=parser_sha),
              new_roster_joined=False, root_authored_training_bodies=0, protected_body_reads=0,
              official_verified_cache_hold_positions_unchanged=110173,
              goal_complete=False, training_authorized=False)
output = AUDIT / 'CURRENT_FIELD_WHOLE_HOLD_ADJUDICATIONS_V2.json'
with output.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
print(json.dumps(dict(status=result['status'], sources=3, positions=result['source_positions'],
                     root_or_cache_adoptions=0), ensure_ascii=False))
