#!/usr/bin/env python3
"""CPU regression for exact frozen evidence views; no new metric/semantic verdict."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import view_p106b_saved_answers as view
from scripts.p106b_shards import ShardWriter


class Tests(unittest.TestCase):
    def test_changed_report_refused(self):
        with tempfile.TemporaryDirectory(prefix="p106b_view_cpu_") as temp:
            root = Path(temp)
            folder = root / view.BASE / "a"
            folder.mkdir(parents=True)
            (folder / "report.json").write_text("{}", encoding="utf-8")
            with patch.object(view, "ROOT", root):
                with self.assertRaisesRegex(ValueError, "SHA changed"):
                    view.report("a")

    def test_shards_are_verified_not_just_listed(self):
        with tempfile.TemporaryDirectory(prefix="p106b_view_cpu_") as temp:
            folder = Path(temp)
            writer = ShardWriter(folder, "fixture")
            writer.append({"answer": "원형"})
            manifest = writer.close(lineage={})
            self.assertEqual(view.rows(folder, "fixture", manifest["concat_sha256"]), [{"answer": "원형"}])
            with self.assertRaises(ValueError):
                view.rows(folder, "fixture", "0"*64)

    def test_actual_question_variants_printed_not_only_ids(self):
        raw = [{"generation_id": "panel_low_C_000", "wall_sec": 1,
                "source": {"source_payload": {"question": "원천 질문"}},
                "teacher": {"teacher_reasoning_content": "PRIVATE_NOT_TARGET"}}]
        record = {"generation_id": raw[0]["generation_id"], "group": 0, "effort": "low",
                  "order": ["low"], "seed": 1, "wire_ok": True, "content_issues": []}
        canonical = [{"messages": [{"content": "생성 질문"}, {"content": answer}],
                      "meta": {"generation_id": raw[0]["generation_id"]+f"_a{i}", "answer_variant": i}}
                     for i, answer in enumerate(("첫 실제 답", "둘째 실제 답"), 1)]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            view.print_panel({"records": [record]}, raw, canonical)
        text = output.getvalue()
        for value in ("원천 질문", "생성 질문", "첫 실제 답", "둘째 실제 답", "입력 없음"):
            self.assertIn(value, text)
        self.assertNotIn("PRIVATE_NOT_TARGET", text)

    def test_all_saved_student_attempts_printed_separately(self):
        rows = [{"id": "fixture", "attempt": i, "prompt": f"질문 시도{i}",
                 "rendered_answer": f"실제답{i}", "narrow_rubric_pass": False, "generation": {}}
                for i in (1, 2, 3)]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            view.print_education({a: {l: rows for l in ("parent","student")} for a in ("a","b")})
        for i in (1, 2, 3):
            self.assertIn(f"실제답{i}", output.getvalue())


if __name__ == "__main__":
    unittest.main()
