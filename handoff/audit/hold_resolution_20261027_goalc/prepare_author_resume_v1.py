"""Bind only unsaved authored reviews to cold-start text-only reviewers."""
from collections import Counter
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
snapshot_path = AUDIT / "supplemental_candidates_snapshot_v7.json"
snapshot = inv.cache.read(snapshot_path)
source_path = BASE / "authored_postsignal_review_v1/manifest.json"
source = inv.cache.read(source_path)
sources = {row["id"]: row for row in source["rows"]}
saved = {row["id"] for row in snapshot["records"] if row["cohort"] == "authored_postsignal_review_v1"}
revisit = {"expanded_train:1079231", "expanded_train:11961"}
rows, assignments = [], {}
out = AUDIT / "AUTHOR_RESUME_20261101_V1.json"
inv.require(not out.exists(), "new immutable resume manifest required")
for role, assignment in source["assignments"].items():
    missing = [key for key in assignment["ids"] if key not in saved or key in revisit]
    directory = BASE / "agents" / role / "authored_postsignal_review_v1"
    tasks = {ROOT / name: (ROOT / name).read_text(encoding="utf-8") for name in assignment["tasks"]}
    text = ["# 2026-11-01 중단된 실제 본문 독립 판독 재개", "",
        "사용자 허가: 원문 판독 및 자기 지정 폴더의 새 txt/md만. 총괄의 CPU/코드/Git 권한은 상속하지 않는다.",
        "이 RESUME와 아래 정확 TASK.md/TASK_NNN, 지정 original/candidate 전문 및 명시한 자기 기존 검토/출력만 읽는다. 코드/시험/계산/통계/해시/모델/GPU/Git/웹/설치/다른원문·다른세션 전용경로 접근 금지. 정확쌍 diff -u 읽기는 허용한다.",
        "기존 TASK.md의 정제 원칙을 읽고 따른다. 모든 지정쌍을 EOF까지 읽으며 잘린 출력은 구간을 나눠 끝까지 확인한다. 기존 판정·파일을 덮거나 지우지 않는다. 이미 실제 본문이 있으면 읽고 검토하되 새 판정이 필요하면 더 높은 vN 파일을 작성한다.",
        "반복·코드·튜플·Unicode·자료명·값 있는 목록을 탐지 신호만으로 삭제하지 않는다. 같은 문단에 있는 온전한 문장은 결손 구절과 함께 버리지 않는다. 학술어/이름/숫자/날짜/조건/부정/인용/불확실성은 보존한다. 없는 사실·표제·공식·정답·배열대응을 생성하지 않는다.",
        "일반 임상/약물 용량/기계 설치·정비 안내의 source-only 형식 정제는 허용된다. 주제나 용량 숫자 자체만으로 전체를 금지하지 않는다. 원문의 조건·수치·경고를 그대로 보존하고 새 의료/수리 조언이나 안전성 검증 주장은 하지 않는다. 실제 병원체 조작·무기 제조 등 고위험 실행 절차가 새로 나타나면 세부 재전사 없이 해당 범위와 일반 사유만 NEEDS_ROOT로 보고한다.",
        "역할은 실제 TXT 작성이다. 레시피/코드 대신 새 expanded_train_ID_vN.txt 및 필요한 _vN_hold.md로 회수한다. 자기 새 TXT로 exact base를 복사하고 좁은 텍스트 패치를 적용하는 것은 허용한다. 검수메모는 md에만 둔다.",
        "검토는 원래 TASK_NNN에 맞는 review_NNN_vN.md로 새 저장한다. 표는 ID | 판정 | 실제 판독 범위 | 정확 출력 | 구체 근거. 판정 ACCEPT_CANDIDATE / KEEP_SOURCE / REVISE_TEXT / EXCLUDE / NEEDS_ROOT. 수정 본문 하나의 정확 TXT 파일명을 적는다. 읽지 않은 것을 EXCLUDE/전문판독으로 표시하지 않는다.",
        "모든 아래 미저장 판독을 마친 뒤 자기 exclusion_second_review_v1/TASK.md와 그 정확 TASK_NNN의 배정을 전부 수행한다. 제외 검토의 지시와 exact inputs만 사용한다. 그 작업에서도 기존 파일은 보존하고 새 TXT/md만 쓴다.",
        "root 채택·캐시 생성·외부 사실 검증·학습 승인은 아니다. 중간에 사용량/도구 오류가 생기면 실제 저장 범위와 남은 ID를 보고한다. 작업은 파일별 실제 저장으로 계속한다.", "",
        "상위 정제 계약: `" + str(ROOT / directory / "TASK.md") + "`", "",
        "후속 제외 검토: `" + str(ROOT / BASE / "agents" / role / "exclusion_second_review_v1/TASK.md") + "`", ""]
    for key in missing:
        row = sources[key]
        task = next(path for path, payload in tasks.items() if "## " + key + chr(10) in payload)
        text += ["## " + key, "", "원래 묶음: `" + str(task) + "`", ""]
        for label in ["original", "candidate"]:
            pin = row[label]
            inv.require(inv.file_sha(ROOT / pin["path"]) == pin["sha256"], "resume source/body changed")
            text += [label + ": `" + str(ROOT / pin["path"]) + "`", label + " SHA: `" + pin["sha256"] + "`", ""]
        if key in revisit:
            text += ["이전 NEEDS_ROOT/부분 판독은 기록으로 보존한다. 임상·유지보수 source-only 정제의 위 명시 범위로 실제 전문 판독을 다시 수행한다.", ""]
        rows.append(dict(id=key, role=role, source=row["original"], candidate=row["candidate"],
                         original_task=str(task.relative_to(ROOT)), reason="REVISIT_SOURCE_ONLY_TRANSFORMATION" if key in revisit else "NO_SAVED_REVIEW_ROW"))
    # Cold-start readers may inspect their own historical notes and already
    # written but unreviewed material. Explicit names prevent guessed paths.
    text += ["## 허용한 자기 기존 검토·출력", ""]
    own_files = sorted(path for path in directory.iterdir() if path.is_file()
                       and path.suffix in {".txt", ".md"} and not path.name.startswith("TASK"))
    for path in own_files:
        text.append("- `" + str(ROOT / path) + "`")
    path = directory / "RESUME_20261101_V1.md"
    with path.open("x", encoding="utf-8") as stream:
        stream.write(chr(10).join(text) + chr(10))
    assignments[role] = dict(task=str(path), sha256=inv.file_sha(path), ids=missing,
                            counts=dict(pending_pairs=len(missing)),
                            own_files=[dict(path=str(p), sha256=inv.file_sha(p)) for p in own_files])
inv.write_json(out, dict(status="TEXT_ONLY_AUTHOR_RESUME_NOT_ADMISSION", assignments=assignments, rows=rows,
    counts=dict(Counter(row["role"] for row in rows)), pins={str(p): inv.file_sha(p) for p in [source_path, snapshot_path, Path(__file__)]},
    goal_complete=False, training_authorized=False))
print(json.dumps(dict(rows=len(rows), counts=dict(Counter(row["role"] for row in rows))), ensure_ascii=False))
