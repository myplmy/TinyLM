"""Pin the completed 753-source cohort; leave global merge and cache pending."""
from collections import Counter
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / "data_cache/p106b_hold_resolution_v1_20261027_goalc"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def pin(path):
    return dict(path=str(path.relative_to(ROOT)), sha256=sha(path))


def check(value):
    path = ROOT / value["path"]
    assert path.is_relative_to(BASE) or path.is_relative_to(AUDIT)
    assert sha(path) == value["sha256"], value["path"]


def main():
    snapshot_path = AUDIT / "supplemental_candidates_snapshot_v51.json"
    audit_path = AUDIT / "BIRTH_AUTHORED_BODY_AUDIT_V2.json"
    manifest_path = BASE / "birth_field_native_counter_v1/manifest.json"
    native_path = BASE / "birth_field_native_proof_v1/complete.json"
    prior_path = AUDIT / "ROOT_AUTHORED_SELECTIONS_V9.json"
    output = AUDIT / "ROOT_BIRTH_BODY_SELECTIONS_V1.json"
    assert not output.exists(), "immutable root cohort selection already exists"
    snapshot, audit, manifest = map(read, [snapshot_path, audit_path, manifest_path])
    assert audit["status"] == "ALL753_POST_REVIEW_BODY_AUDIT_CLEAR"
    assert audit["checked"] == 753 and audit["failures"] == []
    assert audit["input_pins"][str(snapshot_path.relative_to(ROOT))] == sha(snapshot_path)
    source_rows = {row["id"]: row for row in manifest["rows"]}
    audit_rows = {row["id"]: row for row in audit["records"]}
    records = [row for row in snapshot["records"]
               if row["cohort"] == "birth_field_native_counter_v1"]
    assert len(records) == len(source_rows) == len(audit_rows) == 753
    assert {row["id"] for row in records} == set(source_rows) == set(audit_rows)
    assert Counter(row["decision"] for row in records) == Counter(ADOPT_CANDIDATE=735, EDIT_TEXT=18)
    assert snapshot["coverage"]["birth_field_native_counter_v1"]["awaiting_review"] == 0
    for name, digest in audit["input_pins"].items():
        assert sha(ROOT / name) == digest, name
    native = read(native_path)
    assert native["counts"]["all_inherited_checks_terminal_unique"] == 753
    for name, digest in native["source_code_pins"].items():
        assert sha(ROOT / name) == digest, name
    prior = {row["id"]: row for row in read(prior_path)["rows"]}
    selected, overlaps = [], []
    for record in sorted(records, key=lambda row: row["id"]):
        key = record["id"]
        source, checked = source_rows[key], audit_rows[key]
        assert record["decision"] in {"ADOPT_CANDIDATE", "EDIT_TEXT"}
        assert source["original_text_sha256"] == record["original"]["sha256"]
        assert checked["original_text_sha256"] == source["original_text_sha256"]
        assert checked["clean_text_sha256"] == record["clean_text_sha256"]
        assert checked["errors"] == [] and source["complete_eos"] and source["valid_utf8"]
        for value in [source["original"], source["candidate"], record["review"]]:
            check(value)
        check(dict(path=record["body"], sha256=record["clean_text_sha256"]))
        if record["review"].get("archive"):
            check(dict(path=record["review"]["archive"], sha256=record["review"]["sha256"]))
        if record.get("author_output"):
            check(record["author_output"])
        if record["decision"] == "ADOPT_CANDIDATE":
            assert record["clean_text_sha256"] == source["candidate"]["sha256"]
        assert record["clean_text_sha256"] != source["original_text_sha256"]
        old = prior.get(key)
        if old:
            assert old["original_text_sha256"] == source["original_text_sha256"]
            overlaps.append(key)
        selected.append(dict(id=key, original=source["original"],
            source_ids=source["source_ids"], source_ids_sha256=source["source_ids_sha256"],
            occurrences=source["occurrences"], input_ids=source["input_ids"],
            candidate=source["candidate"], body=record["body"],
            clean_text_sha256=record["clean_text_sha256"], review=record["review"],
            author_output=record.get("author_output"), role=record["role"],
            review_decision=record["decision"], decision="EDIT", reason=record["reason"],
            root_approved_for_this_cohort=True,
            global_prior_selection_exists=bool(old),
            global_selection_superseded=False, cache_admitted=False))
    assert len(overlaps) == 10
    report = dict(status="EXACT753_COHORT_BODY_SELECTIONS_GLOBAL_MERGE_AND_CACHE_PENDING",
        source_ids=753, occurrences=sum(row["occurrences"] for row in selected),
        decisions=dict(Counter(row["review_decision"] for row in selected)),
        root_checked_final_revised_diffs=18, root_diff_read_group_sizes=[6, 6, 6],
        exact_guard_exceptions=audit["accepted_exact_guard_exceptions"],
        prior_global_selection_overlap_ids=overlaps,
        prior_global_selection_superseded=0, rows=selected,
        input_pins={str(path.relative_to(ROOT)): sha(path) for path in [
            snapshot_path, audit_path, manifest_path, native_path, prior_path,
            AUDIT / "BIRTH_FIELD_REVIEW_BOUNDARIES_V1.md",
            AUDIT / "BIRTH_PROOF_CONTEXT_COUNTEREXAMPLES_V1.md", Path(__file__)]},
        frozen_production_sources_unchanged=len(native["source_code_pins"]),
        final_cache_created=False, cache_admitted=0, goal_complete=False,
        training_authorized=False)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + chr(10)
    assert len(payload.encode("utf-8")) < 20_000_000
    with output.open("x", encoding="utf-8") as stream:
        stream.write(payload)
    print(json.dumps({key: report[key] for key in ["status", "source_ids", "occurrences", "decisions", "prior_global_selection_superseded"]}))


if __name__ == "__main__":
    main()
