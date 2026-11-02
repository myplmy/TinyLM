"""Prepare blind cross-type reading from the exact sealed nine current bodies."""
from collections import Counter
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

BASE = inv.BASE
GROUP = "resume_guard_independent_20261102_v1"
OUT = BASE / GROUP
inv.require(not OUT.exists(), "new independent pair namespace required")
sealed_path = AUDIT / "CURRENT_TWO_ROLE_REVIEW_RECEIPT_V1.json"
sealed = inv.cache.read(sealed_path)
old_packet_path = BASE / "resume_guard_counter_20261102_v1/manifest.json"
old_packet = inv.cache.read(old_packet_path)
original_rows = {row["id"]: row for row in old_packet["rows"]}
selected_rows = {row["id"]: row for row in sealed["rows"]}
assignments = {
    "context_controls": ["expanded_train:8121", "expanded_train:255342", "expanded_train:1239923", "expanded_train:1081376", "expanded_train:1276826"],
    "context_latin": ["expanded_train:689736", "expanded_train:1254536", "expanded_train:852538", "expanded_train:71604"],
}
inv.require(set(selected_rows) == {ident for ids in assignments.values() for ident in ids}, "sealed nine differ")
for name, digest in old_packet["source_code_pins"].items():
    inv.require(inv.file_sha(ROOT / name) == digest, "production source changed")
(OUT / "inputs").mkdir(parents=True)
rows, sizes = [], Counter()
for role, ids in assignments.items():
    for ident in ids:
        source, selected = original_rows[ident], selected_rows[ident]
        inv.require(source["role"] != role and selected["complete_eos"] and selected["valid_utf8"], "not a cross-type verified assignment")
        pins = {}
        for kind, previous in [("original", source["original"]), ("candidate", selected["body"])]:
            path = ROOT / previous["path"]
            inv.require(inv.file_sha(path) == previous["sha256"], "sealed evidence changed")
            payload = path.read_bytes()
            inv.require(0 < len(payload) < 20_000_000, "pair needs splitting")
            destination = OUT / "inputs" / (ident.replace(":", "_") + "_" + kind + ".txt")
            with destination.open("xb") as stream:
                stream.write(payload)
            pins[kind] = dict(path=str(destination.relative_to(ROOT)), sha256=inv.file_sha(destination))
        sizes[role] += len((ROOT / pins["original"]["path"]).read_text(encoding="utf-8"))
        rows.append(dict({key: source[key] for key in ["id", "source", "split", "source_ids", "source_ids_sha256", "original_text_sha256", "input_ids", "occurrences", "language_bucket"]},
            **pins, role=role, previous_author_role=source["role"], candidate_decision="NEEDS_ROOT",
            candidate_reasons=["INDEPENDENT_SOURCE_MEANING_REVIEW_REQUIRED"], root_approved=False))
evidence = OUT / "EVIDENCE_8121_JING_CITATION_V1.md"
previous_evidence = BASE / "resume_guard_counter_20261102_v1/EVIDENCE_8121_JING_CITATION_V1.md"
with evidence.open("xb") as stream:
    stream.write(previous_evidence.read_bytes())
for role, ids in assignments.items():
    directory = BASE / "agents" / role / GROUP
    directory.mkdir(parents=True, exist_ok=False)
    instructions = [
        "# 서로 다른 원문 유형의 독립 판독", "",
        "지정 original/candidate와 전체 순서뷰 및 이 폴더 START/TASK/READING_VIEWS만 읽는다.",
        "8121은 지정된 저자 표기 증거 사본을 추가로 읽는다. 옛 작성자 리뷰·보류·다른 역할 출력은 받지 않는다.",
        "허용 쓰기는 이 폴더의 새 txt/md뿐이다. 기존 파일을 덮거나 삭제하지 않는다.",
        "코드/시험/통계/해시/Python/모델/GPU/Git/웹/보호자료/타 세션/공유원장 접근은 금지한다.",
        "narrow nl/sed/tail/diff와 새 txt/md 편집만 허용한다. 여러 파일을 cat으로 이어붙이지 않는다.",
        "original과 candidate의 모든 순서뷰·전문·실제 EOF 및 전체 diff를 읽고 의미와 오삭제를 독립 판단한다.",
        "누락 식/인수/변수/날짜/대상을 원문 밖 지식으로 생성하지 않는다. 원문에 실제 채워진 코드·인용·수치·조건·불확실성은 보호한다.",
        "본문 일부를 보류했을 때 남은 문장이 빠진 표제·정의·출력·그림·초기화에 의존하는지 확인한다.",
        "정제 후보가 적절하면 ACCEPT_CANDIDATE와 정확 candidate 입력 한 경로를 출력한다.",
        "수정 필요 시 새 전체 TXT와 원형 보류 MD를 작성하고 REVISE_TEXT로 정확 TXT 한 경로를 출력한다.",
        "보류 원형·검수 메모는 학습 본문에 넣지 않는다. 모호한 경계는 NEEDS_ROOT와 좁은 질문으로 남긴다.",
        "각 TASK 후 review_NNN.md를 표로 저장한다. ID / 판정 / 실제 판독 범위 / 출력 / 구체 근거 열을 쓴다.",
        "파일명이 같은 경우 새 버전으로 보존한다. 전체 캐시 채택·품질 PASS는 선언하지 않는다.",
    ]
    with (directory / "START_HERE.md").open("x", encoding="utf-8") as stream:
        stream.write(chr(10).join(instructions) + chr(10))
    for number, ident in enumerate(ids, 1):
        row = next(row for row in rows if row["id"] == ident)
        text = ["# TASK_" + str(number).zfill(3), ident, "START_HERE와 READING_VIEWS를 따른다.",
            "original: " + str(ROOT / row["original"]["path"]), "candidate: " + str(ROOT / row["candidate"]["path"]),
            "후보와 원문 전량을 실제로 읽고 독립적으로 판단한다. 이전 리뷰나 총괄 선택 이유는 입력에 포함하지 않는다."]
        if ident == "expanded_train:8121":
            text.append("추가 허용 증거: " + str(evidence))
        with (directory / ("TASK_" + str(number).zfill(3) + ".md")).open("x", encoding="utf-8") as stream:
            stream.write(chr(10).join(text) + chr(10))
manifest = dict(status="BLIND_CROSS_TYPE_CURRENT_BODY_REVIEW_NOT_ADMISSION", rows=rows,
    assignments=assignments, source_characters_by_role=dict(sizes), source_code_pins=old_packet["source_code_pins"],
    input_pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in [sealed_path, old_packet_path, Path(__file__)]},
    cache_admitted=0, goal_complete=False, training_authorized=False)
inv.write_json(OUT / "manifest.json", manifest)
producer = (AUDIT / "prepare_resume_guard_views_v1.py").read_text(encoding="utf-8")
with (AUDIT / "prepare_resume_independent_views_v1.py").open("x", encoding="utf-8") as stream:
    stream.write(producer.replace("resume_guard_counter_20261102_v1", GROUP))
print(json.dumps(dict(rows=len(rows), assignments={role: len(ids) for role, ids in assignments.items()}, source_characters=dict(sizes)), ensure_ascii=False))
