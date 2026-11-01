"""Inspect actual reviewed bodies without granting cache or semantic approval.

Existing code/Unicode/style guards are reused. Restricted parent content is
never inspected: only an explicitly pinned source view is eligible there.
"""
from collections import Counter
from pathlib import Path
import json
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v16 as policy
from scripts import p106b_hold_resolution_literal_guard_v2 as literal

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
OUT = AUDIT / "reviewed_body_literals_v1.json"
inv.require(not OUT.exists(), "new body inspection receipt required")
plan_path = AUDIT / "reviewed_selection_plan_v3.json"
plan = inv.cache.read(plan_path)
restricted = {"expanded_train:14760", "expanded_train:756966", "expanded_train:1216576",
              "expanded_train:1250821", "expanded_train:15695", "expanded_train:20624"}
clinical_path = BASE / "clinical_source_view_v1/manifest.json"
clinical = inv.cache.read(clinical_path)
view_paths = [BASE / "limited_biology_views_v2/manifest.json"]
allowed_views = {(clinical["id"], clinical["view"]["path"], clinical["view"]["sha256"])}
for path in view_paths:
    for row in inv.cache.read(path)["rows"]:
        allowed_views.add((row["id"], row["original"]["path"], row["original"]["sha256"]))
cases = literal.load_registry()
numeric = re.compile(r"(?<![A-Za-z0-9_])[-+−]?[0-9]+(?:[.,][0-9]+)*(?:%|°[CF])?")
lexical = re.compile(r"[A-Za-z0-9_]+|[가-힣]+|[\u3400-\u9fff]+")
memo = inv.corpus.MEMOS
texts, records, counts, errors = {}, [], Counter(), []
started = time.monotonic()


def read_pin(path, key):
    if path not in texts:
        payload = (ROOT / path).read_bytes()
        inv.require(inv.sha(payload.decode("utf-8")) == key and inv.file_sha(ROOT / path) == key,
                    "source/body pin changed")
        texts[path] = payload.decode("utf-8"), key
    value, actual = texts[path]
    inv.require(actual == key, "one path is bound to different source pins")
    return value


for source in plan["records"]:
    ident = source["id"]
    if source["root_approved"]:
        chosen = source["selected"]
        if not chosen.get("body"):
            counts.update(root_text_only_decisions=1)
            continue
        choices = [dict(body=chosen["body"], clean_text_sha256=chosen["clean_text_sha256"],
                        compare_source=chosen.get("compare_source") or
                            dict(path=chosen.get("source") or source["original_paths"][0], sha256=source["original_text_sha256"]),
                        cohort="EXACT_ROOT_SELECTION", review=chosen.get("review_inputs"), root_approved=True)]
    else:
        choices = []
        for option in source["body_options"]:
            proofs = option["proposals"]
            if ident in restricted:
                proofs = [row for row in proofs if row.get("compare_source") and
                          (ident, row["compare_source"]["path"], row["compare_source"]["sha256"]) in allowed_views]
            if not proofs:
                counts.update(restricted_parent_body_metadata_only=1)
                continue
            proof = proofs[0]
            choices.append(dict(proof, compare_source=proof.get("compare_source") or proof["original"], root_approved=False))
    for choice in choices:
        compare = choice["compare_source"]
        if ident in restricted:
            inv.require((ident, compare["path"], compare["sha256"]) in allowed_views,
                        "restricted source escaped its exact limited view")
        record = dict(id=ident, cohort=choice["cohort"], compare_source=compare,
                      original_text_sha256=source["original_text_sha256"], body=choice["body"],
                      clean_text_sha256=choice["clean_text_sha256"], review=choice.get("review"),
                      exact_root_selected=choice["root_approved"], cache_admitted=False)
        try:
            raw = read_pin(compare["path"], compare["sha256"])
            clean = read_pin(choice["body"], choice["clean_text_sha256"])
            code_guard = policy.code_preserved(raw, clean)
            exact_literal = False if code_guard else literal.exact_pair_preserved(raw, clean, ident, cases)
            added_numbers = dict(Counter(numeric.findall(clean)) - Counter(numeric.findall(raw)))
            added_words = Counter(lexical.findall(clean)) - Counter(lexical.findall(raw))
            added_memos = Counter(match[0] for match in memo.finditer(clean)) - Counter(match[0] for match in memo.finditer(raw))
            fields = Counter(match[0] for match in inv.cache.MISSING_FIELD.finditer(clean))
            record.update(status="ACTUAL_BODY_LITERAL_READBACK_NOT_SEMANTIC_APPROVAL", code_guard=code_guard,
                exact_reviewed_literal_exception=exact_literal, unicode_guard=policy.unicode_examples_preserved(raw, clean),
                semantic_style_guard=policy.semantic_style_preserved(raw, clean),
                ordered_nonwhitespace_deletion_only=policy.ordered_deletion(raw, clean),
                introduced_numeric_occurrences=added_numbers,
                introduced_lexical_occurrences=dict(added_words.most_common(60)),
                introduced_lexical_distinct=len(added_words), introduced_lexical_total=sum(added_words.values()),
                introduced_editor_memo_occurrences=dict(added_memos), literal_hole_signals=policy.literal_holes(clean),
                remaining_field_literal_signals=dict(fields), source_characters=len(raw), clean_characters=len(clean))
            counts.update(bodies=1)
            counts["code_or_unicode_flags"] += not (record["unicode_guard"] and (code_guard or exact_literal))
            counts["style_flags"] += not record["semantic_style_guard"]
            counts["numeric_flags"] += bool(added_numbers)
            counts["lexical_flags"] += bool(added_words)
            counts["editor_memo_flags"] += bool(added_memos)
            counts["literal_hole_signals"] += bool(record["literal_hole_signals"])
            counts["remaining_field_literal_signals"] += bool(fields)
        except (ValueError, OSError, UnicodeError) as error:
            record.update(status="BODY_NOT_VALIDATED", error=str(error))
            errors.append(dict(id=ident, body=choice["body"], error=str(error)))
        records.append(record)

paths = [plan_path, clinical_path, *view_paths, Path(__file__)]
result = dict(status="ACTUAL_REVIEWED_BODY_LITERAL_DIAGNOSTICS_NOT_ADMISSION", records=records, counts=dict(counts), errors=errors,
    source_ids=len({row["id"] for row in records}), pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in paths},
    seconds=time.monotonic() - started, restricted_parent_full_content_opened=False,
    cache_admitted=0, goal_complete=False, training_authorized=False)
inv.require(len(json.dumps(result, ensure_ascii=False).encode("utf-8")) < 20_000_000, "readback receipt needs shards")
inv.write_json(OUT, result)
print(json.dumps(dict(records=len(records), source_ids=result["source_ids"], counts=result["counts"],
                      errors=len(errors), seconds=result["seconds"]), ensure_ascii=False))
