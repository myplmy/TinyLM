"""Create a new selector with missing newer evidence and purpose conflicts closed."""
from pathlib import Path

base = Path(__file__).resolve().parent
source = (base / "prepare_authored_root_selection_v5.py").read_text(encoding="utf-8")


def change(before, after):
    global source
    assert source.count(before) == 1, before[:100]
    source = source.replace(before, after)


change('"ROOT_AUTHORED_SELECTIONS_V5.json"', '"ROOT_AUTHORED_SELECTIONS_V6.json"')
change('"reviewed_selection_plan_v8.json"', '"reviewed_selection_plan_v9.json"')
change('"ROOT_AUTHORED_SELECTION_CONTRACT_V3.md"', '"ROOT_AUTHORED_SELECTION_CONTRACT_V4.md"')
change('order = ["policy_v20_literal_counter_v1",', 'order = ["root_selected_signal_counter_v2", "policy_v21_literal_counter_v1", "policy_v20_literal_counter_v1",')
change('rows, counts, pending = [], Counter(), []', '''required_paths = [inv.BASE / group / "manifest.json" for group in ["root_selected_signal_counter_v2", "policy_v21_literal_counter_v1"]]
required = {path.parent.name: {row["id"] for row in inv.cache.read(path)["rows"]} for path in required_paths}
rows, counts, pending = [], Counter(), []''')
change('''    if source["root_approved"]:
        chosen = dict(source["selected"])''', '''    fresh_choices = [dict(proposal) for option in source["body_options"] for proposal in option["proposals"]]
    fresh_choices += [dict(proposal) for proposal in source["text_only_decisions"]]
    needed = [group for group, ids in required.items() if ident in ids]
    groups_missing = [group for group in needed if not any(choice["cohort"] == group for choice in fresh_choices)]
    fresh = [choice for choice in fresh_choices if choice["cohort"] in needed]
    unresolved_fresh = any(choice["decision"] == "NEEDS_ROOT" for choice in fresh)
    fresh_identities = {(choice["decision"] in {"EXCLUDE"}, choice.get("clean_text_sha256")) for choice in fresh}
    if groups_missing or unresolved_fresh or len(fresh_identities) > 1:
        pending.append(dict(base, status="NEW_ASSIGNED_REVIEW_MISSING_FAILED_OR_CONFLICTING_REQUIRES_ROOT",
                            missing_cohorts=groups_missing, new_proposals=fresh))
        counts.update(["UNRESOLVED_ROOT_ADJUDICATION"])
        continue
    if source["root_approved"] and fresh:
        chosen_root = source["selected"]
        root_identity = (chosen_root["decision"] == "EXCLUDE", chosen_root.get("clean_text_sha256"))
        if fresh_identities != {root_identity}:
            pending.append(dict(base, status="NEW_REVIEW_DIFFERS_FROM_EXACT_ROOT_REQUIRES_EXPLICIT_SUPERSESSION",
                                existing_exact_root=chosen_root, new_proposals=fresh))
            counts.update(["UNRESOLVED_ROOT_ADJUDICATION"])
            continue
    if source["root_approved"]:
        chosen = dict(source["selected"])''')
change('''    explicit = specific.get(ident)''', '''    explicit = specific.get(ident) if not needed else None''')
change('''for path in [plan_path, core_path, curated_path, contract_path, Path(__file__)]''',
       '''for path in [plan_path, core_path, curated_path, contract_path, *required_paths, Path(__file__)]''')
with (base / "prepare_authored_root_selection_v6.py").open("x", encoding="utf-8") as out:
    out.write(source)
print("new selection6 prepared; execution is separate")
