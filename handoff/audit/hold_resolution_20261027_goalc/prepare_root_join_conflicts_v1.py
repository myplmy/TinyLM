"""Fresh native proof and complete framed reading packets for all 215 conflicts."""
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
import difflib
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

BASE = inv.BASE
GROUP = "root_join_conflict_counter_v1"
OUT = BASE / GROUP
preview_path = AUDIT / "ROOT_AUTHORED_SELECTIONS_V10_PREVIEW2.json"
draft_path = BASE / "draft_proposals_v26_delta_v1/complete.json"
scope_path = BASE / "scope.json"
delegation = AUDIT / "ROOT_JOIN_CONFLICT_DELEGATION_V1.md"
roles = ["context_controls", "context_latin", "context_hangul", "historical_review", "legacy_review"]
inv.require(not OUT.exists(), "new immutable conflict packets required")
preview, draft, scope = map(inv.cache.read, [preview_path, draft_path, scope_path])
conflicts = preview["unresolved"]
inv.require(len(conflicts) == 215 and not any(row["restricted_parent_metadata_only"] for row in conflicts),
            "all215 conflict scope or restricted boundary differs")
for name, digest in draft["lineage"]["source_code_sha256"].items():
    inv.require(inv.file_sha(ROOT / name) == digest, "production sources changed")
inv.verify(draft_path.parent / "unique", draft["unique_manifest"])
needed_hashes = {row["original_text_sha256"] for row in conflicts}
source_rows = {row["original_text_sha256"]: row for row in inv.cache.rows(
    draft_path.parent / "unique", draft["unique_manifest"]) if row["original_text_sha256"] in needed_hashes}
inv.require(set(source_rows) == needed_hashes, "every conflict needs actual source coordinates")
started = time.monotonic()
prepared = []
with ExitStack() as stack:
    reader = inv.OriginalReader(scope, stack)
    for conflict in conflicts:
        source = source_rows[conflict["original_text_sha256"]]
        raw, eos, valid = reader.text(source)
        inv.require(eos and valid and inv.sha(raw) == conflict["original_text_sha256"], "native proof differs")
        previous = conflict["previous_root9"]
        bodies = {}
        for proposal in [previous, *conflict["new_proposals"]]:
            if proposal and proposal.get("body"):
                path = ROOT / proposal["body"]
                inv.require(inv.file_sha(path) == proposal["clean_text_sha256"], "authored variant changed")
                bodies[proposal["clean_text_sha256"]] = path.read_text(encoding="utf-8")
        fresh = sorted(conflict["new_proposals"],
                       key=lambda row: row["cohort"] != "birth_field_native_counter_v1")
        candidate = next(row for row in fresh if row.get("body"))
        previous_body = bodies[previous["clean_text_sha256"]] if previous.get("body") else None
        cost = len(raw) + sum(len(value) for value in bodies.values())
        previous_roles = {Path(row["review"]["path"]).parts[-3] for row in [previous, *fresh]
                          if row.get("review") and "agents" in Path(row["review"]["path"]).parts}
        prepared.append(dict(conflict=conflict, source=source, raw=raw, bodies=bodies,
            previous=previous_body, candidate=candidate, cost=cost, previous_roles=previous_roles))
assignments, sizes = {role: [] for role in roles}, Counter()
for record in sorted(prepared, key=lambda row: (-row["cost"], row["conflict"]["id"])):
    available = [role for role in roles if role not in record["previous_roles"]] or roles
    role = min(available, key=lambda value: (sizes[value], len(assignments[value]), value))
    record["role"] = role
    assignments[role].append(record["conflict"]["id"])
    sizes[role] += record["cost"]
for role in roles:
    assignments[role].sort()
(OUT / "inputs").mkdir(parents=True)
(OUT / "reading_packets_v1").mkdir()


def save(path, text):
    payload = text.encode("utf-8")
    inv.require(0 < len(payload) < 20_000_000, "every new artifact must fit the cap")
    with path.open("xb") as stream:
        stream.write(payload)
    return dict(path=str(path.relative_to(ROOT)), sha256=inv.file_sha(path), bytes=len(payload))


evidence = []
for name in ["EVIDENCE_291381_TOLBERT_DATES_V1.md", "EVIDENCE_50559_ACCESSION_DATE_V1.md"]:
    evidence.append(save(OUT / name, (AUDIT / name).read_text(encoding="utf-8")))
guidance = save(OUT / "ROOT_GUIDANCE_V1.md", delegation.read_text(encoding="utf-8"))
rows, by_id = [], {}
for record in prepared:
    conflict, source = record["conflict"], record["source"]
    ident, stem = conflict["id"], conflict["id"].replace(":", "_")
    original = save(OUT / "inputs" / (stem + "_original.txt"), record["raw"])
    candidate_sha = record["candidate"]["clean_text_sha256"]
    candidate_text = record["bodies"][candidate_sha]
    candidate = save(OUT / "inputs" / (stem + "_candidate.txt"), candidate_text)
    variants = []
    for number, (digest, text) in enumerate(record["bodies"].items(), 1):
        variants.append(dict(**save(OUT / "inputs" / (stem + "_variant_" + str(number) + ".txt"), text),
            clean_text_sha256=digest, previous=conflict["previous_root9"].get("clean_text_sha256") == digest,
            candidate=digest == candidate_sha))
    sections = [("ORIGINAL", record["raw"])]
    if record["previous"] is not None:
        sections.append(("PREVIOUS_ROOT_BODY", record["previous"]))
    sections.append(("CANDIDATE_BODY", candidate_text))
    for number, variant in enumerate(variants, 1):
        if not variant["previous"] and not variant["candidate"]:
            sections.append(("ADDITIONAL_VARIANT_" + str(number), record["bodies"][variant["clean_text_sha256"]]))
    for kind, before in [("ORIGINAL_TO_CANDIDATE_FULL_DIFF", record["raw"]),
                         ("PREVIOUS_TO_CANDIDATE_FULL_DIFF", record["previous"])]:
        if before is not None:
            delta = "".join(difflib.unified_diff(before.splitlines(keepends=True),
                candidate_text.splitlines(keepends=True), fromfile=kind + "_before", tofile=kind + "_after"))
            sections.append((kind, delta or "(비교한 전문의 줄 차이 없음)"))
    sections.append(("REVIEW_REASONS_NOT_TRAINING_TEXT", json.dumps(dict(
        previous=conflict["previous_root9"], fresh=conflict["new_proposals"]), ensure_ascii=False, indent=2)))
    framed = ""
    for kind, text in sections:
        framed += "=== BEGIN " + ident + " " + kind + " characters=" + str(len(text)) + " ===" + chr(10)
        framed += text + chr(10) + "=== END " + ident + " " + kind + " ===" + chr(10)
    parts = []
    reconstructed = ""
    for offset in range(0, len(framed), 6000):
        fragment = framed[offset:offset + 6000]
        pin = save(OUT / "reading_packets_v1" / (stem + "_" + str(offset // 6000 + 1).zfill(4) + ".txt"), fragment)
        parts.append(dict(pin, characters=[offset, offset + len(fragment)]))
        reconstructed += fragment
    inv.require(reconstructed == framed, "ordered complete packet reconstruction differs")
    row = {key: source[key] for key in ["source", "split", "source_ids", "source_ids_sha256",
        "original_text_sha256", "input_ids", "occurrences", "language_bucket"]}
    row.update(id=ident, native_representative_id=source["id"], original=original, candidate=candidate,
        variants=variants, role=record["role"], reading_parts=parts, complete_eos=True, valid_utf8=True,
        candidate_decision="NEEDS_ROOT", candidate_reasons=["PREVIOUS_AND_NEW_BODY_NEED_SOURCE_ADJUDICATION"],
        root_approved=False, previous_root=conflict["previous_root9"], new_proposals=conflict["new_proposals"])
    rows.append(row)
    by_id[ident] = row
for role, ids in assignments.items():
    directory = BASE / "agents" / role / GROUP
    directory.mkdir(parents=True, exist_ok=False)
    instructions = ["# 전체 선택 차이의 원문 판독", "",
        "허용 입력은 이 폴더 START/TASK/READING_VIEWS 및 그 안에서 정확히 지정한 새 패킷·TXT·근거 MD뿐이다.",
        "패킷은 원문·옛 본문·새 본문·추가 변형·전체 차이를 BEGIN/END로 구분한다. 모든 순서 조각을 읽으면 전문 판독이다.",
        "허용 쓰기는 이 폴더의 새 txt/md뿐이다. 기존 파일을 덮거나 삭제하지 않는다. 지정 TXT를 새 출력명으로 복사할 수 있다.",
        "코드·시험·통계·해시·Python·Git·웹·모델·GPU·보호자료·다른 역할·타 세션·공유원장 접근은 금지한다.",
        "narrow sed/nl/tail/diff와 새 txt/md 작성만 한다. 여러 파일 cat 이어붙이기와 잘린 출력을 전문 판독으로 세지 않는다.",
        "각 TASK의 모든 ID·패킷 조각을 순서대로 읽고 실제 EOF까지 확인한다. 검수 의견은 참고 자료이며 원문 내용과 구분한다.",
        "지정 후보가 적절하면 ACCEPT_CANDIDATE와 정확 candidate 한 경로를 출력한다.",
        "옛 본문이 맞거나 추가 수정이 필요하면 새 전체 TXT와 원형 보류 MD를 작성하고 REVISE_TEXT와 정확 TXT 한 경로를 출력한다.",
        "내용을 생성하거나 날짜·나이·단위·값을 역산하지 않는다. 독립 경력·코드·인용·부정·조건을 보존한다.",
        "불분명한 부분만 NEEDS_ROOT로 좁은 질문을 남긴다. 전체 캐시 채택·품질 PASS를 선언하지 않는다.",
        "각 TASK 완료 뒤 review_NNN.md를 표로 저장한다. ID / 판정 / 실제 판독 범위 / 출력 / 구체 근거 5열을 모두 유지한다.",
        "이미 쓴 파일은 새 버전으로 남긴다. 검수 메모·원형 보류는 학습 본문 TXT 밖 MD로 분리한다.",
        "공통 추가 허용 근거: " + str(ROOT / guidance["path"])]
    save(directory / "START_HERE.md", chr(10).join(instructions) + chr(10))
    view_lines = ["# 지정 전문 판독 목록", "모든 지정 패킷의 BEGIN/END와 실제 EOF를 확인한다."]
    for task, offset in enumerate(range(0, len(ids), 5), 1):
        lines = ["# TASK_" + str(task).zfill(3), "START_HERE와 지정 전문 패킷·공통 근거를 따른다."]
        for ident in ids[offset:offset + 5]:
            row = by_id[ident]
            lines.extend(["## " + ident, "original: " + str(ROOT / row["original"]["path"]),
                "candidate: " + str(ROOT / row["candidate"]["path"])])
            lines.extend("variant: " + str(ROOT / value["path"]) for value in row["variants"])
            lines.append("전문 순서 패킷(내용·차이 전체 포함):")
            lines.extend("- " + str(ROOT / value["path"]) for value in row["reading_parts"])
            if ident in {"expanded_train:291381", "expanded_train:50559"}:
                name = "EVIDENCE_291381_TOLBERT_DATES_V1.md" if ident.endswith(":291381") else "EVIDENCE_50559_ACCESSION_DATE_V1.md"
                lines.append("추가 허용 좁은 근거: " + str(OUT / name))
            view_lines.extend(["## " + ident, *["- " + str(ROOT / value["path"]) for value in row["reading_parts"]]])
        save(directory / ("TASK_" + str(task).zfill(3) + ".md"), chr(10).join(lines) + chr(10))
    save(directory / "READING_VIEWS.md", chr(10).join(view_lines) + chr(10))
manifest = dict(status="ALL215_FRESH_NATIVE_VERIFIED_FULL_CONTEXT_VARIANTS_REVIEW_NOT_ADMISSION", rows=rows,
    assignments=assignments, source_characters_by_role=dict(sizes), evidence=evidence, guidance=guidance,
    input_pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in [preview_path, draft_path, scope_path, delegation, Path(__file__)]},
    source_code_pins=draft["lineage"]["source_code_sha256"], fresh_native_sources=215,
    root_approved=False, cache_admitted=0, goal_complete=False, training_authorized=False,
    seconds=time.monotonic() - started)
inv.write_json(OUT / "manifest.json", manifest)
print(json.dumps(dict(sources=len(rows), assignments={role: len(ids) for role, ids in assignments.items()},
    characters=dict(sizes), packet_parts=sum(len(row["reading_parts"]) for row in rows), seconds=manifest["seconds"])))
