"""Record six further actual source/body/diff readings, without admission."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


prior = AUDIT / 'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V7.json'
result = json.loads(prior.read_text(encoding='utf-8'))
contract = json.loads((AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json').read_text())
guards_path = AUDIT / 'EXACT_SELECTION_RUNTIME_GUARDS_V10.json'
guards = {r['id']: r for r in json.loads(guards_path.read_text())['records']}
findings = {
    'expanded_train:1075729': (False, '엔진의미상출력/가속목표/속도는보류하고3.0L/120도/V6/7.45kWh/26.8MJ/25km/1470kg와14초는보존했다. 다만공식사이트뒤의동일296 GTB다섯꼬리는역할/관계가없는중복표제잔존이다. 원형꼬리를sidecar로분리하되정상차종명/공식자료명은보존하도록보완한다.'),
    'expanded_train:1161353': (True, '원형의빈별칭괄호와그에맞는조사및끝개행만수정했다. 실제한국화이자제약/1969/1959와한국/미국/다국적/외국계분류를모두보존했다. 원저자의어색한문장과국적사실을정정하거나검증한것은아니다.'),
    'expanded_train:1198608': (False, '빈별칭을제거하고실제창업자/1999년2월26일/2003/2005/ISO9001/CE등과다섯제품부문을보존했다. 그러나연혁뒤에는다음생산제품절전까지값이없어빈표제만더분리해야한다. 기존연혁사실이나제품목록은손대지않는다.'),
    'expanded_train:1251896': (False, 'Python2.x/raw_input의실제조건은보존했으나입출력REPL예시가한줄로남는다. 실제>>>프롬프트와명시된두32결과사이의유일한행경계만복구할수있고새입력/출력/예제를추가하지않는다.'),
    'expanded_train:129557': (False, '완결된전자기장텐서/퍼텐셜/미분형식관계와명명E/B/c/Eb/Bab/ta및-+++조건은보존했다. 하지만소실성분식예고를지우며실제로채워진Fμν기호까지삭제했다. 원문의동일대상표기를복원하고새텐서성분식/변수/지표는만들지않는다.'),
    'expanded_train:143138': (True, '원형전체와선택문/전체diff를읽었다. 빈외부링크절만분리하고실제퍼프대디/Notorious B.I.G/작품명·날짜·차트순위·멤버와같이보기/분류항목을모두보존했다. 분류라벨/불릿구조와끝개행만추가했다. 음악사사실전체검증은아니다.'),
}
assert len(result['rows']) == 15
for ident, (accepted, finding) in findings.items():
    assert ident not in {r['id'] for r in result['rows']}
    row = guards[ident]
    assert row.get('ordered_source_deletion') is False
    assert ident not in contract['restricted_ids']
    assert row['original_text_sha256'] not in contract['restricted_hashes']
    original, body = ROOT / row['original_comparison_source'], ROOT / row['body']
    assert sha(original) == row['original_text_sha256']
    assert sha(body) == row['clean_text_sha256']
    result['rows'].append({'id': ident,
        'original': {'path': str(original.relative_to(ROOT)), 'sha256': row['original_text_sha256']},
        'body': {'path': row['body'], 'sha256': row['clean_text_sha256']},
        'reviewer': 'root', 'full_original_and_selected_body_read': True, 'full_diff_read': True,
        'observation_tool_chunk': 'e067ff', 'finding': finding,
        'decision': 'REVIEWED_ACCEPTABLE_CHANGES_WITH_STATED_LIMITS' if accepted else
                    'CORRECTION_REQUIRED_BEFORE_SEMANTIC_CLOSURE',
        'source_fact_verification': False})
result.update({'status': 'TWENTY_ONE_ACTUAL_READS_FOUR_NEW_BOUNDED_REPAIRS_PENDING',
    'actually_reviewed_sources': 21, 'remaining_unreviewed_flag_sources': 564,
    'old_root11_acceptable_sources': 7, 'old_root11_sources_requiring_replacement': 14,
    'corrected_semantic_reviewed_sources': 10, 'corrections_still_pending': 4,
    'prior': {'path': str(prior.relative_to(ROOT)), 'sha256': sha(prior)},
    'verification_code': {'path': str(Path(__file__).resolve().relative_to(ROOT)),
                          'sha256': sha(Path(__file__).resolve())},
    'new_root_or_cache_adoption': 0})
out = AUDIT / 'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V8.json'
with out.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
print(json.dumps({'actual_independent_full_reads': 21, 'old_body_defects': 14,
    'known_replacements_reviewed': 10, 'new_replacements_pending': 4,
    'other_flags_unreviewed': 564, 'adopted': 0}))
