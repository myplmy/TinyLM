"""Reuse the full v20 diagnostic census for the independently verified v25."""
from pathlib import Path

AUDIT = Path(__file__).resolve().parent
source = (AUDIT / 'profile_unreviewed_v20_candidates_v1.py').read_text(encoding='utf-8')
source = source.replace('v20', 'v25').replace('V20', 'V25')
before = '''known_paths = [AUDIT / "reviewed_selection_plan_v9.json", BASE / "root_selected_signal_counter_v2/manifest.json",
               BASE / "policy_v21_literal_counter_v1/manifest.json"]'''
assert source.count(before) == 1
source = source.replace(before, '''receipt_path = AUDIT / "DRAFT_V25_EXECUTION_RECEIPT_V2.json"
receipt = inv.cache.read(receipt_path)
inv.require(receipt["completed_artifact"]["sha256"] == inv.file_sha(report_path)
            and receipt["original_process_exit_code"] == 0,
            "v25 actual producer and independent artifact verification are required")
pins[str(receipt_path.relative_to(ROOT))] = inv.file_sha(receipt_path)
known_paths = [AUDIT / "reviewed_selection_plan_v16.json",
               BASE / "root_selected_lexical_counter_v1/manifest.json"]''')
output = AUDIT / 'profile_unreviewed_v25_candidates_v1.py'
compile(source, str(output), 'exec')
with output.open('x', encoding='utf-8') as stream:
    stream.write(source)
print('Reused diagnostic census: all v25 pending, restricted metadata only, current3116 assignments excluded from fresh packets.')
