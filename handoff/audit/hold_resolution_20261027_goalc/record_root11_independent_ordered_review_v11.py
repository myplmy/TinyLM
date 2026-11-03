"""Append five actual original/body/full-diff readings of existing repeat results."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


prior = AUDIT / 'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V10.json'
binding_path = AUDIT / 'EXISTING_REPEAT_ORDERED_FLAG_REVIEW_BINDINGS_V1.json'
result = json.loads(prior.read_text(encoding='utf-8'))
binding = {r['id']: r for r in json.loads(binding_path.read_text(encoding='utf-8'))['rows']}
contract = json.loads((AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json').read_text())
cases = {
    '151': ('7ef77d', 'FORMAT_FOLLOWUP_REQUIRED',
            '결손 식과 직접 의존 단위를 보류한 경계는 유지한다. 표가 사라진 뒤 남은 중복 빈 소제목과, 근거 식을 보류한 뒤 남은 따라서 접속어만 추가 정리해야 한다. 실제 직교성, 구간, 명명, 적용과 노름 한정은 보존한다.'),
    '261707': ('7ef77d', 'SOURCE_RELATION_FOLLOWUP_REQUIRED',
               '실제 t의 운동량 제곱 복원은 맞다. 다만 현재 본문은 파인먼 도형에 해당하는 진폭 성분과 채널의 소유관계를 빠뜨려 실제 도형-진폭-채널 관계를 복원해야 한다. 없는 도형 모양을 추측하지 않는다.'),
    '327633': ('38031c', 'FORMAT_FOLLOWUP_REQUIRED',
               '결손 정의/증명과 직접 의존 식 보류, 실제 f와[a,b] 및 부정/조건 보존은 확인했다. 포함관계 식을 보류한 뒤 남은 즉 접속어만 정리한다. 새로운 정의역이나 노름을 넣지 않는다.'),
    '325783': ('38031c', 'REVIEWED_ACCEPTABLE_CHANGES_WITH_STATED_LIMITS',
               '대응 본문이 없는 네 목차와 피드백UI를 분리했고 실제 AR 설명,150000서명목록 수량,K–12/초등·중등 한정과 저자 두 명의 약력을 보존했다. Peg의 대상 없는 including만 제거했다. 반복 저자 제목을 같은줄이라는 이유로 합치지 않았다.'),
    '937040': ('38031c', 'TRUNCATED_DEPENDENT_CLAUSES_FOLLOWUP_REQUIRED',
               'UI 제거와 첫 미완결 접미사 분리는 확인했다. 뒤 관련활동카드 네 개에는 단어/문장중간 끊김이 남아 그 미완결 절만 추가 보류해야 한다. 카드 앞 완결 문장과 실제 수업,명칭,조건 및1903제조설명은 보존한다.'),
}
assert len(result['rows']) == 21
assert not ({'expanded_train:' + n for n in cases} & {r['id'] for r in result['rows']})
for number, (chunk, decision, finding) in cases.items():
    ident = 'expanded_train:' + number
    row = binding[ident]
    assert ident not in contract['restricted_ids'] and row['original']['sha256'] not in contract['restricted_hashes']
    for pin in (row['original'], row['independent_result_and_current_flagged_body']):
        assert sha(ROOT / pin['path']) == pin['sha256']
    result['rows'].append({
        'id': ident, 'original': row['original'], 'body': row['independent_result_and_current_flagged_body'],
        'reviewer': 'root', 'full_original_and_selected_body_read': True,
        'full_diff_read': True, 'observation_tool_chunk': chunk,
        'original_to_selected_full_diff_tool_chunk': 'a1c9e5',
        'independent_input_to_selected_full_diff_tool_chunk': chunk,
        'independent_review': row['independent_review'], 'finding': finding,
        'decision': decision, 'source_fact_verification': False,
    })
pending = [n for n, (_, decision, _) in cases.items()
           if decision != 'REVIEWED_ACCEPTABLE_CHANGES_WITH_STATED_LIMITS']
result['new_repeat_followups_pending'] = []
for number in pending:
    path = AUDIT / ('ROOT11_' + number + '_CORRECTION_INPUTS_V1.json')
    receipt = json.loads(path.read_text(encoding='utf-8'))
    assert receipt['id'] == 'expanded_train:' + number and receipt['cleaned_prose_authored_by_root'] == 0
    result['new_repeat_followups_pending'].append({
        'id': receipt['id'], 'role': receipt['role'],
        'input_receipt': {'path': str(path.relative_to(ROOT)), 'sha256': sha(path)},
        'guide': receipt['guide'], 'status': 'NEW_LUNA_BODY_AND_ROOT_DIFF_REVIEW_PENDING',
    })
result.update({
    'status': 'TWENTY_SIX_ACTUAL_ROOT_READS_FOUR_ADDITIONAL_REPEAT_FOLLOWUPS_PENDING',
    'actually_reviewed_sources': 26, 'remaining_unreviewed_flag_sources': 559,
    'old_root11_acceptable_sources': 8, 'old_root11_sources_requiring_replacement': 18,
    'corrected_semantic_reviewed_sources': 14, 'corrections_still_pending': 4,
    'prior': {'path': str(prior.relative_to(ROOT)), 'sha256': sha(prior)},
    'verification_code': {'path': str(Path(__file__).resolve().relative_to(ROOT)), 'sha256': sha(Path(__file__).resolve())},
})
result['input_pins'][str(binding_path.relative_to(ROOT))] = sha(binding_path)
out = AUDIT / 'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V11.json'
with out.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({'actual_root_read_annotations': 26, 'known_old_body_followups': 18,
                  'replacement_bodies_reviewed': 14, 'new_followups_pending': 4,
                  'new_root_or_cache_adoptions': 0}))
