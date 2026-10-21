from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
import unittest
import json
import tempfile
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
from scripts.diag_p106b_supported_production8h import (
    VERSION, attach_visible_source, batches, limit_window, replay, visible_source)


class SupportedProductionTests(unittest.TestCase):
    def test_eight_hours(self):
        self.assertEqual(limit_window(28800), 28800)
        with self.assertRaises(ValueError): limit_window(28801)

    def test_expired_authority(self):
        with self.assertRaises(ValueError): limit_window(28800, "2000-01-01T00:00:00Z")

    def test_deadline_caps_window(self):
        end = (datetime.now(timezone.utc) + timedelta(seconds=300)).isoformat()
        self.assertLessEqual(limit_window(28800, end), 240)

    def test_visible_support_and_original_immutable(self):
        source = {"messages": [{"role": "user", "content": "which building?"},
                  {"role": "assistant", "content": "The2013 building is the education center."}]}
        original = {"messages": [{"role": "user", "content": [{"type": "text", "text": "What opened2013?"}]},
                               {"role": "assistant", "content": [{"type": "text", "text": "education center"}]}],
                    "meta": {"parent_concept_id": "original-root", "source_split": "val"}}
        row = attach_visible_source(original, source, "en")
        self.assertIn("education center", row["messages"][0]["content"][0]["text"])
        self.assertEqual(row["meta"]["parent_concept_id"], "original-root")
        self.assertEqual(row["meta"]["source_split"], "val")
        self.assertNotIn("REFERENCE", original["messages"][0]["content"][0]["text"])
        self.assertEqual(row["messages"][1], original["messages"][1])

    def test_no_semantic_blacklist(self):
        self.assertIn("과장증", visible_source({"messages": [{"role": "user", "content": "과장증"}]}, "ko"))

    def test_partial_batch_is_never_silently_replayed(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp)
            (destination / "batch_000000").mkdir()
            with self.assertRaises(FileExistsError): list(batches(None, destination))

    def test_changed_contract_refuses_resume(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / "batch_000000"
            directory.mkdir()
            (directory / "report.json").write_text(json.dumps({"input": {
                "visible_source_contract": "OLD"}}), encoding="utf-8")
            with self.assertRaises(ValueError): list(batches(None, Path(temp)))

    def test_resume_counts_base_and_new_fork_not_old_teacher(self):
        class Quotas:
            def __init__(self, _): self.tokens = {"train:en": 0}
            def admit(self, row, **kwargs):
                self.tokens["train:en"] += row["tokens"]
                return row
        control = SimpleNamespace(Quotas=Quotas, base_rows=lambda _: [{"tokens": 7}])
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp)
            directory = destination / "batch_000000"
            directory.mkdir()
            (directory / "report.json").write_text(json.dumps({"input": {
                "visible_source_contract": VERSION}, "nonpadding_tokens": {"train:en": 7},
                "cursor": [1, 900]}), encoding="utf-8")
            state, cursor, count = replay(control, None, {}, destination, [1, 800])
            self.assertEqual((state.tokens, cursor, count), ({"train:en": 7}, (1, 900), 1))


if __name__ == "__main__": unittest.main()
