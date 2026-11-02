"""Reuse the complete-pair exporter for all223 source-verified alias candidates."""
from pathlib import Path

AUDIT = Path(__file__).resolve().parent


def once(source, old, new):
    assert source.count(old) == 1, old
    return source.replace(old, new, 1)


source = (AUDIT / 'prepare_repeat_local_review_v1.py').read_text(encoding='utf-8')
source = source.replace('all40', 'all223').replace('ALL40', 'ALL223')
for old, new in [
    ('"repeat_local_context_counter_v1"', '"nominal_local_alias_counter_v1"'),
    ('"repeat_local_native_proofs_v1/complete.json"', '"nominal_local_native_proofs_v1/complete.json"'),
    ('len(source["rows"]) == 40', 'len(source["rows"]) == 223'),
    ('source["counts"]["fresh_regeneration_and_proof_match"] == 40',
     'source["counts"]["fresh_regeneration_and_proof_match"] == 223'),
    ('roles = ["context_controls", "context_hangul", "historical_review"]',
     'roles = ["context_controls", "context_hangul", "context_latin", "historical_review", "legacy_review"]'),
    ('REPEATED_LINE_CONTEXT_REQUIRES_INDEPENDENT_SOURCE_READING',
     'NOMINAL_EMPTY_ALIAS_SOURCE_REQUIRES_INDEPENDENT_READING'),
    ('# 반복 문맥의 독립 원문 판독', '# 명명된 대상의 빈 별칭 후보 독립 원문 판독'),
    ('반복 줄이 필요 없는 추출 중복인지, 서로 다른 실제 제목·작성자·문단의 정보인지 원문 전체로 판단한다.',
     '빈 괄호가 명명된 대상의 선택적 별칭인지, 빠진 수식·기호·필수 값인지 원문 전체로 판단한다.'),
    ('정상 반복은 지우지 않고 관계와 순서를 보존한다. 누락식/표·코드·인용·숫자·부정·조건·출처를 보호한다.',
     '괄호 밖 실제 이름·별칭·관계·순서를 보존한다. 수식/표·코드·전사·인용·숫자·부정·조건·출처를 보호한다.'),
    ('이40건은자동탐지의후보이며판독의결론이아니다.',
     '이223건은자동증명의후보이며판독의결론이아니다.'),
    ('sources=40, assignments=', 'sources=223, assignments='),
]:
    source = once(source, old, new)
exec(compile(source, str(Path(__file__)), 'exec'))
