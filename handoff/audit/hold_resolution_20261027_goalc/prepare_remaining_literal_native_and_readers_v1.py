"""Adapt audited full-source machinery; never change frozen production policy."""
from pathlib import Path

AUDIT = Path(__file__).resolve().parent
native = (AUDIT / 'verify_remaining_birth_native_v1.py').read_text(encoding='utf-8')
for before, after in (
    ('remaining_birth_full_sources_v1', 'remaining_literal_full_sources_v1'),
    ('remaining_birth_native_proofs_v1', 'remaining_literal_native_proofs_v1'),
    ('fresh_native_remaining_birth_type', 'fresh_native_remaining_literal_type'),
    ('INTERNAL_BIRTH_YEAR_CONFLICT_UNRESOLVED',
     'GLOBAL_PROGRAM_WORD_DOES_NOT_PROVE_EACH_EMPTY_PAREN_LITERAL'),
):
    assert before in native
    native = native.replace(before, after)
native = native.replace('len(sources) == 2743', 'len(sources) == census["counts"]["queued_unique"]')
native = native.replace('unique_total=2743', 'unique_total=len(sources)')
native = native.replace('all2743 remaining birth-type sources', 'every queued literal-type source')
native = native.replace('ALL2743_FRESH_NATIVE_AND_REGENERATION_CHECKED_REVIEW_STILL_REQUIRED',
                        'ALL_QUEUED_LITERAL_FRESH_NATIVE_CHECKED_REVIEW_REQUIRED')
assert '2743' not in native
with (AUDIT / 'verify_remaining_literal_native_v1.py').open('x', encoding='utf-8') as stream:
    stream.write(native)

reader = (AUDIT / 'prepare_remaining_birth_readers_v1.py').read_text(encoding='utf-8')
begin = reader.index('    start.extend([')
end = reader.index('    save(directory / "START_HERE.md"', begin)
extra = '''    start.extend([
        "전량의 빈 괄호/프로그램 문맥 유형이다. 프로그램 단어만으로 각 괄호의 의미가 증명되지는 않는다.",
        "빈 함수 호출·튜플·서명·코드 문자열·인용은 실제 문법과 문맥을 보고 보존한다.",
        "표적 수식·변수·값이 사라진 설명은 직접 의존 구간만 원형 HOLD하고 독립 정의·코드·예시는 보존한다.",
        "나이·기간·수량·단위·날짜·불확실성과 출처 귀속을 보존하며 없는 값을 만들어 채우지 않는다.",
        "고립 구두점·명백한 닫는 괄호·조사는 의미를 바꾸지 않는 최소 보정만 허용한다.",
        "controls는 별도 고정 reader 허가를 받은 뒤에만 실제 입력을 읽는다. 다른 역할은 자기 지정 입력만 읽는다.",
        "START의 마지막 TASK까지 전체 배정을 처리한다. 일부 종료를 전체 목표 종료로 선언하지 않는다."])
'''
reader = reader[:begin] + extra + reader[end:]
for before, after in (
    ('remaining_birth_full_counter_v1', 'remaining_literal_full_counter_v1'),
    ('remaining_birth_native_proofs_v1', 'remaining_literal_native_proofs_v1'),
    ('len(source["rows"]) == 2743', 'len(source["rows"]) > 0'),
    ('source["counts"]["fresh_regeneration_and_proof_match"] == 2743',
     'source["counts"]["fresh_regeneration_and_proof_match"] == len(source["rows"])'),
    ('sources=2743', 'sources=len(source["rows"])'),
    ('6000', '2000'),
    ('출생연도 충돌의 전량 원문 판독', '빈 괄호의 프로그램 문맥 전량 원문 판독'),
    ('BIRTH_YEAR_CONFLICT_REQUIRES_INDEPENDENT_SOURCE_READING',
     'LITERAL_PROGRAM_CONTEXT_REQUIRES_INDEPENDENT_SOURCE_READING'),
    ('ALL2743_NATIVE_SOURCE_CANDIDATE_FULL_READING_REQUIRED_NOT_ADMISSION',
     'ALL_QUEUED_LITERAL_NATIVE_SOURCE_FULL_READING_REQUIRED_NOT_ADMISSION'),
    ('이2743건은지정유형전량의판독후보이며판독의결론이아니다.',
     '이 배정은 기존 소유와 보호자료를 제외한 유형 전량의 판독 후보이며 판독의 결론이 아니다.'),
):
    assert before in reader, before
    reader = reader.replace(before, after)
reader = reader.replace('all2743', 'all queued literal').replace('all2743', 'all queued literal')
assert '2743' not in reader
with (AUDIT / 'prepare_remaining_literal_readers_v1.py').open('x', encoding='utf-8') as stream:
    stream.write(reader)
print('new literal native verifier and role reader producer saved')
