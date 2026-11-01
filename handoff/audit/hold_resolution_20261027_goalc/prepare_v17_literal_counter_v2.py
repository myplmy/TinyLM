"""Pin every newly terminal purpose source for independent text-only review."""
from collections import Counter
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v17 as policy

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
out = BASE / "policy_v17_literal_counter_v2"
inv.require(not out.exists(), "new immutable counter namespace required")
probe = AUDIT / "policy_v17_purpose_probe_v2.json"
earlier_path = BASE / "policy_v17_literal_counter_v1/manifest.json"
earlier = {row["id"]: row for row in inv.cache.read(earlier_path)["rows"]}
records = []
prior_authors = {}
for value in inv.cache.read(AUDIT / "supplemental_candidates_snapshot_v17.json")["records"]:
    prior_authors.setdefault(value["id"], set()).add(value["role"])
for value in inv.cache.read(BASE / "remaining_candidate_context_v16_v1/manifest.json")["rows"]:
    prior_authors.setdefault(value["id"], set()).add(value["role"])
for row in inv.cache.read(probe)["rows"]:
    if row["decision"] not in {"KEEP", "EDIT"}:
        continue
    pin = row["source"]
    source = ROOT / pin["path"]
    inv.require(inv.file_sha(source) == pin["sha256"], "counter original changed")
    raw = source.read_bytes().decode("utf-8")
    old = policy.previous.propose(dict(id=row["id"], text=raw, complete_eos=True, valid_utf8=True))
    old_clean = old.get("candidate", old["text"])
    if old["decision"] in {"KEEP", "EDIT"} and inv.sha(old_clean) == row["clean_text_sha256"]:
        continue
    if row["id"] in earlier and earlier[row["id"]]["candidate"]["sha256"] == row["clean_text_sha256"]:
        continue
    current = policy.propose(dict(id=row["id"], text=raw, complete_eos=True, valid_utf8=True))
    clean = current.get("candidate", current["text"])
    inv.require(current["decision"] == row["decision"] and inv.sha(clean) == row["clean_text_sha256"],
                "new counter proposal differs from probe")
    path = out / "packets" / (row["id"].replace(":", "_") + "_candidate.txt")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(clean.encode("utf-8"))
    records.append(dict(id=row["id"], original=pin,
                        candidate=dict(path=str(path.relative_to(ROOT)), sha256=inv.file_sha(path)),
                        characters=len(raw), decision=current["decision"], changes=current["changes"],
                        previous_reasons=old["reasons"], root_approved=False))
roles = ["context_latin", "historical_review", "context_hangul", "context_controls", "legacy_review"]
assignments, loads = {role: [] for role in roles}, Counter({role: 0 for role in roles})
for row in sorted(records, key=lambda value: (-value["characters"], value["id"])):
    available = [role for role in roles if role not in prior_authors.get(row["id"], set())] or roles
    role = min(available, key=lambda key: (loads[key], roles.index(key)))
    assignments[role].append(row)
    loads[role] += row["characters"]
for role, assigned in assignments.items():
    directory = BASE / "agents" / role / "policy_v17_literal_counter_v2"
    directory.mkdir(parents=True)
    lines = ["# v17 별도 말미·명사 서술·단층 정보상자의 독립 대조", "",
             "정확 새 출력 폴더: `" + str(directory) + "`. 이 TASK의 지정쌍과 자기 새 TXT/MD만 허용한다. 다른 완료 TASK로 돌아가지 않는다.",
             "허용 입력은 이 TASK와 아래 정확 original/candidate 전문 및 자기 새 출력뿐이다. 원문·기존 산출물은 덮거나 삭제하지 않는다.",
             "텍스트 판독과 새 txt/md만 허용한다. 코드/시험/해시/통계/모델/GPU/Git/웹은 금지한다. 정확 지정쌍 diff -u 읽기는 허용한다.",
             "같이보기·참조·서지에 실제 채워진 항목은 표제와 관계까지 유지됐는지 확인한다. 마지막 별도 문단의 명시 연도/상태와 분류는 전부 그대로여야 하며 실제 값이 있는 표제를 빈 표제로 오삭제하지 않는다. 코드·역사 전사·인용·숫자·조건·Unicode를 보존한다. 실제남은 결손은 없는 값을 채우지 않고 별도 hold와 새 TXT로 회수한다.",
             "숫자에 /가 있는 날짜는 원문대로 보존하고 수식·함수 호출과 구분한다. 실제 자료명·참고문헌을 URL 부재만으로 지우지 않는다.",
             "판정은 ACCEPT_CANDIDATE / REVISE_TEXT / EXCLUDE / NEEDS_ROOT. 행마다 실제 판독 범위를 쓰고 수정은 실제 ID의 콜론을 밑줄로 바꾼 이름_v2.txt와 필요한 hold.md를 저장한다.",
             "review.md 표: ID | 판정 | 실제 판독 범위 | 출력 | 구체 근거. 기존 파일이 있으면 더 높은 새 vN만 쓴다. 검수 문구는 md에만 둔다.",
             "이는 root 채택/외부 사실 검증/실행 성공이 아니다. 현재 재개 묶음과 제외 검토는 보존하고, 진행 중인 묶음 한 개를 마친 뒤 이 작은 배정을 우선 판독한 후 이전 미완을 계속한다.", ""]
    for row in sorted(assigned, key=lambda value: value["id"]):
        lines += ["## " + row["id"], ""]
        for label in ["original", "candidate"]:
            lines += [label + ": `" + str(ROOT / row[label]["path"]) + "`",
                      label + " SHA: `" + row[label]["sha256"] + "`", ""]
    with (directory / "TASK.md").open("x", encoding="utf-8") as stream:
        stream.write(chr(10).join(lines) + chr(10))
inv.write_json(out / "manifest.json", dict(status="FULL_CHANGED_PURPOSE_COUNTER_REVIEW_NOT_ADMISSION", rows=records,
               assignments={role: [row["id"] for row in assigned] for role, assigned in assignments.items()},
               pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in [probe, earlier_path, Path(__file__),
                     BASE / "draft_proposals_v16/complete.json", ROOT / "scripts/p106b_hold_resolution_policy_v17.py"]}))
print(json.dumps(dict(cases=len(records), assignments={role: len(rows) for role, rows in assignments.items()},
                      characters=dict(loads)), ensure_ascii=False))

