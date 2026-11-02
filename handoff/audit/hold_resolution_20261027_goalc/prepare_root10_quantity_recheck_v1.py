"""Assign every prior quantity diagnostic to one available independent reader."""
from pathlib import Path
import difflib
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
GROUP = 'root10_quantity_recheck_v1'
OUT = BASE / GROUP
ROLE = 'context_hangul'
assert not OUT.exists()
source_path = AUDIT / 'ROOT10_STATED_QUANTITY_DIAGNOSTICS_V3.json'
source = json.loads(source_path.read_text(encoding='utf-8'))
contract = json.loads((AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json').read_text())
directory = BASE / 'agents' / ROLE / GROUP
directory.mkdir(parents=True, exist_ok=False)
(OUT / 'inputs').mkdir(parents=True)
(OUT / 'reading_packets_v1').mkdir()


def sha(payload):
    return hashlib.sha256(payload).hexdigest().upper()


def save(path, value):
    payload = value.encode('utf-8')
    assert 0 < len(payload) < 20_000_000
    with path.open('xb') as stream:
        stream.write(payload)
    return dict(path=str(path.relative_to(ROOT)), sha256=sha(payload))


rows = []
for row in source['rows']:
    assert row['id'] not in contract['restricted_ids']
    assert row['original']['sha256'] not in contract['restricted_hashes']
    values, pins = {}, {}
    for kind, old in [('original', row['original']), ('candidate', row['body'])]:
        payload = (ROOT / old['path']).read_bytes()
        assert sha(payload) == old['sha256']
        text = payload.decode('utf-8')
        values[kind] = text
        # Empty rejected bodies are explicit existing selections, not new prose.
        path = OUT / 'inputs' / (row['id'].replace(':', '_') + '_' + kind + '.txt')
        assert len(payload) < 20_000_000
        with path.open('xb') as stream:
            stream.write(payload)
        pins[kind] = dict(path=str(path.relative_to(ROOT)), sha256=sha(payload))
    delta = ''.join(difflib.unified_diff(values['original'].splitlines(keepends=True),
        values['candidate'].splitlines(keepends=True), fromfile='original', tofile='candidate'))
    framed = ''
    for kind, text in [*values.items(), ('full_diff', delta or '전체 줄 차이 없음')]:
        framed += '=== BEGIN ' + row['id'] + ' ' + kind + ' ===' + chr(10) + text + chr(10)
        framed += '=== END ' + row['id'] + ' ' + kind + ' ===' + chr(10)
    parts = []
    for offset in range(0, len(framed), 2000):
        fragment = framed[offset:offset + 2000]
        part = save(OUT / 'reading_packets_v1' / (row['id'].replace(':', '_') + '_' +
            str(offset // 2000 + 1).zfill(4) + '.txt'), fragment)
        parts.append(dict(**part, characters=[offset, offset + len(fragment)]))
    rows.append(dict(id=row['id'], role=ROLE, original_text_sha256=row['original']['sha256'],
        **pins, flags=row['flags'], reading_parts=parts, prior_selection=row,
        root_approved=False, cache_admitted=False))
assert len(rows) == 26
start = ['# ROOT10의 수량·필드 진단 26건 재판독', '',
    '이 START/TASK/READING_VIEWS와 정확 지정 원문·기존 선택 본문·전체 diff만 읽는다. 자기 새 TXT/MD만 쓴다.',
    '총괄이 복사한 원문과 기존 선택은 입력이며 새 정제 실적이 아니다. 실제 수정은 Luna가 문맥을 읽고 작성한다.',
    '코드·Python·시험·통계·해시·Git·웹·GPU·모델·다른 역할/세션/보호 경로는 금지한다. 경로 없는 검색이나 경로 추측도 금지다.',
    '2,000문자 연속 조각을 한 ID의 original→candidate→full_diff 순서로 모두 읽고 마지막 END를 확인한다.',
    '진단은 오류 확정이 아니다. 군주의 서수·전라/전남 지명·반복 제거·표적 결손과 실제 나이·상대 기간 손실을 구별한다.',
    '출생연도 충돌만을 이유로 실제 명시 나이와 다른 사건 기간을 삭제하지 않는다. 나이에서 출생연도를 계산하지 않는다.',
    '동일 사건의 나이 자체가 조건 없이 두 값으로 충돌하면 어느 쪽도 고르지 않고 그 좁은 주장만 HOLD한다.',
    '조건·추정·출처·인용·달력·등록 기록의 차이는 그대로 보존한다. 숫자·단위·부정·의미를 임의 변경하지 않는다.',
    '원래 전체 보류나 결손 의존 문장이 타당하면 그 근거를 적는다. 진단 통과를 위해 값을 무조건 되살리지 않는다.',
    '원문/선택 전문을 다 읽고 유지/실제 수정/총괄 질문을 판단한다. 새 본문은 전체 TXT, 보류 원형은 별도 MD다.',
    '각 TASK 리뷰는 ID/판정/실제 판독 범위/출력/근거 다섯 열을 쓴다. 정확한 출력 열 제목은 출력이다.',
    '유지는 ACCEPT_CANDIDATE와 지정 candidate basename, 수정은 REVISE_TEXT와 자기 새 TXT basename, 질문은 NEEDS_ROOT와 —다.',
    '수정이 없으면 동일 TXT를 복제하지 않는다. 모든 쓰기는 noclobber, 이전 버전·초안·오류 기록은 보존한다.',
    'TASK001–006 전량을 마치고 각 결과를 보고한다. 캐시 채택·전체 goal 완료·학습 재개는 선언하지 않는다.']
save(directory / 'START_HERE.md', chr(10).join(start) + chr(10))
views = ['# 정확한 지정 입력 목록', '']
for task, offset in enumerate(range(0, len(rows), 5), 1):
    lines = ['# TASK_' + str(task).zfill(3), 'START_HERE의 범위를 따른다.', '']
    for row in rows[offset:offset + 5]:
        lines += ['## ' + row['id']]
        for kind in ('original', 'candidate'):
            lines += [kind + ': ' + str(ROOT / row[kind]['path'])]
        lines += ['진단 근거: ' + json.dumps(row['flags'], ensure_ascii=False), '전체 순서 패킷:']
        lines += ['- ' + str(ROOT / pin['path']) for pin in row['reading_parts']]
    save(directory / ('TASK_' + str(task).zfill(3) + '.md'), chr(10).join(lines) + chr(10))
    views += lines
save(directory / 'READING_VIEWS.md', chr(10).join(views) + chr(10))
result = dict(status='PRIOR_SELECTION_DIAGNOSTIC_READING_ASSIGNMENT_NOT_ADMISSION', rows=rows,
    assignments={ROLE: [row['id'] for row in rows]}, source_diagnostic=dict(
        path=str(source_path.relative_to(ROOT)), sha256=sha(source_path.read_bytes())),
    producer_sha256=sha(Path(__file__).read_bytes()), root_approved=False, cache_admitted=False,
    goal_complete=False, training_authorized=False)
with (OUT / 'manifest.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
print(json.dumps(dict(sources=len(rows), packets=sum(len(row['reading_parts']) for row in rows),
    role=ROLE, start=str(directory / 'START_HERE.md')), ensure_ascii=False))
