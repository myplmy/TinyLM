"""Record actual source readings of the nineteen frozen birth repair proposals.

This records human adjudication; byte equality never grants semantic acceptance.
No body, selection root, roster, or cache is changed by this procedure.
"""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BRIDGE = AUDIT / 'ROOT11_AND_BIRTH_SAVED_REVIEW_COVERAGE_BRIDGE_V2.json'
EXPECTED_BRIDGE_BIRTH_VERSION = 'v4'


def digest(data):
    return hashlib.sha256(data).hexdigest().upper()


def verified(pin):
    path = ROOT / pin['path']
    assert path.resolve().is_relative_to(ROOT / 'data_cache') or path.resolve().is_relative_to(AUDIT)
    data = path.read_bytes()
    assert len(data) < 20_000_000
    assert digest(data) == pin['sha256']
    return data.decode('utf-8')


# These decisions were made only after the tool outputs cited below were read.
# The first item used full change hunks and actual original context; the other
# eighteen used the complete original, complete proposal, and complete diff.
DECISIONS = {
    '11036': ('REPAIR_REQUIRED', '72249c',
              '출생일 보류 뒤에도 1769년 전투 직후 임신 6개월과 태아 식별이 남는다. 직접 의존 절을 추가 보류하고 전투, 부친의 독립투쟁 참여, 가족과 귀족 특허 사건은 보존해야 한다.'),
    '1177351': ('REJECT_PROPOSAL_KEEP_INPUT', '73dc81',
                '제안은 참고 문헌 제목만 복원한다. 곧 외부 링크 제목이 나오므로 빈 섹션을 다시 만든다. 실제 네 권 서지와 ISBN은 기존 후보에도 전부 남아 있다.'),
    '1237959': ('PROPOSAL_REVIEWED_NOT_ADOPTED', '73dc81',
                '서로 다른 생년은 선택하지 않고 원문에 실제 있는 5월 25일만 복원했다. 기존 원문에 없는 생일이나 경력을 넣지 않았다.'),
    '144773': ('PROPOSAL_REVIEWED_NOT_ADOPTED', '73dc81',
               '1896와 1894 생년 충돌을 유지 보류하고 실제 7월 16일을 복원한다. 1960년 5월 5일 사망, 일본식 이름, 생애와 명단은 보존했다.'),
    '203193': ('PROPOSAL_REVIEWED_NOT_ADOPTED', '73dc81',
               '열 이름이 없는 축구 수치와 그 직접 기준일을 함께 보류했다. 한자명, 생일 월일, 입단과 실제 경기, 수상, 학교와 분류는 보존했다.'),
    '209327': ('PROPOSAL_REVIEWED_NOT_ADOPTED', '73dc81',
               '5월 25일과 4월 28일을 동일 역법으로 합치거나 하나를 선택하지 않는다. 공통 사망연도와 원문의 실제 68세, 생년, 혼조 사망, 가계는 보존했다.'),
    '417986': ('PROPOSAL_REVIEWED_NOT_ADOPTED', '81d65b',
               '어머니의 빈 구명 슬롯만 제거한다. 실제 일본어 이름, 생일 월일, 공연, 수치 조건, 작품과 역할은 그대로 남는다. 열린 생몰 물결 표기는 후속 가독성 보완 대상이다.'),
    '418525': ('REPAIR_REQUIRED', '81d65b',
               '실제 1178년 무렵이라는 한정은 복원 가능하나 대응 각주 없는 [1]과 법연 문단의 유실된 끝이 남아 있다. 날짜를 선택하지 않고 불완전 단위만 추가 보류한다.'),
    '422570': ('PROPOSAL_REVIEWED_NOT_ADOPTED', '81d65b',
               '1927년 12월 26일과 1926년 12월 25일 중 공통인 12월만 복원했다. 출생지와 가족, 실제 사망일, 독립 연혁은 보존했다.'),
    '614291': ('REPAIR_REQUIRED', '6ce96c+a5272f',
               '끊긴 게이초4년 절 보류는 맞다. 다만 대응 각주 없는 [9]/[30]/[41], 파손된 중복 선교사 괄호절, 역할 없는 선두 사망일을 추가 보완해야 한다.'),
    '735092': ('REPAIR_REQUIRED', '6ce96c',
               '고립 표 행 제거는 맞다. 원문에도 있던 자녀 없음과 자녀 7명, 사망1427과 사후 이장1407의 상충이 남는다. 자녀를 형제자매로 추측 교정하지 않는다. 1402는 수도원 건립시점으로 보존한다.'),
    '76452': ('PROPOSAL_REVIEWED_NOT_ADOPTED', '3c1ce5',
              '서로 다른 사망일 중 공통 1978년 9월을 복원했고 원문에 실제 있는 향년65세를 보존했다. 역산한 새 생년이나 사망일은 넣지 않았다.'),
    '809644': ('REPAIR_REQUIRED', '3c1ce5',
               '상충 사망연도를 선택하지 않고 독립 사건인 성문 폐쇄1926을 복원한 점은 맞다. 선두1746년-4월22일은 출생연도와 사망월일의 역할을 명확하게 표기해야 한다.'),
    '820819': ('PROPOSAL_REVIEWED_NOT_ADOPTED', '3c1ce5',
               '깨진 원문에서 생몰일과 장소 역할을 새로 만든 이전 후보를 철회했다. 실제 1632년 사망 분류, IPA, 인용과 연구 서술을 보존했다.'),
    '1078303': ('REPAIR_REQUIRED', 'cba066',
                '잔여1999 생년과 고립HTML 제거는 맞다. 같은 제시카를 동생과 언니로 적은 상충은 서열어만 추가 보류하고 실제 자매관계와 이름을 남겨야 한다.'),
    '1167883': ('REPAIR_REQUIRED', 'cba066',
                '깨진 style 제거만으로는 열 이름이 없는 세 통계 단위를 해소하지 못한다. 미상 숫자열은 보류하고 실제 팀, 시즌, 전기와 수상은 보존해야 한다. 앞선 총괄 지적 범위가 좁았음을 정정한다.'),
    '1184460': ('PROPOSAL_REVIEWED_NOT_ADOPTED', 'cba066',
                '실제 두 작품과 헌정관계를 복원했다. 미상 작곡가와 기관명을 추측하지 않는다. 기관명이 없다는 이유만으로 실제 악장과 객원교수 역할을 버리지 않는다.'),
    '154749': ('PROPOSAL_REVIEWED_NOT_ADOPTED', '4fc6b2',
               '실제 영화 고증 비판 문맥에 있는 1305년 당시10세 표현을 복원한다. 대안 생년으로 새 나이를 역산하지 않으며 생년 충돌과 서지 제목의 연도는 구분한다.'),
    '2074': ('PROPOSAL_REVIEWED_NOT_ADOPTED', '4fc6b2',
            '미상 생년을 빈 물결 슬롯으로 남기는 대신 실제1665년1월12일 사망으로 명시했다. 결손 정리 수식은 복구하지 않고 실제 업적, 이름, 조건과57세 원문은 보존했다.'),
}


bridge_bytes = BRIDGE.read_bytes()
bridge = json.loads(bridge_bytes)
contract = json.loads((AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json').read_text())
rows = [r for r in bridge['rows'] if r['new_body_differs_from_independent_input']]
assert {r['id'].split(':')[1] for r in rows} == set(DECISIONS)
result_rows = []
for row in rows:
    ident = row['id']
    # Metadata checks precede every source/body read and hash.
    assert ident not in contract['restricted_ids']
    assert row['original']['sha256'] not in contract['restricted_hashes']
    for field in ['original', 'independent_input_candidate', 'saved_body']:
        verified(row[field])
    review_pin = {'path': row['review']['archive'], 'sha256': row['review']['sha256']}
    review_text = verified(review_pin)
    assert ident in review_text
    decision, chunks, rationale = DECISIONS[ident.split(':')[1]]
    result_rows.append({
        'id': ident, 'original': row['original'],
        'independent_input_candidate': row['independent_input_candidate'],
        'proposed_body': row['saved_body'], 'archived_independent_review': review_pin,
        'independent_reviewer_role': row['reviewer_role'],
        'first_editor_role': row['previous_editor_role'],
        'decision': decision, 'rationale': rationale,
        'actual_read_tool_chunks': chunks.split('+'),
        'root_read_method': ('COMPLETE_INPUT_TO_PROPOSED_DIFF_AND_ORIGINAL_DEPENDENCY_CONTEXT'
                             if ident.endswith(':11036') else
                             'FULL_ORIGINAL_FULL_PROPOSED_AND_COMPLETE_INPUT_TO_PROPOSED_DIFF'),
        'accepted_for_future_selection': decision != 'REPAIR_REQUIRED',
        'body_to_select_after_review': (row['independent_input_candidate']
                                       if decision == 'REJECT_PROPOSAL_KEEP_INPUT' else
                                       row['saved_body'] if decision == 'PROPOSAL_REVIEWED_NOT_ADOPTED' else None),
        'cache_adopted': False,
    })

counts = {state: sum(r['decision'] == state for r in result_rows)
          for state in sorted({r['decision'] for r in result_rows})}
result = {
    'status': 'NINETEEN_PROPOSALS_SOURCE_ADJUDICATED_WITH_PENDING_MINIMAL_REPAIRS',
    'input_bridge': {'path': str(BRIDGE.relative_to(ROOT)), 'sha256': digest(bridge_bytes)},
    'frozen_birth_snapshot_version': EXPECTED_BRIDGE_BIRTH_VERSION,
    'sources': len(result_rows), 'counts': counts, 'rows': result_rows,
    'root_or_cache_adoptions': 0, 'automatic_semantic_waivers': 0,
    'protected_body_reads': 0, 'goal_complete': False,
    'limits': ['첫19개 보완안의 실제 원문 대조 기록이며 출생2707개나 전체잔여검토의 완료가 아니다.',
               '614291 결합 출력 중간이 잘려 새본문과 전체diff는 a5272f로 재열람했다.',
               '735092는 결합 출력의 잘리지 않은 뒷부분에서 원문과 제안 전문 및 전체diff를 읽었다.',
               '새 보완이 저장되면 해당 실제 차이와 원문 의존 경계를 다시 확인해야 한다.'],
    'verification_code': {'path': str(Path(__file__).resolve().relative_to(ROOT)),
                          'sha256': digest(Path(__file__).read_bytes())},
}
out = AUDIT / 'BIRTH_SECOND_REPAIR_SOURCE_ADJUDICATION_V1.json'
with out.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({'sources': len(result_rows), 'counts': counts, 'cache_adopted': 0,
                  'report': str(out.relative_to(ROOT))}, ensure_ascii=False))
