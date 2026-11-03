"""Record two individually adjudicated nonadmissions with honest reading scopes."""
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

contract_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
contract = inv.cache.read(contract_path)
resolve, parse, parser_sha = load_parser()
pins = {str(contract_path.relative_to(ROOT)): inv.file_sha(contract_path),
        str(FROZEN.relative_to(ROOT)): parser_sha}
specs = [
    dict(id='expanded_train:49092', page=4, review='review_020_v2.md',
         sidecar='hold_49092_mixed_scraped_text_unresolved_20261104_v2.md',
         full_root_original=False, original_characters=49649,
         reason_code='DISTRIBUTED_FOREIGN_ENTRY_INSERTIONS_AND_BROKEN_SCRAPE_CONTEXT',
         reason='외계생명 서술 안에 EARTH 음악그룹·Greek/Thales·disambiguation·GEnie·틀 조각 등 독립 항목의 문구가 넓게 혼입되어 있다. 이 고정 원문의 신뢰할 수 있는 본문 경계를 복원하지 못해 전체를 학습 후보에서 분리한다. 단어가 패킷 경계에서 나뉜 현상은 손상 근거로 쓰지 않는다.',
         root_read_chunks=['755329', 'aec7de', '1b5271', '3996b1'],
         root_read_scope='원문 처음/중간/말미 및 대표 네 연속 문맥; 정정된 sidecar 전문. 총괄 원문 전량 판독 주장은 하지 않는다.'),
    dict(id='expanded_train:50689', page=5, review='review_001.md',
         sidecar='hold_50689_unidentified_kana_subject_20261104_v1.md',
         full_root_original=True, original_characters=966,
         reason_code='MAIN_GLYPHS_LOST_AND_REMAINING_PROPERTIES_UNBOUND',
         reason='핵심 두 글리프와 행·단이 소실되어 i·이·순위·모스부호도 독립 주체에 귀속되지 않는다. 자형 유래의 실제 伊/イ로 선두 대상을 추정하지 않고 원형 전체를 보존해 분리한다.',
         root_read_chunks=['ccd068', 'f2868a'],
         root_read_scope='원문966자 전체와 원형 전문이 든 sidecar 전체.')]
rows = []
for item in specs:
    cohort = f"remaining_field_title_page_{item['page']:03}_counter_v1"
    manifest_path = inv.BASE / cohort / 'manifest.json'
    manifest = inv.cache.read(manifest_path)
    sources = {row['id']: row for row in manifest['rows']}
    source = sources[item['id']]
    assert source['role'] == 'historical_review'
    # Both identities must pass before any original/candidate/sidecar body is opened.
    assert source['id'] not in contract['restricted_ids']
    assert source['original']['sha256'] not in contract['restricted_hashes']
    for label in ('original', 'candidate'):
        path = ROOT / source[label]['path']
        assert not path.is_symlink() and path.resolve().is_relative_to(inv.BASE)
        assert inv.file_sha(path) == source[label]['sha256']
    original = (ROOT / source['original']['path']).read_text(encoding='utf-8')
    assert len(original) == item['original_characters']
    directory = inv.BASE / 'agents/historical_review' / cohort
    review_path, sidecar_path = directory / item['review'], directory / item['sidecar']
    entry = exact_entry(review_path.read_bytes(), item['id'], set(sources), resolve, parse)
    assert entry['cells'][1] == 'NEEDS_ROOT'
    exact_reason_note = re.search(r'(?<![\w.-])' + re.escape(item['sidecar']) + r'(?![\w.-])', entry['cells'][4])
    assert entry['cells'][3] == item['sidecar'] or (entry['cells'][3] in {'—', '-'} and exact_reason_note)
    note = sidecar_path.read_text(encoding='utf-8')
    quotes = re.findall(r'```text\n(.*?)\n```', note, re.S)
    assert quotes and all(quote in original for quote in quotes), 'sidecar quote differs from continuous original'
    if item['id'].endswith(':50689'):
        assert len(quotes) == 1 and quotes[0] == original.rstrip(chr(10))
    else:
        assert len(quotes) == 4
        assert all(word in note for word in ('infinite', 'current', 'carrying', '정정'))
    quote_ranges = [[original.index(quote), original.index(quote) + len(quote)] for quote in quotes]
    review_pin = dict(path=str(review_path.relative_to(ROOT)), sha256=inv.file_sha(review_path))
    note_pin = dict(path=str(sidecar_path.relative_to(ROOT)), sha256=inv.file_sha(sidecar_path))
    rows.append(dict(id=item['id'], source=source['source'],
                     source_ids=source['source_ids'], source_ids_sha256=source['source_ids_sha256'],
                     input_ids=source['input_ids'], occurrences=source['occurrences'],
                     original=source['original'], candidate=source['candidate'],
                     decision='HOLD', root_approved_hold_decision=True,
                     reason_code=item['reason_code'], reason=item['reason'],
                     author_first_review=review_pin, author_exact_review_row=entry['raw'],
                     author_declared_full_original_read=True, sidecar=note_pin,
                     source_quote_character_ranges=quote_ranges,
                     second_review=dict(reviewer='root', full_original_read=item['full_root_original'],
                                        actual_read_scope=item['root_read_scope'], chunks=item['root_read_chunks']),
                     clean_text_path=None, clean_text_sha256=None, cache_admitted=False,
                     raw_source_preserved=True, permanent_recovery_impossible_claim=False,
                     all_web_or_original_dumps_exhausted=False,
                     status='INDIVIDUALLY_REVIEWED_WHOLE_HOLD_PENDING_NEW_ROSTER_JOIN'))
    for path in (manifest_path, review_path, sidecar_path):
        pins[str(path.relative_to(ROOT))] = inv.file_sha(path)
for path in (Path(__file__).resolve(), AUDIT / 'exact_manifest_review_row_binding_v1.py'):
    pins[str(path.relative_to(ROOT))] = inv.file_sha(path)
result = dict(status='TWO_CURRENT_FIELD_WHOLE_NONADMISSIONS_ADJUDICATED', rows=rows,
              unique_sources=2, source_positions=sum(row['occurrences'] for row in rows),
              raw_input_ids=sum(row['input_ids'] * row['occurrences'] for row in rows),
              input_pins=pins, new_roster_joined=False, root_authored_training_bodies=0,
              protected_body_reads=0, official_verified_cache_hold_positions_unchanged=110173,
              goal_complete=False, training_authorized=False)
target = AUDIT / 'CURRENT_FIELD_WHOLE_HOLD_ADJUDICATIONS_V1.json'
with target.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
print(json.dumps(dict(status=result['status'], unique_sources=2,
                     positions=result['source_positions'], root_authored_training_bodies=0), ensure_ascii=False))
