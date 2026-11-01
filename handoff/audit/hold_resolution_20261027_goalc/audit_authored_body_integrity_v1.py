"""Read back every current curated/legacy body; do not approve or admit it."""
from collections import Counter
from pathlib import Path
import json
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v11 as policy
from scripts import p106b_hold_resolution_literal_guard_v1 as literal
from scripts.p106b_hold_resolution_refinement import ordered_deletion

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
out = AUDIT / "authored_body_integrity_v1.json"
inv.require(not out.exists(), "new immutable integrity receipt required")
curated_path = AUDIT / "authored_candidates_snapshot_v5.json"
legacy_path = max((AUDIT / "legacy_progress_v10").glob("*.json"))
overrides = {row["id"]: row for row in inv.cache.read(AUDIT / "ROOT_CURATED_OVERRIDES_V1.json")["rows"]}
legacy_sources = {row["id"]: row for row in inv.cache.read(BASE / "legacy_span_review_v2/manifest.json")["rows"]}
cases = literal.load_registry()
counter_text = {
    "expanded_train:24865": ("historical_review", "expanded_train_24865_v2.txt"),
    "expanded_train:9352": ("context_controls", "expanded_train_9352_v3.txt"),
    "expanded_train:8455": ("context_hangul", "expanded_train_8455_v2.txt"),
}
numeric = re.compile(r"(?<![A-Za-z0-9_])[-+−]?[0-9]+(?:[.,][0-9]+)*(?:%|°[CF])?")
lexical = re.compile(r"[A-Za-z0-9_]+|[가-힣]+|[\u3400-\u9fff]+")
records, counts = [], Counter()
started = time.monotonic()


def inspect(ident, cohort, decision, source, source_sha, body, body_sha, evidence):
    record = dict(id=ident, cohort=cohort, decision=decision, original_text_sha256=source_sha,
                  source=str(source.relative_to(ROOT)), evidence=evidence, root_approved=False)
    if decision in {"EXCLUDE", "NEEDS_ROOT"}:
        record["status"] = "TEXT_DECISION_NOT_BODY_OR_CACHE_APPROVAL"
        counts.update([decision])
        records.append(record)
        return
    if body is None:
        record["status"] = "NO_MATERIALIZED_BODY_NOT_ADMITTED"
        counts.update(["NO_BODY"])
        records.append(record)
        return
    raw_payload, clean_payload = source.read_bytes(), body.read_bytes()
    inv.require(inv.file_sha(source) == source_sha, "authored source pin changed")
    inv.require(inv.file_sha(body) == body_sha, "authored body pin changed")
    raw, clean = raw_payload.decode("utf-8"), clean_payload.decode("utf-8")
    unicode_guard = policy.unicode_examples_preserved(raw, clean)
    code_guard = policy.code_preserved(raw, clean)
    exact_reviewed_literal = False
    if not code_guard:
        exact_reviewed_literal = literal.exact_pair_preserved(raw, clean, ident, cases)
    value = policy.propose(dict(id=ident, text=clean, complete_eos=True, valid_utf8=True))
    introduced_numeric = dict(Counter(numeric.findall(clean)) - Counter(numeric.findall(raw)))
    introduced_lexical = dict(Counter(lexical.findall(clean)) - Counter(lexical.findall(raw)))
    memo_added = bool(inv.corpus.MEMOS.search(clean) and not inv.corpus.MEMOS.search(raw))
    record.update(status="BODY_READBACK_NOT_SEMANTIC_OR_CACHE_APPROVAL", body=str(body.relative_to(ROOT)),
                  clean_text_sha256=body_sha, original_characters=len(raw), clean_characters=len(clean),
                  exact_source_preserved=raw_payload == clean_payload,
                  ordered_nonwhitespace_deletion_only=ordered_deletion(raw, clean),
                  code_guard=code_guard, exact_reviewed_literal_exception=exact_reviewed_literal,
                  unicode_guard=unicode_guard, introduced_numeric_occurrences=introduced_numeric,
                  introduced_lexical_occurrences=introduced_lexical, newly_added_editor_memo=memo_added,
                  post_body_policy_decision=value["decision"], post_body_policy_reasons=value["reasons"],
                  post_body_policy_would_edit=value.get("candidate", value["text"]) != clean)
    counts.update(["BODY"])
    counts["CODE_OR_UNICODE_FLAG"] += not (unicode_guard and (code_guard or exact_reviewed_literal))
    counts["NUMERIC_READBACK_FLAG"] += bool(introduced_numeric)
    counts["MEMO_FLAG"] += memo_added
    counts["POST_POLICY_PENDING"] += value["decision"] == "PENDING"
    records.append(record)


for row in inv.cache.read(curated_path)["rows"]:
    chosen = dict(row, **{key: value for key, value in overrides.get(row["id"], {}).items() if key != "id"})
    decision = chosen["decision"]
    body = ROOT / chosen["body"] if chosen.get("body") else ROOT / chosen["source"] if decision == "KEEP" else None
    body_sha = chosen.get("clean_text_sha256") or chosen["original_text_sha256"] if body else None
    inspect(chosen["id"], "CURATED340", decision, ROOT / chosen["source"], chosen["original_text_sha256"], body, body_sha,
            dict(review=chosen.get("review"), root_override=row["id"] in overrides))

for row in inv.cache.read(legacy_path)["records"]:
    ident = row["id"]
    original = legacy_sources[ident]["paths"]["original"]
    body = ROOT / row["body"] if row.get("body") else None
    body_sha = row.get("clean_text_sha256")
    decision = row["status"]
    evidence = dict(review=row["review"], review_sha256=row["review_sha256"], snapshot=str(legacy_path.relative_to(ROOT)))
    if ident in counter_text:
        role, filename = counter_text[ident]
        directory = BASE / "agents" / role / "strict_failure_text_repair_v1"
        body = directory / filename
        body_sha = inv.file_sha(body)
        decision = "EDIT_TEXT"
        evidence.update(independent_text_repair=dict(path=str((directory / "review.md").relative_to(ROOT)),
                                                      sha256=inv.file_sha(directory / "review.md")))
    # This later explicit correction restores normal same-paragraph pronouns.
    if ident == "expanded_train:16838":
        directory = BASE / "agents/legacy_review/legacy_span_review_v2"
        body = directory / "expanded_train_16838_v3.txt"
        body_sha, decision = inv.file_sha(body), "EDIT_TEXT"
        evidence.update(later_same_paragraph_correction=dict(path=str((directory / "review_003_v4.md").relative_to(ROOT)),
                                                            sha256=inv.file_sha(directory / "review_003_v4.md")))
    inspect(ident, "LEGACY1770", decision, ROOT / original["path"], original["sha256"], body, body_sha, evidence)

result = dict(status="FULL_CURATED_AND_LEGACY_BODY_READBACK_NOT_ADMISSION", records=records, counts=dict(counts),
              proposal_records=len(records), unique_original_bodies=len({r["original_text_sha256"] for r in records}),
              pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in [curated_path, legacy_path, Path(__file__)]},
              seconds=time.monotonic() - started, root_adopted=0, goal_complete=False, training_authorized=False)
inv.require(len(json.dumps(result, ensure_ascii=False).encode("utf-8")) < 20_000_000, "integrity receipt needs sharding")
inv.write_json(out, result)
print(json.dumps(dict(records=len(records), unique_original_bodies=result["unique_original_bodies"],
                      counts=result["counts"], seconds=result["seconds"]), ensure_ascii=False))
