"""Preserve a failed test fixture and prepare immutable follow-up producers."""
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parents[3]
audit = Path(__file__).resolve().parent
test = root / "scripts/test_p106b_hold_resolution_policy_v23.py"
failed = test.read_bytes()
archive = audit / "test_policy_v23_v1_failed_source.py"
with archive.open("xb") as stream:
    stream.write(failed)
receipt = dict(test_exit_code=1, tests=351, errors=1,
    cause="New fixture omitted required valid_utf8 field; no production failure was observed.",
    failed_test_sha256=hashlib.sha256(failed).hexdigest().upper(),
    failed_log_sha256=hashlib.sha256((audit / "test_policy_v23_v1.log").read_bytes()).hexdigest().upper(),
    production_changed=False)
with (audit / "POLICY_V23_INITIAL_TEST_FIXTURE_FAILURE_V1.json").open("x", encoding="utf-8") as stream:
    json.dump(receipt, stream, ensure_ascii=False, indent=2)
    stream.write("\n")
text = failed.decode("utf-8")
old = "text=text, complete_eos=True))"
assert text.count(old) == 1
test.write_text(text.replace(old, "text=text, complete_eos=True, valid_utf8=True))"), encoding="utf-8")
source = (audit / "collect_supplemental_candidates_v33.py").read_text(encoding="utf-8")
assert source.count("supplemental_candidates_snapshot_v33.json") == 1
with (audit / "collect_supplemental_candidates_v34.py").open("x", encoding="utf-8") as stream:
    stream.write(source.replace("supplemental_candidates_snapshot_v33.json", "supplemental_candidates_snapshot_v34.json"))
source = (audit / "prepare_reviewed_selection_plan_v10.py").read_text(encoding="utf-8")
source = source.replace("reviewed_selection_plan_v10.json", "reviewed_selection_plan_v11.json").replace(
    "supplemental_candidates_snapshot_v31.json", "supplemental_candidates_snapshot_v34.json")
old = '"root_selected_signal_counter_v2", "policy_v21_literal_counter_v1", "remaining_unreviewed_context_v20_v1"]]'
assert source.count(old) == 1
source = source.replace(old, '"root_selected_signal_counter_v2", "policy_v21_literal_counter_v1", "remaining_unreviewed_context_v20_v1", "root_selected_literal_counter_v3", "policy_v22_literal_counter_v1"]]')
with (audit / "prepare_reviewed_selection_plan_v11.py").open("x", encoding="utf-8") as stream:
    stream.write(source)
source = (audit / "probe_policy_v22_v1.py").read_text(encoding="utf-8")
source = source.replace("policy_v22 as policy", "policy_v23 as policy").replace(
    "revision_v22 as revision", "revision_v23 as revision").replace(
    "policy_v22_purpose_probe_v1.json", "policy_v23_purpose_probe_v1.json")
source = source.replace("from scripts.p106b_hold_resolution_refinement import ordered_deletion",
    "from scripts.p106b_hold_resolution_refinement import ordered_deletion\nfrom scripts import p106b_hold_resolution_policy_v21 as verified_baseline")
source = source.replace("baseline = policy.previous.propose(", "baseline = verified_baseline.propose(")
with (audit / "probe_policy_v23_v1.py").open("x", encoding="utf-8") as stream:
    stream.write(source)
print(json.dumps(dict(failed_fixture_preserved=True, collector_version=34, plan_version=11, probe_version=23)))
