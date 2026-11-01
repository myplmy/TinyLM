"""Recover saved review bindings, not unavailable historical Markdown bytes."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
snapshots = sorted((AUDIT / "legacy_progress_v8").glob("*.json"))
before = json.loads(snapshots[0].read_bytes())
after = json.loads(snapshots[-1].read_bytes())
review = "data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_latin/legacy_span_review_v2/review_015.md"
current = (ROOT / review).read_bytes()
current_text = current.decode("utf-8")
current_ids = set()
for line in current_text.splitlines():
    if line.startswith("|"):
        cell = line.split("|")[1].strip(" `*")
        if re.fullmatch(r"[0-9]+", cell):
            current_ids.add("expanded_train:" + cell)
        elif re.fullmatch(r"expanded_train:[0-9]+", cell):
            current_ids.add(cell)
rows = [row for row in before["records"] if row["role"] == "context_latin"
        and row["review"] == review and row["id"] not in current_ids]
assert rows
for row in rows:
    proof = row.get("proof")
    if proof:
        actual = hashlib.sha256((ROOT / proof["path"]).read_bytes()).hexdigest().upper()
        assert actual == proof["sha256"], "saved authored recipe changed"
    if row.get("body"):
        assert hashlib.sha256((ROOT / row["body"]).read_bytes()).hexdigest().upper() == row["clean_text_sha256"]
records = dict(status="RECOVERED_BINDINGS_FROM_SNAPSHOT_NOT_WHOLE_HISTORICAL_MD", rows=rows,
               before_snapshot=str(snapshots[0].relative_to(ROOT)), after_snapshot=str(snapshots[-1].relative_to(ROOT)),
               lost_review=review, old_review_sha256=rows[0]["review_sha256"],
               current_review_sha256=hashlib.sha256(current).hexdigest().upper(), root_approved=False)
output = AUDIT / "LOST_LATIN_REVIEW_015_BINDINGS_V1.json"
with output.open("x", encoding="utf-8") as stream:
    json.dump(records, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
lines = ["# review_015의 유실된 명시 연결 복구", "",
         "root가 저장한 이전 스냅샷에서 복구한 판정/출력 연결이다. 과거 review_015.md 전체의 원래 바이트를 복구한 것은 아니다.",
         "본인 context_latin만 이 파일 읽기를 허용한다. 아래 기존 자기 recipe/본문은 이미 있던 정확 산출물이며 root가 실제 SHA를 재검산했다.",
         "기존 검토표를 다시 덮지 말고 존재하지 않는 새 review_020.md 또는 더 높은 새 순번에 아래 canonical 행을 모두 보존해 복구한다.",
         "추가 원문 재작성·없는 값 생성은 하지 않는다. 이미 기계거부였던 항목은 그 상태를 보존하고 다음 실제 보완으로 넘긴다.",
         "복구 행의 root 승인이나 새 캐시 채택은 아니다. 현재14건 실제새본문 작업도 새 파일 이름만 사용한다.", "",
         "이전 검토표SHA: `" + records["old_review_sha256"] + "`",
         "현재 바뀐 검토표SHA: `" + records["current_review_sha256"] + "`", "",
         "| ID | 판정 | 실제 판독 범위 기록 | 실제 출력 연결 | 당시 기계 상태 |",
         "|---|---|---|---|---|"]
for row in rows:
    lines.append("| " + " | ".join([row["id"], row["status"], row["read_scope"].replace("|", "&#124;"),
                                    row["output_references"].replace("|", "&#124;"), row["mechanical_status"]]) + " |")
path = AUDIT / "LOST_LATIN_REVIEW_015_BINDINGS_V1.md"
with path.open("x", encoding="utf-8") as stream:
    stream.write(chr(10).join(lines) + chr(10))
print(json.dumps(dict(lost_rows=len(rows), ids=[row["id"] for row in rows], feedback=str(path.relative_to(ROOT)))))
