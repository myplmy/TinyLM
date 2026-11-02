"""Prepare full-type native verification and source-only reader jobs from proven machinery."""
from pathlib import Path

AUDIT=Path(__file__).resolve().parent
native_target=AUDIT/'verify_remaining_birth_native_v1.py'
reader_target=AUDIT/'prepare_remaining_birth_readers_v1.py'
assert not native_target.exists() and not reader_target.exists()
native=(AUDIT/'verify_remaining_repeat_native_v2.py').read_text(encoding='utf-8')
for before,after in [
 ('repeat_remaining_named_strata_v2','remaining_birth_full_sources_v1'),
 ('repeat_remaining_native_proofs_v2','remaining_birth_native_proofs_v1'),
 ('732','2743'),
 ('fresh_native_named_strata','fresh_native_remaining_birth_type'),
 ('MAIN_BODY_REPETITION_REQUIRES_CONTEXT','INTERNAL_BIRTH_YEAR_CONFLICT_UNRESOLVED')
]:
    assert before in native,before
    native=native.replace(before,after)
before='inv.sha(clean) == targets[key]["candidate_sha256"]'
assert native.count(before)==1
native=native.replace(before,'inv.sha(clean) == inv.sha(row["diagnostic_candidate"])')
native=native.replace('all2743 named-stratum sources','all2743 remaining birth-type sources')
with native_target.open('x',encoding='utf-8') as stream:
    stream.write(native)

reader=(AUDIT/'prepare_named_repeat_review_v2.py').read_text(encoding='utf-8')
for before,after in [
 ('repeat_named_roles_counter_v2','remaining_birth_full_counter_v1'),
 ('repeat_remaining_native_proofs_v2','remaining_birth_native_proofs_v1'),
 ('732','2743'),
 ('반복 문맥의 독립 원문 판독','출생연도 충돌의 전량 원문 판독'),
 ('REPEATED_LINE_CONTEXT_REQUIRES_INDEPENDENT_SOURCE_READING',
  'BIRTH_YEAR_CONFLICT_REQUIRES_INDEPENDENT_SOURCE_READING')
]:
    assert before in reader,before
    reader=reader.replace(before,after)
anchor='    save(directory / "START_HERE.md", chr(10).join(start) + chr(10))'
assert reader.count(anchor)==1
extra='''    start.extend([
        "출생연도충돌유형전량이다.원문/동결후보를그대로보는것은어느연도도정답으로승인한것이아니다.",
        "나이/월일에서연도를역산하거나분류와도입중하나를임의로선택하지않는다.웹/외부자료접근도금지다.",
        "다른사람의날짜·인용·재임/재위·사망일·음양력·추정/논쟁·조건/부정을충돌당사자의출생필드로합치지않는다.",
        "같은인물의실제서로다른출생연도필드가충돌하면두값과직접의존부를원형sidecar에남기고유효한월일·이름·직함·생애를보존한다.",
        "연도만분리해도나머지문장과사건시점이독립적으로이해되는지확인한다.미상대상을다른사람이나날짜로채우지않는다.",
        "실제서로다른사람/역할의날짜등으로충돌신호가해명되면정확원문역할을근거열에적고전체후보가정상일때만ACCEPT한다.",
        "이미소실된수식/표/대상이나페이지UI등다른결손도무시하지않는다.완결부분을살리고직접불완결구간만원형보류한다.",
        "독립본문을확정할수없으면정확구간과이유를NEEDS_ROOT로묻고다른TASK를계속한다.문법증명불일치를복구불가로자동승격하지않는다.",
        "역할변경/전체캐시채택/학습재개는총괄과사용자소유다.한TASK종료가전체배정종료가아니다."])
'''
reader=reader.replace(anchor,extra+anchor)
with reader_target.open('x',encoding='utf-8') as stream:
    stream.write(reader)
print('출생충돌2743 전량 native 재생성과 다섯 역할 reader 준비; 실행/판독/채택과 구별')
