from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
import unittest
import json
import tempfile
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from scripts.diag_p106b_supported_production8h import (
    ROOT, VERSION, attach_visible_source, batches, limit_window, replay, scope,
    supported_wall_limit, require_pilot, execute, visible_source)


class SupportedProductionTests(unittest.TestCase):
    def test_eight_hours(self):
        self.assertEqual(limit_window(28800), 28800)
        with self.assertRaises(ValueError): limit_window(28801)

    def test_real_producer_uses_new_eight_hour_timer_only_in_scope(self):
        from scripts import diag_p106b_gemma_mtp_resume as old
        from scripts import diag_p106b_gemma_deficit_production as producer
        from scripts import diag_p106b_gemma_stream_fork as streaming
        original = producer.wall_limit
        with patch.object(old, "on_scope", return_value=nullcontext()), \
             patch.object(old, "pinned_ancestors", return_value=[(None, {"cursor": [1, 3]})]), \
             patch.object(streaming, "pinned_on_reports", return_value=[]), \
             patch.object(producer, "require_pilots", return_value={}):
            with scope(ROOT / "runs/eval/uncreated_supported8h_cpu_fixture") as (actual, _):
                self.assertIs(actual.wall_limit, supported_wall_limit)
                with patch("signal.getsignal", return_value=None), \
                     patch("signal.getitimer", return_value=(0.0, 0.0)), \
                     patch("signal.signal"), patch("signal.setitimer") as timer:
                    with actual.wall_limit(28799.5): pass
                    self.assertEqual(timer.call_args_list[0].args[1], 28799.5)
        self.assertIs(producer.wall_limit, original)

    def test_expired_authority(self):
        with self.assertRaises(ValueError): limit_window(28800, "2000-01-01T00:00:00Z")

    def test_failed_pilot_cannot_open_bulk_even_with_four_claimed_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / "batch_000000"
            directory.mkdir()
            (directory / "report.json").write_text(json.dumps(dict(input={},
                status="TOOL_FAILURE", returncode=9, accepted_groups=4,
                candidate_manifest={"rows": 4})), encoding="utf-8")
            with self.assertRaises(FileNotFoundError): require_pilot({}, Path(temp))

    def test_missing_pilot_shard_cannot_open_bulk(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / "batch_000000"
            directory.mkdir()
            (directory / "report.json").write_text(json.dumps(dict(input={},
                status="PRODUCTION_PAUSED", returncode=8, error_type="ProductionBudgetPause",
                accepted_groups=4, raw_manifest={"rows": 4}, candidate_manifest={"rows": 4})), encoding="utf-8")
            with self.assertRaises((ValueError, KeyError, FileNotFoundError)):
                require_pilot({}, Path(temp))

    def test_deadline_rechecked_after_scope_verification(self):
        from scripts import diag_p106b_supported_production8h as module
        memory = SimpleNamespace(snapshot=lambda: {})
        production = SimpleNamespace(production=lambda **kwargs: kwargs["max_wall_sec"])
        args = SimpleNamespace(mode="pilot", stop_file=None, max_wall_sec=600,
                               deadline_utc="2026-10-21T14:00:00Z")
        with patch.object(module, "scope", return_value=nullcontext((production, {}))), \
             patch.object(module, "limit_window", side_effect=[600, 90]) as limit, \
             patch("scripts.p106b_memory_stream.PersistentMemory", return_value=nullcontext(memory)), \
             patch("scripts.p106b_memory_stream.stream_session_scope", return_value=nullcontext()):
            self.assertEqual(execute(args), 90)
            self.assertEqual(limit.call_count, 2)

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
