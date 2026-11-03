"""Bind the nineteen actual adjudications to the corrected snapshot8 bodies."""
from pathlib import Path
import copy
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def verified(pin):
    path = ROOT / pin['path']
    assert path.resolve().is_relative_to(BASE) or path.resolve().is_relative_to(AUDIT)
    data = path.read_bytes()
    assert len(data) < 20_000_000 and hashlib.sha256(data).hexdigest().upper() == pin['sha256']
    return data.decode('utf-8')


prior_path = AUDIT / 'BIRTH_SECOND_REPAIR_SOURCE_ADJUDICATION_V1.json'
snapshot_path = BASE / 'birth_root11_independent_v1_snapshots/v8/complete.json'
manifest_path = BASE / 'birth_root11_independent_v1/manifest.json'
prior = json.loads(prior_path.read_text(encoding='utf-8'))
snapshot = json.loads(snapshot_path.read_text(encoding='utf-8'))
assert not snapshot['errors'] and not snapshot['needs_root']
sources = {r['id']: r for r in json.loads(manifest_path.read_text(encoding='utf-8'))['rows']}
records = {}
for pin in snapshot['shards']:
    for record in json.loads(verified(pin)):
        assert record['id'] not in records
        records[record['id']] = record
contract = json.loads((AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json').read_text())
followups = {
    '11036': (['002605'], '임신·태아 및 망명 불가 인과절만 추가 보류하고 전투·망명·부친의 독립투쟁 참여와 귀족 특허 사건을 보존했다.'),
    '418525': (['506bff'], '고립 각주1만 제거하고 끝의 행위가 유실된 법난 문단을 원형 보류했다. 실제 근사생년 한정과 나머지 생애는 보존했다.'),
    '614291': (['506bff'], '선두 실제 사망일의 역할을 명시하고 고립 각주9/30/41 및 파손 중복 인용 괄호절만 정리했다. 앞 실제 인용과 뒤 자료명·경력은 보존했다.'),
    '735092': (['cf0284'], '상충 자녀 유무·수량 조각과 이장연도1407만 보류했다.1426후계회의·주라지·혼인·계보·프레스코와1402수도원건립·묘소 이동·1427사망은 보존했다.'),
    '809644': (['cf0284'], '1746출생과4월22일사망을 역할로만 명시했다. 상충 사망연도는 보류하고 독립1926폐쇄 사건은 보존했다.'),
    '1078303': (['cf0284', '9b2637'], '자매서열을 선택하지 않고 실제 자매·이름·우승 관계를 보존했다. 추가로 빈 우승 제목만 제거하고 실제 수량/성적/조건과 명칭은 보존했다.'),
    '1167883': (['cf0284', '9b2637'], '열 이름이 없는 숫자와 합계는 원형 sidecar로 보류하고 실제 시즌·팀·리그를 보존했다. 대응주석없는두†만 추가 분리했다.'),
}
rows = []
for previous in prior['rows']:
    ident = previous['id']
    source, record = sources[ident], records[ident]
    assert ident not in contract['restricted_ids']
    assert source['original']['sha256'] not in contract['restricted_hashes']
    assert source['original']['sha256'] == previous['original']['sha256']
    assert source['role'] == record['role'] != source['previous_editor_role']
    assert source['role'] != source.get('correction_author_role')
    assert record['status'] in {'PINNED_BODY_NOT_ROOT_ADMISSION', 'MATERIALIZED_BODY_NOT_ROOT_ADMISSION'}
    pin = {'path': record['body'], 'sha256': record['clean_text_sha256']}
    verified(source['original'])
    verified(pin)
    review = record['review']
    review_text = verified({'path': review['archive'], 'sha256': review['sha256']})
    assert ident in review_text
    row = copy.deepcopy(previous)
    row['previous_frozen_decision'] = previous['decision']
    row['current_body_for_future_selection'] = pin
    row['current_archived_independent_review'] = review
    if previous['decision'] == 'PROPOSAL_REVIEWED_NOT_ADOPTED':
        assert pin['sha256'] == previous['proposed_body']['sha256']
        row['decision'] = 'EXACT_PREVIOUSLY_REVIEWED_PROPOSAL'
    elif previous['decision'] == 'REJECT_PROPOSAL_KEEP_INPUT':
        assert pin['sha256'] == previous['independent_input_candidate']['sha256']
        row['decision'] = 'PROPOSAL_WITHDRAWN_INPUT_RESTORED'
        row['followup_verification_tool_chunks'] = ['41e9a1']
    else:
        chunks, note = followups[ident.split(':')[1]]
        assert pin['sha256'] != previous['proposed_body']['sha256']
        row['decision'] = 'ROOT_FOLLOWUP_REPAIR_REVIEWED'
        row['followup_verification_tool_chunks'] = chunks
        row['followup_rationale'] = note
        row['followup_read_method'] = 'PREVIOUS_SOURCE_BODY_READING_AND_COMPLETE_CHANGED_CONTEXTS_NOT_A_NEW_FULL_ORIGINAL_READING'
    row['body_to_select_after_review'] = pin
    row['accepted_for_future_selection'] = True
    row['cache_adopted'] = False
    rows.append(row)
counts = {state: sum(r['decision'] == state for r in rows)
          for state in sorted({r['decision'] for r in rows})}
assert counts == {'EXACT_PREVIOUSLY_REVIEWED_PROPOSAL': 11,
                  'PROPOSAL_WITHDRAWN_INPUT_RESTORED': 1, 'ROOT_FOLLOWUP_REPAIR_REVIEWED': 7}
result = {
    'status': 'NINETEEN_FROZEN_PROPOSALS_ADJUDICATED_AND_KNOWN_SEVEN_FOLLOWUPS_REVIEWED_NOT_ADOPTED',
    'sources': len(rows), 'counts': counts, 'pending_known_followups_in_this_nineteen': 0,
    'rows': rows,
    'input_pins': {str(p.relative_to(ROOT)): sha(p) for p in
                   (prior_path, snapshot_path, manifest_path, Path(__file__).resolve())},
    'root_or_cache_adoptions': 0, 'protected_body_reads': 0, 'goal_complete': False,
    'limits': ['이19개는 snapshot4의 초기 보완안 범위이며 이후의 새 보완안이나 출생2707개 전부의 의미 검토 완료가 아니다.',
               '기존 실제 전문 판독과 새 전체 차이를 연결했다. 같은 원문을 또 전량 판독했다고 중복 집계하지 않는다.',
               '후속 선택 후보와 실제 ROOT/캐시 채택은 별개다. 남은 전체 유형과 새 보완안 검토를 계속한다.'],
}
out = AUDIT / 'BIRTH_SECOND_REPAIR_SOURCE_ADJUDICATION_V2.json'
with out.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({'sources': len(rows), 'counts': counts, 'pending_known_followups': 0,
                  'root_or_cache_adoptions': 0}))
