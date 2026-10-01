#!/usr/bin/env python3
"""CPU-only request/paired-panel/selection contracts; never load a teacher/student."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import p106b_gate_runtime as runtime
from scripts import p106b_education_followup as edu
from scripts import p106b_pipeline as pipeline
from scripts import test_p106b_education_followup as fixture_data
from tinylm.data.prepare import SyntheticTokenizer


class ControlTests(unittest.TestCase):
    def test_numeric_and_quoted_language_is_not_a_parser_failure(self):
        from scripts.p106b_teacher_format import parse_tagged, parse_json_control, script_observations, teacher_prompt
        from scripts.p106b_multi_answer import parse_multi
        final = "[[QUESTION]]\n1이라고 말해봐\n[[/QUESTION]]\n[[ANSWER]]\n1\n[[/ANSWER]]"
        self.assertEqual(parse_tagged(final, language="ko")["assistant_text"], "1")
        self.assertEqual(parse_json_control(json.dumps({"question":"1이라고 말해봐", "answer":"1", "note":""}), language="ko")["assistant_text"], "1")
        self.assertTrue(script_observations("1", "ko"))
        self.assertTrue(script_observations("Hello의 뜻은 인사", "ko"))
        multi = "[[QUESTION]]\nGive Japanese greetings\n[[/QUESTION]]\n[[ANSWER_1]]\nこんにちは\n[[/ANSWER_1]]\n[[ANSWER_2]]\nおはよう\n[[/ANSWER_2]]"
        self.assertEqual(parse_multi({"choices":[{"finish_reason":"stop","message":{"content":multi}}]},2,"en")["status"], "MULTI_FORMAT_READY")
        self.assertIn("INSIDE ANSWER", teacher_prompt("qa_generate", "ko", {"topic":"JSON example"})[0]["content"])
        array = multi.replace("こんにちは", "[[1,2],[3,4]]")
        self.assertEqual(parse_multi({"choices":[{"finish_reason":"stop","message":{"content":array}}]},2,"en")["status"], "MULTI_FORMAT_READY")

    def test_native_budget_is_top_level_and_effort_matches_template(self):
        calls = []
        def http(url, _key, body=None, **kwargs):
            calls.append((url, body, kwargs))
            if url.endswith("apply-template"):
                return {"prompt": "fixture"}
            if url.endswith("tokenize"):
                return {"tokens": [1, 2]}
            return {"choices": []}
        with patch.object(runtime, "_free_port", return_value=1), patch.object(runtime, "_http_json", side_effect=http):
            session = runtime.TeacherSession(32768, effort="medium", thinking_budget=8192)
            view = runtime.EffortView(session, "xhigh")
            view.count_prompt([], 32768, 16384)
            view.complete([], 1337, 16384)
        self.assertEqual(calls[0][1]["reasoning_effort"], "xhigh")
        self.assertEqual(calls[-1][1]["reasoning_effort"], "xhigh")
        self.assertEqual(calls[-1][1]["thinking_budget_tokens"], 8192)
        self.assertNotIn("chat_template_kwargs", calls[-1][1])
        self.assertEqual(calls[-1][1]["max_tokens"], 16384)
        self.assertEqual(calls[-1][2]["timeout"], 600)
        self.assertEqual(session.effort, "medium")

    def test_same_outputs_across_efforts_do_not_bias_deduplication(self):
        class Teacher:
            key = "fixture"
            def __init__(self, _context, _slots, **controls):
                self.thinking_budget = controls["thinking_budget"]
            def __enter__(self): return self
            def __exit__(self, *_): pass
            def count_prompt(self, *_args, **_kwargs): return {"decision": "DIRECT"}
            def complete(self, messages, seed, _maximum, **_kwargs):
                ko = "Korean" in messages[0]["content"]
                q, a = (f"질문{seed}", f"답변{seed}") if ko else (f"Question{seed}", f"Answer{seed}")
                if "[[ANSWER_2]]" in messages[0]["content"]:
                    final = f"[[QUESTION]]\n{q}\n[[/QUESTION]]\n[[ANSWER_1]]\n{a}\n[[/ANSWER_1]]\n[[ANSWER_2]]\n{a} variant2\n[[/ANSWER_2]]"
                else:
                    final = f"[[QUESTION]]\n{q}\n[[/QUESTION]]\n[[ANSWER]]\n{a}\n[[/ANSWER]]"
                return {"choices": [{"finish_reason": "stop", "message": {"content": final,
                    "reasoning_content": "SIDECAR"}}], "usage": {"completion_tokens": 20}}
            def check_monitor(self): pass
            def require_valid_resources(self): pass
            def evidence(self): return {"fixture": "CPU_ONLY"}
        with tempfile.TemporaryDirectory(prefix="p106b_effort_cpu_") as directory:
            root = Path(directory)
            target = root / "effort-panel"
            target.mkdir()
            info = {"context": 32768, "max_output": 16384, "thinking_budget_tokens": 8192}
            with patch.object(edu, "ROOT", root), patch.object(edu, "BASE", root), \
                 patch.object(pipeline, "ROOT", root), patch.object(edu, "TeacherSession", Teacher), \
                 patch.object(edu, "original_rows", return_value=fixture_data.Tests.correction_fixture_rows()), \
                 patch("tokenizers.Tokenizer.from_file", return_value=SyntheticTokenizer()):
                report = edu.effort_panel(target, info)
            self.assertEqual(report["raw_rows"], 12)
            self.assertEqual(report["canonical_rows"], 18)
            for effort in edu.EFFORTS:
                self.assertTrue(report["per_effort"][effort]["wire_complete"])
                self.assertIsNone(report["per_effort"][effort]["content_screen_passed_groups"])
                self.assertIsNone(report["per_effort"][effort]["usable_groups_per_sec"])
            self.assertEqual(report["student_training"], "NOT_RUN")

    def test_no_effort_is_silently_chosen_for_unattended_queue(self):
        panel = {"per_effort": {"medium": {"wire_complete": True}}}
        with patch.object(edu, "read_report", return_value=panel), \
             patch.object(edu, "require_current_stage"), patch.object(sys.stdin, "isatty", return_value=False):
            with self.assertRaises(runtime.PrerequisiteHold):
                edu.choose_effort({"eligible_efforts": ["medium"]})

    def test_explicit_selection_never_reads_stdin(self):
        panel = {"per_effort": {"xhigh": {"wire_complete": True}}}
        with patch.object(edu, "read_report", return_value=panel), \
             patch.object(edu, "require_current_stage"), \
             patch("builtins.input", side_effect=AssertionError("input forbidden")):
            result = edu.choose_effort({"eligible_efforts": ["xhigh"]}, "xhigh")
            self.assertEqual(result["effort"], "xhigh")
            with self.assertRaises(runtime.PrerequisiteHold):
                edu.choose_effort({"eligible_efforts": ["xhigh"]}, "low")


if __name__ == "__main__":
    unittest.main()
