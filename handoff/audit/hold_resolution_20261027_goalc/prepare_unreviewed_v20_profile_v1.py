"""Reuse the full census while selecting new source IDs for every stratum."""
from pathlib import Path

base = Path(__file__).resolve().parent
source = (base / "profile_remaining_v19_candidates_v1.py").read_text(encoding="utf-8")
source = source.replace("v19", "v20").replace("V19", "V20")
assert source.count('"remaining_candidate_profile_v20_v1"') == 1
source = source.replace('"remaining_candidate_profile_v20_v1"', '"remaining_unreviewed_candidate_profile_v20_v1"')
needle = 'counts, reasons, fields, tails, repeat_shapes = (Counter() for _ in range(5))'
assert source.count(needle) == 1
source = source.replace(needle, '''known_paths = [AUDIT / "reviewed_selection_plan_v9.json", BASE / "root_selected_signal_counter_v2/manifest.json",
               BASE / "policy_v21_literal_counter_v1/manifest.json"]
covered_ids = set()
for path in known_paths:
    value = inv.cache.read(path)
    covered_ids.update(row["id"] for row in value.get("records", value.get("rows", [])))
    pins[str(path.relative_to(ROOT))] = inv.file_sha(path)
counts, reasons, fields, tails, repeat_shapes = (Counter() for _ in range(5))''')
needle = '    rank = (row["original_text_sha256"], row["id"])'
assert source.count(needle) == 1
source = source.replace(needle, '''    if row["id"] in covered_ids:
        return
    rank = (row["original_text_sha256"], row["id"])''')
needle = '    counts.update(unique_pending=1, occurrences=row["occurrences"])'
assert source.count(needle) == 1
source = source.replace(needle, needle + '''
    if row["id"] in covered_ids:
        counts.update(previously_assigned_unique_sources=1)''')
needle = '              source_reasons=dict(reasons), features=dict(features), field_literals=dict(fields),'
assert source.count(needle) == 1
source = source.replace(needle, '''              source_reasons=dict(reasons), features=dict(features), field_literals=dict(fields),
              packet_selection_scope="EVERY_STRATUM_EXCLUDING_PREVIOUSLY_ASSIGNED_IDS_NOT_A_GLOBAL_WORK_CAP",
              previously_assigned_ids=len(covered_ids),
              strata_without_unassigned_examples=sorted(set(features) - set(selected)),''')
with (base / "profile_unreviewed_v20_candidates_v1.py").open("x", encoding="utf-8") as out:
    out.write(source)
print("new full v20 census prepared, packets exclude all previously assigned IDs")
