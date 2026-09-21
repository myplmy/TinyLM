#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from recover_bench_tsv_from_items import summarize


class RecoverBenchTsvTests(unittest.TestCase):
    def test_mc_rows_reconstruct_three_metrics(self) -> None:
        rows = [
            {"id": "x", "model": "m", "task": "t", "gold": 1,
             "pred_internal": 1, "pred_internal_norm": 0,
             "mean_nll": [3.0, 1.0]},
            {"id": "y", "model": "m", "task": "t", "gold": 0,
             "pred_internal": 1, "pred_internal_norm": 0,
             "mean_nll": [2.0, 4.0]},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "items.jsonl"
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            result = summarize(path, seed=99, pmi=True)
        metrics = {row["metric"]: row for row in result}
        self.assertEqual(metrics["acc"]["value"], 0.5)
        self.assertEqual(metrics["acc_norm"]["value"], 0.5)
        self.assertEqual(metrics["gold_ce"]["value"], 1.5)
        self.assertEqual(metrics["acc"]["n"], 2)
        self.assertTrue(metrics["acc"]["pmi"])

    def test_duplicate_identity_is_rejected(self) -> None:
        row = {"id": "x", "model": "m", "task": "t", "gold": 0,
               "pred_internal": 0, "pred_internal_norm": 0, "mean_nll": [1.0]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "items.jsonl"
            path.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate item"):
                summarize(path, seed=99, pmi=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
