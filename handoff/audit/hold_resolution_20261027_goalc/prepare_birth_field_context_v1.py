"""Prepare all753 raw-proven terminal candidates for independent context reading."""
from pathlib import Path
import difflib
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_review_safeguards_v3 as safeguards

BASE = inv.BASE
GROUP = "birth_field_native_counter_v1"
OUT = BASE / GROUP
inv.require(not OUT.exists(), "new immutable context namespace required")
source_dir = BASE / "birth_field_native_proof_v1"
report_path = source_dir / "complete.json"
report = inv.cache.read(report_path)
inv.verify(source_dir / "rows", report["rows"])
sources = [row for row in inv.cache.rows(source_dir / "rows", report["rows"]) if row["decision"] == "EDIT"]
inv.require(len(sources) == 753, "all753 terminal role-proven candidates required")
roles = ["context_controls", "context_latin", "context_hangul", "historical_review", "legacy_review"]
assigned, loads = {role: [] for role in roles}, {role: 0 for role in roles}
for row in sorted(sources, key=lambda row: (-len(row["proposed_body"]), row["id"])):
    role = min(roles, key=lambda role: (loads[role], roles.index(role)))
    assigned[role].append(row["id"])
    loads[role] += len(row["proposed_body"])
source_by_id = {row["id"]: row for row in sources}
(OUT / "inputs").mkdir(parents=True)
(OUT / "reading_packets").mkdir()
rows, packets = [], []
for role in roles:
    assigned[role].sort()
    directory = BASE / "agents" / role / GROUP
    directory.mkdir(parents=True, exist_ok=False)
    instructions = [
        "# 生年" if False else "# 생년 필드 후보의 전량 독립 문맥 판독", "",
        "정확 허용 입력은 자기 TASK와 그 original/candidate/diff, 명시된 읽기 패킷/조각 및 START/READING_VIEWS다.",
        "옛 작성자 리뷰·정책·증명 JSON·다른 역할 출력은 읽지 않는다.",
        "허용 쓰기는 이 폴더의 새 txt/md뿐이며 기존 파일을 덮거나 삭제하지 않는다.",
        "코드/시험/통계/해시/Python/모델/GPU/Git/웹/설치/보호자료/타 세션/공유원장은 금지한다.",
        "narrow nl/sed/tail/diff와 새 TXT/MD 편집만 허용한다. 직접 통계나 해시를 계산하지 않는다.",
        "모든 TASK를 순서대로 진행하고 original/candidate/전체diff/EOF를 실제로 읽는다. 미판독·출력잘림은 완료가 아니다.",
        "읽기 패킷은 여러 원문을 명시 BEGIN/END 경계로 담은 검수용 파일이다. 경계·표지는 원문이나 학습 본문의 일부가 아니다.",
        "각 TASK의 패킷 순서 조각을 모두 읽으면 원문/후보/전체diff를 모두 볼 수 있다. 의심스러우면 지정 원본 TXT도 읽는다.",
        "두 상충 생년 중 어느 것이 맞는지 선택하지 않는다. 실제 월일·사망일·경력 수치·부정·불확실성·주체의 보존과 남은 본문의 독립성을 본다.",
        "원문 연도나 논란에 의존한 문장이 남았거나 다른 정보가 잘못 지워졌다면 수용하지 않는다. 누락 사실을 생성하지 않는다.",
        "후보 수용은 ACCEPT_CANDIDATE 및 지정 candidate TXT 정확 한 경로를 출력한다.",
        "수정 필요 시 새 전체 TXT와 별도 hold MD를 작성하고 REVISE_TEXT로 정확 TXT 한 경로를 출력한다.",
        "두 보류 연도와 이유는 별도 hold_NNN.md에 ID별로 원형 보존할 수 있다. 본문에 HOLD/검수 메모를 넣지 않는다.",
        "TASK_NNN마다 review_NNN.md를 저장한다. ID / 판정 / 실제 판독 범위 / 출력 / 구체 근거 표를 쓰고 배정된 각 ID를 모두 기록한다.",
        "모호하면 NEEDS_ROOT와 좁은 질문을 남기고 다음 지정 ID를 계속한다. 전체 캐시·품질 PASS는 선언하지 않는다.",
        "중단 복구가 필요하면 자기 PROGRESS.md 새 버전에 마지막 완료 TASK와 다음 TASK를 기록한다. 임의 몇 건을 작업량 한도로 삼지 않는다.",
    ]
    with (directory / "START_HERE.md").open("x", encoding="utf-8") as stream:
        stream.write(chr(10).join(instructions) + chr(10))
    for start in range(0, len(assigned[role]), 10):
        batch = assigned[role][start:start + 10]
        number = start // 10 + 1
        task_lines = ["# TASK_" + str(number).zfill(3), "START_HEREとREADING_VIEWS" if False else "START_HERE와 READING_VIEWS를 따른다."]
        packet_parts = []
        for ident in batch:
            row = source_by_id[ident]
            original = row["native_proof"]["candidate"]
            for change in row["native_proof"]["changes"]:
                lo, hi = change["prepared_candidate_characters"]
                inv.require(hi - lo == len(change["original"]), "native coordinate length differs")
                original = original[:lo] + change["original"] + original[lo:]
            inv.require(inv.sha(original) == row["original_text_sha256"], "native original reconstruction differs")
            candidate = row["proposed_body"]
            inv.require(inv.sha(candidate) == row["clean_text_sha256"], "verified candidate changed")
            values = {}
            for kind, text in [("original", original), ("candidate", candidate)]:
                path = OUT / "inputs" / (ident.replace(":", "_") + "_" + kind + ".txt")
                payload = text.encode("utf-8")
                inv.require(0 < len(payload) < 20_000_000, "source pair needs splitting")
                with path.open("xb") as stream:
                    stream.write(payload)
                values[kind] = dict(path=str(path.relative_to(ROOT)), sha256=inv.file_sha(path))
            records = {key: row[key] for key in ["id", "source", "split", "source_ids", "source_ids_sha256", "original_text_sha256", "input_ids", "occurrences", "language_bucket"]}
            rows.append(dict(records, **values, role=role, task=number, complete_eos=True, valid_utf8=True,
                candidate_decision="EDIT", candidate_reasons=["TWO_DISPUTED_BIRTH_FIELDS_QUARANTINED_REQUIRES_INDEPENDENT_CONTEXT"], root_approved=False))
            task_lines += ["## " + ident, "original: " + str(ROOT / values["original"]["path"]),
                           "candidate: " + str(ROOT / values["candidate"]["path"])]
            delta = "".join(difflib.unified_diff(original.splitlines(keepends=True), candidate.splitlines(keepends=True),
                fromfile=values["original"]["path"], tofile=values["candidate"]["path"]))
            for kind, text in [("ORIGINAL", original), ("CANDIDATE", candidate), ("FULL DIFF", delta)]:
                packet_parts += ["# BEGIN " + kind + " " + ident, text, "# END " + kind + " " + ident, ""]
        packet = chr(10).join(packet_parts)
        packet_path = OUT / "reading_packets" / (role + "_TASK_" + str(number).zfill(3) + ".md")
        with packet_path.open("x", encoding="utf-8") as stream:
            stream.write(packet)
        inv.require(packet_path.stat().st_size < 20_000_000, "reading packet needs artifact sharding")
        views = []
        for lo in range(0, len(packet), 6000):
            path = packet_path.with_name(packet_path.stem + "_part_" + str(lo // 6000 + 1).zfill(4) + ".txt")
            with path.open("x", encoding="utf-8") as stream:
                stream.write(packet[lo:lo + 6000])
            views.append(dict(path=str(path.relative_to(ROOT)), sha256=inv.file_sha(path), characters=[lo, min(lo + 6000, len(packet))]))
        inv.require("".join((ROOT / item["path"]).read_text(encoding="utf-8") for item in views) == packet, "framed packet views differ")
        task_lines += ["## 전체 읽기 패킷", str(packet_path), "모든 순서 조각과 실제 EOF를 확인한다."]
        task_lines.extend(str(ROOT / item["path"]) + " chars " + str(item["characters"]) for item in views)
        task = directory / ("TASK_" + str(number).zfill(3) + ".md")
        with task.open("x", encoding="utf-8") as stream:
            stream.write(chr(10).join(task_lines) + chr(10))
        inv.require(safeguards.explicit_task_ids(task.read_text(encoding="utf-8")) == set(batch), "TASK exact source binding differs")
        packets.append(dict(role=role, task=number, ids=batch, path=str(packet_path.relative_to(ROOT)),
            sha256=inv.file_sha(packet_path), ordered_parts=views))
manifest = dict(status="ALL753_NATIVE_PROVEN_CANDIDATES_ASSIGNED_TO_FIVE_CONTEXT_ROLES_NOT_ADMISSION",
    rows=rows, assignments=assigned, source_characters_by_role=loads, reading_packets=packets,
    input_pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in [report_path, Path(__file__),
        AUDIT / "BIRTH_FIELD_CONTEXT_DELEGATION_V1.md"]}, source_code_pins=report["source_code_pins"],
    cache_admitted=0, goal_complete=False, training_authorized=False)
inv.write_json(OUT / "manifest.json", manifest)
producer = (AUDIT / "prepare_resume_guard_views_v1.py").read_text(encoding="utf-8")
with (AUDIT / "prepare_birth_field_views_v1.py").open("x", encoding="utf-8") as stream:
    stream.write(producer.replace("resume_guard_counter_20261102_v1", GROUP))
print(json.dumps(dict(sources=len(rows), roles={role: len(ids) for role, ids in assigned.items()}, tasks=len(packets)), ensure_ascii=False))
