"""Pin root's 15 source-specific numerical judgments without changing policy."""
from collections import Counter
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

source = AUDIT / 'EXACT_COHORT_NUMERIC_LOCAL_PROOFS_V1.json'
document = inv.cache.read(source)
contract = inv.cache.read(AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json')
repeat = inv.BASE / 'repeat_named_roles_counter_v2'
birth = inv.BASE / 'remaining_birth_full_counter_v1'
math = inv.BASE / 'repeat_named_full_independent_v1/ROOT_MATH_AND_TABLE_MEDIATION_V1.md'
rules = {
    '748223': ('FACT_CORRECTION', '경로 표제의137→139 한곳. 실제139도 경로·고정판 대조 근거에 한정한다.',
        repeat / 'ROOT_EVIDENCE_748223_MERIDIAN_V1.md', []),
    '663410': ('FACT_CORRECTION', '서경29도와 동경151도의 대권 연결문 한곳26→29. 표제·고정 출판판·보각 관계의 좁은 중재다.',
        repeat / 'ROOT_EVIDENCE_663410_MERIDIAN_V1.md', []),
    '305748': ('FACT_CORRECTION', '동경131도 경로 표제 한곳130→131. 실제 고정 출판판의 표제·표 경로 대조에 한정한다.',
        repeat / 'ROOT_EVIDENCE_305748_MERIDIAN_V1.md', []),
    '132438': ('SAME_SOURCE_HEADINGS', '2차 예선전·16강전·8강전은 빈 wiki 경계 제거 뒤에도 실제 동일 단계 표제로 남는다. 경기 결과를 새로 생성하지 않았다.',
        repeat / 'ROOT_MEDIATION_V1.md', [('2차 예선전', '2차 예선전'), ('16강전', '16강전'), ('8강전', '8강전')]),
    '273220': ('SAME_EVENT_DATE_MOVED', '충돌 생년을 분리하면서 실제 리드의 사망 날짜를 다음 문장으로 이동했다. 덴쇼17년 음력5월19일과 괄호1589년7월1일의 원문 대응을 그대로 유지하며 새 달력 변환을 하지 않았다.',
        None, [('덴쇼 17년 음력 5월 19일(1589년 7월 1일)', '덴쇼 17년 음력 5월 19일(1589년 7월 1일)')]),
    '110981': ('SAME_EVENT_DATE_MOVED', '생일 불확실성은 원문 귀속대로 두고, 원문 리드의 생몰 범위 중 사망1997년11월25일을 같은 인물의 사망 괄호로 옮겼다.',
        None, [('~1997년 11월 25일', '1997년 11월 25일 사망')]),
    '140146': ('EXPLICIT_SAME_PARAGRAPH_YEAR', '원문 간에이10년(1633년) 문단의 같은 스덴 사망 사건이다. 리드2월28일과 본문1월20일의 무조건 날짜를 보류한 뒤 같은 문단의 명시1633년만 유지했으며 환산/역산하지 않았다. 향년65세도 유지한다.',
        None, [('간에이 10년(1633년)', '간에이 10년(1633년)'), ('향년 65세였다.', '향년 65세였다.')]),
    '11036': ('FACT_CORRECTION', '동일 나폴레옹의 어린시절 생일1771년12월31일→1769년8월15일과 출생분류1771→1769. 박물관·서명 연구 글의 좁은 근거를 따른다.',
        birth / 'ROOT_EVIDENCE_11036_BIRTH_V1.md', [('1771년 12월 31일', '1769년 8월 15일'), ('1771년 출생', '1769년 출생')]),
    '1066704': ('EXACT_NAME_TOKEN_PRESERVED', 'AKB48의48은 수량 변경이 아니라 그대로 보존된 동일 그룹명·공식 홈페이지 라벨이다. 빈 절 제거로 위치만 바뀌었다.',
        None, [('AKB48 Team SH 공식 홈페이지－우안치', 'AKB48 Team SH 공식 홈페이지－우안치')]),
    '1177351': ('EXPLICIT_TYPED_FIELD_REUSED', '원문1912년 출생 분류의 명시 필드를 같은 보리스 체르토크 리드의 빠진 생년 칸에 연결했다. 새 월일이나 외부 전기 사실은 만들지 않았다.',
        None, [('1912년 출생', '보리스 체르토크(1912년 ~ 2011년 12월 14일)')]),
    '182113': ('DATE_RANGE_SEPARATOR_NOT_SIGN', '원문1850년10월17일-1913년6월30일의 하이픈은 생몰 범위 구분자이며 음수1913이 아니다. 충돌 생년만 보류하고 같은 사망일을 보존했다.',
        None, [('1850년 10월 17일-1913년 6월 30일', '1913년 6월 30일 사망')]),
    '1024340': ('PUBLISHED_NOTATION_CORRECTION', 'Calc지수 설명에서 소실된 위첨자23을 공식 문서의2^3과 명시 곱2*2*2에 연결한 좁은 표기 복구다. 새로운 계산이나 다른 결합 연산자를 추정하지 않았다.',
        math, [('23 = 2*2*2', '2^3 = 2*2*2')]),
    '151': ('EXACT_COMPLETE_CLAIM_PRESERVED', '누락된 미분/점화/생성 수식 의존부와 별개로 실제 완결된 직교구간[-1,1] 주장과 노름1이 아니라는 한정을 원문대로 보존했다.',
        None, [('따라서, 르장드르 다항식은 구간 [-1,1]에서 서로 수직함을 알 수 있다.', '따라서, 르장드르 다항식은 구간 [-1,1]에서 서로 수직함을 알 수 있다.'), ('다만, 통상적으로 그 노름이 1이 아니게 정의한다.', '다만, 통상적으로 그 노름이 1이 아니게 정의한다.')]),
    '638977': ('EXACT_HISTORY_CLAIMS_PRESERVED', '실제 역사 문단의 카르탕1894년·간트마헤르1939년 분류 서술은 결손 정의/표 설명과 독립이다. 같은 사건·인물·연도를 보존한 것이며 새 역사 사실을 추가하지 않았다.',
        None, [('엘리 카르탕이 1894년에 박사 학위 논문에서 분류하였다.', '엘리 카르탕이 1894년에 박사 학위 논문에서 분류하였다.'), ('1939년에 분류하였다.', '1939년에 분류하였다.')]),
    '805989': ('EXACT_COMPLETE_GROUP_CLAIM_PRESERVED', '실제SO(1,5)절의 Spin(1,5) 최소 스피너4차원·왼쪽/오른쪽·마요라나 부재는 완결된 같은 원문 주장이다. 미상 군의 정의 표현 관계만 따로 보류했다.',
        None, [('SO(1,5)', 'SO(1,5)'), ('Spin(1,5)의 최소 스피너는 4차원 왼쪽·오른쪽 바일 스피너이며, 마요라나 스피너는 존재하지 않는다.', 'Spin(1,5)의 최소 스피너는 4차원 왼쪽·오른쪽 바일 스피너이며, 마요라나 스피너는 존재하지 않는다.')]),
}
rows = []
counts = Counter()
evidence_pins = {}
for row in document['rows']:
    pending = [p for p in row['proofs'] if p['status'] == 'MANUAL_CONTEXT_REQUIRED']
    if not pending: continue
    ident = row['id']
    assert ident not in contract['restricted_ids'] and row['original']['sha256'] not in contract['restricted_hashes']
    number = ident.split(':')[1]
    kind, reason, evidence, anchors = rules[number]
    for name in ['original', 'body', 'review']:
        pin = row[name]
        assert inv.file_sha(ROOT / pin['path']) == pin['sha256']
    raw = (ROOT / row['original']['path']).read_text(encoding='utf-8')
    body = (ROOT / row['body']['path']).read_text(encoding='utf-8')
    anchor_proofs = []
    for old, new in anchors:
        assert old in raw and new in body, (ident, old, new)
        anchor_proofs.append(dict(source_anchor=old, body_anchor=new,
            source_character_span=[raw.index(old), raw.index(old) + len(old)],
            body_character_span=[body.index(new), body.index(new) + len(new)]))
    evidence_pin = None
    if evidence:
        evidence_pin = dict(path=str(evidence.relative_to(ROOT)), sha256=inv.file_sha(evidence))
        evidence_pins[evidence_pin['path']] = evidence_pin['sha256']
    for p in pending:
        flag = p['flag']; lo, hi = flag['body_span']
        assert body[lo:hi] == flag['body_token']
    counts['exact_body_pairs'] += 1
    counts['individual_numeric_flags'] += len(pending)
    rows.append(dict(id=ident, cohort=row['cohort'], original=row['original'], body=row['body'],
        review=row['review'], reviewed_flags=[p['flag'] for p in pending],
        kind=kind, reason=reason, source_anchors=anchor_proofs, evidence=evidence_pin,
        root_numeric_context_approved=True, full_document_fact_approval=False,
        production_policy_waiver=False, cache_admitted=False))
assert len(rows) == 19 and counts['individual_numeric_flags'] == 38
assert {r['id'].split(':')[1] for r in rows} == set(rules) and len(rules) == 15
result = dict(status='EXACT_SOURCE_BODY_NUMERIC_CONTEXT_CLEARANCES_NOT_ADMISSION',
    counts=dict(counts, unique_sources=len(rules)), rows=rows,
    input_pins={str(source.relative_to(ROOT)): inv.file_sha(source),
        str(Path(__file__).relative_to(ROOT)): inv.file_sha(Path(__file__)), **evidence_pins},
    original_bodies_protected=False, global_guard_changed=False,
    meaning='51 local atom proofs and these 38 individually reviewed flags close only this numerical provenance diagnostic.',
    goal_complete=False, training_authorized=False)
inv.write_json(AUDIT / 'EXACT_NUMERIC_CONTEXT_CLEARANCES_V1.json', result)
print(json.dumps(result['counts']))
