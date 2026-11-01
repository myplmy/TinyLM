"""Assign the remaining single-risk purpose packets without claiming coverage."""
from collections import Counter
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v10 as policy

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
out = BASE / "remaining_structure_context_v1"
inv.require(not out.exists(), "new immutable namespace required")
(out / "packets").mkdir(parents=True)
source_path = AUDIT / "policy_v10_purpose_probe_v1.json"
excluded = {row["original_text_sha256"] for row in inv.cache.read(AUDIT / "authored_candidates_snapshot_v5.json")["rows"]}
excluded |= {row["original_text_sha256"] for row in inv.cache.read(BASE / "legacy_span_review_v2/manifest.json")["rows"]}
excluded |= {row["original"]["sha256"] for row in inv.cache.read(BASE / "policy_counter_review_v1/manifest.json")["rows"]}
excluded |= {row["original"]["sha256"] for row in inv.cache.read(BASE / "policy_v10_literal_counter_v1/manifest.json")["rows"]}
eligible = {"APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT", "MAIN_BODY_REPETITION_REQUIRES_CONTEXT"}
records = []
for row in inv.cache.read(source_path)["rows"]:
    if row["decision"] != "PENDING" or not set(row["reasons"]) <= eligible or row["source"]["sha256"] in excluded:
        continue
    original = ROOT / row["source"]["path"]
    inv.require(inv.file_sha(original) == row["source"]["sha256"], "purpose source differs")
    text = original.read_bytes().decode("utf-8")
    value = policy.propose(dict(id=row["id"], text=text, complete_eos=True, valid_utf8=True))
    candidate = value.get("candidate", value["text"])
    inv.require(value["decision"] == "PENDING" and inv.sha(candidate) == row["clean_text_sha256"], "v10 pending replay differs")
    path = out / "packets" / (row["id"].replace(":", "_") + "_candidate.txt")
    with path.open("xb") as stream:
        stream.write(candidate.encode("utf-8"))
    records.append(dict(id=row["id"], original=row["source"], candidate=dict(path=str(path.relative_to(ROOT)), sha256=inv.file_sha(path)),
                        characters=len(text), reasons=row["reasons"]))
roles = ["historical_review", "context_controls"]
assignments = {role: [] for role in roles}
loads = Counter({role: 0 for role in roles})
for row in sorted(records, key=lambda item: (-item["characters"], item["id"])):
    role = min(roles, key=lambda key: (loads[key], roles.index(key)))
    assignments[role].append(row)
    loads[role] += row["characters"]
for role, assigned in assignments.items():
    directory = BASE / "agents" / role / "remaining_structure_context_v1"
    directory.mkdir()
    lines = ["# 남은 반복·부록 경계의 실제 문맥 복구", "",
             "이 자료는 기존 목적 패킷 중 다른 판독에 이미 배정되지 않은 해당 유형 전부다. 코퍼스 전량 검토/완료 근거는 아니다.",
             "먼저 자기 기존 실제 수정·기계 피드백을 마친 뒤 아래 배정을 전부 읽고 실제 산출물까지 작성한다. 별도 허가를 기다리지 않는다.",
             "읽기는 이 TASK, 아래 정확 original/candidate 전량, 자기 새 출력만 허용한다. 원형/기존파일 덮기·삭제와 다른 경로는 금지한다.",
             "텍스트 판독/새 txt/md만 허용한다. 코드/시험/계산/해시/통계/모델/GPU/Git/웹은 금지한다. 정확 두 입력의 diff -u는 읽기 도구로 허용한다.",
             "정상 반복은 삭제하지 않는다. 도입과 절의 반복 설명·서로 다른 표 행의 같은 값·연도/대상별 항목·가사 후렴·직접인용은 실제 문맥을 유지한다.",
             "반복 UI/실제 동일한 인접 추출 문단은 그 실물 근거로만 정리한다. 일괄 줄 중복제거, 다른 시점/대상/부정/조건 삭제는 금지한다.",
             "빈 각주/외부링크 표제와 실제 자료명/서지/정상 분류를 구분한다. URL이 없어도 실제 자료명은 보존하며 분류/외부참조 귀속을 추정하지 않는다.",
             "값/수식/이름/날짜/표 열/출처를 새로 만들지 않는다. 소실부를 발견하면 직접 의존부만 hold로 분리하고 독립 설명/정상코드/Unicode/조건·수량은 보존한다.",
             "review.md 표: ID | 판정 | 실제 판독 범위 | 출력 | 구체 근거. 판정은 KEEP_SOURCE / ADOPT_CANDIDATE / EDIT_TEXT / EDIT_RECIPE / EXCLUDE / NEEDS_ROOT.",
             "EDIT_TEXT는 실제 expanded_train_ID_v2.txt와 hold.md를 작성한다. EDIT_RECIPE는 expanded_train_ID_v1.edits.md에 아래 strict 형식을 따른다.",
             "모든 ORIGINAL은 같은 base의 실제 원문에서 유일하고 서로 겹치지 않아야 한다. 단계적 치환 뒤 텍스트를 다음 ORIGINAL로 쓰지 않는다.",
             "# P106B_LITERAL_TEXT_EDITS_V1", "source_id: 정확ID", "base: original 또는 candidate", "base_sha256: 아래 해당 SHA", "reason: 구체 사유",
             "## Change 1", "ORIGINAL", "````````text", "정확한 실제 원문 anchor", "````````", "REPLACEMENT", "````````text", "실제 보존할 대체문", "````````", "",
             "판정만으로 끝내지 말고 필요한 실제 파일을 저장한다. 검수 메모는 md에만 둔다. root 최종채택/외부진위확인/코드실행 성공이 아니다.", ""]
    for row in sorted(assigned, key=lambda item: item["id"]):
        lines += ["## " + row["id"], "", "현재 추가처리 사유: " + ", ".join(row["reasons"])]
        for label in ["original", "candidate"]:
            lines += [label + ": `" + str(ROOT / row[label]["path"]) + "`", label + " SHA: `" + row[label]["sha256"] + "`"]
        lines.append("")
    with (directory / "TASK.md").open("x", encoding="utf-8") as stream:
        stream.write(chr(10).join(lines) + chr(10))
inv.write_json(out / "manifest.json", dict(status="TEXT_CONTEXT_RECOVERY_REQUIRED_NOT_ADMISSION", rows=records,
    assignments={role: [row["id"] for row in assigned] for role, assigned in assignments.items()},
    producer_sha256=inv.file_sha(Path(__file__)), source_sha256=inv.file_sha(source_path), excluded_sources=len(excluded)))
print(json.dumps(dict(cases=len(records), assignments={role: len(assigned) for role, assigned in assignments.items()}, characters=dict(loads))))
