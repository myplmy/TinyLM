"""Write role-local text feedback; never approve or rewrite source content."""
from collections import Counter
from pathlib import Path
import json

AUDIT = Path(__file__).resolve().parent
snapshot = max((AUDIT / "legacy_progress_v2").glob("*.json"))
value = json.loads(snapshot.read_bytes())
out = AUDIT / "legacy_mechanical_feedback_v2"
out.mkdir(exist_ok=False)
for role in value["roles"]:
    rows = [row for row in value["records"] if row["role"] == role and
            (row.get("mechanical_error") or row["mechanical_status"] == "NONCANONICAL_AUTHOR_STATUS_NEEDS_REVIEW")]
    lines = ["# 실제 편집 적용 대조 피드백", "", "- 기준 스냅샷: `" + snapshot.name + "`",
             "- 빈 치환 인접 fence는 적용기 v2에서 수정했고 11회귀 실제0입니다.",
             "- 아래 오류는 그 수정 뒤 실제 대조에서 남았습니다. 자동 채택은0입니다.",
             "- source anchor는 기준 원문에서 정확히 한 번만 나와야 합니다. 반복 표제는 앞뒤 실제 문맥을 함께 인용해 유일하게 만드세요.",
             "- recipe는 자유서술 지시가 아니라 TASK의 source_id/base/base_sha256/reason 및 ORIGINAL/REPLACEMENT literal 형식입니다.",
             "- 기존 제안은 보존하고 수정은 별도 `_v2.edits.md` 등 새 파일과 review_NNN_v2.md의 명시 새 행으로 남기세요.",
             "- root가 본인 역할에 한해 이 피드백 파일 읽기를 허용합니다. 다른 역할 산출물은 범위가 아닙니다.", "",
             "| 원문 ID | 상태 | 실제 적용 거부 또는 표기 문제 | 실제 참조 |", "|---|---|---|---|"]
    for row in rows:
        cells = [row["id"], row["status"], row.get("mechanical_error", "KEEP_SOURCE/ADOPT_CANDIDATE/EDIT_TEXT/EDIT_RECIPE/EXCLUDE/NEEDS_ROOT 중 실제 상태를 명시"),
                 row["output_references"].replace("|", "&#124;")]
        lines.append("| " + " | ".join(cells) + " |")
    path = out / (role + ".md")
    with path.open("x", encoding="utf-8") as stream:
        stream.write(chr(10).join(lines) + chr(10))
    print(role, len(rows), path.relative_to(AUDIT))
