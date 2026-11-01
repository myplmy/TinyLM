"""Export newly selected v19 census shapes as exact text-only source pairs."""
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
OUT = BASE / "remaining_candidate_context_v19_v1"
inv.require(not OUT.exists(), "new text-only assignment namespace required")
inputs = [BASE / "remaining_candidate_profile_v19_v1/review_packets/manifest.json",
          AUDIT / "authored_body_integrity_v2.json", AUDIT / "supplemental_candidates_snapshot_v26.json",
          BASE / "scope.json", AUDIT / "prepare_remaining_context_v14_v1.py", Path(__file__)]
profile, core, supplemental = [inv.cache.read(path) for path in inputs[:3]]
covered = {row["id"] for row in core["records"] + supplemental["records"]}
selected = [row for row in profile["rows"] if row["id"] not in covered]
restricted = {"expanded_train:14760", "expanded_train:756966", "expanded_train:15695",
              "expanded_train:1216576", "expanded_train:1250821", "expanded_train:20624",
              "expanded_train:6030"}
inv.require(not (restricted & {row["id"] for row in selected}), "restricted parent cannot enter general packets")
tree = ast.parse(inputs[4].read_text(encoding="utf-8"))
contracts = [ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
             and any(isinstance(target, ast.Name) and target.id == "contract" for target in node.targets)]
inv.require(len(contracts) == 1, "reuse exact prior text-only contract")
contract = contracts[0].replace("expanded_train_ID_v2.txt", "ID의 콜론을 밑줄로 바꾼 이름_v2.txt")
pins = {str(path.relative_to(ROOT)): inv.file_sha(path) for path in inputs}
roles = ["context_controls", "context_hangul", "context_latin", "historical_review", "legacy_review"]
rows, loads = [], Counter()
assignments = {role: [] for role in roles}
started = time.monotonic()
directory = OUT / "originals"
directory.mkdir(parents=True)
with ExitStack() as stack:
    reader = inv.OriginalReader(inv.cache.read(BASE / "scope.json"), stack)
    for source_row in selected:
        candidate = source_row["candidate"]
        inv.require(inv.file_sha(ROOT / candidate["path"]) == candidate["sha256"], "candidate census packet changed")
        raw, complete, valid = reader.text(source_row)
        inv.require(complete and valid, "source pair lacks complete text")
        payload = raw.encode("utf-8")
        inv.require(payload.strip() and len(payload) < 20_000_000, "source pair needs ordered splitting")
        path = directory / (source_row["id"].replace(":", "_") + "_original.txt")
        with path.open("xb") as stream:
            stream.write(payload)
        if source_row["language_bucket"] == "NO_HANGUL":
            eligible = ["context_latin", "historical_review", "legacy_review"]
        elif any("FORMAL" in value or "CODE" in value or "DECLARATION" in value for value in source_row["reasons"]):
            eligible = ["context_controls", "legacy_review"]
        else:
            eligible = roles
        role = min(eligible, key=lambda value: (loads[value], roles.index(value)))
        loads[role] += len(raw)
        rows.append(dict(source_row, role=role, original=dict(path=str(path.relative_to(ROOT)),
                         sha256=source_row["original_text_sha256"]), original_characters=len(raw), root_approved=False))
        assignments[role].append(source_row["id"])

for role in roles:
    destination = BASE / "agents" / role / OUT.name
    inv.require(not destination.exists(), "new role output directory required")
    destination.mkdir()
    owned = [row for row in rows if row["role"] == role]
    start = f"""# 현재 작업: {OUT.name} / {role}

이 폴더의 정확 TASK만 새로 허용한다. 이전 435/59/70/194/36과 개별 중재는 완료되어 새 읽기·쓰기 범위를 닫는다.
원문·후보의 정확 경로는 TASK에 있다. 새 출력의 유일한 폴더는 `{destination}`다.
지정 원문/후보와 이 START/TASK를 읽고 자기 새 TXT/MD만 저장한다. 코드·시험·계산·해시·통계·웹·모델·GPU·Git·설치·다른 폴더·원형 덮기·삭제는 금지한다.
TXT에는 학습시킬 실제 본문/자료값만 저장한다. 버전/원문행번호/검수설명/hold·sidecar 안내/보존했습니다 같은 메모는 MD에만 기록한다.
특정 탐지 신호만 면제하지 말고 전문 끝까지 광고·검색/상품UI·미리보기·빈 수식/필드·깨진 목록을 함께 판독한다. 유효한 코드/인용/참고자료/조건/날짜/수치/용어는 보존한다.
ID가 validation:N이면 validation_N_v2.txt, expanded_train:N이면 expanded_train_N_v2.txt를 사용한다.
전체 TASK를 마친 뒤 정확 산출물/미판독/좁은 질문만 보고하고 final로 종료한다. 옛 TASK로 복귀하지 않는다.
"""
    names = []
    for offset in range(0, len(owned), 4):
        name = "TASK_" + str(offset // 4 + 1).zfill(3) + ".md"
        names.append(name)
        parts = [start, contract, "후보는 v19 diagnostic_candidate이며 원문이 아니다. 자동 후보의 오삭제도 원문과 대조해 복구한다."]
        for row in owned[offset:offset + 4]:
            parts += ["## " + row["id"], "original: `" + str(ROOT / row["original"]["path"]) + "`",
                      "original SHA: `" + row["original"]["sha256"] + "`",
                      "candidate: `" + str(ROOT / row["candidate"]["path"]) + "`",
                      "candidate SHA: `" + row["candidate"]["sha256"] + "`",
                      "미확정 사유: " + ", ".join(row["reasons"]), "문맥 유형: " + ", ".join(row["profile_kinds"])]
        with (destination / name).open("x", encoding="utf-8") as stream:
            stream.write((chr(10) * 2).join(parts) + chr(10))
    with (destination / "START_HERE.md").open("x", encoding="utf-8") as stream:
        stream.write(start + chr(10) + "현재 TASK: " + ", ".join(names) + chr(10))

for path, expected in pins.items():
    inv.require(inv.file_sha(ROOT / path) == expected, "assignment input changed")
result = dict(status="ALL_NEW_CANDIDATE_SHAPE_PAIRS_ASSIGNED_NOT_ADMISSION", rows=rows, assignments=assignments,
              source_characters_by_role=dict(loads), profile_packets=len(profile["rows"]),
              reused_previously_assigned_ids=sorted({row["id"] for row in profile["rows"]} & covered),
              input_pins=pins, root_adopted=0, seconds=time.monotonic() - started,
              goal_complete=False, training_authorized=False)
inv.require(len(rows) + len(result["reused_previously_assigned_ids"]) == len(profile["rows"]), "packet coverage lost")
inv.write_json(OUT / "manifest.json", result)
print(json.dumps(dict(rows=len(rows), assignments={key: len(value) for key, value in assignments.items()},
                      reused=len(result["reused_previously_assigned_ids"]), source_characters_by_role=dict(loads),
                      seconds=result["seconds"]), ensure_ascii=False))
