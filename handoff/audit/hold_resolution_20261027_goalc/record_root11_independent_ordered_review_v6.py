"""Record six additional actual readings; retain all unresolved old-body defects."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main():
    prior_path = AUDIT / 'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V5.json'
    result = json.loads(prior_path.read_text(encoding='utf-8'))
    guarded = json.loads((AUDIT / 'EXACT_SELECTION_RUNTIME_GUARDS_V10.json').read_text())
    records = {r['id']: r for r in guarded['records']}
    contract = json.loads((AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json').read_text())
    findings = {
        '104207': '실제 한자명 林達植이 함께 삭제됐으며 도입1963은 분리했지만 분류1964는 남아 있다. 한자명과 월일·나머지 정보를 보존하고 두 상충 출생연도만 함께 분리해야 한다.',
        '1056327': '도입1987은 분리했지만 분류1978은 남아 한 출생연도를 고른 모양이다. 두 상충 출생연도만 함께 분리하고 실제 월일·학력·2009년 경력을 보존해야 한다.',
        '1056993': '도입1959와 분류1958은 분리했지만 초기생애의 실제1959년 출생 주장은 남는다. 그 출생연도도 분리하면서 실제2월12일·뉴욕·부친·나이·경력·모든 채워진 관련 자료는 보존해야 한다.',
        '1060163': '도입1985는 분리했지만 분류1981은 남아 있다. 두 상충 출생연도만 함께 분리하고 실제 영문명·월일·작품/연도·나머지 분류는 보존해야 한다.',
        '1066704': '도입2002/분류2001 양쪽을 분리했고 실제4월3일·활동일/30001표/4위·작품명·공식출처명·살아있는사람 등은 보존했다. 빈 작품절과 병기슬롯만 줄였으며 이 범위의 의미보존은 수용 가능하다.',
        '106989': '양쪽 상충 출생연도1980/1977은 분리됐으나 도입의 실제 출생지 중국 베이징도 삭제됐다. 단순 베이징시출신 분류는 같은 출생지 문장의 대체가 아니므로 실제 출생지만 복원해야 한다.',
    }
    for digits, finding in findings.items():
        ident = 'expanded_train:' + digits
        assert ident not in {r['id'] for r in result['rows']}
        r = records[ident]
        assert ident not in contract['restricted_ids']
        assert r['original_text_sha256'] not in contract['restricted_hashes']
        original, body = ROOT / r['original_comparison_source'], ROOT / r['body']
        assert sha(original) == r['original_text_sha256']
        assert sha(body) == r['clean_text_sha256']
        result['rows'].append({
            'id': ident, 'original': {'path': r['original_comparison_source'], 'sha256': r['original_text_sha256']},
            'body': {'path': r['body'], 'sha256': r['clean_text_sha256']},
            'reviewer': 'root', 'full_original_and_selected_body_read': True,
            'full_diff_read': True,
            'observation_tool_chunk': '88e40e' if digits == '1056993' else '451c21',
            'finding': finding,
            'decision': 'REVIEWED_ACCEPTABLE_CHANGES_WITH_STATED_LIMITS' if digits == '1066704' else 'CORRECTION_REQUIRED_BEFORE_SEMANTIC_CLOSURE',
            'source_fact_verification': False,
        })
    assert len(result['rows']) == len({r['id'] for r in result['rows']}) == 15
    result.update({'status': 'FIFTEEN_ACTUAL_READS_TEN_OLD_BODY_DEFECTS_FIVE_REPAIRS_REVIEWED_FIVE_PENDING',
                   'actually_reviewed_sources': 15, 'remaining_unreviewed_flag_sources': 570,
                   'old_root11_acceptable_sources': 5, 'old_root11_sources_requiring_replacement': 10,
                   'corrected_semantic_reviewed_sources': 5, 'corrections_still_pending': 5,
                   'prior': {'path': str(prior_path.relative_to(ROOT)), 'sha256': sha(prior_path)},
                   'verification_code': {'path': str(Path(__file__).resolve().relative_to(ROOT)), 'sha256': sha(Path(__file__).resolve())}})
    out = AUDIT / 'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V6.json'
    with out.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write(chr(10))
    print(json.dumps({'path': str(out.relative_to(ROOT)), 'reviewed': 15, 'other_flags_unread': 570,
                      'old_bodies_requiring_replacement': 10, 'repairs_reviewed': 5, 'repairs_pending': 5}))


if __name__ == '__main__':
    main()
