"""Pin four already-authored repairs for a second independent text reader."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
snapshot_path = AUDIT / "supplemental_candidates_snapshot_v11.json"
snapshot = inv.cache.read(snapshot_path)
choices = {46028: ("formal_source_second_review_v1", "context_latin"),
           62929: ("formal_source_second_review_v1", "context_latin"),
           492111: ("formal_source_second_review_v1", "context_latin"),
           1250821: ("clinical_source_review_v1", "context_controls")}
out = BASE / "secondary_body_counter_v1"
inv.require(not out.exists(), "new secondary text counter namespace required")
rows, assignments = [], {}
for number, (cohort, role) in choices.items():
    ident = "expanded_train:" + str(number)
    row = next(row for row in snapshot["records"] if row["id"] == ident and row["cohort"] == cohort)
    original = row.get("compare_source", row["original"])
    candidate = dict(path=row["body"], sha256=row["clean_text_sha256"])
    for pin in [original, candidate]:
        inv.require(inv.file_sha(ROOT / pin["path"]) == pin["sha256"], "secondary input changed")
    record = dict(id=ident, role=role, original=original, candidate=candidate,
                  source_cohort=cohort, original_author=row["role"], root_approved=False)
    if row.get("compare_source"):
        record["restricted_parent_metadata_only"] = row["original"]
        record["restricted_parent_not_opened_or_copied"] = True
    rows.append(record)
    assignments.setdefault(role, []).append(ident)
for role, ids in assignments.items():
    directory = BASE / "agents" / role / "secondary_body_counter_v1"
    directory.mkdir(parents=True)
    lines = ["# 実際に保存した部分本文の第二独立対照", "",
        "この見出しの言語は本文の判定根拠ではない。以下の韓国語契約を適用する。", "",
        "현재 진행 묶음 한 개를 끝낸 뒤 이 정확 지정쌍을 독립 전문 대조한다. 허용은 이 TASK와 아래 exact original/candidate 및 자기 새 txt/md뿐이다.",
        "text-only: cat/sed/nl, exact 지정쌍 diff -u 읽기, 자기 새TXT/MD 저장만. 코드/시험/계산/통계/해시/모델/GPU/Git/웹/설치/다른원문 접근과 기존파일덮기·삭제 금지.",
        "각 지정 original/candidate를 처음부터 EOF까지 읽는다. 큰 출력이 잘리면 작은 줄구간으로 이어 실제 전체를 확인한다. 읽지 못한 것을 전문 대조로 기록하지 않는다.",
        "독립된 완결 정의·역사·논리·조건·값·출처·코드·Unicode가 과잉삭제됐는지, 실제 소실식/값을 전제로한 문장이 본문에 남았는지 대조한다. 빈표제/빈필드만 바뀐 것을 실제내용손실로 보지 않는다.",
        "수식·반도체 문서의 누락 기호/계수/조건/공식을 새로 채우지 않는다. 규격의 <>와 코드형 예시는 실제문법일 수 있어 그대로 보호한다. 실제결손과 직접의존 구간만분리하고 같은문단의 완결독립문장을 함께 지우지 않는다.",
        "1250821의 original은 제한구간을 이미 뺀 명시 view다. 원전체/빠진43–45행/다른버전은 열지 않는다. 일반 질환·역사·임상·참고자료의 이 view와 후보만 대조하고 실험/제조/병원체조작 절차를 새로작성하거나추론하지 않는다. 과학적/임상적 외부사실검증은하지않는다.",
        "판정 ACCEPT_CANDIDATE / REVISE_TEXT / EXCLUDE / NEEDS_ROOT. 새review.md에 ID | 판정 | 실제판독범위 | 정확출력 | 구체근거를 쓴다. 수정필요시 실제expanded_train_ID_v2.txt와 _v2_hold.md를 새로저장한다. 코드/레시피대신실제TXT로회수하고검수메모는md에만둔다.",
        "원래본문/이전검토/실패이력은유지한다. 이것은 root채택·캐시검산·전량사실검증·학습승인이아니다.", ""]
    for row in rows:
        if row["id"] not in ids:
            continue
        lines += ["## " + row["id"], ""]
        for label in ["original", "candidate"]:
            pin = row[label]
            lines += [label + ": `" + str(ROOT / pin["path"]) + "`", label + " SHA: `" + pin["sha256"] + "`", ""]
    with (directory / "TASK.md").open("x", encoding="utf-8") as stream:
        stream.write(chr(10).join(lines) + chr(10))
out.mkdir(parents=True)
inv.write_json(out / "manifest.json", dict(status="SECOND_INDEPENDENT_PARTIAL_BODY_REVIEW_NOT_ADMISSION",
    rows=rows, assignments=assignments, pins={str(p.relative_to(ROOT)): inv.file_sha(p) for p in [snapshot_path, Path(__file__)]},
    root_adopted=0, goal_complete=False, training_authorized=False))
print(json.dumps(dict(cases=len(rows), assignments=assignments), ensure_ascii=False))
