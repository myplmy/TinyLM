#!/usr/bin/env python3
"""Synthetic CPU checks of the new statistics root receipt, with no model IO."""
from pathlib import Path
import copy
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from handoff.audit.oct26_research import run_native_stats as root


def candidate():
    s = root.stats
    return dict(schema=s.SCHEMA, returncode=9, candidate_returncode=0,
                candidate_status="PAIR_STATS_CPU_COMPLETE", source_identity=dict(sha256=root.SOURCE),
                models={k: {} for k in (*s.NEW_MODELS, *s.PEERS)},
                pairs={a + "__" + b: {} for a, b in s.PAIRS}, exact_tests=[{}] * 30,
                holm_family=dict(size=30, families=1), models_loaded=0, gpu_calls=0,
                model_weight_bodies_read=False, whole_parent_seconds=1.)


class RootClosure(unittest.TestCase):
    def test_actual_zero_closes_pending_leaf_without_rewriting_it(self):
        report = candidate()
        before = copy.deepcopy(report)
        root.validate_close(report, [dict(event="OBSERVATION", returncode=0)], 0, 2.)
        self.assertEqual(report, before)
        self.assertEqual(report["returncode"], 9)

    def test_nonzero_boolean_or_late_terminal_veto_cannot_close(self):
        for code in (8, 9, True):
            with self.subTest(code=code), self.assertRaises(ValueError):
                root.validate_close(candidate(), [dict(event="OBSERVATION", returncode=0)], code, 2.)
        with self.assertRaises(ValueError):
            root.validate_close(candidate(), [dict(event="OBSERVATION", returncode=0),
                                              dict(event="TERMINAL_VETO", returncode=9)], 0, 2.)

    def test_missing_fulls_hold_without_reading_model_or_writing_inputs(self):
        with tempfile.TemporaryDirectory(prefix="native_stats_root_", dir="/tmp") as name:
            directory = Path(name)
            with patch.object(root, "ROOT", directory), patch.object(root, "BASE", directory), \
                 patch.object(root.stats, "source_identity", return_value=dict(sha256=root.SOURCE)):
                with self.assertRaises(root.stats.Hold):
                    root.prepare(allow_write=True)
            self.assertEqual(list(directory.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
