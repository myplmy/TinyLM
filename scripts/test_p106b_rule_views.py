"""CPU fixtures only; no source files, teacher, tokenizer or model execution."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.p106b_rule_views import make_rule_view, make_condition_followup, make_format_followup
from tinylm.chat.serialize import loss_spans, serialize


def task(kind="integer_arithmetic", language="ko"):
    return {"owner": "code", "kind": kind, "language": language, "split": "train",
            "root_id": "rule_fixture_01", "source": {"scope": "public_or_code",
            "family": "repository_fixture", "license": "repository-code-generated", "sha256": "A" * 64},
            "minimum": 0, "maximum": 20, "payload": {"a": 2, "b": 3, "op": "+"}}


def text(row, index=-1):
    return row["messages"][index]["content"][0]["text"]


class RuleViewTests(unittest.TestCase):
    def test_96_arithmetic_cases_recalculate_answer(self):
        for language in ("ko", "en"):
            for op in ("+", "-", "*"):
                for seed in range(16):
                    spec = task(language=language); spec["payload"]["op"] = op
                    row = make_rule_view(spec, seed=seed, view_index=1)
                    p = row["meta"]["derived_payload"]
                    gold = p["a"] + p["b"] if op == "+" else p["a"] - p["b"] if op == "-" else p["a"] * p["b"]
                    self.assertEqual(text(row), str(gold))
                    self.assertNotEqual(p, spec["payload"])

    def test_input_immutable_and_deterministic(self):
        spec = task(); saved = copy.deepcopy(spec)
        a = make_rule_view(spec, seed=1, view_index=1)
        self.assertEqual(a, make_rule_view(spec, seed=1, view_index=1))
        self.assertEqual(spec, saved)

    def test_root_first_question_split_stays_fixed(self):
        rows = [make_rule_view(task(), seed=i, view_index=i) for i in range(8)]
        self.assertEqual(len({text(r, 0) for r in rows}), 1)
        self.assertEqual(len({r["meta"]["root_concept_id"] for r in rows}), 1)

    def test_answer_json_known_envelope(self):
        spec = task(); spec["output_format"] = "answer_json"
        row = make_rule_view(spec, seed=1, view_index=1)
        p = row["meta"]["derived_payload"]
        self.assertEqual(json.loads(text(row)), {"answer": str(p["a"] + p["b"])})

    def test_lookup_changes_target_not_source_values(self):
        spec = task("table_lookup"); spec["payload"] = {"entries": [["가", "빨강"], ["나", "파랑"]], "target": "가"}
        row = make_rule_view(spec, seed=1, view_index=1)
        p = row["meta"]["derived_payload"]
        self.assertEqual(p["target"], "나"); self.assertEqual(text(row), "파랑")
        self.assertEqual(dict(p["entries"]), dict(spec["payload"]["entries"]))

    def test_lookup_equal_values_are_not_bad_answers(self):
        spec = task("table_lookup"); spec["payload"] = {"entries": [["a", "red"], ["b", "red"]], "target": "a"}
        self.assertEqual(text(make_rule_view(spec, seed=1, view_index=1)), "red")

    def test_json_projection_recalculates_fields(self):
        spec = task("json_projection"); spec["payload"] = {"record": {"name": "민수", "age": 14}, "fields": ["name"]}
        row = make_rule_view(spec, seed=1, view_index=1)
        self.assertEqual(json.loads(text(row)), {"age": 14})

    def test_fixed_literal_is_protected_not_forced_to_vary(self):
        spec = task("fixed_literal"); spec["payload"] = {"question": "1만 출력하세요.", "answer": "1"}
        row = make_rule_view(spec, seed=1, view_index=1)
        self.assertEqual(len(row["messages"]), 2); self.assertEqual(text(row), "1")
        self.assertEqual(row["meta"]["augmentation_status"], "UNCHANGED_PROTECTED")

    def test_singleton_numeric_domain_is_protected(self):
        spec = task(); spec.update(minimum=1, maximum=1, payload={"a": 1, "b": 1, "op": "+"})
        self.assertFalse(make_rule_view(spec, seed=1, view_index=1)["meta"]["changed"])

    def test_no_eval_or_protected_source_augmentation(self):
        for split in ("val", "dev", "sealed", "test"):
            spec = task(); spec["split"] = split
            with self.assertRaises(ValueError): make_rule_view(spec, seed=1, view_index=1)
        spec = task(); spec["source"]["scope"] = "protected"
        with self.assertRaises(ValueError): make_rule_view(spec, seed=1, view_index=1)

    def test_unknown_contract_never_inferred_from_words(self):
        for field, value in (("owner", "teacher_guess"), ("kind", "free_medical_qa"), ("language", "unknown")):
            spec = task(); spec[field] = value
            with self.assertRaises(ValueError): make_rule_view(spec, seed=1, view_index=1)

    def test_invalid_bool_nan_and_source_sha_rejected(self):
        spec = task(); spec["payload"]["a"] = True
        with self.assertRaises(ValueError): make_rule_view(spec, seed=1, view_index=1)
        spec = task(); spec["source"]["sha256"] = "bad"
        with self.assertRaises(ValueError): make_rule_view(spec, seed=1, view_index=1)
        spec = task("json_projection"); spec["payload"] = {"record": {"x": float("nan")}, "fields": ["x"]}
        with self.assertRaises(ValueError): make_rule_view(spec, seed=1, view_index=1)

    def test_canonical_chatml_and_two_correct_assistant_targets(self):
        row = make_rule_view(task(), seed=1, view_index=1)
        self.assertEqual(len(loss_spans(row)), 2)
        self.assertIn("<|im_start|>assistant", serialize(row))

    def test_provenance_no_new_knowledge_or_measured_tokens_claim(self):
        row = make_rule_view(task(), seed=1, view_index=1); m = row["meta"]
        self.assertEqual(m["source_license"], "repository-code-generated")
        self.assertEqual(len(m["source_contract_sha256"]), 64)
        self.assertFalse(m["unique_knowledge_claim"])
        self.assertEqual(m["dataset_token_coverage"], "NOT_MEASURED")

    def test_boolean_ast_recomputes_16_changed_assignments(self):
        spec = task("boolean_expression")
        spec["payload"] = {"values": {"A": True, "B": False},
            "expression": {"op": "and", "args": ["A", {"op": "not", "args": ["B"]}]}}
        for seed in range(16):
            row = make_condition_followup(spec, seed=seed, view_index=seed)
            values = row["meta"]["derived_payload"]["values"]
            self.assertEqual(text(row), str(values["A"] and not values["B"]).lower())
            self.assertIn("앞의 논리식", text(row, -2))

    def test_boolean_unknown_operation_not_eval(self):
        spec = task("boolean_expression")
        spec["payload"] = {"values": {"A": True}, "expression": {"op": "call", "args": ["A"]}}
        with self.assertRaises(ValueError): make_rule_view(spec, seed=1, view_index=1)

    def test_c1_arithmetic_previous_operation_and_format_kept(self):
        spec = task(); spec["output_format"] = "answer_json"
        row = make_condition_followup(spec, seed=1, view_index=1)
        p = row["meta"]["derived_payload"]
        self.assertIn("앞의 계산", text(row, -2))
        self.assertEqual(json.loads(text(row)), {"answer": str(p["a"] + p["b"])})
        self.assertEqual(len(loss_spans(row)), 2)

    def test_c1_table_and_projection_keep_context(self):
        spec = task("table_lookup"); spec["payload"] = {"entries": [["A", "red"], ["B", "blue"]], "target": "A"}
        row = make_condition_followup(spec, seed=1, view_index=1)
        self.assertEqual(text(row), "blue"); self.assertIn("앞 표", text(row, -2))
        spec = task("json_projection"); spec["payload"] = {"record": {"x": 1, "y": 2}, "fields": ["x"]}
        row = make_condition_followup(spec, seed=1, view_index=1)
        self.assertEqual(json.loads(text(row)), {"y": 2}); self.assertIn("앞 입력", text(row, -2))

    def test_c3_preserves_full_answer_string_quotes_and_newlines(self):
        spec = task("verbatim_qa"); spec["payload"] = {"question": "설명을 다시 써 주세요.", "answer": '첫 줄 "인용"\n둘째 줄'}
        row = make_format_followup(spec)
        self.assertEqual(json.loads(text(row)), {"answer": spec["payload"]["answer"]})
        self.assertEqual(text(row, 0), spec["payload"]["question"])
        self.assertEqual(row["meta"]["original_factual_truth"], "NOT_REVIEWED")
        self.assertEqual(len(loss_spans(row)), 2)
        with self.assertRaises(ValueError): make_rule_view(spec, seed=1, view_index=1)

    def test_c3_eval_and_protected_source_rejected(self):
        spec = task(); spec["split"] = "val"
        with self.assertRaises(ValueError): make_format_followup(spec)
        spec = task(); spec["source"]["scope"] = "protected"
        with self.assertRaises(ValueError): make_format_followup(spec)


if __name__ == "__main__":
    unittest.main(verbosity=2)
