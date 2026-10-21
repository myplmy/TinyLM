from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
import unittest
from scripts.diag_p101a_clean_eval import score, prompt_messages, readable_case
from scripts.p106b_verified_trace_data import render_row


class CleanEvalTests(unittest.TestCase):
    def row(self, policy="direct"):
        return render_row(dict(family="addition", a=12, b=14), "ko", policy, "test")

    def test_exact_final_value_not_any_numeric_substring(self):
        self.assertTrue(score(self.row(), "답: 26")["primary_correct"])
        self.assertFalse(score(self.row(), "126 26 926")["primary_correct"])

    def test_trace_format_separate_from_final_answer(self):
        result = score(self.row("trace"), "답: 26")
        self.assertTrue(result["primary_correct"])
        self.assertFalse(result["policy_compliant"])

    def test_prompt_contains_no_gold_assistant(self):
        self.assertEqual([m["role"] for m in prompt_messages(self.row())], ["user"])

    def test_extraction_failure_not_false_empty_match(self):
        self.assertFalse(score(self.row(), "답: 26", False)["primary_correct"])

    def test_readable_question_answer_not_opaque_json(self):
        row = self.row()
        text = readable_case(0, row, "답: 26", score(row, "답: 26"),
            dict(finish_reason="STOP_SEQUENCE", generated_tokens=4))
        self.assertIn("12+14", text)
        self.assertIn("모델의 첫 실제 답", text)
        self.assertIn("답: 26", text)


if __name__ == "__main__": unittest.main()
