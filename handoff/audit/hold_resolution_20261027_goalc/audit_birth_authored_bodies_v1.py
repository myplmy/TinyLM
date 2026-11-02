"""Audit every saved birth candidate after human reading, including new life-role conflicts."""
from collections import Counter
from pathlib import Path
import argparse
import json
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_birth_conflicts_v1 as birth


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    source_path = (ROOT / args.snapshot).resolve()
    output = (ROOT / args.output).resolve()
    inv.require(source_path.is_relative_to(AUDIT) and output.is_relative_to(AUDIT) and not output.exists(), "exact new owned paths required")
    snapshot = inv.cache.read(source_path)
    group = "birth_field_native_counter_v1"
    manifest_path = inv.BASE / group / "manifest.json"
    manifest = inv.cache.read(manifest_path)
    expected = {row["id"]: row for row in manifest["rows"]}
    rows = [row for row in snapshot["records"] if row["cohort"] == group]
    inv.require(len(rows) == len(expected) == 753 and {row["id"] for row in rows} == set(expected), "all753 source rows required")
    exception_path = AUDIT / "BIRTH_FIELD_EXACT_SEMANTIC_EXCEPTIONS_V1.json"
    exceptions = {row["id"]: row for row in inv.cache.read(exception_path)["rows"]}
    checked, failures, accepted_exceptions, counts = [], [], [], Counter()
    started = time.monotonic()
    for row in rows:
        counts[row["decision"]] += 1
        errors = []
        if row["decision"] not in {"ADOPT_CANDIDATE", "EDIT_TEXT"} or not row.get("body"):
            failures.append(dict(id=row["id"], error="NO_FINAL_MATERIALIZED_BODY", review=row["review"]))
            continue
        spec = expected[row["id"]]
        inv.require(row["original"]["sha256"] == spec["original_text_sha256"], "source identity differs")
        original_path, body_path = ROOT / row["original"]["path"], ROOT / row["body"]
        inv.require(inv.file_sha(original_path) == row["original"]["sha256"], "original changed")
        inv.require(inv.file_sha(body_path) == row["clean_text_sha256"], "body changed")
        inv.require(inv.file_sha(ROOT / row["review"]["path"]) == row["review"]["sha256"], "review changed")
        original, body = original_path.read_text(encoding="utf-8"), body_path.read_text(encoding="utf-8")
        flags = dict(ordered=birth.baseline.ordered_deletion(original, body),
            code=birth.baseline.code_preserved(original, body), unicode=birth.baseline.unicode_examples_preserved(original, body),
            style=birth.baseline.semantic_style_preserved(original, body))
        for name, okay in flags.items():
            if okay:
                continue
            exception = exceptions.get(row["id"])
            allowed = (name == "ordered" and exception and exception["root_approved"] is True
                and exception["original_text_sha256"] == row["original"]["sha256"]
                and exception["body"]["sha256"] == row["clean_text_sha256"]
                and exception["allowed_guard_exception"] == "ORDERED_DELETION_ONLY_FOR_THIS_EXACT_BODY")
            if allowed:
                accepted_exceptions.append(dict(id=row["id"], guard=name, body_sha256=row["clean_text_sha256"],
                    evidence=dict(path=str(exception_path.relative_to(ROOT)), sha256=inv.file_sha(exception_path))))
            else:
                errors.append("UNPROVEN_" + name.upper() + "_CHANGE")
        introduced = Counter(re.findall(r"[0-9]+", body)) - Counter(re.findall(r"[0-9]+", original))
        if introduced:
            errors.append("INTRODUCED_NUMERIC_OCCURRENCES")
        for marker in ["# BEGIN ORIGINAL", "NEEDS_ROOT", "--- HOLD START", "検収", "검수 메모", "원형 보존"]:
            if marker in body and marker not in original:
                errors.append("INTRODUCED_EDITOR_MEMO")
        old_lead, lead = birth.baseline.v12.INTRO_NAME.match(original), birth.baseline.v12.INTRO_NAME.match(body)
        if old_lead and lead:
            old_parts = birth.SPAN.split(old_lead["fields"], maxsplit=1)
            new_parts = birth.SPAN.split(lead["fields"], maxsplit=1)
            old_born = birth.DATE.search(old_parts[0])
            if old_born and "".join(old_born[0].split()) in "".join(body.split()):
                errors.append("EXACT_OLD_BIRTH_DATE_REMAINS_OUTSIDE_THE_QUARANTINED_FIELDS")
            if re.search(r"[12][0-9]{3}년", new_parts[0]):
                errors.append("LEAD_BIRTH_YEAR_REMAINS")
            if len(new_parts) == 2:
                right = new_parts[1].strip()
                death = birth.DATE.fullmatch(right)
                death_categories = re.findall(r"(?m)^[ \t]*([12][0-9]{3})년[ _\t]+사망[ \t]*$", body)
                if death and death_categories and any(value != death["year"] for value in death_categories):
                    errors.append("DEATH_YEAR_CONFLICT_REMAINS")
                if right and re.search(r"(?m)^[ \t]*살아있는[ _\t]+사람[ \t]*$", body):
                    errors.append("LIVING_CATEGORY_WITH_EXPLICIT_LIFE_END")
            if len(old_parts) == 2:
                old_death = birth.DATE.fullmatch(old_parts[1].strip())
                old_categories = re.findall(r"(?m)^[ \t]*([12][0-9]{3})년[ _\t]+사망[ \t]*$", original)
                if old_death and old_categories and any(value != old_death["year"] for value in old_categories):
                    if len(new_parts) == 2 and birth.DATE.fullmatch(new_parts[1].strip()):
                        errors.append("CONFLICTING_OLD_DEATH_YEAR_STILL_SELECTED_IN_LEAD")
                    if re.search(r"(?m)^[ \t]*[12][0-9]{3}년[ _\t]+사망[ \t]*$", body):
                        errors.append("CONFLICTING_OLD_DEATH_CATEGORY_STILL_SELECTED")
        if re.search(r"(?m)^[ \t]*[12][0-9]{3}년[ _\t]+출생[ \t]*$", body):
            errors.append("BIRTH_CATEGORY_REMAINS")
        record = dict(id=row["id"], original_text_sha256=row["original"]["sha256"], body=row["body"],
            clean_text_sha256=row["clean_text_sha256"], review=row["review"], guards=flags,
            introduced_numeric_occurrences=dict(introduced), errors=sorted(set(errors)))
        checked.append(record)
        if errors:
            failures.append(record)
    inv.require(snapshot["coverage"][group]["awaiting_review"] == 0, "not all source reviews saved")
    report = dict(status="ALL753_POST_REVIEW_BODY_AUDIT_CLEAR" if not failures else "POST_REVIEW_COUNTEREXAMPLES_REQUIRE_REPAIR_NOT_ADMISSION",
        source_ids=753, checked=len(checked), decisions=dict(counts), failures=failures,
        accepted_exact_guard_exceptions=accepted_exceptions, records=checked,
        input_pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in [source_path,manifest_path,exception_path,Path(__file__)]},
        cache_admitted=0, goal_complete=False, training_authorized=False, seconds=time.monotonic() - started)
    inv.write_json(output, report)
    print(json.dumps(dict(status=report["status"], checked=len(checked), failures=len(failures),
        failure_ids=[row["id"] for row in failures], exact_guard_exceptions=len(accepted_exceptions), seconds=report["seconds"])))
    if failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
