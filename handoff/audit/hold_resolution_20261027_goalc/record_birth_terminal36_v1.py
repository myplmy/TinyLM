"""Join only individually read unnamed sources into reviewed HOLD evidence."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

prior_path = AUDIT / 'ROOT_REVIEWED_TERMINAL_HOLD19_V1.json'
prior = inv.cache.read(prior_path)
manifest_path = inv.BASE / 'remaining_birth_full_counter_v1/manifest.json'
sources = {r['id']: r for r in inv.cache.read(manifest_path)['rows']}
snapshot_path = inv.BASE / 'remaining_birth_full_counter_v1_snapshots/v10/complete.json'
snapshot = inv.cache.read(snapshot_path)
saved = {}
for shard in snapshot['shards']:
    assert inv.file_sha(ROOT / shard['path']) == shard['sha256']
    saved.update({r['id']: r for r in inv.cache.read(ROOT / shard['path'])})
contract = inv.cache.read(AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json')
numbers = '1252027 1253251 1253259 1253395 1253627 1254094 1254374 1254530 1254897 1255075 1255513 1252412 1253135 1253510 1253556 1255242 1252918'.split()
rows = list(prior['rows'])
for number in numbers:
    row = sources['expanded_train:' + number]
    assert row['id'] not in contract['restricted_ids']
    assert row['original']['sha256'] not in contract['restricted_hashes']
    assert inv.file_sha(ROOT / row['original']['path']) == row['original']['sha256']
    raw = (ROOT / row['original']['path']).read_text(encoding='utf-8')
    assert 0 < len(raw) < 1600 and raw.lstrip().startswith('(')
    review = saved[row['id']]
    assert review['decision'] == 'NEEDS_ROOT' and not review.get('body')
    detail = '도입 인명이 비고 축구 선수 소개·빈 절·분류만 있어 같은 주체의 독립 학습 본문이 없다.'
    if number == '1255513':
        detail = ('참고 자료의 기사 제목에는 박두흥 등 여러 인명이 실제 남아 있지만, '
                  '도입의 소실된 인물이 그 중 누구인지는 원문에서 확정되지 않는다. '
                  '두 기사 제목은 원형에 보존한다. 표적 검색 두 차례에서 일치하는 발행처 자료를 '
                  '확인하지 못했으며 전 웹 또는 모든 덤프의 복구 불가능을 주장하지 않는다.')
    rows.append(dict(id=row['id'], source=row['source'], source_ids=row['source_ids'],
        source_ids_sha256=row['source_ids_sha256'], occurrences=row['occurrences'],
        input_ids=row['input_ids'], original=row['original'], candidate=row['candidate'],
        original_character_range=[0, len(raw)], original_characters=len(raw),
        decision='HOLD', reviewed=True, root_approved=True,
        reason_code='WHOLE_SOURCE_SUBJECT_IDENTITY_LOST_NO_INDEPENDENT_TRAINING_BODY',
        reason=detail, author_first_review=review['review'], author_reason=review['reason'],
        second_review=dict(reviewer='root', full_original_read=True,
            method='17건의 실제 전문을 각 ID/문자수와 함께 표시하고 끝까지 판독했다.'),
        clean_text_path=None, clean_text_sha256=None, cache_admitted=False,
        status='REVIEWED_TERMINAL_HOLD_FOR_THIS_FROZEN_SOURCE_PENDING_NEW_ROSTER_JOIN',
        raw_source_preserved=True, source_identity_invented=False))
assert len(rows) == len({r['id'] for r in rows}) == 36
result = dict(status='THIRTYSIX_INDIVIDUALLY_REVIEWED_HOLDS_NOT_UNPROCESSED_RENAMING',
    rows=rows, unique_sources=len(rows), source_positions=sum(r['occurrences'] for r in rows),
    raw_input_ids=sum(r['occurrences'] * r['input_ids'] for r in rows),
    prior_terminal_ledger=dict(path=str(prior_path.relative_to(ROOT)), sha256=inv.file_sha(prior_path)),
    source_manifest=dict(path=str(manifest_path.relative_to(ROOT)), sha256=inv.file_sha(manifest_path)),
    snapshot=dict(path=str(snapshot_path.relative_to(ROOT)), sha256=inv.file_sha(snapshot_path)),
    producer_sha256=inv.file_sha(Path(__file__)), new_roster_joined=False,
    official_verified_cache_hold_positions_unchanged=115526,
    limits='현재 고정 원문의 개별 판정이다. 미판독을 종결 보류로 개명하지 않았고, 원형을 삭제하지 않았다.',
    goal_complete=False, training_authorized=False)
inv.write_json(AUDIT / 'ROOT_REVIEWED_TERMINAL_HOLD36_V1.json', result)
with (AUDIT / 'ROOT_REVIEWED_TERMINAL_HOLD36_V1.md').open('x', encoding='utf-8') as stream:
    stream.write('# 주체 소실 원문 36건의 개별 검토 완료 보류' + chr(10) * 2)
    stream.write('기존 19건에 Luna 판독과 총괄 전문 판독을 각각 확인한 17건을 더했다. '
        '1255513은 참고 자료에 인명이 있지만 원문의 주체와 같다는 근거가 부족한 별도 사유다. '
        '원형·전체 문자 범위·SHA·위치 수·두 판독 근거를 JSON에 보존한다. '
        '아직 새 roster에 연결하지 않아 공식 캐시 잔여 115526위치는 변하지 않는다. '
        '모든 원문을 전역적으로 복구할 수 없다는 선언이나 전체 목표 완료가 아니다.' + chr(10))
print(json.dumps(dict(reviewed_terminal_hold_unique=36, positions=result['source_positions'],
    original_cache_unchanged=True), ensure_ascii=False))
