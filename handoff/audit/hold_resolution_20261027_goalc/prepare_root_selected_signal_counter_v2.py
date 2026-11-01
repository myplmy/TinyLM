"""Assign the full union of unexplained selected-body signals, without a cap."""
from collections import Counter
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_preservation_v1 as preservation
from scripts import p106b_hold_resolution_literal_guard_v3 as literal

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
OUT = BASE / "root_selected_signal_counter_v2"
inv.require(not OUT.exists(), "new selected-body review namespace required")
audit_path = AUDIT / "root_selected_body_literals_v2.json"
selection_path = AUDIT / "ROOT_AUTHORED_SELECTIONS_V5.json"
audit = inv.cache.read(audit_path)
selections = {row["id"]: row for row in inv.cache.read(selection_path)["rows"]}
known = {"expanded_train:1709", "expanded_train:383689", "expanded_train:5416", "expanded_train:6175",
         "expanded_train:20216", "expanded_train:929270", "expanded_train:6773", "expanded_train:1242413"}
known.update(ident for ident, value in selections.items() if value.get("exact_root_evidence"))
known.update({"expanded_train:193877", "expanded_train:50559", "expanded_train:1027859", "expanded_train:119838",
              "expanded_train:48585", "expanded_train:356616", "expanded_train:452781"})
in_fresh_mediation = {"expanded_train:306600"}
roles = ["context_controls", "context_hangul", "context_latin", "historical_review"]
literal_cases = literal.load_registry()
context_pins = [AUDIT / "V20_DRAFT_PREFLIGHT_V1.json",
                AUDIT / "EVIDENCE_50559_ACCESSION_DATE_V1.md",
                AUDIT / "EVIDENCE_193877_DEATH_DATE_V1.md",
                AUDIT / "NONPROGRAM_SEARCH_UI_APPROVAL_V1.json",
                ROOT / "scripts/p106b_hold_resolution_preservation_v1.py",
                ROOT / "scripts/p106b_hold_resolution_literal_guard_v3.py"]
for ident in ["expanded_train:6773", "expanded_train:48585", "expanded_train:1027859", "expanded_train:119838"]:
    record = next(value for value in audit["records"] if value["id"] == ident)
    raw = (ROOT / record["compare_source"]["path"]).read_text(encoding="utf-8")
    clean = (ROOT / record["body"]).read_text(encoding="utf-8")
    if ident == "expanded_train:6773":
        inv.require(literal.exact_pair_preserved(raw, clean, ident, literal_cases), "exact Search UI proof differs")
    elif ident == "expanded_train:48585":
        inv.require(preservation.unicode_examples_preserved(raw, clean), "filled Unicode source value changed")
    else:
        phrase = "titles appear in 《》" if ident.endswith(":1027859") else "겹꽂쇠《》"
        if ident.endswith(":119838"):
            phrase = next((value for value in ["겹꺽쇠《》", "겹꽂쇠《》", "겹꺾쇠《》"] if value in raw and value in clean), "")
        inv.require(phrase and phrase in raw and phrase in clean, "actual punctuation-teaching context differs")
fresh_pairs = {value["id"]: value for value in inv.cache.read(context_pins[0])["independently_reviewed_new_terminal_pairs"]}
for ident in ["expanded_train:356616", "expanded_train:452781"]:
    inv.require(selections[ident]["selected"]["clean_text_sha256"] == fresh_pairs[ident]["sha256"],
                "fresh independent program pair changed")
assignments, loads, rows, reused = {role: [] for role in roles}, Counter(), [], []
flagged = []
for row in audit["records"]:
    if row["status"] != "ACTUAL_BODY_LITERAL_READBACK_NOT_SEMANTIC_APPROVAL":
        continue
    signals = []
    if not (row["unicode_guard"] and (row["code_guard"] or row["exact_reviewed_literal_exception"])):
        signals.append("CODE_OR_UNICODE")
    if not row["semantic_style_guard"]:
        signals.append("STYLE")
    if row["introduced_numeric_occurrences"]:
        signals.append("NUMERIC")
    if row["literal_hole_signals"]:
        signals += row["literal_hole_signals"]
    if row["remaining_field_literal_signals"]:
        signals.append("POST_CANDIDATE_EMPTY_FIELD_LITERAL")
    if row["raw_wiki_literal_signals"]:
        signals.append("RAW_WIKI_LITERAL")
    if row["introduced_lexical_total"] and not row["ordered_nonwhitespace_deletion_only"]:
        signals.append("SOURCE_WORDING_OR_RELATION_CHANGED_REQUIRES_INDEPENDENT_CONTEXT")
    if not signals:
        continue
    if row["id"] in known | in_fresh_mediation:
        chosen = selections[row["id"]]["selected"]
        inv.require(chosen["clean_text_sha256"] == row["clean_text_sha256"], "previously adjudicated exact body changed")
        reused.append(dict(id=row["id"], body=row["body"], clean_text_sha256=row["clean_text_sha256"],
                           signals=signals, disposition="EXACT_ROOT_CONTEXT_ALREADY_REVIEWED" if row["id"] in known
                           else "NEW_EXACT_ROOT_MEDIATION_ALREADY_ASSIGNED"))
        if row["id"] == "expanded_train:306600":
            fixed = BASE / "agents/context_hangul/repeat_context_counter_v1/expanded_train_306600_v3.txt"
            fixed_review = fixed.parent / "review_001_v3.md"
            inv.require("왕중왕()" not in fixed.read_text(encoding="utf-8") and "? ~" in fixed.read_text(encoding="utf-8"),
                        "new merged correction did not retain unknown life marker or still has the empty alias")
            reused[-1].update(disposition="NEW_SAVED_CORRECTION_REQUIRES_RESELECTION_OLD_BODY_NOT_ADMITTED",
                              corrected_body=dict(path=str(fixed.relative_to(ROOT)), sha256=inv.file_sha(fixed)),
                              corrected_review=dict(path=str(fixed_review.relative_to(ROOT)), sha256=inv.file_sha(fixed_review)))
        continue
    flagged.append((row, signals))

for row, signals in sorted(flagged, key=lambda value: (-value[0]["source_characters"], value[0]["id"])):
    prior_authors = set(re.findall(r"/agents/([^/]+)/", json.dumps(row.get("review"), ensure_ascii=False)))
    eligible = [role for role in roles if role not in prior_authors]
    inv.require(eligible, "no different active text-only role for this selected body")
    role = min(eligible, key=lambda value: (loads[value], roles.index(value)))
    loads[role] += row["source_characters"]
    original = row["compare_source"]
    candidate = dict(path=row["body"], sha256=row["clean_text_sha256"])
    for pin in [original, candidate]:
        inv.require(inv.file_sha(ROOT / pin["path"]) == pin["sha256"], "selected signal source/body changed")
    record = dict(id=row["id"], role=role, original=original, candidate=candidate, diagnostic_signals=signals,
                  source_characters=row["source_characters"], prior_cohort=row["cohort"],
                  avoided_current_body_author_roles=sorted(prior_authors),
                  assigned_role_had_current_body_review=False, root_approved=False)
    if original["sha256"] != row["original_text_sha256"]:
        previous = selections[row["id"]]
        record["restricted_parent_metadata_only"] = dict(path=previous["original_paths"][0], sha256=row["original_text_sha256"])
    rows.append(record)
    assignments[role].append(record["id"])

contract = """# 실제 선택 본문의 남은 신호에 대한 독립 대조

신호는 오류 확정이 아니다. 정확 original/candidate 전문을 EOF까지 읽고 전체 diff와 실제 남은 해당 리터럴 문맥을 확인한다. 출력이 잘리면 작은 줄 범위로 이어 읽고 실제 미판독은 보고한다.
허용은 지정 TASK/원문/후보와 자기 새TXT/MD뿐이다. cat/sed/nl 및 exact diff -u 판독만 허용하며 코드·계산·계수·통계·해시·시험·웹·모델·GPU·Git·설치·원형/타폴더변경·덮기/삭제는 금지한다.
원문에 없는 명칭/날짜/수식/조건을 만들거나 용어를 동의어로 바꾸지 않는다. 값이 채워진 목록·표·서지·코드·Unicode·역사 전사·인용의 주체·불확실성·조건은 보존한다.

## 신호별 판독

- 문구/관계 변경 신호는 새 사실 확정이 아니다. 원문에 없던 단어·관계·조건 축소가 생겼는지 전체 문맥으로 확인하고, 원문에서 완결되는 표현은 그대로 보존한다. 정의식/전제 삭제 뒤의 위 식/정의는 위와같다 같은 의존 참조가 남지 않게 한다. 필요한 목록/표 구조만 중립 라벨로 제시하고 사실 해설/수식/주어를 새로 만들지 않는다.
- 색/굵기/기울임을 source 의미와 분리해 확인한다. 채워진 실제 스타일 값·범례의 관계는 원형 또는 정확 값으로 보존하며 단순 포장이라고 일괄 지우지 않는다.

- ()나 ( )가 실제 함수/메서드 이름·호출·서명·기호의 일부이면 지우지 않는다. 실제 API/설명 문맥과 정확 리터럴을 리뷰에 적는다. 비어 있는 인명/선택병기이면 그 빈 슬롯만 정리하되 인구/수량/변수 값의 소실과 혼동하지 않는다.
- 《》 등 실제 이름이 비었으면 보충하지 않는다. 인접한 채워진 일반명사와 원문의 완결 사실만 남길 수 있으면 실제 새TXT로 보존하고, 누락 이름에 직접 의존하는 부분은 sidecar로 분리한다. 작품명이 명시되지 않은 완결 문장이라는 이유만으로 지우지 않는다.
- 남아 있는 ]] / {{ / {| / :en: 등은 실제 코드/문법/인용 예제이면 그대로 보존하고 이유와 정확 문맥을 적는다. 실제 위키 추출 잔재이면 채워진 보이는 명칭/항목/값/순서/관계를 보존하며 포장만 정리한다. 여는 링크나 필드 관계가 사라졌으면 표시명/대응을 새로 만들지 않는다.
- 실제 표의 행과 열 제목이 채워져 있으면 관계를 보존한 읽을 수 있는 구조로 정리한다. 값을 줄이거나 여러 배열을 추정 결합하지 않는다. 소속 표가 없는 색/굵기 범례와 CSS/탐색UI/서명은 실제 코드·값과 구분해 분리한다.
- 빈 각주/외부링크/표/목록 표제는 실제 다음 본문이 있는 부모인지 확인한다. 빈 자식만 있고 값이 없는 절이면 그 표제만 sidecar로 분리하며, 실제 참고자료/목록을 지우지 않는다.
- 생일/사망일 신호는 다른 인물·다른 달력/시간대의 날짜인지 먼저 귀속을 확인한다. 같은 사람의 실제 상충이면 어느 일자도 선택하지 않고 root에 두 정확 문맥을 좁게 보고하며 독립 작업을 계속한다. source 그대로라는 이유로 충돌 해결/통과라 쓰지 않는다.
- 식/변수/표/인용이 실제 빠졌다면 그 직접 의존 구간만 보류한다. 문단 전체에서 독립된 완결 정의·역사·조건·서지까지 함께 지우지 않는다. 수식/증명/누락 인용은 만들지 않는다.

필요한 실제 새 본문은 ID의 콜론을 밑줄로 바꾼 이름_v2.txt와 새 hold.md에 저장한다. 기존 파일이 있으면 더 높은 새버전을 쓴다. TXT에는 실제 원문 본문/값만 두고 검수 메모·버전/행번호·보존했습니다/hold·sidecar 안내를 넣지 않는다. 쓰기 전 정확 새 출력 경로 존재 여부를 확인하고 이미 있으면 새 vN만 쓴다. 자기 파일이라도 Update/Delete/이동/덮기/근사복구하지 않는다.
review_NNN.md 표: ID | 판정 | 실제 판독 범위 | 출력 | 구체 근거. ACCEPT_CANDIDATE / REVISE_TEXT / KEEP_SOURCE / EXCLUDE / NEEDS_ROOT를 사용한다. ACCEPT/KEEP은 남은 리터럴이 실제로 정상인 구체 문맥을 기록해야 한다. 오류 여부가 불분명하면 좁은 해당 범위만 root에 묻는다.
이 검토는 상위 캐시 채택·전체 사실검증·모델 품질·학습 승인과 별개다. 이번 배정의 모든 TASK를 마친 뒤 정확 산출물/미판독을 보고하고 final로 종료한다. 이전 완료 TASK로 돌아가지 않는다.
"""
for role in roles:
    directory = BASE / "agents" / role / OUT.name
    inv.require(not directory.exists(), "new selected-signal role directory required")
    directory.mkdir()
    owned = [row for row in rows if row["role"] == role]
    batches, batch, characters = [], [], 0
    for row in owned:
        if batch and (len(batch) == 4 or characters + row["source_characters"] > 80_000):
            batches.append(batch)
            batch, characters = [], 0
        batch.append(row)
        characters += row["source_characters"]
    if batch:
        batches.append(batch)
    names = []
    for index, batch in enumerate(batches, 1):
        name = "TASK_" + str(index).zfill(3) + ".md"
        names.append(name)
        parts = [contract, "유일한 새 출력 폴더: `" + str(directory) + "`."]
        for row in batch:
            parts += ["## " + row["id"], "original: `" + str(ROOT / row["original"]["path"]) + "`",
                      "original SHA: `" + row["original"]["sha256"] + "`",
                      "candidate: `" + str(ROOT / row["candidate"]["path"]) + "`",
                      "candidate SHA: `" + row["candidate"]["sha256"] + "`",
                      "남은 신호: " + ", ".join(row["diagnostic_signals"])]
        with (directory / name).open("x", encoding="utf-8") as stream:
            stream.write((chr(10) * 2).join(parts) + chr(10))
    with (directory / "START_HERE.md").open("x", encoding="utf-8") as stream:
        stream.write("# 현재 새 배정" + chr(10) * 2 +
                     "진행 중인 좁은 정형 리뷰 한 건만 먼저 마친 뒤 이 새 TASK를 시작한다. 완료한 이전 묶음은 다시 열지 않는다. review는 반드시 지정된 표 행으로 저장하고 굵은글씨 프로즈로 대신하지 않는다." +
                     chr(10) * 2 + "정확 출력: `" + str(directory) + "`" + chr(10) * 2 +
                     "현재 TASK: " + ", ".join(names) + chr(10))
OUT.mkdir()
result = dict(status="ALL_UNEXPLAINED_SELECTED_BODY_SIGNALS_ASSIGNED_NOT_ADMISSION", rows=rows,
              assignments=assignments, source_characters_by_role=dict(loads), reused_exact_contexts=reused,
              input_pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in [audit_path, selection_path, *context_pins, Path(__file__)]},
              cache_admitted=0, goal_complete=False, training_authorized=False)
inv.require(len(rows) + len(reused) == len(flagged) + len(reused), "selected signal coverage differs")
inv.write_json(OUT / "manifest.json", result)
print(json.dumps(dict(rows=len(rows), reused=len(reused), assignments={key:len(value) for key,value in assignments.items()},
                      source_characters_by_role=dict(loads)),ensure_ascii=False))
