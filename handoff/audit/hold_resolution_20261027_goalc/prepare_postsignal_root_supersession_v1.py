"""Supersede exact 62929 only after verifying the source-linked one-line repair."""
from pathlib import Path
import difflib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v19 as policy

AUDIT = Path(__file__).resolve().parent
OUT = AUDIT / "ROOT_POSTSIGNAL_BODY_SELECTIONS_V1.json"
inv.require(not OUT.exists(), "new exact root supersession required")
plan_path = AUDIT / "reviewed_selection_plan_v6.json"
snapshot_path = AUDIT / "supplemental_candidates_snapshot_v25.json"
plan, snapshot = inv.cache.read(plan_path), inv.cache.read(snapshot_path)
old_record = next(row for row in plan["records"] if row["id"] == "expanded_train:62929")
old = old_record["selected"]
new = next(row for row in snapshot["records"] if row["id"] == old["id"]
           and row["cohort"] == "root_selected_signal_counter_v1")
inv.require(old_record["root_approved"] and new["original"]["sha256"] == old["original_text_sha256"],
            "exact source identity or predecessor differs")
for path, expected in [(old["body"], old["clean_text_sha256"]),
                       (new["body"], new["clean_text_sha256"]),
                       (new["original"]["path"], new["original"]["sha256"]),
                       (new["review"]["path"], new["review"]["sha256"])]:
    inv.require(inv.file_sha(ROOT / path) == expected, "pinned supersession artifact changed")
before = (ROOT / old["body"]).read_bytes().decode("utf-8")
after = (ROOT / new["body"]).read_bytes().decode("utf-8")
raw = (ROOT / new["original"]["path"]).read_bytes().decode("utf-8")
left, right = before.splitlines(keepends=True), after.splitlines(keepends=True)
changes = [row for row in difflib.SequenceMatcher(None, left, right, autojunk=False).get_opcodes() if row[0] != "equal"]
inv.require(len(changes) == 1 and changes[0][0] == "insert", "62929 changed beyond the root-read inserted sentence")
_, lo, hi, start, end = changes[0]
inserted = "".join(right[start:end])
inv.require(inserted.strip() == "전압이 모스 구조에 인가됐을 때, 반도체에 있는 전하의 분포를 변경한다."
            and inserted.strip() in raw, "restored sentence is not the exact filled source statement")
guards = dict(code_guard=policy.code_preserved(raw, after), unicode_guard=policy.unicode_examples_preserved(raw, after),
              semantic_style_guard=policy.semantic_style_preserved(raw, after))
inv.require(all(guards.values()), "source literal guard differs")
supersedes = []
for name in old_record["exact_root_evidence"]:
    path = ROOT / name
    rows = [row for row in inv.cache.read(path)["rows"] if row["id"] == old["id"]]
    inv.require(len(rows) == 1 and rows[0]["decision"] == old["decision"]
                and rows[0]["clean_text_sha256"] == old["clean_text_sha256"], "exact predecessor binding differs")
    supersedes.append(dict(selection_file=name, selection_file_sha256=inv.file_sha(path),
                           id=old["id"], decision=old["decision"], clean_text_sha256=old["clean_text_sha256"]))
row = dict(id=old["id"], decision="EDIT", source=new["original"]["path"],
    original_text_sha256=new["original"]["sha256"], body=new["body"], clean_text_sha256=new["clean_text_sha256"],
    selected_cohort=new["cohort"], review_inputs=[new["review"]], supersedes=supersedes,
    reason="ROOT_READ_SOURCE_AND_ONE_INSERTION_DIFF_RESTORES_INDEPENDENT_MOS_CHARGE_DISTRIBUTION_STATEMENT",
    exact_inserted_source_statement=inserted.strip(), literal_guards=guards,
    root_approved=True, cache_admitted=False, goal_complete=False, training_authorized=False)
inv.write_json(OUT, dict(status="EXACT_ROOT_SUPERSESSION_NOT_CACHE_ADMISSION", rows=[row],
    input_pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in [plan_path, snapshot_path, Path(__file__)]},
    cache_admitted=0, goal_complete=False, training_authorized=False))
print(json.dumps(dict(id=row["id"], superseded_exact_decisions=len(supersedes),
                      new_body_sha256=row["clean_text_sha256"], literal_guards=guards), ensure_ascii=False))
