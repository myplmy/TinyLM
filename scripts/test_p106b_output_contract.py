"""CPU-only real wrapper/coordinator fixtures, no teacher/student model loading."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.p106b_output_contract import OutputContract, reviewed_contract, request_group, text_sha
from scripts import p106b_pipeline as pipeline
from scripts.p106b_lexical_observation import TextObserver
from scripts.p106b_report_domains import separated_report
from scripts.test_p106b_pipeline_gates import job
from tinylm.data.prepare import SyntheticTokenizer


class Session:
    key = "fixture"
    def __init__(self, finals):
        self.finals, self.calls, self.prompts = list(finals), 0, []
    def count_prompt(self, *_args):
        return {"decision": "DIRECT"}
    def complete(self, messages, *_args):
        self.prompts.append(messages)
        final = self.finals[self.calls]
        self.calls += 1
        return {"choices": [{"finish_reason": "stop", "message": {
            "content": final, "reasoning_content": "RAW_REASONING_ONLY"}}],
            "usage": {"completion_tokens": 20}}


def response(q, values):
    return f"[[QUESTION]]\n{q}\n[[/QUESTION]]\n" + "\n".join(
        f"[[ANSWER_{i}]]\n{a}\n[[/ANSWER_{i}]]" for i, a in enumerate(values, 1))


class Tests(unittest.TestCase):
    def run_group(self, contract, finals, count=2):
        with tempfile.TemporaryDirectory(prefix="p106b_contract_fixture_") as tmp:
            root = Path(tmp)
            with patch.object(pipeline, "ROOT", root), \
                 patch("tokenizers.Tokenizer.from_file", return_value=SyntheticTokenizer()):
                writer, session = pipeline.CandidateWriter(root, {}, observer=TextObserver()), Session(finals)
                rows, summary = request_group(writer, session, job(), "fixture", 10,
                    count=count, per_slot=32768, maximum=16384, contract=contract)
                metrics = writer.close()
                raw = [json.loads(line) for line in (root / "raw_000000.jsonl").read_text().splitlines()]
                return rows, summary, metrics, raw, session

    def test_literal_duplicate_is_normal_and_not_regenerated(self):
        contract = OutputContract("EXACT_LITERAL", "Say only1", "CODE_TEMPLATE", "literal-v1", "1")
        rows, summary, metrics, raw, session = self.run_group(contract, [response(contract.question, ["1", "1"])])
        self.assertEqual(session.calls, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(metrics["canonical_rows"], 1)
        self.assertEqual(summary["physical_attempts"], 1)
        self.assertEqual(summary["budget_attempts"], 1)
        self.assertEqual(raw[0]["duplicate_slots"], [2])
        self.assertEqual(raw[0]["output_contract"]["kind"], "EXACT_LITERAL")
        self.assertEqual(rows[0]["meta"]["output_contract_effective"], "EXACT_LITERAL")
        self.assertIn("RAW_REASONING_ONLY", json.dumps(raw))
        self.assertNotIn("RAW_REASONING_ONLY", json.dumps(rows[0]["messages"]))

    def test_unknown_and_teacher_rewording_do_not_regenerate(self):
        for contract in (OutputContract(), OutputContract("CONSTRAINED_UNKNOWN", "question", "CODE_TEMPLATE", "v1"), OutputContract("VARIANT_ALLOWED", "different question", "CODE_TEMPLATE", "v1")):
            rows, summary, _m, _r, session = self.run_group(contract, [response("question", ["same", "same"])])
            self.assertEqual(session.calls, 1)
            self.assertIn(summary["effective_contract"], ("UNKNOWN", "CONSTRAINED_UNKNOWN"))
            self.assertEqual(len(rows), 1)

    def test_variant_recovery_keeps_good_slot_and_requests_only_bad_slot(self):
        c = OutputContract("VARIANT_ALLOWED", "Explain4", "CODE_TEMPLATE", "v1")
        rows, summary, _m, _r, session = self.run_group(c, [response(c.question, ["4", "4"]),
            "[[ANSWER_2]]\n2+2 equals4.\n[[/ANSWER_2]]"])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["meta"]["generation_id"], "fixture_try1_a1")
        self.assertEqual(rows[1]["meta"]["generation_id"], "fixture_try2_a2")
        self.assertIn("[[ANSWER_2]]", session.prompts[1][0]["content"])
        self.assertNotIn("[[ANSWER_1]]", session.prompts[1][0]["content"])
        self.assertEqual(summary["attempt_reasons"], ["initial", "duplicate_slot_recovery"])

    def test_parse_and_duplicate_failures_share_three_attempts(self):
        c = OutputContract("VARIANT_ALLOWED", "Explain4", "CODE_TEMPLATE", "v1")
        rows, summary, _m, raw, session = self.run_group(c, ["bad fields", response(c.question, ["4", "4"]),
            "[[ANSWER_2]]\n4\n[[/ANSWER_2]]"])
        self.assertEqual(session.calls, 3)
        self.assertEqual(summary["physical_attempts"], 3)
        self.assertEqual(len(raw), 3)
        self.assertEqual(len(rows), 1)
        self.assertFalse(summary["all_variants_present"])

    def test_review_adapter_requires_exact_question_revision_and_approval(self):
        annotation = {"kind": "EXACT_LITERAL", "literal": "1", "question_sha256": text_sha("say1"),
            "revision": "r1", "approval_ref": "review:1", "status": "REVIEWED"}
        c = reviewed_contract("say1", annotation, expected_revision="r1", approval_ref="review:1")
        self.assertEqual(c.kind, "EXACT_LITERAL")
        for q, revision, approval in (("say2", "r1", "review:1"), ("say1", "r2", "review:1"), ("say1", "r1", "")):
            with self.assertRaises(ValueError):
                reviewed_contract(q, annotation, expected_revision=revision, approval_ref=approval)

    def test_case_negation_and_value_differences_are_not_exact_duplicates(self):
        rows, _s, _m, _r, session = self.run_group(OutputContract(), [response("question", ["A is X", "A is Y"])])
        self.assertEqual(len(rows), 2)
        self.assertEqual(session.calls, 1)

    def test_lexical_modes_are_bounded_and_warning_only(self):
        for mode in ("within", "recent"):
            observer = TextObserver(mode, window=2)
            observer.observe("first", "question1", ["A is X", "A is Y"])
            output = observer.observe("second", "question2", ["A is X", "A is not X"])
            self.assertEqual(output["effect"], "WARNING_ONLY_NO_ADMISSION_RETRY_OR_TRUTH_DECISION")
            self.assertLessEqual(output["queue_rows"], 2)
            self.assertEqual(output["cross_pairs_examined"] > 0, mode == "recent")
            short = observer.observe("third", "say1", ["1", "1"])
            self.assertIsNone(short["pairs"][0]["scores"][0]["jaccard"])

    def test_reporting_unknown_is_null_not_zero_or_correct(self):
        output = separated_report({"raw_rows": 100, "canonical_rows": 82})
        self.assertEqual(output["operational"]["requests"], 100)
        self.assertEqual(output["corpus"]["canonical_rows"], 82)
        self.assertIsNone(output["posthoc_review"]["fact_correctness"])
        self.assertIsNone(output["posthoc_review"]["reviewed_rows"])
        self.assertEqual(output["student_effect"]["status"], "NOT_RUN")
        with self.assertRaises(ValueError):
            separated_report({"canonical_rows": True})


if __name__ == "__main__":
    unittest.main()
