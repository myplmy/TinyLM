"""Use current guards on actual selected bodies; keep literal losses visible."""
from pathlib import Path

AUDIT = Path(__file__).resolve().parent
text = (AUDIT / "audit_root_selected_bodies_v2.py").read_text(encoding="utf-8")
for before, after in [
    ("p106b_hold_resolution_policy_v19", "p106b_hold_resolution_policy_v21"),
    ("p106b_hold_resolution_literal_guard_v2", "p106b_hold_resolution_literal_guard_v3"),
    ("root_selected_body_literals_v2.json", "root_selected_body_literals_v3.json"),
    ("ROOT_AUTHORED_SELECTIONS_V5.json", "ROOT_AUTHORED_SELECTIONS_V7.json"),
]:
    assert text.count(before) == 1
    text = text.replace(before, after)
anchor = "from scripts import p106b_hold_resolution_literal_guard_v3 as literal"
text = text.replace(anchor, anchor + chr(10) + "from scripts import p106b_hold_resolution_source_relations_v1 as relations")
anchor = "            plain = "
assert text.count(anchor) == 1
text = text.replace(anchor, '''            new_pairs = relations.ungrounded_new_link_pairs(raw, clean)
            missing_pairs = relations.missing_source_link_pairs(raw, clean)
            call_losses = policy.proven_source_call_losses(raw, clean)
''' + anchor)
anchor = '                introduced_numeric_occurrences=added_numbers,'
assert text.count(anchor) == 1
text = text.replace(anchor, '''                source_function_parentheses_losses=call_losses,
                ungrounded_literal_link_pairs=[dict(target=pair[0], display=pair[1], count=count) for pair, count in sorted(new_pairs.items())],
                missing_source_literal_link_pairs=[dict(target=pair[0], display=pair[1], count=count) for pair, count in sorted(missing_pairs.items())],
                literal_link_diagnostics_are_not_automatic_semantic_verdicts=True,
''' + anchor)
anchor = '            counts["code_or_unicode_flags"] +='
assert text.count(anchor) == 1
text = text.replace(anchor, '''            counts["source_function_parentheses_loss_flags"] += bool(call_losses)
            counts["ungrounded_literal_link_pair_flags"] += bool(new_pairs)
            counts["missing_source_literal_link_pair_flags"] += bool(missing_pairs)
''' + anchor)
path = AUDIT / "audit_root_selected_bodies_v3.py"
compile(text, str(path), "exec")
with path.open("x", encoding="utf-8") as stream:
    stream.write(text)
print("prepared actual-body audit3, not run")
