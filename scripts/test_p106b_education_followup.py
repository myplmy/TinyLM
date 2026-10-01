#!/usr/bin/env python3
"""CPU-only regression for source/lineage separation and fail-closed downstream gates."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import p106b_education_followup as edu
from scripts.p106b_gate_runtime import PrerequisiteHold
from scripts.p106b_shards import ShardWriter
from tinylm.chat.canonical import normalize
from tinylm.data.prepare import SyntheticTokenizer
from scripts import p106b_pipeline as pipeline


class Tests(unittest.TestCase):
    @staticmethod
    def correction_fixture_rows():
        rows = [normalize({"messages": [{"role": "user", "content": f"질문{i}"},
                     {"role": "assistant", "content": f"답변{i}"}],
             "meta": {"source": "fixture", "source_id": f"fixture:{i}", "generation_id": f"old{i}",
                      "language": "ko", "parent_concept_id": f"{i:064X}",
                      "source_repo": "fixture/public", "source_revision": "fixture-revision",
                      "source_license": "fixture-only"}}) for i in range(12)] + [normalize({
             "messages": [{"role": "user", "content": f"Question{i}"}, {"role": "assistant", "content": f"Answer{i}"}],
             "meta": {"source": "fixture", "source_id": f"fixture:en{i}", "generation_id": f"old_en{i}",
                      "language": "en", "parent_concept_id": f"{i:064X}",
                      "source_repo": "fixture/public", "source_revision": "fixture-revision",
                      "source_license": "fixture-only"}}) for i in range(12)]
        # Preserve concept/question identity across real two-answer variants.
        for index in (0, 1, 12, 13):
            variant = json.loads(json.dumps(rows[index]))
            variant["meta"]["generation_id"] += "_a2"
            variant["messages"][1]["content"][0]["text"] += " variant2"
            rows.append(variant)
        return rows

    def run_correction_fixture(self, pilot=False, bad_multi=False):
        class FakeTeacher:
            key = "fixture"
            contexts = []
            requests = []
            def __init__(self, context, slots, **controls):
                self.contexts.append((context, slots))
                self.effort = controls.get("effort")
                self.thinking_budget = controls.get("thinking_budget")
            def __enter__(self):
                return self
            def __exit__(self, *_args):
                pass
            def count_prompt(self, _messages, context, maximum):
                self.requests.append((context, maximum))
                return {"decision": "DIRECT"}
            def complete(self, messages, seed, _maximum):
                ko = "Korean" in messages[0]["content"]
                q, a = (f"질문{seed}", f"답변{seed}") if ko else (f"Question{seed}", f"Answer{seed}")
                if bad_multi and ko and "[[ANSWER_2]]" in messages[0]["content"]:
                    q, a = "열불견증은 무엇인가?", f"갑상선 기능 과장증 답변{seed}"
                if "[[ANSWER_2]]" in messages[0]["content"]:
                    final = f"[[QUESTION]]\n{q}\n[[/QUESTION]]\n[[ANSWER_1]]\n{a}\n[[/ANSWER_1]]\n[[ANSWER_2]]\n{a} variant2\n[[/ANSWER_2]]"
                else:
                    final = f"[[QUESTION]]\n{q}\n[[/QUESTION]]\n[[ANSWER]]\n{a}\n[[/ANSWER]]"
                return {"choices": [{"finish_reason": "stop", "message": {"content": final,
                        "reasoning_content": "SIDE_CAR_ONLY"}}], "usage": {"completion_tokens": 20}}
            def check_monitor(self):
                pass
            def require_valid_resources(self):
                pass
            def evidence(self):
                return {"fixture": "CPU_ONLY"}
        with tempfile.TemporaryDirectory(prefix="p106b_actual_C_fixture_") as directory:
            root = Path(directory)
            target = root / "correction"
            target.mkdir()
            contract = edu.runtime_contract()
            info = {"code_sha256": edu.sha256_file(Path(edu.__file__)), "runtime_contract": contract,
                    "mode": "correct-pilot" if pilot else "correct"}
            with patch.object(edu, "ROOT", root), patch.object(edu, "BASE", root), \
                 patch.object(edu, "runtime_contract", return_value=contract), \
                 patch.object(edu, "arm_inputs", side_effect=lambda arm: edu.ARMS[arm]), \
                 patch.object(pipeline, "ROOT", root), \
                 patch.object(edu, "TeacherSession", FakeTeacher), \
                 patch.object(edu, "original_rows", return_value=self.correction_fixture_rows()), \
                 patch("tokenizers.Tokenizer.from_file", return_value=SyntheticTokenizer()):
                report = edu.correct(target, info)
                self.assertGreater(report["whole_wall_sec"], 0)
                persisted = json.loads((target / "report.json").read_text(encoding="utf-8"))
                self.assertEqual(persisted["whole_wall_sec"], report["whole_wall_sec"])
                self.assertEqual(report["status"], "CORRECTION_WIRING_PASSED" if pilot else "COLLECTION_TECHNICAL_READY")
                rows = edu.read_rows(target, "selected", report["selected_concat_sha256"])
                self.assertEqual(len(rows), 6 if pilot else 28)
                self.assertTrue(all(r["meta"]["source_transform"] == "teacher_answer" for r in rows))
                self.assertTrue(all("SIDE_CAR_ONLY" not in json.dumps(r["messages"]) for r in rows))
                if not pilot:
                    _train, _val, preview = edu.prepare_preview()
                    self.assertEqual(preview["source_concat_sha256"], report["selected_concat_sha256"])
                    self.assertEqual(len(_train)+len(_val), 28)
                self.assertEqual(FakeTeacher.contexts, [(32768, 1)])
                self.assertEqual(FakeTeacher.requests, [(32768, 16384)] * (4 if pilot else 24))
                self.assertEqual(report["required_groups_by_language"], {"ko": 2, "en": 2} if pilot else {"ko": 9, "en": 9})
                return report

    def test_real_correction_to_canonical_roundtrip(self):
        self.run_correction_fixture()

    def test_wire_pilot_does_not_semantically_screen_or_retry(self):
        report = self.run_correction_fixture(pilot=True, bad_multi=True)
        self.assertTrue(report["wire_passed"])
        self.assertIsNone(report["quality_screen_passed"])
        self.assertFalse(report["student_training_allowed"])
        self.assertEqual(report["accepted_groups_by_language"], {"ko": 2, "en": 2})
        self.assertEqual(report["wired_groups_by_language"], {"ko": 2, "en": 2})

    def test_primary_prompt_has_no_detected_badword_feedback(self):
        from scripts.p106b_teacher_format import teacher_prompt
        from scripts.p106b_multi_answer import multi_prompt
        group = [self.correction_fixture_rows()[0]]
        group[0]["messages"][0]["content"][0]["text"] = "22세 여성의 열불견증은?"
        job = edu.build_correction_job(group)
        self.assertNotIn("answer", job["source_payload"])
        self.assertNotIn("detected_source_issues", job["source_payload"])
        for prompt in (teacher_prompt(job["teacher_task"], "ko", job["source_payload"]), multi_prompt(job, 2)):
            self.assertIn("Draft answers are unverified", prompt[0]["content"])
            self.assertIn("열불견증", prompt[1]["content"])
        self.assertFalse(hasattr(edu, "content_issues"))
        self.assertFalse(hasattr(edu, "retry_feedback"))

    def test_budget_recovery_does_not_reuse_old_output_or_child_tags(self):
        self.assertEqual(edu.CORRECTION_CONTEXT, 32768)
        self.assertEqual(edu.CORRECTION_MAX_OUTPUT, 16384)
        self.assertEqual(edu.CORRECTION_THINKING_BUDGET, 8192)
        self.assertEqual(edu.BASE.name, "v33_online_technical_contract")
        self.assertIn("_contract_", edu.ARMS["a"]["stem"])
        self.assertIn("_contract_", edu.ARMS["b"]["stem"])

    def test_global_three_of_four_cannot_override_korean_threshold(self):
        passed, required = edu.correction_gate(True, {"ko": 2, "en": 2}, {"ko": 1, "en": 2}, 4)
        self.assertEqual(required, {"ko": 2, "en": 2})
        self.assertFalse(passed)
        self.assertTrue(edu.correction_gate(True, {"ko": 2, "en": 2}, {"ko": 2, "en": 2}, 6)[0])
        self.assertFalse(edu.correction_gate(False, {"ko": 2, "en": 2}, {"ko": 2, "en": 2}, 6)[0])

    def test_length_diagnostics_distinguish_reasoning_and_partial_final(self):
        for final, expected in (("", "OUTPUT_LIMIT_REASONING_ONLY"),
                                ("[[QUESTION]]\n질문", "OUTPUT_LIMIT_PARTIAL_FINAL")):
            reply = {"choices": [{"finish_reason": "length", "message": {
                "content": final, "reasoning_content": "thinking"}}],
                "usage": {"completion_tokens": 4096, "prompt_tokens": 1412}}
            row = pipeline.response_diagnostic(reply, 4096)
            self.assertEqual(row["cause"], expected)
            self.assertTrue(row["at_requested_output_limit"])
            self.assertEqual(row["reasoning_chars"], 8)
            self.assertEqual(row["server_usage"]["completion_tokens"], 4096)
            row = pipeline.response_diagnostic(reply, 6144)
            self.assertEqual(row["cause"], "FINISH_LENGTH_OTHER_OR_UNKNOWN_LIMIT")

    def test_diagnostic_cannot_destroy_a_malformed_paid_reply(self):
        for reply in (None, {}, {"choices": None}, {"choices": "invalid"},
                      {"choices": [None]}, {"choices": [{"message": None}]}):
            row = pipeline.response_diagnostic(reply, 6144)
            self.assertEqual(row["reasoning_chars"], 0)
            self.assertEqual(row["final_chars"], 0)
            self.assertEqual(row["cause"], "NO_REPLY" if reply is None else "OTHER_FINISH_REASON")

    def test_length_response_with_closed_fields_is_not_admitted(self):
        from scripts.p106b_teacher_format import parse_reply
        from scripts.p106b_multi_answer import parse_multi
        final = "[[QUESTION]]\n질문\n[[/QUESTION]]\n[[ANSWER]]\n답변\n[[/ANSWER]]"
        reply = {"choices": [{"finish_reason": "length", "message": {"content": final}}],
                 "usage": {"completion_tokens": 6144}}
        self.assertIsNone(parse_reply(reply, language="ko")["parsed_content"])
        multi = final.replace("[[ANSWER]]", "[[ANSWER_1]]").replace("[[/ANSWER]]", "[[/ANSWER_1]]")
        reply["choices"][0]["message"]["content"] = multi + "\n[[ANSWER_2]]\n답변2\n[[/ANSWER_2]]"
        self.assertIsNone(parse_multi(reply, 2, "ko")["parsed"])

    def test_small_pilot_contains_all_four_profiles(self):
        plans = edu.correction_plan(self.correction_fixture_rows(), pilot=True)
        self.assertEqual(len(plans), 4)
        self.assertEqual({(g[0]["meta"]["language"], 2 if len(g)>1 else 1) for _i,g in plans},
                         {("ko",1),("ko",2),("en",1),("en",2)})

    def test_correction_producer_and_consumer_directory_agree(self):
        self.assertEqual(edu.stage_directory("correct"), edu.BASE / "correction")
        self.assertEqual(edu.stage_directory("train-a"), edu.BASE / "a")

    def test_invalid_provenance_is_rejected_before_teacher_call(self):
        job = edu.build_correction_job([self.correction_fixture_rows()[0]])
        job["source_transform"] = "C_correction_v28"
        with self.assertRaisesRegex(ValueError, "unknown source transformation"):
            pipeline.validate_job_contract(job)

    def test_paid_reply_survives_wrapper_error(self):
        from scripts.p106b_teacher_wrapper import wrap_turns as real_wrap
        from scripts.p106b_gate_runtime import ToolFailure
        job = edu.build_correction_job([self.correction_fixture_rows()[0]])
        class Session:
            key = "fixture"
            calls = 0
            def count_prompt(self, *_args):
                return {"decision": "DIRECT"}
            def complete(self, *_args):
                self.calls += 1
                return {"choices": [{"finish_reason": "stop", "message": {"content":
                    "[[QUESTION]]\n질문\n[[/QUESTION]]\n[[ANSWER]]\n답변\n[[/ANSWER]]",
                    "reasoning_content": "RETAIN_RAW_ONLY"}}], "usage": {"completion_tokens": 7}}
        calls = []
        def wrap_then_fail(*args, **kwargs):
            calls.append(1)
            if len(calls) == 1:  # Pre-request contract validates normally.
                return real_wrap(*args, **kwargs)
            raise ValueError("injected post-response wrapper failure")
        with tempfile.TemporaryDirectory(prefix="p106b_raw_failure_fixture_") as directory:
            root = Path(directory)
            with patch.object(pipeline, "ROOT", root), \
                 patch("tokenizers.Tokenizer.from_file", return_value=SyntheticTokenizer()), \
                 patch.object(pipeline, "wrap_turns", side_effect=wrap_then_fail):
                writer = pipeline.CandidateWriter(root, {"fixture": True})
                session = Session()
                with self.assertRaises(ToolFailure):
                    writer.request(session, job, "failure1", 1)
                report = writer.close()
                self.assertEqual(session.calls, 1)
                self.assertEqual(report["raw_rows"], 1)
                self.assertEqual(report["canonical_rows"], 0)
                self.assertEqual(report["teacher_completion_tokens"], 7)
                raw = json.loads((root/"raw_000000.jsonl").read_text(encoding="utf-8"))
                self.assertEqual(raw["screen_status"], "PIPELINE_PROCESSING_ERROR")
                self.assertIn("RETAIN_RAW_ONLY", json.dumps(raw["teacher_raw_reply"]))

    def test_failed_upstream_is_not_accepted_as_complete(self):
        with tempfile.TemporaryDirectory(prefix="p106b_edu_fixture_") as directory:
            root = Path(directory)
            (root / "report.json").write_text(json.dumps({"schema": "fixture", "status": "COMPLETE"}), encoding="utf-8")
            (root / "failure.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(PrerequisiteHold):
                edu.read_report(root / "report.json", "fixture", "COMPLETE")

    def test_hash_changed_rows_rejected(self):
        with tempfile.TemporaryDirectory(prefix="p106b_edu_fixture_") as directory:
            root = Path(directory)
            writer = ShardWriter(root, "train")
            writer.append({"text": "fixture"})
            spec = writer.close(lineage={})
            self.assertEqual(edu.read_rows(root, "train", spec["concat_sha256"]), [{"text": "fixture"}])
            with self.assertRaises(ValueError):
                edu.read_rows(root, "train", "0"*64)

    def test_variants_and_translations_do_not_cross_split(self):
        rows = [normalize({"messages": [{"role": "user", "content": f"q{i//4} {i%2}"},
                {"role": "assistant", "content": "answer"}],
                "meta": {"source": "fixture", "source_id": str(i),
                         "language": "ko" if i%2 else "en", "parent_concept_id": f"{i//4:064X}"}})
                for i in range(80)]
        train, val = edu.group_split(rows)
        self.assertFalse({r["meta"]["parent_concept_id"] for r in train} & {r["meta"]["parent_concept_id"] for r in val})
        self.assertEqual(len(train)+len(val), 80)

    def test_parent_baseline_check_never_loads_model(self):
        with patch.object(edu, "load_student", side_effect=AssertionError("model loading forbidden")), \
             patch.object(edu, "arm_inputs", side_effect=PrerequisiteHold("fixture parent missing")):
            with self.assertRaises(PrerequisiteHold):
                edu.parent_baseline_check()

    def test_parent_lineages_and_conditional_retry_score(self):
        self.assertEqual(edu.ARMS["a"]["lineage"], "legacy")
        self.assertEqual(edu.ARMS["b"]["lineage"], "chat32")
        self.assertNotEqual(edu.ARMS["a"]["cache"], edu.ARMS["b"]["cache"])
        self.assertEqual(edu.ARMS["b"]["layers"], 14)
        self.assertFalse(edu.score_answer("arithmetic_en", "3 or 4"))
        self.assertFalse(edu.score_answer("format_en", '{"result":5,"extra":1}'))
        self.assertTrue(edu.score_answer("format_en", '{"result":5}'))

    def test_resource_negative_keeps_exit8_and_raw_record(self):
        from scripts.p106b_gate_runtime import GateNegative, disposition
        job = edu.build_correction_job([self.correction_fixture_rows()[0]])
        class Session:
            key = "fixture"
            def count_prompt(self, *_args):
                return {"decision": "DIRECT"}
            def complete(self, *_args):
                raise GateNegative("fixture resource margin")
        with tempfile.TemporaryDirectory(prefix="p106b_resource_fixture_") as directory:
            root = Path(directory)
            with patch.object(pipeline, "ROOT", root), \
                 patch("tokenizers.Tokenizer.from_file", return_value=SyntheticTokenizer()):
                writer = pipeline.CandidateWriter(root, {})
                with self.assertRaises(GateNegative) as caught:
                    writer.request(Session(), job, "resource1", 1)
                self.assertEqual(disposition(caught.exception)[1], 8)
                self.assertEqual(writer.close()["raw_rows"], 1)


if __name__ == "__main__":
    unittest.main()
