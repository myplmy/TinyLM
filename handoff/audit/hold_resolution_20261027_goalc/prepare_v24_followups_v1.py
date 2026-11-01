"""Prepare immutable regression and all-pair probes for the corrected scope."""
from pathlib import Path

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
old = (ROOT / "scripts/test_p106b_hold_resolution_policy_v23.py").read_text(encoding="utf-8")
old = old.replace("policy_v23 as policy", "policy_v24 as policy")
anchor = 'if __name__ == "__main__":'
assert old.count(anchor) == 1
addition = '''
class AliasScopeAndEnglishRoles(unittest.TestCase):
    def test_single_named_definition_retains_its_narrow_release(self):
        raw = "힐베르트 공간()은 완비 내적 공간이다." + chr(10)
        self.assertFalse(policy.unchecked_body_after_named_alias(raw))
        value = policy.propose(dict(id="expanded_train:987654321", text=raw, complete_eos=True, valid_utf8=True))
        self.assertEqual(value["decision"], "EDIT")

    def test_a_named_definition_does_not_certify_any_following_formal_prose(self):
        raw = "힐베르트 공간()은 완비 내적 공간이다." + chr(10) + "정의와 증명은 다음과 같다."
        value = policy.propose(dict(id="expanded_train:987654321", text=raw, complete_eos=True, valid_utf8=True))
        self.assertEqual(value["decision"], "PENDING")
        self.assertIn(policy.ALIAS_BODY, value["reasons"])

    def test_complete_following_prose_still_requires_the_scoped_review(self):
        raw = "힐베르트 공간()은 완비 내적 공간이다." + chr(10) + "이는 독립적으로 완결된 설명이다."
        self.assertTrue(policy.unchecked_body_after_named_alias(raw))

    def test_actual_missing_english_data_and_coefficients_are_observed(self):
        raw = "Suppose that the data set consists of the points with ." + chr(10)
        raw += "Suppose it is quadratic, where , and are not yet known."
        self.assertEqual(len([r for r in policy.observed_formal_holes(raw) if r["reason"] == policy.ENGLISH_ROLE]), 2)
        self.assertIn(policy.ENGLISH_ROLE, policy.literal_holes(raw))

    def test_actual_english_symbols_and_protected_source_literals_remain(self):
        self.assertNotIn(policy.ENGLISH_ROLE, policy.literal_holes("The data points with x=3 are given."))
        fence = chr(96) * 3
        self.assertEqual(policy.observed_formal_holes(fence + "text" + chr(10) +
            "points with ." + chr(10) + fence), [])

'''
old = old.replace(anchor, addition + anchor).replace(
    "classes = [ObservedSourceHolesAndEmptyLeaves]", "classes = [ObservedSourceHolesAndEmptyLeaves, AliasScopeAndEnglishRoles]")
with (ROOT / "scripts/test_p106b_hold_resolution_policy_v24.py").open("x", encoding="utf-8") as stream:
    stream.write(old)
old = (ROOT / "scripts/test_p106b_hold_resolution_refinement_v10.py").read_text(encoding="utf-8")
old = old.replace("from scripts import test_p106b_hold_resolution_refinement as original_tests",
    "from scripts import test_p106b_hold_resolution_refinement as original_tests" + chr(10) +
    "from scripts import p106b_hold_resolution_policy_v24 as current_policy")
old = old.replace(anchor, '''
class EnglishFormalRoleReplay(ObservedFormalRoleReplay):
    def test_missing_english_role_in_frozen_keep_is_reprocessed(self):
        row, frozen, selector, calls = self.make("The data set consists of points with .")
        self.assertEqual(selector.propose(row)["decision"], "PENDING")
        self.assertEqual(calls, [row["id"]])
        self.assertIs(selector.records[row["original_text_sha256"]], frozen)

''' + anchor)
old = old.replace("    r9 = refinement.previous", "    refinement.policy = current_policy" + chr(10) + "    r9 = refinement.previous")
old = old.replace("                   ObservedFormalRoleReplay]", "                   ObservedFormalRoleReplay, EnglishFormalRoleReplay]")
with (ROOT / "scripts/test_p106b_hold_resolution_refinement_v10_current24.py").open("x", encoding="utf-8") as stream:
    stream.write(old)
old = (AUDIT / "probe_policy_v23_v1.py").read_text(encoding="utf-8")
old = old.replace("policy_v23 as policy", "policy_v24 as policy").replace(
    "revision_v23 as revision", "revision_v24 as revision").replace(
    "policy_v23_purpose_probe_v1.json", "policy_v24_purpose_probe_v1.json")
anchor = 'code_paths = revision.CODE + [str(Path(__file__).relative_to(ROOT))]'
assert old.count(anchor) == 1
old = old.replace(anchor, '''
structural_path = BASE / "policy_v23_structural_counter_v1/manifest.json"
for row in inv.cache.read(structural_path)["rows"]:
    pin = row["original"]
    if row["id"] in rows:
        inv.require(rows[row["id"]]["source"]["sha256"] == pin["sha256"], "structural source duplicates a different original")
    rows[row["id"]] = dict(row, source=pin)
paths.append(structural_path)
''' + anchor)
with (AUDIT / "probe_policy_v24_v1.py").open("x", encoding="utf-8") as stream:
    stream.write(old)
old = (AUDIT / "prepare_root_selected_literal_counter_v3.py").read_text(encoding="utf-8")
old = old.replace("root_selected_literal_counter_v3", "root_selected_literal_counter_v4")
old = old.replace("root_selected_body_literals_v3.json", "root_selected_body_literals_v4.json")
old = old.replace("ROOT_AUTHORED_SELECTIONS_V7.json", "ROOT_AUTHORED_SELECTIONS_V8.json")
old = old.replace("reviewed_selection_plan_v10.json", "reviewed_selection_plan_v12.json")
old = old.replace('roles = ["context_controls", "structure_counter"]', 'roles = ["structure_counter"]')
anchor = '    if row["status"] != "ACTUAL_BODY_LITERAL_READBACK_NOT_SEMANTIC_APPROVAL":'
assert old.count(anchor) == 1
old = old.replace(anchor, '    if row["id"] not in {"expanded_train:1239923", "expanded_train:529487"}:' +
    chr(10) + '        continue' + chr(10) + anchor)
old = old.replace('for source in repair_plan["records"]:', "for source in []:")
anchor = 'inv.require(len({row["id"] for row, signals in flagged}) == len(flagged),'
old = old.replace(anchor, 'inv.require(len(flagged) == 2, "the two new source pairs differ")' + chr(10) + anchor)
old = old.replace("신호 합집합46과 기계적 미결2의 전체", "새 미결2쌍의 전체")
with (AUDIT / "prepare_root_selected_literal_counter_v4.py").open("x", encoding="utf-8") as stream:
    stream.write(old)
print("Prepared current24 regressions/replay,955+33 union probe and exact new two-body counter.")
