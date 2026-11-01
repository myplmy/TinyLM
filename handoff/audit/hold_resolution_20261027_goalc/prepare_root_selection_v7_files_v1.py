"""Keep all assigned source IDs visible, including reviews not yet saved."""
from pathlib import Path

AUDIT = Path(__file__).resolve().parent
source = (AUDIT / "prepare_reviewed_selection_plan_v9.py").read_text(encoding="utf-8")
source = source.replace("reviewed_selection_plan_v9.json", "reviewed_selection_plan_v10.json")
source = source.replace("supplemental_candidates_snapshot_v29.json", "supplemental_candidates_snapshot_v31.json")
anchor = "root_decisions = defaultdict(list)"
assert source.count(anchor) == 1
source = source.replace(anchor, '''assigned_paths = [BASE / group / "manifest.json" for group in [
    "root_selected_signal_counter_v2", "policy_v21_literal_counter_v1", "remaining_unreviewed_context_v20_v1"]]
saved_pairs = {(row["cohort"], row["id"]) for row in supp["records"]}
assigned_missing_review_placeholders = []
for assigned_path in assigned_paths:
    assigned_manifest = inv.cache.read(assigned_path)
    for assigned in assigned_manifest["rows"]:
        group = assigned_path.parent.name
        if (group, assigned["id"]) in saved_pairs:
            continue
        assigned_source = dict(assigned, **assigned.get("paths", {}))["original"]
        placeholder = dict(id=assigned["id"], cohort=group, decision="NEEDS_ROOT", original=assigned_source,
            status="ASSIGNED_REVIEW_NOT_SAVED_REQUIRES_REPAIR", body=None, clean_text_sha256=None,
            reason="배정된 정확 원문의 저장 검토행이 없어 옛 후보로 우회할 수 없다.",
            root_approved=False, cache_admitted=False)
        proposals[assigned["id"]].append(placeholder)
        assigned_missing_review_placeholders.append(dict(id=assigned["id"], cohort=group,
            source=assigned_source, assigned_manifest=str(assigned_path.relative_to(ROOT))))

''' + anchor)
source = source.replace("paths = [core_path, supp_path, *root_paths, Path(__file__)]",
                        "paths = [core_path, supp_path, *root_paths, *assigned_paths, Path(__file__)]")
anchor = '              source_ids=len(records), proposal_records=sum(map(len, proposals.values())),\n'
assert source.count(anchor) == 1
source = source.replace(anchor, anchor + '''              assigned_missing_review_placeholders=assigned_missing_review_placeholders,
              assigned_missing_review_count=len(assigned_missing_review_placeholders),
''')
output = AUDIT / "prepare_reviewed_selection_plan_v10.py"
compile(source, str(output), "exec")
with output.open("x", encoding="utf-8") as stream:
    stream.write(source)

selector = (AUDIT / "prepare_authored_root_selection_v6.py").read_text(encoding="utf-8")
for before, after in [
    ("ROOT_AUTHORED_SELECTIONS_V6.json", "ROOT_AUTHORED_SELECTIONS_V7.json"),
    ("reviewed_selection_plan_v9.json", "reviewed_selection_plan_v10.json"),
    ("ROOT_AUTHORED_SELECTION_CONTRACT_V4.md", "ROOT_AUTHORED_SELECTION_CONTRACT_V5.md"),
    ('order = ["root_selected_signal_counter_v2"', 'order = ["remaining_unreviewed_context_v20_v1", "root_selected_signal_counter_v2"'),
    ('["root_selected_signal_counter_v2", "policy_v21_literal_counter_v1"]',
     '["root_selected_signal_counter_v2", "policy_v21_literal_counter_v1", "remaining_unreviewed_context_v20_v1"]'),
]:
    assert selector.count(before) == 1
    selector = selector.replace(before, after)
output = AUDIT / "prepare_authored_root_selection_v7.py"
compile(selector, str(output), "exec")
with output.open("x", encoding="utf-8") as stream:
    stream.write(selector)
print("prepared selection plan10 and intended body selection7; neither has run")
