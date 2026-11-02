"""Seal the nine current source/review pairs without changing any cache roster."""
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
import ast
import datetime
import difflib
import json
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_review_safeguards_v3 as safeguards

BASE = inv.BASE
GROUP = "resume_guard_counter_20261102_v1"
PACKET = BASE / GROUP
REPORT = AUDIT / "CURRENT_TWO_ROLE_REVIEW_RECEIPT_V1.json"
ARCHIVE = AUDIT / "current_two_role_review_archive_v1"

# Explicit root choices; no mtime, filename-rank, or last-writer selection.
CHOICES = [
    ("context_controls", 689736, 1, "review_001_v3.md", "expanded_train_689736_reviewed_v6.txt", "hold_689736_v3.md"),
    ("context_controls", 1254536, 2, "review_002_v4.md", "expanded_train_1254536_reviewed_v7.txt", "hold_1254536_v5.md"),
    ("context_controls", 852538, 3, "review_003_v3.md", "expanded_train_852538_reviewed_v7.txt", "hold_852538_v3.md"),
    ("context_controls", 71604, 4, "review_004_v2.md", "expanded_train_71604_reviewed_v2.txt", "hold_71604_v2.md"),
    ("context_latin", 8121, 1, "review_001.md", "expanded_train_8121_reviewed_v2.txt", "expanded_train_8121_hold_v1.md"),
    ("context_latin", 255342, 2, "review_002.md", None, None),
    ("context_latin", 1239923, 3, "review_003.md", None, "expanded_train_1239923_hold_v2.md"),
    ("context_latin", 1081376, 4, "review_004.md", None, "expanded_train_1081376_hold_v2.md"),
    ("context_latin", 1276826, 5, "review_005.md", None, "expanded_train_1276826_hold_v1.md"),
]


def pin(path):
    path = path.resolve()
    inv.require(path.is_relative_to(ROOT), "evidence outside the workspace")
    inv.require(0 < path.stat().st_size < 20_000_000, "empty or oversized evidence")
    return {"path": str(path.relative_to(ROOT)), "sha256": inv.file_sha(path), "bytes": path.stat().st_size}


def load_review_parser():
    # Reuse the actual saved parser without running its whole-collection driver.
    path = AUDIT / "collect_supplemental_candidates_v46.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef)
             and node.name in {"ident", "review_entries"}]
    inv.require(len(nodes) == 2, "saved review parser differs")
    namespace = {"re": re, "inv": inv}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    return namespace["review_entries"], namespace["ident"], pin(path)


def main():
    started = time.monotonic()
    inv.require(not REPORT.exists() and not ARCHIVE.exists(), "new immutable receipt required")
    packet_path = PACKET / "manifest.json"
    packet = inv.cache.read(packet_path)
    source_rows = {row["id"]: row for row in packet["rows"]}
    expected = {"expanded_train:" + str(row[1]) for row in CHOICES}
    inv.require(set(source_rows) == expected and len(expected) == 9, "exact nine IDs required")
    inv.require(packet["cache_admitted"] == 0, "packet is not a cache-admission record")
    frozen = packet["source_code_pins"]
    inv.require(len(frozen) == 66, "production freeze scope differs")
    for name, digest in frozen.items():
        inv.require(inv.file_sha(ROOT / name) == digest, "frozen production source changed")
    for name, digest in packet["input_pins"].items():
        inv.require(inv.file_sha(ROOT / name) == digest, "packet input changed")

    views_path = PACKET / "reading_views_manifest_v1.json"
    views = inv.cache.read(views_path)
    inv.require(views["source_manifest"]["sha256"] == inv.file_sha(packet_path), "view lineage differs")
    view_rows = {row["id"]: row for row in views["rows"]}
    inv.require(set(view_rows) == expected, "view source scope differs")
    reader_parser, review_ident, parser_pin = load_review_parser()
    rows, copies, all_local_files, body_text = [], [], {}, {}
    scope = inv.cache.read(BASE / "scope.json")
    inv.require(all(spec["path"].startswith("data_cache/") and "TinyDataset" not in spec["path"]
                    for spec in scope["inputs"]), "only the authorized native caches are eligible")
    with ExitStack() as stack:
        reader = inv.OriginalReader(scope, stack)
        for role, number, task_number, review_name, body_name, hold_name in CHOICES:
            ident = "expanded_train:" + str(number)
            source = source_rows[ident]
            inv.require(source["role"] == role, "role binding differs")
            raw, eos, valid = reader.text(source)
            inv.require(eos and valid, "EOS or UTF-8 check failed")
            values = {}
            for kind in ["original", "candidate"]:
                item = source[kind]
                path = ROOT / item["path"]
                inv.require(inv.file_sha(path) == item["sha256"], "source pair bytes changed")
                values[kind] = path.read_bytes()
            inv.require(values["original"] == raw.encode("utf-8"), "native decode differs from source copy")
            diff = "".join(difflib.unified_diff(
                values["original"].decode("utf-8").splitlines(keepends=True),
                values["candidate"].decode("utf-8").splitlines(keepends=True),
                fromfile=source["original"]["path"], tofile=source["candidate"]["path"])).encode("utf-8")
            for kind, payload in [*values.items(), ("diagnostic_diff", diff)]:
                fragments, next_character = [], 0
                for fragment in view_rows[ident]["views"][kind]:
                    path = ROOT / fragment["path"]
                    data = path.read_bytes()
                    lo, hi = fragment["source_characters"]
                    inv.require(inv.file_sha(path) == fragment["sha256"], "reading view changed")
                    inv.require(lo == next_character and hi - lo == len(data.decode("utf-8")), "view order gap")
                    next_character = hi
                    fragments.append(data)
                inv.require(b"".join(fragments) == payload, "views fail exact reconstruction")

            directory = BASE / "agents" / role / GROUP
            review_path = directory / review_name
            review = review_path.read_bytes()
            parsed = reader_parser(review)
            inv.require(len(parsed) == 1, "one explicit review row required")
            entry = parsed[0]
            inv.require(review_ident(entry["cells"][0]) == ident, "review ID differs")
            task = directory / ("TASK_" + str(task_number).zfill(3) + ".md")
            inv.require(safeguards.review_row_matches_task(ident, task.read_text(encoding="utf-8")), "TASK differs")
            selected_body = directory / body_name if body_name else ROOT / source["candidate"]["path"]
            decision = "REVISE_TEXT" if body_name else "ACCEPT_CANDIDATE"
            inv.require(entry["cells"][1] == decision, "explicit final review decision differs")
            outputs = re.findall(r"/home/uranus/tinyLM/[^\s`|()]+[.]txt", entry["cells"][3])
            inv.require(outputs == [str(selected_body)], "exactly one selected output required")
            inv.require(entry["cells"][2] and entry["cells"][4], "reading scope and reason required")
            text = selected_body.read_text(encoding="utf-8")
            inv.require(text.strip(), "empty final body")
            inv.require(not any(token in text for token in ["--- HOLD START", "--- HOLD END", "NEEDS_ROOT", "review_00", "hold_852538", "hold_689736"]), "review or quarantine leaked into body")
            body_text[number] = text
            hold_pin = None
            if hold_name:
                hold = directory / hold_name
                hold_pin = pin(hold)
                copies.append((role + "_" + str(number) + "_hold.md", hold.read_bytes(), hold_pin))
            review_pin = pin(review_path)
            copies.append((role + "_" + str(number) + "_review.md", review, review_pin))
            rows.append(dict(id=ident, source=source["source"], split=source["split"], source_ids=source["source_ids"],
                source_ids_sha256=source["source_ids_sha256"], original_text_sha256=source["original_text_sha256"],
                occurrences=source["occurrences"], source_kind="UNKNOWN_MIXED_NATIVE_CACHE",
                original=pin(ROOT / source["original"]["path"]), previous_candidate=pin(ROOT / source["candidate"]["path"]),
                body=pin(selected_body), review=review_pin, hold=hold_pin, task=pin(task), decision=decision,
                exact_task_match=True, fresh_native_decode=True, complete_eos=True, valid_utf8=True,
                ordered_views_reconstruct=True, root_reviewed_for_checkpoint=True, final_cache_roster_approved=False))
            for path in sorted(directory.iterdir()):
                if path.is_file() and path.suffix in {".txt", ".md"}:
                    all_local_files[str(path.relative_to(ROOT))] = pin(path)

    # Exact mediated boundaries; these are not general fact or model-quality tests.
    inv.require("The Hospital for Tropical Diseases (HTD), Ho Chi Minh City, Vietnam." in body_text[8121]
                and "The number of cases is likely underreported" in body_text[8121]
                and "N.T.H Mai et al." not in body_text[8121], "institution/count boundary differs")
    inv.require("왼쪽 위부터 시계 방향으로" not in body_text[1239923]
                and all(word in body_text[1239923] for word in ["바즈라요기니", "스리 얀트라", "차크라", "찰라차크라", "다키니"]), "image/caption boundary differs")
    inv.require("2004년 4월 1일" not in body_text[1081376] and "2004년 3월 1일" not in body_text[1081376]
                and "2004년" in body_text[1081376], "conflicting dates were selected")
    inv.require("Writers Write offers" not in body_text[1276826], "advertisement remains")
    inv.require("nhlDF.set_index" in body_text[689736] and "lastSeasonDF =" not in body_text[689736], "incomplete aggregate restored")
    inv.require("dictionary.iterkeys()" not in body_text[1254536]
                and "The following accessors are available." not in body_text[1254536], "unbound API description restored")
    inv.require("f()" not in body_text[852538] and "t()" not in body_text[852538]
                and "The single-crossing condition is known" not in body_text[852538]
                and "수익 등가정리는 대규모 경매" not in body_text[852538], "missing mathematical antecedent restored")
    inv.require("FloydWarshallWithPathReconstruction" not in body_text[71604]
                and "initialized to ∞" in body_text[71604] and "슐츠 선거 제도와 결합해서" in body_text[71604], "path example boundary differs")

    for name, value in all_local_files.items():
        inv.require(inv.file_sha(ROOT / name) == value["sha256"], "author file changed during seal")
    for name, digest in frozen.items():
        inv.require(inv.file_sha(ROOT / name) == digest, "production source changed during seal")
    ARCHIVE.mkdir()
    archived = []
    for name, payload, source_pin in copies:
        destination = ARCHIVE / name
        with destination.open("xb") as stream:
            stream.write(payload)
        inv.require(inv.file_sha(destination) == source_pin["sha256"], "archive differs")
        archived.append(dict(source=source_pin, archive=pin(destination)))
    selected_reviews = {row["review"]["path"] for row in rows}
    historical_reviews = [value for path, value in all_local_files.items()
                          if Path(path).name.startswith("review") and path not in selected_reviews]
    receipt = dict(status="TWO_ROLE_NINE_SOURCE_REVIEW_CHECKPOINT_NOT_CACHE_ADMISSION",
        observed_at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),
        rows=rows, review_decisions=dict(Counter(row["decision"] for row in rows)),
        source_pairs=9, source_characters=sum(packet["source_characters_by_role"].values()),
        source_roles={role: len(ids) for role, ids in packet["assignments"].items()},
        reading_views=50, frozen_production_files=66, preserved_local_author_files=list(all_local_files.values()),
        nonselected_reviews_preserved=historical_reviews, selected_review_and_hold_archives=archived,
        input_pins=[pin(packet_path), pin(views_path), parser_pin, pin(BASE / "scope.json"), pin(Path(__file__))],
        boundary_checks="EXACT_MEDIATED_CASES_ONLY_NOT_GENERAL_SEMANTIC_CERTIFICATION",
        new_native_policy_run=False, whole_collection_updated=False, final_cache_created=False,
        cache_admitted=0, goal_complete=False, training_authorized=False, seconds=time.monotonic() - started)
    inv.write_json(REPORT, receipt)
    print(json.dumps(dict(source_pairs=9, decisions=receipt["review_decisions"], native_decode=9,
        preserved_local_files=len(all_local_files), historical_reviews=len(historical_reviews),
        archived_reviews_and_holds=len(archived), frozen_production_files=66, seconds=receipt["seconds"]), ensure_ascii=False))


if __name__ == "__main__":
    main()
