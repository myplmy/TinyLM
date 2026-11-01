"""Pin every changed terminal v10 purpose case for exact text-only review."""
from collections import Counter
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v10 as policy

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
out = BASE / "policy_v10_literal_counter_v1"
inv.require(not out.exists(), "new immutable review namespace required")
old_path = AUDIT / "policy_v9_purpose_probe_v1.json"
new_path = AUDIT / "policy_v10_purpose_probe_v1.json"
old = {row["id"]: row for row in inv.cache.read(old_path)["rows"]}
selected = [row for row in inv.cache.read(new_path)["rows"] if row["decision"] in {"KEEP", "EDIT"}
            and (row["decision"] != old[row["id"]]["decision"]
                 or row["clean_text_sha256"] != old[row["id"]]["clean_text_sha256"])]
(out / "packets").mkdir(parents=True)
records = []
for row in selected:
    source = ROOT / row["source"]["path"]
    inv.require(inv.file_sha(source) == row["source"]["sha256"], "review original differs")
    value = policy.propose(dict(id=row["id"], text=source.read_bytes().decode("utf-8"), complete_eos=True, valid_utf8=True))
    candidate = value.get("candidate", value["text"])
    inv.require(value["decision"] == row["decision"] and inv.sha(candidate) == row["clean_text_sha256"], "v10 draft replay differs")
    path = out / "packets" / (row["id"].replace(":", "_") + "_candidate.txt")
    with path.open("xb") as stream:
        stream.write(candidate.encode("utf-8"))
    records.append(dict(id=row["id"], original=row["source"], candidate=dict(path=str(path.relative_to(ROOT)), sha256=inv.file_sha(path)),
                        characters=len(source.read_bytes().decode("utf-8")), decision=value["decision"], changes=value["changes"]))
roles = ["context_controls", "historical_review", "context_hangul"]
assignments = {role: [] for role in roles}
loads = Counter({role: 0 for role in roles})
for row in sorted(records, key=lambda item: (-item["characters"], item["id"])):
    role = min(roles, key=lambda key: (loads[key], roles.index(key)))
    assignments[role].append(row)
    loads[role] += row["characters"]
for role, assigned in assignments.items():
    directory = BASE / "agents" / role / "policy_v10_literal_counter_v1"
    directory.mkdir()
    lines = ["# v10 실제 오탐 수정 후보의 독립 전량 대조", "",
             "읽기 허용은 이 TASK와 아래 정확 original/candidate 전량 및 자기 새 출력뿐이다. 원문/기존 산출물은 덮거나 삭제하지 않는다.",
             "텍스트 판독과 새 txt/md만 허용한다. 코드/시험/해시/통계/모델/GPU/Git/웹은 금지한다. 정확 두 입력의 diff -u는 읽기 전용 대조로 허용한다.",
             "빈 필드/외형만 보지 말고 온전한 역사·관계·논문·작품·교통 목록, 수량/조건/인용/불확실성/코드/Unicode가 실제로 보존됐는지 확인한다.",
             "말줄임표·채워진 화살표는 값 소실과 구분한다. 빈 제목뿐인 서지라도 남은 실제 저널/권호/쪽수/저자를 추정 연결하거나 지우지 않는다.",
             "판정은 ACCEPT_CANDIDATE / REVISE_TEXT / EXCLUDE / NEEDS_ROOT이며 행마다 실제 판독 범위를 쓴다. 수정이면 실제 expanded_train_ID_v2.txt와 hold.md를 저장한다.",
             "review.md 표: ID | 판정 | 실제 판독 범위 | 출력 | 근거. 검수 문구는 md에만 둔다. 이는 root 채택/외부 사실 검증/실행 성공이 아니다.", ""]
    for row in sorted(assigned, key=lambda item: item["id"]):
        lines += ["## " + row["id"], ""]
        for label in ["original", "candidate"]:
            lines += [label + ": `" + str(ROOT / row[label]["path"]) + "`", label + " SHA: `" + row[label]["sha256"] + "`"]
        lines.append("")
    with (directory / "TASK.md").open("x", encoding="utf-8") as stream:
        stream.write(chr(10).join(lines) + chr(10))
inv.write_json(out / "manifest.json", dict(status="TEXT_COUNTER_REVIEW_NOT_ADMISSION", rows=records,
    assignments={role: [row["id"] for row in assigned] for role, assigned in assignments.items()},
    pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in [old_path, new_path, Path(__file__), ROOT / "scripts/p106b_hold_resolution_policy_v10.py"]}))
print(json.dumps(dict(cases=len(records), assignments={role: len(assigned) for role, assigned in assignments.items()}, characters=dict(loads))))
