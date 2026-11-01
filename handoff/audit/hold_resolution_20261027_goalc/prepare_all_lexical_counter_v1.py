"""Assign every unreviewed current-body lexical signal, reusing exact proofs."""
from pathlib import Path

AUDIT = Path(__file__).resolve().parent
source = (AUDIT / "prepare_root_selected_literal_counter_v3.py").read_text(encoding="utf-8")
source = source.replace("root_selected_literal_counter_v3", "root_selected_lexical_counter_v1")
source = source.replace("root_selected_body_literals_v3.json", "root_selected_body_literals_v5.json")
source = source.replace("ROOT_AUTHORED_SELECTIONS_V7.json", "ROOT_AUTHORED_SELECTIONS_V9.json")
source = source.replace("reviewed_selection_plan_v10.json", "reviewed_selection_plan_v15.json")
source = source.replace('roles = ["context_controls", "structure_counter"]',
    'roles = ["context_controls", "context_hangul", "context_latin", "historical_review", "structure_counter"]')
anchor = 'flagged = []'
assert source.count(anchor) == 1
source = source.replace(anchor, anchor + '''
snapshot_path = AUDIT / "supplemental_candidates_snapshot_v38.json"
snapshot = inv.cache.read(snapshot_path)
context_pins.append(snapshot_path)
independent_groups = {
    "root_selected_signal_counter_v1", "root_selected_signal_counter_v2",
    "root_selected_literal_counter_v3", "root_selected_literal_counter_v4",
    "authored_literal_counter_v3", "secondary_body_counter_v1",
    "legacy_incident_counter_v1", "retracted_review_counter_v1",
    "formal_source_second_review_v1", "style_value_counter_v1"}
accepted_exact = {}
for previous in snapshot["records"]:
    if (previous["cohort"] in independent_groups and previous["decision"] == "ADOPT_CANDIDATE"
            and previous.get("clean_text_sha256")):
        key = (previous["id"], previous["original"]["sha256"], previous["clean_text_sha256"])
        accepted_exact.setdefault(key, []).append(previous)
''')
start, end = source.index("    signals = []"), source.index("\nrepair_plan = ")
source = source[:start] + '''
    if not row["introduced_lexical_total"]:
        continue
    key = (row["id"], row["compare_source"]["sha256"], row["clean_text_sha256"])
    prior = accepted_exact.get(key)
    if prior:
        for review in prior:
            inv.require(inv.file_sha(ROOT / review["review"]["path"]) == review["review"]["sha256"], "reused exact source review changed")
            inv.require(inv.file_sha(ROOT / review["body"]) == review["clean_text_sha256"], "reused exact independent body changed")
        reused.append(dict(id=row["id"], original=row["compare_source"],
            body=dict(path=row["body"], sha256=row["clean_text_sha256"]),
            explicit_independent_accept_reviews=[review["review"] for review in prior],
            basis="EXACT_SAME_ORIGINAL_AND_CURRENT_BODY_ALREADY_INDEPENDENTLY_ACCEPTED"))
        continue
    inv.require(row["compare_source"]["sha256"] == row["original_text_sha256"], "a restricted parent view needs separate exact mediation")
    signals = ["INTRODUCED_LEXICAL_TOKENS_ARE_DIAGNOSTIC_NOT_CONFIRMED_NEW_FACTS"]
    if not row["ordered_nonwhitespace_deletion_only"]:
        signals.append("NONWHITESPACE_ADDITION_OR_REORDER")
    if row["introduced_numeric_occurrences"]:
        signals.append("INTRODUCED_NUMERIC_TOKEN_SIGNAL")
    flagged.append((row, signals))
''' + source[end:]
source = source.replace('for source in repair_plan["records"]:', "for source in []:")
anchor = 'inv.require(len({row["id"] for row, signals in flagged}) == len(flagged),'
assert source.count(anchor) == 1
source = source.replace(anchor, 'inv.require(len(flagged) == 579 and len(reused) == 57, "all636 lexical signals must be assigned or exactly reused")' + chr(10) + anchor)
source = source.replace("신호 합집합46과 기계적 미결2의 전체", "추가 어휘 신호636 중 정확 독립 수용 근거57을 재사용한 나머지579쌍 전체")
anchor = 'contract += """'
assert source.count(anchor) == 1
source = source.replace(anchor, '''contract += """
이번 묶음은 실제 선택9 본문에 대한 추가어휘 신호의 미판독579쌍 전부다. 추가 토큰은 공백/구두점/태그 정리로 생길 수도 있어 오류 확정이 아니다.
한편 실제 원문에 없던 단어/숫자/관계/문단이 추가됐다면 원문에서 확인되지 않는 후보 추가를 본문으로 채택하지 않는다. 원문 자체의 사실 주장과 구분하고 failed-candidate 근거로 남긴다.
정의/조건/부정/범위/인용 주체가 삭제되어 문장이 다른 뜻이 됐는지도 확인한다. 필요한 반복·명칭·수치·완결 문단을 일괄 지우거나 문서를 처음6000문자 등 임의 길이로 자르지 않는다.
전체 source/candidate와 diagnostic diff의 모든 순서뷰를 EOF까지 실제로 읽는다. 자신의 새 TXT도 전체 차이와 EOF를 검산한다. 새파일 생성용 좁은 표준 파일 API는 텍스트 편집에 포함되며 코드/통계/시험 구현 권한이 아니다.
각 TASK의모든ID를실제처리한뒤즉시정확표형review_NNN.md를저장하고다음TASK로간다. 일부분만 완료하고 전량완료라 쓰지 않는다. 판단 곤란은 정확 문맥으로 root에 묻고 독립 다음 ID를 계속한다.
""" + chr(10)
''' + anchor)
output = AUDIT / "materialize_all_lexical_counter_v1.py"
compile(source, str(output), "exec")
with output.open("x", encoding="utf-8") as stream:
    stream.write(source)
views = (AUDIT / "prepare_selected_literal_views_v3.py").read_text(encoding="utf-8")
views = views.replace("root_selected_literal_counter_v3", "root_selected_lexical_counter_v1")
with (AUDIT / "prepare_all_lexical_views_v1.py").open("x", encoding="utf-8") as stream:
    stream.write(views)
print("Prepared all579 current lexical pairs and exact57 reuse; not yet materialized.")
