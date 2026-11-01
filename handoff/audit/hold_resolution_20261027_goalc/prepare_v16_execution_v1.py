"""Pin the reviewed CPU draft execution without approving any cache body."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_revision_v16 as revision
from scripts import p106b_hold_resolution_policy_v16 as policy

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
OUT = AUDIT / "V16_DRAFT_PREFLIGHT_V1.json"
inv.require(not OUT.exists(), "preflight receipt must be new")
old_path = BASE / "draft_proposals_v14/complete.json"
old = inv.cache.read(old_path)
old_pins = old["lineage"]["source_code_sha256"]
inv.require(len(old_pins) == 30, "v14 source inventory differs")
for name, expected in old_pins.items():
    inv.require(inv.file_sha(ROOT / name) == expected, "frozen production source changed: " + name)
code_pins = {name: inv.file_sha(ROOT / name) for name in revision.CODE}
inv.require(len(revision.CODE) == len(code_pins) == 34, "new runtime source inventory differs")
for name in revision.CODE:
    compile((ROOT / name).read_bytes(), name, "exec")
manifest_path = BASE / "policy_v16_literal_counter_v2/manifest.json"
manifest = inv.cache.read(manifest_path)
inv.require(len(manifest["rows"]) == 1, "changed source counter differs")
row = manifest["rows"][0]
raw_path, clean_path = (ROOT / row[key]["path"] for key in ["original", "candidate"])
for key, path in [("original", raw_path), ("candidate", clean_path)]:
    inv.require(inv.file_sha(path) == row[key]["sha256"], "independent counter pair changed")
raw, clean = raw_path.read_text(encoding="utf-8"), clean_path.read_text(encoding="utf-8")
value = policy.propose(dict(id=row["id"], text=raw, complete_eos=True, valid_utf8=True))
inv.require(value["decision"] in {"KEEP", "EDIT"} and inv.sha(value["text"]) == row["candidate"]["sha256"],
            "current policy differs from independently reviewed candidate")
review = BASE / "agents/context_latin/policy_v16_literal_counter_v2/review.md"
reviewed = [line for line in review.read_text(encoding="utf-8").splitlines()
            if line.startswith("|") and "41725" in line]
inv.require(len(reviewed) == 1 and "ACCEPT_CANDIDATE" in reviewed[0], "independent source review not accepted")
probe_path = AUDIT / "policy_v16_purpose_probe_v2.json"
probe = inv.cache.read(probe_path)
terminals = [row for row in probe["rows"] if row["decision"] in {"KEEP", "EDIT"}]
inv.require(all(row[key] for row in terminals for key in
                ["code_guard", "unicode_guard", "semantic_style_guard", "ordered_deletion"]), "purpose preservation flag")
for name, expected in probe["source_code_pins"].items():
    inv.require(inv.file_sha(ROOT / name) == expected, "purpose probe source changed")
result = dict(status="CPU_DRAFT_PREFLIGHT_NOT_CACHE_ADMISSION", baseline=str(old_path.relative_to(ROOT)),
              baseline_sha256=inv.file_sha(old_path), previous_30_sources_unchanged=True,
              source_code_sha256=code_pins, syntax_compiled_sources=len(code_pins),
              changed_purpose_counter=dict(id=row["id"], candidate=row["candidate"],
                                           independent_review=str(review.relative_to(ROOT)), review_sha256=inv.file_sha(review)),
              probe_sha256=inv.file_sha(probe_path), purpose_rows=len(probe["rows"]),
              full_scope_unique_sources=297539, full_scope_occurrences=460695,
              automatic_partial_sources_require_separate_independent_review=194,
              automatic_partial_occurrences=331, cache_admitted=0, goal_complete=False,
              training_authorized=False, gpu_or_model_execution=False,
              producer_sha256=inv.file_sha(Path(__file__)))
inv.write_json(OUT, result)
print(json.dumps(dict(status=result["status"], code_sources=len(code_pins), previous_sources_unchanged=True,
                      purpose_rows=len(probe["rows"]), independent_counter=row["id"]), ensure_ascii=False))
