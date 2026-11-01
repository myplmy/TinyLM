"""Reuse the exact-source counter exporter for every one of the27 new matches."""
from pathlib import Path

AUDIT = Path(__file__).resolve().parent
source = (AUDIT / 'prepare_v23_structural_counter_v1.py').read_text(encoding='utf-8')
changes = [
    ('from scripts import p106b_hold_resolution_policy_v23 as policy',
     'from scripts import p106b_hold_resolution_policy_v26 as policy'),
    ('from scripts import p106b_hold_resolution_revision_v23 as revision',
     'from scripts import p106b_hold_resolution_policy_v25 as old_policy'),
    ('structural_candidate_profile_v22_v1', 'ordinal_metadata_candidate_census_v26_v1'),
    ('policy_v23_structural_counter_v1', 'ordinal_metadata_counter_v26_v1'),
    ('len(selected) == 33 and len({r["original_text_sha256"] for r in selected}) == 33',
     'len(selected) == 27 and len({r["original_text_sha256"] for r in selected}) == 27'),
    ('roles = ["context_controls", "context_hangul", "context_latin"]',
     'roles = ["context_controls", "context_hangul", "context_latin", "historical_review", "structure_counter"]'),
    ('pins = {name: inv.file_sha(ROOT / name) for name in revision.CODE}',
     '''pins = dict(profile["production_source_pins"])
for name, digest in pins.items():
    inv.require(inv.file_sha(ROOT / name) == digest, "whole-census ordinal proof code changed")'''),
    ('        value = policy.propose(dict(source, text=raw, complete_eos=complete, valid_utf8=valid))',
     '''        input_row = dict(source, text=raw, complete_eos=complete, valid_utf8=valid)
        before = old_policy.propose(input_row)
        inv.require(before["decision"] == "PENDING"
                    and inv.sha(before.get("candidate", before["text"])) == source["diagnostic_sha256"],
                    "fresh exact original does not reproduce its v25 diagnostic")
        value = policy.propose(input_row)'''),
    ('rows.append(dict(source, **pair, role=role, candidate_decision=value["decision"],',
     '''rows.append(dict(source, **pair, role=role, raw_original_not_redecoded=False,
                         fresh_exact_original_readback=True,
                         original_native_v25_proposal_reproduced=True,
                         original_source_code_guard=policy.code_preserved(raw, clean),
                         original_source_unicode_guard=policy.unicode_examples_preserved(raw, clean),
                         original_source_style_guard=policy.semantic_style_preserved(raw, clean),
                         ordered_deletion=policy.ordered_deletion(raw, clean),
                         candidate_decision=value["decision"],'''),
    ('"전체 계수 유형: " + ", ".join(row["proof_kinds"])',
     '"전량 계수된 실제 서수 분류값: " + ", ".join(row["proof"]["dotted_category_values"])'),
    ('pins == {name: inv.file_sha(ROOT / name) for name in revision.CODE}',
     'pins == {name: inv.file_sha(ROOT / name) for name in pins}'),
    ('ALL_33_STRUCTURE_CENSUS_MATCHES_HAVE_EXACT_SOURCE_PAIRS_NOT_ADMISSION',
     'ALL_27_ORDINAL_CENSUS_MATCHES_HAVE_EXACT_SOURCE_PAIRS_NOT_ADMISSION'),
    ('이 33쌍은 전체 v21 미결의 구조 후보 전수계수 결과 전부다.',
     '이 27쌍은 전체 v25 미결의 서수 분류 경계 후보 전수계수 결과 전부다.'),
    ('prepare_v23_structural_views_v1.py', 'prepare_v26_ordinal_views_v1.py')
]
for before, after in changes:
    assert source.count(before) == 1, before
    source = source.replace(before, after)
anchor = '    for number, row in enumerate(owned, 1):'
assert source.count(anchor) == 1
source = source.replace(anchor, '''    instructions += [
        "현재 root_selected_lexical_counter_v1의 기존32TASK 전부를 먼저 마친 뒤 이 묶음을 시작한다.",
        "이 새 묶음은 분류명 내부의 서수 마침표를 지우지 않는 경계 증명이다. 원문 값/분류 순서/참고자료를 보존한다.",
        "일반 마침표를 전부 허용하거나, 처음6000문자만 읽고 완료라 쓰거나, 공통 수식 결손을 무시하면 안 된다.",
        "코드/통계/모델/GPU/Git/웹은 금지한다. 새 TXT/MD 편집용 좁은 파일 API와 nl/sed/diff/tail 읽기 보조만 허용한다.",
        "raw EOF에서 마지막 개행이 없을 수 있으므로 wc-l을 마지막 논리줄로 오인하지 않는다. 마지막 실제 행과 전체 diff를 확인한다."]
''' + anchor)
output = AUDIT / 'materialize_v26_ordinal_counter_v1.py'
compile(source, str(output), 'exec')
with output.open('x', encoding='utf-8') as stream:
    stream.write(source)
print('Prepared every27 exact-source counter pair; prior579 tasks remain first priority.')
