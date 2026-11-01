"""Independently review every v14 automatically quarantined terminal source."""
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
import ast
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
OUT = BASE / "automatic_partial_counter_v1"
inv.require(not OUT.exists(), "automatic partial counter requires a new namespace")
frozen = BASE / "draft_proposals_v14"
report = inv.cache.read(frozen / "complete.json")
quarantine = "QUARANTINE_ACTUAL_VALUE_HOLE_AND_PREMISE_DEPENDENTS"
selected = [row for row in inv.cache.rows(frozen / "unique", report["unique_manifest"])
            if row["decision"] in {"KEEP", "EDIT"}
            and any(change["reason"] == quarantine for change in row["changes"])]
inv.require(len(selected) == 194 and sum(row["occurrences"] for row in selected) == 331,
            "frozen automatic partial selection differs from the actual full count")
restricted = {"expanded_train:14760", "expanded_train:756966", "expanded_train:1250821",
              "expanded_train:15695", "expanded_train:1216576", "expanded_train:20624"}
inv.require(not (restricted & {row["id"] for row in selected}), "restricted parent cannot enter general counter")
contract_source = AUDIT / "prepare_remaining_context_v14_v1.py"
tree = ast.parse(contract_source.read_text(encoding="utf-8"))
node = next(node for node in tree.body if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "contract" for target in node.targets))
contract = ast.literal_eval(node.value)
contract += (chr(10) * 2) + "이 묶음은 과거 자동 부분 삭제를 사용한 종결 초안 전부의 독립 대조다. 실제 식/값이 없다는 이유로 완결 정의·역사·조건·정성 설명까지 함께 빠졌는지 특히 확인한다. 과거 KEEP/EDIT는 채택 근거가 아니다. 후보의 나머지 오류도 원문에서만 보완하며 이 묶음 완료를 전체 goal 완료로 삼지 않는다."
OUT.mkdir()
(OUT / "packets").mkdir()
started = time.monotonic()
rows = []
with ExitStack() as stack:
    reader = inv.OriginalReader(inv.cache.read(BASE / "scope.json"), stack)
    for row in selected:
        raw, complete, valid = reader.text(row)
        inv.require(complete and valid and inv.sha(raw) == row["original_text_sha256"], "original interval/hash differs")
        clean = row["text"]
        inv.require(inv.sha(clean) == row["clean_text_sha256"], "frozen partial candidate differs")
        pins = {}
        for label, value in [("original", raw), ("candidate", clean)]:
            path = OUT / "packets" / (row["id"].replace(":", "_") + "_" + label + ".txt")
            payload = value.encode("utf-8")
            inv.require(payload.strip() and len(payload) < 20_000_000, "partial packet needs ordered splitting")
            with path.open("xb") as stream:
                stream.write(payload)
            pins[label] = dict(path=str(path.relative_to(ROOT)), sha256=inv.file_sha(path))
        rows.append(dict(id=row["id"], **pins, original_characters=len(raw), language_bucket=row["language_bucket"],
                         original_text_sha256=row["original_text_sha256"], source_ids=row["source_ids"],
                         source_ids_sha256=row["source_ids_sha256"], source=row["source"], occurrences=row["occurrences"],
                         changes=row["changes"], previous_decision=row["decision"], root_approved=False))
roles = ["context_controls", "context_hangul", "context_latin", "historical_review", "legacy_review"]
assignments, loads = {role: [] for role in roles}, Counter()
for row in sorted(rows, key=lambda value: -value["original_characters"]):
    role = min(roles, key=lambda name: (loads[name], roles.index(name)))
    assignments[role].append(row["id"])
    loads[role] += row["original_characters"]
for role in roles:
    directory = BASE / "agents" / role / OUT.name
    inv.require(not directory.exists(), "new role output directory required")
    directory.mkdir()
    owned = [row for row in rows if row["id"] in assignments[role]]
    for offset in range(0, len(owned), 4):
        sections = [contract]
        for row in owned[offset:offset + 4]:
            sections.append("## " + row["id"])
            for label in ["original", "candidate"]:
                sections.append(label + ": `" + str(ROOT / row[label]["path"]) + "`")
                sections.append(label + " SHA: `" + row[label]["sha256"] + "`")
        with (directory / ("TASK_" + str(offset // 4 + 1).zfill(3) + ".md")).open("x", encoding="utf-8") as stream:
            stream.write((chr(10) * 2).join(sections) + chr(10))
paths = [frozen / "complete.json", BASE / "scope.json", contract_source, Path(__file__)]
result = dict(status="ALL_AUTOMATIC_PARTIAL_TERMINALS_INDEPENDENT_REVIEW_NOT_ADMISSION",
              rows=rows, assignments=assignments, source_characters_by_role=dict(loads),
              unique_sources=len(rows), occurrences=sum(row["occurrences"] for row in rows),
              input_pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in paths},
              root_adopted=0, seconds=time.monotonic() - started, goal_complete=False, training_authorized=False)
inv.write_json(OUT / "manifest.json", result)
print(json.dumps(dict(unique_sources=len(rows), occurrences=result["occurrences"],
                      assignments={role: len(ids) for role, ids in assignments.items()},
                      source_characters_by_role=dict(loads), seconds=result["seconds"]), ensure_ascii=False))
