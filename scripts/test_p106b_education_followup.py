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


class Tests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
