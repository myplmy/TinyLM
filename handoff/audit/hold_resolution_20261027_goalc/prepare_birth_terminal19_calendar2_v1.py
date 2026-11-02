"""Record four individually read sources and reopen two calendar-pair cases."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv


def write_json(path, value):
    payload = (json.dumps(value, ensure_ascii=False, indent=2) + chr(10)).encode('utf-8')
    assert len(payload) < 20_000_000
    with path.open('xb') as stream:
        stream.write(payload)


def write_md(path, lines):
    with path.open('x', encoding='utf-8') as stream:
        stream.write(chr(10).join(lines) + chr(10))


cohort = 'remaining_birth_full_counter_v1'
manifest_path = inv.BASE / cohort / 'manifest.json'
manifest = inv.cache.read(manifest_path)
sources = {row['id']: row for row in manifest['rows']}
snapshot_path = inv.BASE / (cohort + '_snapshots') / 'v6/complete.json'
snapshot = inv.cache.read(snapshot_path)
saved = {}
for shard in snapshot['shards']:
    assert inv.file_sha(ROOT / shard['path']) == shard['sha256']
    saved.update({row['id']: row for row in inv.cache.read(ROOT / shard['path'])})
contract = inv.cache.read(AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json')
prior_path = AUDIT / 'ROOT_REVIEWED_TERMINAL_HOLD15_V1.json'
prior = inv.cache.read(prior_path)
rows = list(prior['rows'])
dates = {
    '1251865': '도입 1964년과 분류 1984년이 다르며 인명은 전혀 없다.',
    '1252536': '도입 1976년과 분류 1990년이 다르며 인명은 전혀 없다.',
    '1252600': '도입 1995년과 분류 1990년이 다르며 인명은 전혀 없다.',
    '1252623': '도입 1986년과 분류 1983년이 다르며 인명은 전혀 없다.',
}
for number, detail in dates.items():
    source = sources['expanded_train:' + number]
    assert source['id'] not in contract['restricted_ids']
    assert source['original']['sha256'] not in contract['restricted_hashes']
    assert inv.file_sha(ROOT / source['original']['path']) == source['original']['sha256']
    text = (ROOT / source['original']['path']).read_text(encoding='utf-8')
    review = saved[source['id']]
    assert review['decision'] == 'NEEDS_ROOT' and not review.get('body')
    assert text.lstrip().startswith('(') and len(text) < 6000
    rows.append(dict(id=source['id'], source=source['source'], source_ids=source['source_ids'],
        source_ids_sha256=source['source_ids_sha256'], occurrences=source['occurrences'],
        input_ids=source['input_ids'], original=source['original'], candidate=source['candidate'],
        original_character_range=[0, len(text)], original_characters=len(text),
        decision='HOLD', reviewed=True, root_approved=True,
        reason_code='WHOLE_SOURCE_SUBJECT_IDENTITY_LOST_NO_INDEPENDENT_TRAINING_BODY',
        reason='이름이 소실된 축구 선수 소개이고 팀·학교 분류로 인명을 추정할 수 없다. 독립적으로 채택할 동일 대상 본문이 없다.',
        specific_limit=detail, author_first_review=review['review'], author_reason=review['reason'],
        second_review=dict(reviewer='root', full_original_read=True,
            method='4건 전체 원문을 실제 표시하고 끝까지 재판독; 빈 인명과 독립 본문 부재 확인'),
        clean_text_path=None, clean_text_sha256=None, cache_admitted=False,
        status='REVIEWED_TERMINAL_HOLD_FOR_THIS_FROZEN_SOURCE_PENDING_NEW_ROSTER_JOIN',
        raw_source_preserved=True, source_identity_invented=False))
assert len(rows) == len({r['id'] for r in rows}) == 19
result = dict(status='NINETEEN_INDIVIDUALLY_REVIEWED_HOLDS_NOT_UNPROCESSED_RENAMING', rows=rows,
    unique_sources=19, source_positions=sum(r['occurrences'] for r in rows),
    raw_input_ids=sum(r['occurrences'] * r['input_ids'] for r in rows),
    prior_terminal_ledger=dict(path=str(prior_path.relative_to(ROOT)), sha256=inv.file_sha(prior_path)),
    source_manifest=dict(path=str(manifest_path.relative_to(ROOT)), sha256=inv.file_sha(manifest_path)),
    snapshot=dict(path=str(snapshot_path.relative_to(ROOT)), sha256=inv.file_sha(snapshot_path)),
    producer_sha256=inv.file_sha(Path(__file__)), new_roster_joined=False,
    official_verified_cache_hold_positions_unchanged=115526, goal_complete=False, training_authorized=False,
    limits='현재 고정 원문만으로 주체를 복구할 수 없다는 개별 판정이다. 다른 덤프 전체의 영구 복구 불가능을 뜻하지 않는다.')
write_json(AUDIT / 'ROOT_REVIEWED_TERMINAL_HOLD19_V1.json', result)
write_md(AUDIT / 'ROOT_REVIEWED_TERMINAL_HOLD19_V1.md', [
    '# 주체 소실 원문 19건의 개별 검토 완료 보류', '',
    '기존 전문 판독 15건의 근거를 보존하고 1251865·1252536·1252600·1252623 네 건의 Luna 판독과 총괄의 실제 전문 판독을 추가했다.',
    '빈 인명을 생년·학교·팀으로 추측하지 않는다. 생년만 제거한 무명 소개도 채택하지 않는다. 사유와 전체 문자 범위, 원문 SHA, 원래 위치, 두 판독 근거는 JSON에 연결했다.',
    '이 19건은 검토 완료 보류이고 미판독 구간과 다르다. 아직 새 roster에 연결하지 않아 공식 캐시 잔여 115526위치는 변하지 않았다. 전체 목표는 계속 진행한다.',
])

evidence = inv.BASE / cohort / 'ROOT_EVIDENCE_CALENDAR_310298_312420_V1.md'
write_md(evidence, [
    '# 두 날짜 쌍의 달력 맥락', '',
    '310298의 나가시노·시타라가하라 전투와 312420의 혼노지 사건은 원문 안에서 같은 사건의 날짜가 서로 다른 표기로 놓인 사례다. 두 원문 전문을 총괄도 읽었다. 출생 연도 자체는 각 문서 안에서 일치한다.',
    '310298: 도입 1575년 6월 29일과 본문의 텐쇼 3년 5월 21일을 모두 보존한다. 공익재단법인 忍郷友会가 공개한 「長篠の合戦」と「設楽ヶ原の決戦」의 검색 색인 도입문에서 이 두 날짜가 함께 제시된다.',
    '출처: https://www.oshi-goyukai.or.jp/data/pdf/rekishi_190924.pdf ; 검색 색인에서 해당 도입과 인쇄 15쪽을 확인했다. PDF 전체 열기는 10,896,224바이트의 도구 제한으로 실패했다. 전체 문서 판독 또는 자체 달력 계산을 수행한 것으로 기록하지 않는다.',
    '312420: 도입 1582년 6월 21일과 덴쇼 10년 6월 2일의 혼노지 사건을 모두 보존한다. 作花一志의 「本能寺の変と天変～その影に改暦問題が」는 구력 6월 2일과 율리우스력 6월 21일의 관계를 명시한다.',
    '출처: https://www.kwasan.kyoto-u.ac.jp/hosizora/astron/astron37/astron37.pdf#page=20 ; あすとろん 37호(2017-01), PDF 20번째 쪽/인쇄 18쪽, 파싱 488–493행을 실제 확인했다. 이 출처를 근거로 그레고리력이라고 쓰지 않는다.',
    '본문의 원래 날짜·원호·사건·수명은 그대로 보존한다. 새 날짜나 달력 라벨을 학습 본문에 넣지 않는다. 빈 외부 링크 표제나 명명값 뒤 빈 괄호만 원형 sidecar와 함께 분리할 수 있다. 전기 전체의 사실 검증을 뜻하지 않는다.',
])
directory = inv.BASE / 'agents/context_hangul' / cohort
scope_path = directory / 'ROOT_CALENDAR_RECHECK_SCOPE_V1.md'
lines = ['# 지정 두 날짜 사례 재판독 범위', '',
    '현재 역할의 기존 TASK049 중 아래 두 ID만 다시 열어 달력 맥락을 반영한다. ROOT_EVIDENCE_CALENDAR_310298_312420_V1.md의 전문 읽기를 추가 허용한다.',
    '기존 초안과 리뷰는 보존하고 noclobber로 새 전체 TXT/sidecar 및 review_049_v10.md에 두 행만 기록한다. 출력 폴더는 현재 자기 remaining_birth_full_counter_v1 폴더뿐이다.',
    '두 건 뒤에는 현재 미저장 TASK054부터 TASK110까지 기존 START/TASK/READING_VIEWS의 지정 원문만 판독하며 계속한다. 다른 역할 폴더/코드/실행/시험/Git/웹은 허용하지 않는다.',
    'evidence: ' + str(evidence), 'evidence_sha256: ' + inv.file_sha(evidence),
    'TASK: ' + str(directory / 'TASK_049.md'), '']
for number in ('310298', '312420'):
    source = sources['expanded_train:' + number]
    assert source['role'] == 'context_hangul'
    lines += ['## ' + source['id']]
    for kind in ('original', 'candidate'):
        pin = source[kind]
        assert inv.file_sha(ROOT / pin['path']) == pin['sha256']
        lines += [kind + ': ' + str(ROOT / pin['path']), kind + '_sha256: ' + pin['sha256']]
    for part in source['reading_parts']:
        assert inv.file_sha(ROOT / part['path']) == part['sha256']
        lines += ['`cat -- ' + "'" + str(ROOT / part['path']) + "'" + '`']
write_md(scope_path, lines)
write_json(AUDIT / 'BIRTH_TERMINAL19_CALENDAR2_SCOPE_V1.json', dict(
    terminal_unique=19, newly_root_read=4, calendar_ids=['expanded_train:310298', 'expanded_train:312420'],
    evidence=dict(path=str(evidence.relative_to(ROOT)), sha256=inv.file_sha(evidence)),
    scope=dict(path=str(scope_path.relative_to(ROOT)), sha256=inv.file_sha(scope_path)),
    official_verified_cache_unchanged=True, goal_complete=False, training_authorized=False))
print(json.dumps(dict(terminal_unique=19, positions=result['source_positions'], calendar_scope=str(scope_path)), ensure_ascii=False))
