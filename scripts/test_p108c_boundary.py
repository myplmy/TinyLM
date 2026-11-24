"""CPU input-role and independently recomputed synthetic-answer checks."""
from collections import Counter
import unittest
from scripts import p108c_boundary_data as data


class BoundaryContracts(unittest.TestCase):
    def test_membership_matches_independent_expected_families(self):
        value = data.dataset(); rows = data.validate(value)
        self.assertEqual(Counter(r["family"] for r in rows), dict(target=48,
            same_subject_other_relation=48, open_sentence=48, arithmetic=16,
            provided_role=16, normal_copy=8, normal_repetition=8, json_format=8,
            missing_information=8, actual_history=12))
        self.assertFalse(value["training_allowed"])
        self.assertFalse(value["official"])

    def test_arithmetic_answers_recomputed_without_stored_expected(self):
        import re
        for row in data.dataset()["singles"]:
            if row["family"] == "arithmetic":
                numbers = [int(v) for v in re.findall("[0-9]+", row["question"])]
                self.assertEqual(int(row["expected"]), sum(numbers))

    def test_format_and_normal_repetition_are_not_negative_training(self):
        import json
        for row in data.dataset()["singles"]:
            if row["family"] == "json_format":
                parsed = json.loads(row["expected"])
                self.assertEqual(list(parsed), ["answer"])
                self.assertIsInstance(parsed["answer"], str)
            if row["family"] == "normal_repetition":
                self.assertEqual(len(row["expected"].split()), 3)
                self.assertEqual(len(set(row["expected"].split())), 1)

    def test_freshness_normalizes_case_and_space_and_rejects_duplicates(self):
        value = data.dataset(); question = value["singles"][0]["question"]
        with self.assertRaises(ValueError):
            data.validate(value, ["  "+question.upper()+"  "])
        value["singles"][1]["question"] = question
        with self.assertRaises(ValueError):
            data.validate(value)

    def test_scope_metadata_requires_current_relation_not_entity_only(self):
        rows = data.validate(data.dataset())
        for fact in (f[0] for f in data.FACTS):
            target = [r for r in rows if r.get("fact") == fact and r["family"] == "target"]
            other = [r for r in rows if r.get("fact") == fact and r["family"] != "target"]
            self.assertEqual(len(target), 4); self.assertEqual(len(other), 4)
            self.assertTrue(all(r["scope_expected"] for r in target))
            self.assertTrue(all(not r["scope_expected"] for r in other))
            self.assertIsNone(target[-1]["expected"])
            self.assertTrue(target[-1]["full_sentence_requested"])

    def test_own_history_outcomes_do_not_pollute_same_input_causal_panel(self):
        from scripts import diag_p108c_boundary as driver
        records = []
        for arm in driver.ARMS:
            for mode in ("SINGLE", "OWN_HISTORY"):
                for identifier in ("retained", "changed"):
                    exact = identifier == "retained" if arm == "ORIGINAL" else identifier == "changed"
                    records.append(dict(arm=arm, mode=mode, id=identifier,
                        family="synthetic", expected="a", exact=exact, protected=False,
                        scope_expected=False, routing=dict(enabled=arm != "ORIGINAL"),
                        diagnostics=dict(loop_indicator=False, question_echo=False, empty=False),
                        generation=dict(finish_reason="STOP_SEQUENCE", generated_tokens=2,
                                        generated_ids=[1 if exact else 2, 4])))
        _, paired = driver.summaries(records)
        self.assertEqual(paired["GLOBAL"]["same_inputs"], 2)
        self.assertEqual(paired["GLOBAL"]["strict_corrected"], 1)
        self.assertEqual(paired["GLOBAL"]["strict_harmed"], 1)


if __name__ == "__main__":
    unittest.main()
