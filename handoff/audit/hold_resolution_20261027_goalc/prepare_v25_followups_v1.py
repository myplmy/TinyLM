"""Prepare regressions and the same complete source-union purpose probe."""
from pathlib import Path

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
source = (ROOT / "scripts/test_p106b_hold_resolution_policy_v24.py").read_text(encoding="utf-8")
source = source.replace("policy_v24 as policy", "policy_v25 as policy")
anchor = 'if __name__ == "__main__":'
assert source.count(anchor) == 1
source = source.replace(anchor, '''
class EntireMissingContentAxis(unittest.TestCase):
    def table(self, second="부양어"):
        return chr(10).join(['{| class="wikitable"', "! 어근 !! " + second + " !! 비교 언어",
            "|-", "| 눈 || || *mata", "|-", "| 새 || || *manuk", "|}", ""])

    def test_whole_content_column_cannot_borrow_sparse_cell_proof(self):
        raw = self.table()
        holes = policy.missing_table_axes(raw)
        self.assertEqual([(r["column"], r["header"]) for r in holes], [(1, "부양어")])
        value = policy.propose(dict(id="expanded_train:987654321", text=raw, complete_eos=True, valid_utf8=True))
        self.assertEqual(value["decision"], "PENDING")
        self.assertIn(policy.COLUMN_REASON, value["reasons"])
        self.assertEqual(value["candidate"], raw)

    def test_optional_metadata_blanks_remain_literal_without_inferred_values(self):
        for label in ["ISBN", "ISBN-13", "비고", "특기사항", "Notes"]:
            self.assertEqual(policy.missing_table_axes(self.table(label)), [])

    def test_one_real_value_in_each_axis_is_different_from_a_missing_axis(self):
        raw = self.table().replace("| 눈 || ||", "| 눈 || actual ||")
        self.assertEqual(policy.missing_table_axes(raw), [])

    def test_recovered_actual_two_column_pairs_have_no_missing_target_axis(self):
        raw = self.table().replace(" !! 부양어", "").replace(" || ||", " ||")
        self.assertEqual(policy.missing_table_axes(raw), [])

    def test_protected_table_syntax_example_is_not_a_missing_dataset(self):
        fence = chr(96) * 3
        self.assertEqual(policy.missing_table_axes(fence + "text" + chr(10) + self.table() + fence), [])

''' + anchor)
source = source.replace("classes = [ObservedSourceHolesAndEmptyLeaves, AliasScopeAndEnglishRoles]",
    "classes = [ObservedSourceHolesAndEmptyLeaves, AliasScopeAndEnglishRoles, EntireMissingContentAxis]")
with (ROOT / "scripts/test_p106b_hold_resolution_policy_v25.py").open("x", encoding="utf-8") as stream:
    stream.write(source)
source = (ROOT / "scripts/test_p106b_hold_resolution_refinement_v10_current24.py").read_text(encoding="utf-8")
source = source.replace("policy_v24 as current_policy", "policy_v25 as current_policy")
source = source.replace(anchor, '''
class MissingAxisReplay(unittest.TestCase):
    make = ObservedFormalRoleReplay.make
    def test_old_keep_of_a_wholly_missing_content_axis_is_freshly_checked(self):
        raw = chr(10).join(['{| class="wikitable"', "! 항목 !! 부양어 !! 비교 언어",
            "|-", "| 눈 || || *mata", "|}", ""])
        row, frozen, selector, calls = self.make(raw)
        self.assertEqual(selector.propose(row)["decision"], "PENDING")
        self.assertEqual(calls, [row["id"]])
        self.assertIs(selector.records[row["original_text_sha256"]], frozen)

''' + anchor)
source = source.replace("ObservedFormalRoleReplay, EnglishFormalRoleReplay]",
    "ObservedFormalRoleReplay, EnglishFormalRoleReplay, MissingAxisReplay]")
with (ROOT / "scripts/test_p106b_hold_resolution_refinement_v10_current25.py").open("x", encoding="utf-8") as stream:
    stream.write(source)
source = (AUDIT / "probe_policy_v24_v1.py").read_text(encoding="utf-8")
source = source.replace("policy_v24 as policy", "policy_v25 as policy").replace(
    "revision_v24 as revision", "revision_v25 as revision").replace(
    "policy_v24_purpose_probe_v1.json", "policy_v25_purpose_probe_v1.json")
with (AUDIT / "probe_policy_v25_v1.py").open("x", encoding="utf-8") as stream:
    stream.write(source)
print("Prepared current25 regressions/replay and the unchanged987-source purpose union.")
